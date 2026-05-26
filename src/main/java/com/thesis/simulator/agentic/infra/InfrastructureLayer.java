package com.thesis.simulator.agentic.infra;

import com.thesis.simulator.agentic.config.AgenticConfig.AgentDefinition;
import com.thesis.simulator.agentic.config.AgenticConfig.InfraNode;

import java.util.*;

/**
 * Stateful infrastructure layer that models the physical hardware for the agentic simulation.
 * <p>
 * Computes infrastructure latency (CPU time with contention + queue wait) for each
 * agent step. Maintains persistent state across calls: active jobs accumulate on nodes,
 * pod thread pools fill and drain, and CPU speeds are recalculated via time-slicing.
 * <p>
 * Derived from v1's {@link com.thesis.simulator.Simulation} pod/node model.
 */
public class InfrastructureLayer {

    /** A pod replica with a bounded thread pool and request queue. */
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

    /** An in-flight computation bound to a pod, tracking CPU progress. */
    static class ActiveJob {
        final String jobId;
        final Pod pod;
        double lastUpdateTime;
        double remainingInstructions;
        double currentSpeed;  // instructions per second; recalculated on contention changes

        ActiveJob(String jobId, Pod pod, double nowMs, double instructions) {
            this.jobId = jobId;
            this.pod = pod;
            this.lastUpdateTime = nowMs;
            this.remainingInstructions = instructions;
            this.currentSpeed = 0.0;
        }
    }

    /** A job waiting in a pod's request queue. */
    record QueuedJob(String jobId, double arrivalMs, long instructions) {}


    private final Map<String, List<Pod>> agentToPods = new HashMap<>();
    private final Map<Integer, List<ActiveJob>> nodeActiveJobs = new HashMap<>();
    private final Map<Integer, InfraNode> nodeMap = new HashMap<>();
    private final Map<String, ActiveJob> jobIndex = new HashMap<>();
    private final Map<String, Integer> roundRobinCounters = new HashMap<>();

    /** Deploys pod replicas for each agent, assigned round-robin across infrastructure nodes. */
    public InfrastructureLayer(List<InfraNode> nodes, Map<String, AgentDefinition> agents) {
        for (InfraNode node : nodes) {
            nodeMap.put(node.nodeId(), node);
            nodeActiveJobs.put(node.nodeId(), new ArrayList<>());
        }

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

    /**
     * Submits a compute job and returns the estimated infrastructure latency.
     * Mutates internal state: the job is either assigned to an active CPU slot
     * or enqueued if the selected pod is at capacity.
     */
    public InfraResult submitJob(String agentId, String jobId, double nowMs, long instructions) {
        // Select pod via round-robin load balancing
        List<Pod> pods = agentToPods.get(agentId);
        int counter = roundRobinCounters.get(agentId);
        Pod chosenPod = pods.get(counter % pods.size());
        roundRobinCounters.put(agentId, counter + 1);

        InfraNode node = nodeMap.get(chosenPod.nodeId);
        List<ActiveJob> jobsOnNode = nodeActiveJobs.get(node.nodeId());

        updateProgress(jobsOnNode, nowMs);

        if (!chosenPod.hasCapacity()) {
            // Pod at capacity: estimate queue wait and enqueue
            double queueWaitMs = estimateQueueWait(chosenPod, node, jobsOnNode, nowMs);
            chosenPod.requestQueue.add(new QueuedJob(jobId, nowMs, instructions));

            // Approximate compute time using projected contention (current + 1)
            int futureJobCount = jobsOnNode.size() + 1;
            double speedPerJob = ((double) node.cores() / futureJobCount) * node.frequencyHz();
            double computeMs = (instructions / speedPerJob) * 1000.0;

            ActiveJob placeholder = new ActiveJob(jobId, chosenPod, nowMs + queueWaitMs, instructions);
            placeholder.currentSpeed = speedPerJob;
            jobIndex.put(jobId, placeholder);

            return new InfraResult(queueWaitMs + computeMs, queueWaitMs, computeMs);
        }

        // Pod has capacity: schedule immediately
        chosenPod.activeRequests++;
        ActiveJob newJob = new ActiveJob(jobId, chosenPod, nowMs, instructions);
        jobsOnNode.add(newJob);
        jobIndex.put(jobId, newJob);

        rescheduleNode(node, jobsOnNode);
        double computeMs = (instructions / newJob.currentSpeed) * 1000.0;

        return new InfraResult(computeMs, 0.0, computeMs);
    }

    /**
     * Releases resources held by a completed job. Frees the pod's thread slot,
     * dequeues the next waiting job (if any), and recalculates CPU speeds.
     */
    public void releaseJob(String jobId, double nowMs) {
        ActiveJob job = jobIndex.remove(jobId);
        if (job == null) return;

        InfraNode node = nodeMap.get(job.pod.nodeId);
        List<ActiveJob> jobsOnNode = nodeActiveJobs.get(node.nodeId());

        updateProgress(jobsOnNode, nowMs);
        jobsOnNode.removeIf(j -> j.jobId.equals(jobId));
        job.pod.activeRequests--;

        if (!job.pod.requestQueue.isEmpty() && job.pod.hasCapacity()) {
            QueuedJob queued = job.pod.requestQueue.poll();
            job.pod.activeRequests++;

            ActiveJob newJob = new ActiveJob(queued.jobId(), job.pod, nowMs, queued.instructions());
            jobsOnNode.add(newJob);
            jobIndex.put(queued.jobId(), newJob);
        }

        if (!jobsOnNode.isEmpty()) {
            rescheduleNode(node, jobsOnNode);
        }
    }

    // ── Internal Computation ──────────────────────────────────────

    /** Updates remaining instructions for all active jobs based on elapsed time. */
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
     * Recalculates time-sliced CPU speed for all jobs on a node.
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
     * Estimates queue wait time by finding the earliest-finishing active job
     * on this pod and scaling by the current queue position.
     */
    private double estimateQueueWait(Pod pod, InfraNode node, List<ActiveJob> jobsOnNode, double nowMs) {
        double earliestFinishMs = Double.MAX_VALUE;
        for (ActiveJob job : jobsOnNode) {
            if (job.pod.id == pod.id && job.currentSpeed > 0) {
                double timeToFinishSec = job.remainingInstructions / job.currentSpeed;
                double finishMs = job.lastUpdateTime + (timeToFinishSec * 1000.0);
                earliestFinishMs = Math.min(earliestFinishMs, finishMs);
            }
        }

        if (earliestFinishMs == Double.MAX_VALUE) return 0.0;

        double baseWait = Math.max(0, earliestFinishMs - nowMs);
        int queuePosition = pod.requestQueue.size() + 1;
        return baseWait * queuePosition;
    }
}
