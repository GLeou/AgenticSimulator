package com.thesis.simulator.agentic.infra;

import com.thesis.simulator.agentic.config.AgenticConfig.AgentDefinition;
import com.thesis.simulator.agentic.config.AgenticConfig.InfraNode;

import java.util.*;

/**
 * Stateful infrastructure service that models the physical hardware layer.
 * Ported from v1's Simulation.java: CPU time-slicing, pod queuing, and contention.
 *
 * When v2's agent processes a step, this layer computes the infrastructure cost
 * (CPU compute time with contention + queue wait) based on the current system state.
 *
 * State persists across calls: jobs accumulate, pods get loaded, CPU speeds change.
 */
public class InfrastructureLayer {

    // --- Inner classes (simplified from v1's Simulation.java) ---

    static class Pod {
        final int id;
        final String agentId;
        final int nodeId;
        int activeRequests = 0;
        final int maxConcurrency;
        final Queue<QueuedJob> requestQueue = new LinkedList<>();

        Pod(int id, String agentId, int nodeId, int maxConcurrency) {
            this.id = id;
            this.agentId = agentId;
            this.nodeId = nodeId;
            this.maxConcurrency = maxConcurrency;
        }

        boolean hasCapacity() {
            return activeRequests < maxConcurrency;
        }
    }

    static class ActiveJob {
        final String jobId;
        final Pod pod;
        double lastUpdateTime;
        double remainingInstructions;
        double currentSpeed; // instructions per second

        ActiveJob(String jobId, Pod pod, double nowMs, double instructions) {
            this.jobId = jobId;
            this.pod = pod;
            this.lastUpdateTime = nowMs;
            this.remainingInstructions = instructions;
            this.currentSpeed = 0.0;
        }
    }

    record QueuedJob(String jobId, double arrivalMs, long instructions) {}

    // --- State ---

    private final Map<String, List<Pod>> agentToPods = new HashMap<>();
    private final Map<Integer, List<ActiveJob>> nodeActiveJobs = new HashMap<>();
    private final Map<Integer, InfraNode> nodeMap = new HashMap<>();
    private final Map<String, ActiveJob> jobIndex = new HashMap<>();
    private final Map<String, Integer> roundRobinCounters = new HashMap<>();

    // --- Constructor: deploy pods round-robin (same as v1 lines 138-155) ---

    public InfrastructureLayer(List<InfraNode> nodes, Map<String, AgentDefinition> agents) {
        // Build node map
        for (InfraNode node : nodes) {
            nodeMap.put(node.nodeId(), node);
            nodeActiveJobs.put(node.nodeId(), new ArrayList<>());
        }

        // Deploy pods for each agent, round-robin across nodes
        int podIdCounter = 1;
        int nodeIndex = 0;
        for (var entry : agents.entrySet()) {
            String agentId = entry.getKey();
            AgentDefinition def = entry.getValue();
            List<Pod> pods = new ArrayList<>();

            for (int i = 0; i < def.replicas(); i++) {
                InfraNode assignedNode = nodes.get(nodeIndex % nodes.size());
                Pod pod = new Pod(podIdCounter++, agentId, assignedNode.nodeId(), def.maxConcurrency());
                pods.add(pod);
                nodeIndex++;
            }

            agentToPods.put(agentId, pods);
            roundRobinCounters.put(agentId, 0);
        }
    }

    // --- Public API ---

    /**
     * Submit a job and get the estimated infrastructure latency.
     * Mutates state: adds job to active list or queue.
     */
    public InfraResult submitJob(String agentId, String jobId, double nowMs, long instructions) {
        // 1. Load balance: pick pod via round-robin
        List<Pod> pods = agentToPods.get(agentId);
        int counter = roundRobinCounters.get(agentId);
        Pod chosenPod = pods.get(counter % pods.size());
        roundRobinCounters.put(agentId, counter + 1);

        InfraNode node = nodeMap.get(chosenPod.nodeId);
        List<ActiveJob> jobsOnNode = nodeActiveJobs.get(node.nodeId());

        // 2. Update progress of existing jobs to current time
        updateProgress(jobsOnNode, nowMs);

        // 3. Check capacity
        if (!chosenPod.hasCapacity()) {
            // Pod is full — estimate queue wait
            double queueWaitMs = estimateQueueWait(chosenPod, node, jobsOnNode, nowMs);

            // Enqueue the job
            chosenPod.requestQueue.add(new QueuedJob(jobId, nowMs, instructions));

            // Estimate compute time (after queue wait, state may have changed,
            // but we use current contention + 1 as approximation)
            int futureJobCount = jobsOnNode.size() + 1;
            double speedPerJob = ((double) node.cores() / futureJobCount) * node.frequencyHz();
            double computeMs = (instructions / speedPerJob) * 1000.0;

            // Store a placeholder so releaseJob can find it later
            ActiveJob placeholder = new ActiveJob(jobId, chosenPod, nowMs + queueWaitMs, instructions);
            placeholder.currentSpeed = speedPerJob;
            jobIndex.put(jobId, placeholder);

            return new InfraResult(queueWaitMs + computeMs, queueWaitMs, computeMs);
        }

        // 4. Pod has capacity — add job immediately
        chosenPod.activeRequests++;
        ActiveJob newJob = new ActiveJob(jobId, chosenPod, nowMs, instructions);
        jobsOnNode.add(newJob);
        jobIndex.put(jobId, newJob);

        // 5. Recalculate speeds for all jobs on this node (time-slicing)
        rescheduleNode(node, jobsOnNode);

        // 6. Compute estimated time for this job
        double computeMs = (instructions / newJob.currentSpeed) * 1000.0;

        return new InfraResult(computeMs, 0.0, computeMs);
    }

