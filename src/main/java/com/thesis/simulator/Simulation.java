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
 * DISCRETE EVENT SIMULATOR (Concurrent Version)
 * * Features:
 * 1. Event-Driven: Jumps from event to event (Arrival -> Start -> Finish).
 * 2. Concurrency: Multiple requests run on the CPU simultaneously (Time Slicing).
 * 3. Thread Pools: Pods have a limit (50 threads). If full, requests wait in a queue.
 * 4. Metrics: Logs Execution Time (Gantt) and Queue Sizes over time.
 */
public class Simulation {

    // ==========================================
    // 1. INNER CLASSES (The "Actors" of the System)
    // ==========================================

    // Simple container to record "At Time X, Pod Y had Z people waiting"
    static class QueueLog {
        double time;
        String podName;
        int size;

        public QueueLog(double time, String podName, int size) {
            this.time = time;
            this.podName = podName;
            this.size = size;
        }

        public String toCSV() {
            // US Locale ensures dot (.) is used for decimals, not comma
            return String.format(Locale.US, "%.4f,%s,%d", time, podName, size);
        }
    }

    // Represents a single running instance (Replica) of a Service
    static class Pod {
        int id;
        int serviceId;
        int nodeId;

        // --- CONCURRENCY LOGIC ---
        // Instead of a boolean isBusy, we use a counter.
        // This mimics a Thread Pool (e.g., Tomcat, Jetty).
        int activeRequests = 0;
        int maxConcurrency = 10; // The Pod can handle 10 requests at once before queuing.

        // The "Waiting Room" for this specific Pod
        Queue<RequestState> requestQueue = new LinkedList<>();

        public Pod(int id, int serviceId, int nodeId) {
            this.id = id;
            this.serviceId = serviceId;
            this.nodeId = nodeId;
        }

        // Returns TRUE if we have an open thread slot
        public boolean hasCapacity() {
            return activeRequests < maxConcurrency;
        }
    }

    // Represents a User Request traveling through the system
    static class RequestState {
        int requestId;
        double arrivalTime; // When the user clicked the button
        Services currentService;
        double currentServiceInstructionsRemaining; // Work left to do

        // --- STATS ---
        double queueEntryTime = 0.0; // "Stopwatch" start time for waiting in line
        double startTime = -1;       // When did it actually touch the CPU?
        double endTime = -1;

        public RequestState(int requestId, double arrivalTime, Services startService) {
            this.requestId = requestId;
            this.arrivalTime = arrivalTime;
            this.currentService = startService;
            this.currentServiceInstructionsRemaining = startService.getTotalInstructions();
        }
    }

    // Links a Request to a Pod while it is actively running on the CPU
    static class ActiveJob {
        RequestState request;
        Pod pod;
        double lastUpdateTime;       // When did we last calculate progress?
        double remainingInstructions;
        double currentSpeed;         // Instructions Per Second (Changes dynamically!)

        public ActiveJob(RequestState request, Pod pod, double now, double totalInstructions) {
            this.request = request;
            this.pod = pod;
            this.lastUpdateTime = now;
            this.remainingInstructions = totalInstructions;
        }
    }

    // ==========================================
    // 2. THE EVENT SYSTEM
    // ==========================================

    enum EventType { ARRIVAL, POD_FINISH, NETWORK_FINISH }

    static class SimEvent implements Comparable<SimEvent> {
        double time;      // When will this happen?
        EventType type;   // What is happening?
        RequestState request;
        Pod pod;

        public SimEvent(double time, EventType type, RequestState request, Pod pod) {
            this.time = time;
            this.type = type;
            this.request = request;
            this.pod = pod;
        }

        // This ensures the PriorityQueue always gives us the EARLIEST event next.
        @Override
        public int compareTo(SimEvent other) {
            return Double.compare(this.time, other.time);
        }
    }

    // ==========================================
    // 3. MAIN SIMULATION LOGIC
    // ==========================================

