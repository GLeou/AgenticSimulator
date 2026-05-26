package com.thesis.simulator;

import com.thesis.simulator.Application.ServiceCall;
import com.thesis.simulator.Application.Services;
import com.thesis.simulator.Infrastructure.ComputingNodes;

import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.*;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * Discrete-event simulator for Kubernetes microservice deployments.
 * <p>
 * Models concurrent request processing with CPU time-slicing, per-pod thread pool
 * limits, request queuing, and inter-service network latency. Produces execution
 * traces (Gantt chart data) and queue-depth logs for post-simulation analysis.
 */
public class Simulation {

    // ── Inner Classes ──────────────────────────────────────────────

    /** Records the queue depth of a specific pod at a given simulation time. */
    @lombok.Data
    @lombok.AllArgsConstructor
    static class QueueLog {
        private double time;
        private String podName;
        private int size;

        public String toCSV() {
            return String.format(Locale.US, "%.4f,%s,%d", time, podName, size);
        }
    }

    /** A single replica (pod) of a service, with a bounded thread pool and request queue. */
    @lombok.Getter
    @lombok.Setter
    @lombok.RequiredArgsConstructor
    static class Pod {
        private final int id;
        private final int serviceId;
        private final int nodeId;

        private int activeRequests = 0;
        private int maxConcurrency = 10;
        private Queue<RequestState> requestQueue = new LinkedList<>();

        public boolean hasCapacity() {
            return activeRequests < maxConcurrency;
        }
    }

    /** Tracks the state of a single request as it traverses the service chain. */
    static class RequestState {
        int requestId;
        double arrivalTime;
        Services currentService;
        double currentServiceInstructionsRemaining;

        double queueEntryTime = 0.0;
        double startTime = -1;
        double endTime = -1;

        public RequestState(int requestId, double arrivalTime, Services startService) {
            this.requestId = requestId;
            this.arrivalTime = arrivalTime;
            this.currentService = startService;
            this.currentServiceInstructionsRemaining = startService.getTotalInstructions();
        }
    }

    /** An in-flight computation: binds a request to a pod and tracks CPU progress. */
    static class ActiveJob {
        RequestState request;
        Pod pod;
        double lastUpdateTime;
        double remainingInstructions;
        double currentSpeed;  // instructions per second; recalculated on contention changes

        public ActiveJob(RequestState request, Pod pod, double now, double totalInstructions) {
            this.request = request;
            this.pod = pod;
            this.lastUpdateTime = now;
            this.remainingInstructions = totalInstructions;
        }
    }

    // ── Event System ────────────────────────────────────────────────

    enum EventType { ARRIVAL, POD_FINISH, NETWORK_FINISH }

    /** A scheduled simulation event, ordered by time for the priority queue. */
    @lombok.Data
    @lombok.AllArgsConstructor
    static class SimEvent implements Comparable<SimEvent> {
        private double time;
        private EventType type;
        private RequestState request;
        private Pod pod;

        @Override
        public int compareTo(SimEvent other) {
            return Double.compare(this.time, other.time);
        }
    }

    // ── Simulation Entry Point ─────────────────────────────────────

