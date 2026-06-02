package com.thesis.simulator.agentic;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.simulator.agentic.config.AgenticConfig.*;
import com.thesis.simulator.agentic.engine.AgentDecision;
import com.thesis.simulator.agentic.engine.LLMEngine;
import com.thesis.simulator.agentic.engine.ToolPool;
import com.thesis.simulator.agentic.infra.InfrastructureLayer;
import com.thesis.simulator.agentic.metrics.TrajectoryCollector;
import com.thesis.simulator.agentic.runtime.AgentService;
import com.thesis.simulator.agentic.runtime.Orchestrator;
import com.thesis.simulator.agentic.scheduler.EventScheduler;

import java.io.InputStream;
import java.nio.file.Path;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Entry point for the agentic simulation (v2).
 * <p>
 * Loads the experiment configuration from JSON, constructs the simulation topology
 * (infrastructure, agents, LLM profiles, tools), generates Poisson-distributed
 * traffic for each configured workload, and executes the discrete-event loop.
 * Multiple workloads run concurrently on the same infrastructure, producing
 * realistic resource contention. Results are exported as a trajectory CSV.
 */
public class AgenticSimulationRunner {

    public void run(String configPath) throws Exception {
        System.out.println("=== Starting Agentic Simulation (v2) ===");

        // Load and parse configuration
        ObjectMapper mapper = new ObjectMapper();
        InputStream is = getClass().getClassLoader().getResourceAsStream(configPath);
        if (is == null) throw new IllegalArgumentException("Config not found: " + configPath);
        JsonNode root = mapper.readTree(is);

        Topology topology = parseTopology(root);
        JsonNode simNode = root.get("simulation");
        double T = simNode.get("durationSeconds").asDouble() * 1000.0; // convert to ms
        long seed = simNode.get("seed").asLong();

        Random rng = new Random(seed);

        // Build weighted-random decision policy from configured weights
        JsonNode weightsNode = root.get("llmModels").get(0).get("decisionWeights");
        Map<String, Double> decisionWeights = new LinkedHashMap<>();
        weightsNode.fields().forEachRemaining(e -> decisionWeights.put(e.getKey(), e.getValue().asDouble()));

        List<String> allToolIds = new ArrayList<>(topology.tools().keySet());

        LLMEngine llm = new LLMEngine(new Random(seed), (inputTokens, availableTools) -> {
            LLMProfile profile = topology.llmProfiles().values().iterator().next();
            int outTokens = Math.max(1, (int) Math.round(
                    profile.outputTokensMean() + rng.nextGaussian() * profile.outputTokensStd()));

            double roll = rng.nextDouble();
            double cumulative = 0.0;
            for (Map.Entry<String, Double> entry : decisionWeights.entrySet()) {
                cumulative += entry.getValue();
                if (roll < cumulative) {
                    return switch (entry.getKey()) {
                        case "call_tool" -> {
                            String toolId = availableTools.isEmpty()
                                    ? allToolIds.get(0)
                                    : availableTools.get(rng.nextInt(availableTools.size()));
                            yield AgentDecision.tool(toolId, outTokens);
                        }
                        case "delegate" -> AgentDecision.delegate("agent-1", outTokens);
                        case "fail" -> AgentDecision.fail();
                        default -> AgentDecision.text(outTokens);
                    };
                }
            }
            return AgentDecision.text(outTokens);
        });

        ToolPool tools = new ToolPool(topology.tools(), new Random(seed + 1));

        // Wire simulation components
        EventScheduler scheduler = new EventScheduler();
        TrajectoryCollector trace = new TrajectoryCollector();
        Orchestrator orchestrator = new Orchestrator(topology, scheduler, trace);

        InfrastructureLayer infraLayer = new InfrastructureLayer(
                topology.infraNodes(), topology.agents());

        // Register all agents (pass workload lookup via orchestrator)
        for (Map.Entry<String, AgentDefinition> entry : topology.agents().entrySet()) {
            AgentService agent = new AgentService(
                    entry.getValue(), topology, llm, tools, scheduler, trace, infraLayer,
                    orchestrator::getWorkload);
            orchestrator.registerAgent(entry.getKey(), agent);
        }

        printConfig(topology, decisionWeights, T);

        // Generate per-workload Poisson arrival streams
        int reqId = 1;
        // Collect all arrivals across workloads, then sort by time
        List<ScheduledArrival> allArrivals = new ArrayList<>();

        for (WorkloadDefinition workload : topology.workloads()) {
            double currentArrivalMs = 0.0;
            double lambdaMs = workload.arrivalRate() / 1000.0;

            while (currentArrivalMs <= T) {
                int promptTokens = (int) Math.max(10,
                        Math.round(workload.userMessageTokensMean()
                                + rng.nextGaussian() * workload.userMessageTokensStdDev()));

                String wfId = "wf-" + workload.name() + "-" + String.format("%04d", reqId);
                allArrivals.add(new ScheduledArrival(currentArrivalMs, wfId, workload, promptTokens));
                reqId++;

                double u = 1.0 - rng.nextDouble();
                currentArrivalMs += -Math.log(u) / lambdaMs;
            }
        }

        // Sort all arrivals chronologically and submit
        allArrivals.sort(Comparator.comparingDouble(a -> a.timeMs));
        for (ScheduledArrival arrival : allArrivals) {
            orchestrator.submit(arrival.workflowId, arrival.workload, arrival.promptTokens, arrival.timeMs);
        }

        int totalRequests = allArrivals.size();
        System.out.println("Generated " + totalRequests + " requests over "
                + String.format("%.0f", T / 1000.0) + "s across "
                + topology.workloads().size() + " workload(s):");
        for (WorkloadDefinition w : topology.workloads()) {
            long count = allArrivals.stream().filter(a -> a.workload.name().equals(w.name())).count();
            System.out.printf("  %s: %d requests (lambda=%.1f/s)%n", w.name(), count, w.arrivalRate());
        }

        // Execute the discrete-event loop
        scheduler.run(orchestrator::process);

        // Export trajectory data
        Path traceOut = Path.of("agentic_trajectory.csv");
        trace.writeCsv(traceOut);
        System.out.println("Trajectory saved to " + traceOut.toAbsolutePath());

        printSummary(trace, topology.workloads());
    }