    public void runSimulation(List<ComputingNodes> nodes, List<Services> services, List<ServiceCall> calls, double T) {
        System.out.println("--- Starting Kubernetes Simulation (Concurrent + Queue Logging) ---");

        // --- STEP A: Setup Lookups (Optimizing for speed) ---
        Map<Integer, ComputingNodes> nodeMap = nodes.stream().collect(Collectors.toMap(ComputingNodes::getNode_id, Function.identity()));
        Map<Integer, Services> serviceMap = services.stream().collect(Collectors.toMap(Services::getService_id, Function.identity()));
        Map<Integer, ServiceCall> callMap = calls.stream().collect(Collectors.toMap(ServiceCall::getCallerId, Function.identity()));

        // --- STEP B: Deploy Pods (The "Kubernetes Scheduler") ---
        // We create 2 replicas (Pods) for every Service and assign them Round-Robin to nodes.
        List<Pod> allPods = new ArrayList<>();
        Map<Integer, List<Pod>> serviceToPods = new HashMap<>(); // Helper for Load Balancer
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

        // --- STEP C: Initialize State Containers ---
        PriorityQueue<SimEvent> eventQueue = new PriorityQueue<>(); // The Master Timeline
        List<TraceEvent> traceEvents = new ArrayList<>();           // For Gantt Chart
        List<RequestResult> results = new ArrayList<>();            // For Final Statistics
        List<QueueLog> queueLogs = new ArrayList<>();               // For Queue Graph

        // This Map tracks who is currently using the CPU on each Node
        Map<Integer, List<ActiveJob>> nodeActiveJobs = new HashMap<>();
        for (ComputingNodes n : nodes) nodeActiveJobs.put(n.getNode_id(), new ArrayList<>());

        // --- STEP D: Generate Traffic (Poisson Process) ---
        // 1. Find the "Entry Point" Service (The one users call first)
        Set<Integer> calleeIds = calls.stream().map(ServiceCall::getCalleeId).collect(Collectors.toSet());
        Services startService = services.stream()
                .filter(s -> !calleeIds.contains(s.getService_id()))
                .findFirst()
                .orElse(services.get(0));

        // 2. Pre-calculate all user arrivals using Random Number Generation
        Random random = new Random(42); // Fixed seed = Reproducible results
        double currentArrival = 0.0;
        int reqId = 1;
        double lambda = 0.5; // Requests Per Second (Workload)

        while (currentArrival <= T) {
            RequestState req = new RequestState(reqId++, currentArrival, startService);
            eventQueue.add(new SimEvent(currentArrival, EventType.ARRIVAL, req, null));

            // Random time gap based on Exponential Distribution
            double u = 1.0 - random.nextDouble();
            double randomGap = -Math.log(u) / lambda;
            currentArrival += randomGap;
        }

        // --- STEP E: The Event Loop (The Engine) ---
        while (!eventQueue.isEmpty()) {
            SimEvent currentEvent = eventQueue.poll(); // Get earliest event
            double now = currentEvent.time;            // Move clock forward

            // Stop accepting new arrivals if we passed the simulation duration
            if (now > T && currentEvent.type == EventType.ARRIVAL) break;

            switch (currentEvent.type) {
                case ARRIVAL:       // User enters system
                case NETWORK_FINISH: // Request finished moving between nodes
                    handleArrival(now, currentEvent.request, serviceToPods, nodeActiveJobs, eventQueue, nodeMap, traceEvents, queueLogs);
                    break;

                case POD_FINISH:    // Computation finished
                    handlePodFinish(now, currentEvent, nodeActiveJobs, eventQueue, callMap, serviceMap, nodeMap, traceEvents, serviceToPods, results, queueLogs);
                    break;
            }
        }

        // --- STEP F: Export Data ---
        exportToCSV(traceEvents, "simulation_trace_k8s.csv");
        exportQueueLogs(queueLogs, "queue_trace.csv");
    }

    // ==========================================
    // 4. EVENT HANDLERS (The Logic)
    // ==========================================

    /**
     * Called when a request is ready to be processed by a Service.
     * Acts as the "Load Balancer".
     */
    private void handleArrival(double now, RequestState req, Map<Integer, List<Pod>> serviceToPods,
                               Map<Integer, List<ActiveJob>> nodeActiveJobs, PriorityQueue<SimEvent> eventQueue,
                               Map<Integer, ComputingNodes> nodeMap, List<TraceEvent> traceEvents,
                               List<QueueLog> queueLogs) {

        // 1. Load Balancing: Pick a specific Pod
        List<Pod> pods = serviceToPods.get(req.currentService.getService_id());
        Pod chosenPod = pods.get(req.requestId % pods.size()); // Round-Robin

        // 2. Add to that Pod's Queue (Wait Line)
        chosenPod.requestQueue.add(req);

        // 3. Log Queue Metrics
        req.queueEntryTime = now; // Start "Wait" stopwatch
        queueLogs.add(new QueueLog(now, "S" + chosenPod.serviceId + " (Pod " + chosenPod.id + ")", chosenPod.requestQueue.size()));

        // 4. Try to move from Queue to CPU immediately
        trySchedulePod(now, chosenPod, nodeActiveJobs, eventQueue, nodeMap, traceEvents, queueLogs);
    }

    /**
     * Tries to move a request from the Pod's Queue to the Node's CPU.
     * Checks Thread Pool capacity.
     */
    private void trySchedulePod(double now, Pod pod, Map<Integer, List<ActiveJob>> nodeActiveJobs,
                                PriorityQueue<SimEvent> eventQueue, Map<Integer, ComputingNodes> nodeMap,
                                List<TraceEvent> traceEvents, List<QueueLog> queueLogs) {

        // CONSTRAINT CHECK: Do we have open threads? Is there anyone waiting?
        if (!pod.hasCapacity() || pod.requestQueue.isEmpty()) return;

        // 1. Pull request from Queue
        RequestState req = pod.requestQueue.poll();

        // 2. Log "Waiting Time" (If they waited at all)
        if (now > req.queueEntryTime) {
            traceEvents.add(new TraceEvent(req.requestId, "Wait", "Wait", req.queueEntryTime, now));
        }
        // Log that queue size went down
        queueLogs.add(new QueueLog(now, "S" + pod.serviceId + " (Pod " + pod.id + ")", pod.requestQueue.size()));

        // 3. Occupy a Thread
        pod.activeRequests++;
        if (req.startTime < 0) req.startTime = now; // Record strict start time

        // 4. CPU Scheduling Logic
        ComputingNodes node = nodeMap.get(pod.nodeId);
        List<ActiveJob> jobsOnNode = nodeActiveJobs.get(node.getNode_id());

        // A. Save progress of EXISTING jobs (because speed is about to change)
        updateProgress(jobsOnNode, now);

        // B. Add NEW job
        ActiveJob newJob = new ActiveJob(req, pod, now, req.currentServiceInstructionsRemaining);
        jobsOnNode.add(newJob);

        // C. Slow everyone down (Time Slicing) & Predict new finish times
        rescheduleNode(now, node, jobsOnNode, eventQueue);

        // 5. RECURSION: If we still have thread slots left, try to pull another request!
        if (pod.hasCapacity() && !pod.requestQueue.isEmpty()) {
            trySchedulePod(now, pod, nodeActiveJobs, eventQueue, nodeMap, traceEvents, queueLogs);
        }
    }