    /**
     * Runs the full simulation for the given duration {@code T} (in seconds).
     * Deploys pods, generates Poisson traffic, processes the event loop,
     * and exports trace and queue-depth CSVs.
     */
    public void runSimulation(List<ComputingNodes> nodes, List<Services> services, List<ServiceCall> calls, double T) {
        System.out.println("--- Starting Kubernetes Simulation (Concurrent + Queue Logging) ---");

        // Build lookup maps for O(1) access
        Map<Integer, ComputingNodes> nodeMap = nodes.stream().collect(Collectors.toMap(ComputingNodes::getNode_id, Function.identity()));
        Map<Integer, Services> serviceMap = services.stream().collect(Collectors.toMap(Services::getService_id, Function.identity()));
        Map<Integer, ServiceCall> callMap = calls.stream().collect(Collectors.toMap(ServiceCall::getCallerId, Function.identity()));

        // Deploy pods: 2 replicas per service, assigned round-robin across nodes
        List<Pod> allPods = new ArrayList<>();
        Map<Integer, List<Pod>> serviceToPods = new HashMap<>();
        int podIdCounter = 1;
        int nodeIndex = 0;

        int podsPerService = 2;
        for (Services service : services) {
            List<Pod> servicePods = new ArrayList<>();
            for (int i = 0; i < podsPerService; i++) {
                ComputingNodes assignedNode = nodes.get(nodeIndex % nodes.size());
                Pod pod = new Pod(podIdCounter++, service.getService_id(), assignedNode.getNode_id());
                allPods.add(pod);
                servicePods.add(servicePods.size(), pod);
                serviceToPods.computeIfAbsent(service.getService_id(), k -> new ArrayList<>()).add(pod);

                System.out.println("Deployed Pod " + pod.id + " (Service " + service.getService_id() + ") on Node " + assignedNode.getNode_id());
                nodeIndex++;
            }
        }

        // Initialize state containers
        PriorityQueue<SimEvent> eventQueue = new PriorityQueue<>();
        List<TraceEvent> traceEvents = new ArrayList<>();
        List<RequestResult> results = new ArrayList<>();
        List<QueueLog> queueLogs = new ArrayList<>();

        Map<Integer, List<ActiveJob>> nodeActiveJobs = new HashMap<>();
        for (ComputingNodes n : nodes) nodeActiveJobs.put(n.getNode_id(), new ArrayList<>());

        // Identify the entry-point service (the service that is never a callee)
        Set<Integer> calleeIds = calls.stream().map(ServiceCall::getCalleeId).collect(Collectors.toSet());
        Services startService = services.stream()
                .filter(s -> !calleeIds.contains(s.getService_id()))
                .findFirst()
                .orElse(services.get(0));

        // Generate Poisson-distributed arrival events over [0, T]
        Random random = new Random(42);
        double currentArrival = 0.0;
        int reqId = 1;
        double lambda = 0.5; // arrival rate (requests/second)

        while (currentArrival <= T) {
            RequestState req = new RequestState(reqId++, currentArrival, startService);
            eventQueue.add(new SimEvent(currentArrival, EventType.ARRIVAL, req, null));

            double u = 1.0 - random.nextDouble();
            double randomGap = -Math.log(u) / lambda;
            currentArrival += randomGap;
        }

        // Main event loop: process events in chronological order
        while (!eventQueue.isEmpty()) {
            SimEvent currentEvent = eventQueue.poll();
            double now = currentEvent.time;

            if (now > T && currentEvent.type == EventType.ARRIVAL) break;

            switch (currentEvent.type) {
                case ARRIVAL:
                case NETWORK_FINISH:
                    handleArrival(now, currentEvent.request, serviceToPods, nodeActiveJobs, eventQueue, nodeMap, traceEvents, queueLogs);
                    break;

                case POD_FINISH:
                    handlePodFinish(now, currentEvent, nodeActiveJobs, eventQueue, callMap, serviceMap, nodeMap, traceEvents, serviceToPods, results, queueLogs);
                    break;
            }
        }

        // Export results
        exportToCSV(traceEvents, "simulation_trace_k8s.csv");
        exportQueueLogs(queueLogs, "queue_trace.csv");
    }

    // ── Event Handlers ────────────────────────────────────────────

    /**
     * Handles a request arrival at a service. Selects a pod via round-robin
     * load balancing, enqueues the request, and attempts immediate scheduling.
     */
    private void handleArrival(double now, RequestState req, Map<Integer, List<Pod>> serviceToPods,
                               Map<Integer, List<ActiveJob>> nodeActiveJobs, PriorityQueue<SimEvent> eventQueue,
                               Map<Integer, ComputingNodes> nodeMap, List<TraceEvent> traceEvents,
                               List<QueueLog> queueLogs) {

        List<Pod> pods = serviceToPods.get(req.currentService.getService_id());
        Pod chosenPod = pods.get(req.requestId % pods.size());

        chosenPod.requestQueue.add(req);
        req.queueEntryTime = now;
        queueLogs.add(new QueueLog(now, "S" + chosenPod.serviceId + " (Pod " + chosenPod.id + ")", chosenPod.requestQueue.size()));

        trySchedulePod(now, chosenPod, nodeActiveJobs, eventQueue, nodeMap, traceEvents, queueLogs);
    }

    /**
     * Attempts to dequeue a request from the pod and assign it to the node's CPU.
     * If the pod has available thread capacity, the request is scheduled immediately;
     * otherwise it remains queued. Recurses to drain multiple waiting requests.
     */
    private void trySchedulePod(double now, Pod pod, Map<Integer, List<ActiveJob>> nodeActiveJobs,
                                PriorityQueue<SimEvent> eventQueue, Map<Integer, ComputingNodes> nodeMap,
                                List<TraceEvent> traceEvents, List<QueueLog> queueLogs) {

        if (!pod.hasCapacity() || pod.requestQueue.isEmpty()) return;

        RequestState req = pod.requestQueue.poll();

        if (now > req.queueEntryTime) {
            traceEvents.add(new TraceEvent(req.requestId, "Wait", "Wait", req.queueEntryTime, now));
        }
        queueLogs.add(new QueueLog(now, "S" + pod.serviceId + " (Pod " + pod.id + ")", pod.requestQueue.size()));

        pod.activeRequests++;
        if (req.startTime < 0) req.startTime = now;

        ComputingNodes node = nodeMap.get(pod.nodeId);
        List<ActiveJob> jobsOnNode = nodeActiveJobs.get(node.getNode_id());

        // Snapshot existing job progress before adding a new job (contention changes speed)
        updateProgress(jobsOnNode, now);

        ActiveJob newJob = new ActiveJob(req, pod, now, req.currentServiceInstructionsRemaining);
        jobsOnNode.add(newJob);

        // Recalculate time-sliced speeds and predicted finish times
        rescheduleNode(now, node, jobsOnNode, eventQueue);

        if (pod.hasCapacity() && !pod.requestQueue.isEmpty()) {
            trySchedulePod(now, pod, nodeActiveJobs, eventQueue, nodeMap, traceEvents, queueLogs);
        }
    }