    /**
     * Release resources when the infrastructure compute is done.
     * Frees pod slot, dequeues waiting jobs, recalculates speeds.
     */
    public void releaseJob(String jobId, double nowMs) {
        ActiveJob job = jobIndex.remove(jobId);
        if (job == null) return;

        InfraNode node = nodeMap.get(job.pod.nodeId);
        List<ActiveJob> jobsOnNode = nodeActiveJobs.get(node.nodeId());

        // Update progress of all jobs
        updateProgress(jobsOnNode, nowMs);

        // Remove this job from active list
        jobsOnNode.removeIf(j -> j.jobId.equals(jobId));

        // Free pod thread
        job.pod.activeRequests--;

        // Try to dequeue waiting jobs on this pod
        if (!job.pod.requestQueue.isEmpty() && job.pod.hasCapacity()) {
            QueuedJob queued = job.pod.requestQueue.poll();
            job.pod.activeRequests++;

            ActiveJob newJob = new ActiveJob(queued.jobId(), job.pod, nowMs, queued.instructions());
            jobsOnNode.add(newJob);
            jobIndex.put(queued.jobId(), newJob);
        }

        // Recalculate speeds (remaining jobs speed up)
        if (!jobsOnNode.isEmpty()) {
            rescheduleNode(node, jobsOnNode);
        }
    }

    // --- Internal math (ported from v1's Simulation.java) ---

    /**
     * Update remainingInstructions for all running jobs based on elapsed time.
     * Same as v1 Simulation.java lines 363-372.
     */
    private void updateProgress(List<ActiveJob> jobs, double nowMs) {
        for (ActiveJob job : jobs) {
            double durationMs = nowMs - job.lastUpdateTime;
            if (durationMs > 0 && job.currentSpeed > 0) {
                double durationSec = durationMs / 1000.0;
                double workDone = durationSec * job.currentSpeed;
                job.remainingInstructions = Math.max(0, job.remainingInstructions - workDone);
                job.lastUpdateTime = nowMs;
            }
        }
    }

    /**
     * Recalculate CPU speed per job using time-slicing.
     * Same as v1 Simulation.java lines 375-391.
     * Formula: speedPerJob = (cores / activeJobCount) * frequency
     */
    private void rescheduleNode(InfraNode node, List<ActiveJob> jobs) {
        if (jobs.isEmpty()) return;
        double coresPerJob = (double) node.cores() / jobs.size();
        double speedPerJob = coresPerJob * node.frequencyHz();
        for (ActiveJob job : jobs) {
            job.currentSpeed = speedPerJob;
        }
    }

    /**
     * Estimate how long a new job would wait in queue.
     * Finds the earliest-finishing active job on this pod's node.
     */
    private double estimateQueueWait(Pod pod, InfraNode node, List<ActiveJob> jobsOnNode, double nowMs) {
        // Find the job on this pod that will finish soonest
        double earliestFinishMs = Double.MAX_VALUE;
        for (ActiveJob job : jobsOnNode) {
            if (job.pod.id == pod.id && job.currentSpeed > 0) {
                double timeToFinishSec = job.remainingInstructions / job.currentSpeed;
                double finishMs = job.lastUpdateTime + (timeToFinishSec * 1000.0);
                earliestFinishMs = Math.min(earliestFinishMs, finishMs);
            }
        }

        if (earliestFinishMs == Double.MAX_VALUE) return 0.0;

        // Queue wait = (earliest finish - now) * position in queue
        double baseWait = Math.max(0, earliestFinishMs - nowMs);
        int queuePosition = pod.requestQueue.size() + 1;
        return baseWait * queuePosition;
    }
}