    /** Holds a pre-generated arrival for sorting across workloads. */
    private record ScheduledArrival(double timeMs, String workflowId,
                                     WorkloadDefinition workload, int promptTokens) {}

    // ── Configuration Parsing ──────────────────────────────────────

    /** Parses the full simulation topology from the root JSON configuration. */
    private Topology parseTopology(JsonNode root) {
        List<Zone> zones = new ArrayList<>();
        List<InfraNode> infraNodes = new ArrayList<>();
        for (JsonNode n : root.get("nodes")) {
            zones.add(new Zone(n.get("zone").asText()));
            infraNodes.add(new InfraNode(
                    n.get("nodeId").asInt(),
                    n.get("zone").asText(),
                    n.get("cores").asInt(),
                    n.get("frequencyHz").asDouble(),
                    n.has("bandwidthBytesPerSec") ? n.get("bandwidthBytesPerSec").asDouble() : 1_250_000_000.0));
        }
        zones = zones.stream().distinct().toList();

        List<NetworkLink> links = new ArrayList<>();
        for (JsonNode zl : root.get("zonePairLatencies")) {
            links.add(new NetworkLink(
                    zl.get("from").asText(),
                    zl.get("to").asText(),
                    zl.get("latencyMs").asDouble(),
                    zl.has("bandwidthMbps") ? zl.get("bandwidthMbps").asDouble() : 1000.0));
        }

        Map<String, LLMProfile> llmProfiles = new LinkedHashMap<>();
        for (JsonNode m : root.get("llmModels")) {
            String id = m.get("modelId").asText();
            llmProfiles.put(id, new LLMProfile(
                    id,
                    m.get("ttftMeanMs").asDouble(),
                    m.get("ttftGammaShape").asDouble(),
                    m.get("tpotMeanMs").asDouble(),
                    m.get("tpotGammaShape").asDouble(),
                    m.get("outputTokensMean").asInt(),
                    m.has("outputTokensStdDev") ? m.get("outputTokensStdDev").asInt() : m.get("outputTokensStd").asInt(),
                    m.get("costPerInputToken").asDouble(),
                    m.get("costPerOutputToken").asDouble(),
                    m.has("hostZone") ? m.get("hostZone").asText()
                            : root.get("nodes").get(0).get("zone").asText()));
        }

        Map<String, ToolProfile> toolProfiles = new LinkedHashMap<>();
        for (JsonNode t : root.get("tools")) {
            String id = t.get("toolId").asText();
            toolProfiles.put(id, new ToolProfile(
                    id,
                    t.get("latencyMeanMs").asDouble(),
                    t.has("latencyStdDevMs") ? t.get("latencyStdDevMs").asDouble() : t.get("latencyStdMs").asDouble(),
                    t.has("resultTokensMean") ? t.get("resultTokensMean").asInt() : t.get("responseTokensMean").asInt(),
                    t.has("errorRate") ? t.get("errorRate").asDouble() : 0.0,
                    t.has("hostZone") ? t.get("hostZone").asText()
                            : root.get("nodes").get(0).get("zone").asText()));
        }

        Map<String, AgentDefinition> agents = new LinkedHashMap<>();
        for (JsonNode a : root.get("agentServices")) {
            String id = a.get("serviceId").asText();
            List<String> toolIds = new ArrayList<>(toolProfiles.keySet());
            agents.put(id, new AgentDefinition(
                    id,
                    a.get("modelId").asText(),
                    toolIds,
                    a.has("hostZone") ? a.get("hostZone").asText()
                            : root.get("nodes").get(a.get("nodeId").asInt() - 1).get("zone").asText(),
                    a.get("maxConcurrency").asInt(),
                    a.has("coldStartMs") ? a.get("coldStartMs").asDouble() : 0.0,
                    a.has("instructionsPerStep") ? a.get("instructionsPerStep").asLong() : 50_000_000L,
                    a.has("replicas") ? a.get("replicas").asInt() : 1));
        }

        // Parse workloads array
        List<WorkloadDefinition> workloads = new ArrayList<>();
        for (JsonNode w : root.get("workloads")) {
            workloads.add(new WorkloadDefinition(
                    w.get("name").asText(),
                    w.get("entryAgent").asText(),
                    w.get("arrivalRate").asDouble(),
                    w.get("userMessageTokensMean").asDouble(),
                    w.get("userMessageTokensStdDev").asDouble(),
                    w.get("maxStepsPerWorkflow").asInt(),
                    w.get("maxTokensPerWorkflow").asInt()));
        }

        return new Topology(zones, links, llmProfiles, toolProfiles, agents, infraNodes, workloads);
    }