    /**
     * Called when the Event Queue says "Job X should be done now".
     */
    private void handlePodFinish(double now, SimEvent event, Map<Integer, List<ActiveJob>> nodeActiveJobs,
                                 PriorityQueue<SimEvent> eventQueue, Map<Integer, ServiceCall> callMap,
                                 Map<Integer, Services> serviceMap, Map<Integer, ComputingNodes> nodeMap,
                                 List<TraceEvent> traceEvents, Map<Integer, List<Pod>> serviceToPods,
                                 List<RequestResult> results, List<QueueLog> queueLogs) {

        ComputingNodes node = nodeMap.get(event.pod.nodeId);
        List<ActiveJob> jobsOnNode = nodeActiveJobs.get(node.getNode_id());

        // 1. Update progress to current time
        updateProgress(jobsOnNode, now);

        // 2. Validate Completion (Filter out "Stale" events)
        ActiveJob job = null;
        Iterator<ActiveJob> it = jobsOnNode.iterator();
        while(it.hasNext()){
            ActiveJob j = it.next();
            if(j.request.requestId == event.request.requestId && j.pod.id == event.pod.id) {
                // Tolerance for floating point math errors
                if (j.remainingInstructions <= 1.0) {
                    job = j;
                    it.remove(); // Remove from CPU
                }
                break;
            }
        }

        if (job == null) return; // False alarm (Job wasn't actually done)

        // 3. Log Computation Bar for Visualization
        traceEvents.add(new TraceEvent(job.request.requestId, "Computation",
                "S" + job.request.currentService.getService_id() + " (Pod " + job.pod.id + ")",
                job.request.startTime, now));

        // 4. Free up the Thread Slot
        job.pod.activeRequests--;

        // 5. Immediately check if someone is waiting to take this spot
        trySchedulePod(now, job.pod, nodeActiveJobs, eventQueue, nodeMap, traceEvents, queueLogs);

        // 6. Speed up remaining jobs (One less job to share CPU with)
        rescheduleNode(now, node, jobsOnNode, eventQueue);

        // 7. Route to Next Step
        ServiceCall call = callMap.get(job.request.currentService.getService_id());

        if (call != null) {
            // A. NETWORK TRANSFER
            double networkTime = (double) call.getBytes() / node.getBandwidth();
            traceEvents.add(new TraceEvent(job.request.requestId, "Network", "Net", now, now + networkTime));

            // Prepare for next service
            job.request.currentService = serviceMap.get(call.getCalleeId());
            job.request.currentServiceInstructionsRemaining = job.request.currentService.getTotalInstructions();
            job.request.startTime = -1; // Reset stopwatch for next service

            // Schedule arrival at next node
            eventQueue.add(new SimEvent(now + networkTime, EventType.NETWORK_FINISH, job.request, null));
        } else {
            // B. REQUEST COMPLETE
            job.request.endTime = now;
            results.add(new RequestResult(job.request.requestId, job.request.arrivalTime, job.request.startTime, now, now - job.request.arrivalTime));
            System.out.println("Req " + job.request.requestId + " Finished. Latency: " + (now - job.request.arrivalTime));
        }
    }

    // ==========================================
    // 5. HELPER METHODS (The Math)
    // ==========================================

    // Updates 'remainingInstructions' for all running jobs based on time passed
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

    // Calculates CPU speed (Time Slicing) and creates new Finish Events
    private void rescheduleNode(double now, ComputingNodes node, List<ActiveJob> jobs, PriorityQueue<SimEvent> eventQueue) {
        if (jobs.isEmpty()) return;

        // Formula: Actual Frequency = (Freq * Cores) / Active Jobs

        double coresPerJob =  (node.getCores() / jobs.size());
        double speedPerJob = coresPerJob * node.getFrequency();

        for (ActiveJob job : jobs) {
            job.currentSpeed = speedPerJob;
            double timeToFinish = job.remainingInstructions / speedPerJob;

            // Create a prediction for the future.
            // Note: We might create multiple predictions for the same job.
            // 'handlePodFinish' filters out the wrong ones.
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