    /**
     * Handles a pod-finish event. Validates that the job has actually completed
     * (filtering stale predictions), frees the thread slot, and either routes
     * the request to the next service via network transfer or marks it as complete.
     */
    private void handlePodFinish(double now, SimEvent event, Map<Integer, List<ActiveJob>> nodeActiveJobs,
                                 PriorityQueue<SimEvent> eventQueue, Map<Integer, ServiceCall> callMap,
                                 Map<Integer, Services> serviceMap, Map<Integer, ComputingNodes> nodeMap,
                                 List<TraceEvent> traceEvents, Map<Integer, List<Pod>> serviceToPods,
                                 List<RequestResult> results, List<QueueLog> queueLogs) {

        ComputingNodes node = nodeMap.get(event.pod.nodeId);
        List<ActiveJob> jobsOnNode = nodeActiveJobs.get(node.getNode_id());

        updateProgress(jobsOnNode, now);

        // Validate completion; stale events are discarded (tolerance for floating-point error)
        ActiveJob job = null;
        Iterator<ActiveJob> it = jobsOnNode.iterator();
        while(it.hasNext()){
            ActiveJob j = it.next();
            if(j.request.requestId == event.request.requestId && j.pod.id == event.pod.id) {
                if (j.remainingInstructions <= 1.0) {
                    job = j;
                    it.remove();
                }
                break;
            }
        }

        if (job == null) return;

        traceEvents.add(new TraceEvent(job.request.requestId, "Computation",
                "S" + job.request.currentService.getService_id() + " (Pod " + job.pod.id + ")",
                job.request.startTime, now));

        job.pod.activeRequests--;

        // Dequeue next waiting request for this pod
        trySchedulePod(now, job.pod, nodeActiveJobs, eventQueue, nodeMap, traceEvents, queueLogs);

        // Recalculate speeds for remaining jobs on this node
        rescheduleNode(now, node, jobsOnNode, eventQueue);

        // Route to downstream service or mark request as complete
        ServiceCall call = callMap.get(job.request.currentService.getService_id());

        if (call != null) {
            double networkTime = (double) call.getBytes() / node.getBandwidth();
            traceEvents.add(new TraceEvent(job.request.requestId, "Network", "Net", now, now + networkTime));

            job.request.currentService = serviceMap.get(call.getCalleeId());
            job.request.currentServiceInstructionsRemaining = job.request.currentService.getTotalInstructions();
            job.request.startTime = -1;

            eventQueue.add(new SimEvent(now + networkTime, EventType.NETWORK_FINISH, job.request, null));
        } else {
            job.request.endTime = now;
            results.add(new RequestResult(job.request.requestId, job.request.arrivalTime, job.request.startTime, now, now - job.request.arrivalTime));
            System.out.println("Req " + job.request.requestId + " Finished. Latency: " + (now - job.request.arrivalTime));
        }
    }

    // ── Helper Methods ────────────────────────────────────────────

    /** Updates remaining instructions for all active jobs based on elapsed time. */
    private void updateProgress(List<ActiveJob> jobs, double now) {
        for (ActiveJob job : jobs) {
            double duration = now - job.lastUpdateTime;
            if (duration > 0) {
                double workDone = duration * job.currentSpeed;
                job.remainingInstructions -= workDone;
                job.lastUpdateTime = now;
            }
        }
    }

    /**
     * Recalculates time-sliced CPU speed for all jobs on a node and schedules
     * predicted finish events. Stale predictions are filtered in {@link #handlePodFinish}.
     * <p>
     * Speed per job = (cores / active_jobs) * frequency
     */
    private void rescheduleNode(double now, ComputingNodes node, List<ActiveJob> jobs, PriorityQueue<SimEvent> eventQueue) {
        if (jobs.isEmpty()) return;

        double coresPerJob =  (node.getCores() / jobs.size());
        double speedPerJob = coresPerJob * node.getFrequency();

        for (ActiveJob job : jobs) {
            job.currentSpeed = speedPerJob;
            double timeToFinish = job.remainingInstructions / speedPerJob;
            eventQueue.add(new SimEvent(now + timeToFinish, EventType.POD_FINISH, job.request, job.pod));
        }
    }

    private void exportToCSV(List<TraceEvent> events, String filename) {
        try (PrintWriter writer = new PrintWriter(new FileWriter(filename))) {
            writer.println("RequestId,Type,Name,StartTime,EndTime");
            for (TraceEvent event : events) {
                writer.println(event.toCSV());
            }
            System.out.println("Trace saved to " + filename);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    private void exportQueueLogs(List<QueueLog> logs, String filename) {
        try (PrintWriter writer = new PrintWriter(new FileWriter(filename))) {
            writer.println("Time,PodName,Size");
            for (QueueLog log : logs) {
                writer.println(log.toCSV());
            }
            System.out.println("Queue logs saved to " + filename);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}