    // ── Output ────────────────────────────────────────────────────

    /** Prints the parsed configuration to stdout for verification. */
    private void printConfig(Topology topology, Map<String, Double> weights, double durationMs) {
        System.out.println("--- Configuration ---");
        System.out.println("Zones: " + topology.zones().stream().map(Zone::id).toList());
        topology.infraNodes().forEach(n ->
                System.out.printf("  Node %d | zone=%s | cores=%d | freq=%.0fHz%n",
                        n.nodeId(), n.zone(), n.cores(), n.frequencyHz()));
        topology.agents().values().forEach(a ->
                System.out.printf("  Agent '%s' | zone=%s | model=%s | concurrency=%d | replicas=%d | instrPerStep=%d | tools=%s%n",
                        a.id(), a.hostZone(), a.llmProfileId(), a.maxConcurrency(),
                        a.replicas(), a.instructionsPerStep(), a.toolIds()));
        topology.llmProfiles().values().forEach(m ->
                System.out.printf("  LLM '%s' | zone=%s | TTFT~Gamma(shape=%.1f,mean=%.0fms) | TPOT~Gamma(shape=%.1f,mean=%.1fms)%n",
                        m.id(), m.hostZone(), m.ttftGammaShape(), m.ttftMeanMs(),
                        m.tpotGammaShape(), m.tpotMeanMs()));
        topology.tools().values().forEach(t ->
                System.out.printf("  Tool '%s' | zone=%s | latency~N(%.0f,%.0f)ms | errorRate=%.1f%%%n",
                        t.id(), t.hostZone(), t.latencyMeanMs(), t.latencyStdMs(), t.errorRate() * 100));
        System.out.println("Workloads:");
        for (WorkloadDefinition w : topology.workloads()) {
            System.out.printf("  '%s' | entry=%s | lambda=%.1f/s | tokens~N(%.0f,%.0f) | maxSteps=%d | maxTokens=%d%n",
                    w.name(), w.entryAgent(), w.arrivalRate(),
                    w.userMessageTokensMean(), w.userMessageTokensStdDev(),
                    w.maxStepsPerWorkflow(), w.maxTokensPerWorkflow());
        }
        System.out.println("Decision weights: " + weights);
        System.out.printf("Duration: %.0fs%n", durationMs / 1000.0);
        System.out.println("---------------------");
    }

    /** Prints aggregate and per-workload simulation metrics to stdout. */
    private void printSummary(TrajectoryCollector trace, List<WorkloadDefinition> workloads) {
        List<TrajectoryCollector.Row> completeRows = trace.rows().stream()
                .filter(r -> "COMPLETE".equals(r.eventType()))
                .toList();

        if (completeRows.isEmpty()) {
            System.out.println("No completed workflows.");
            return;
        }

        System.out.println("\n=== Agentic Simulation Summary ===");
        printWorkloadStats("ALL", completeRows);

        // Per-workload breakdown
        Map<String, List<TrajectoryCollector.Row>> byWorkload = completeRows.stream()
                .collect(Collectors.groupingBy(r -> {
                    Object wl = r.payload().get("workload");
                    return wl != null ? wl.toString() : "unknown";
                }));

        for (WorkloadDefinition w : workloads) {
            List<TrajectoryCollector.Row> rows = byWorkload.getOrDefault(w.name(), List.of());
            if (!rows.isEmpty()) {
                printWorkloadStats(w.name(), rows);
            }
        }

        System.out.printf(Locale.US, "Total trace events:   %d%n", trace.rows().size());
        System.out.println("==================================");
    }

    private void printWorkloadStats(String label, List<TrajectoryCollector.Row> rows) {
        DoubleSummaryStatistics latencyStats = rows.stream()
                .mapToDouble(r -> ((Number) r.payload().get("total_latency_ms")).doubleValue())
                .summaryStatistics();

        double totalCost = rows.stream()
                .mapToDouble(r -> ((Number) r.payload().get("total_cost_usd")).doubleValue())
                .sum();

        long successCount = rows.stream()
                .filter(r -> "SUCCESS".equals(r.payload().get("reason")))
                .count();

        int totalSteps = rows.stream()
                .mapToInt(r -> ((Number) r.payload().get("steps")).intValue())
                .sum();

        System.out.printf(Locale.US, "--- %s ---%n", label);
        System.out.printf(Locale.US, "  Completed:    %d | Successful: %d (%.0f%%)%n",
                rows.size(), successCount, 100.0 * successCount / rows.size());
        System.out.printf(Locale.US, "  Avg latency:  %.1f ms (%.3f s)%n",
                latencyStats.getAverage(), latencyStats.getAverage() / 1000.0);
        System.out.printf(Locale.US, "  Max latency:  %.1f ms (%.3f s)%n",
                latencyStats.getMax(), latencyStats.getMax() / 1000.0);
        System.out.printf(Locale.US, "  Total cost:   $%.4f | Total steps: %d%n", totalCost, totalSteps);
    }
}
