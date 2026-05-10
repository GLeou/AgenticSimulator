package com.thesis.simulator.agentic;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.simulator.agentic.config.AgenticConfig.*;
import com.thesis.simulator.agentic.engine.AgentDecision;
import com.thesis.simulator.agentic.engine.LLMEngine;
import com.thesis.simulator.agentic.engine.ToolPool;
import com.thesis.simulator.agentic.events.AgenticEvent;
import com.thesis.simulator.agentic.metrics.TrajectoryCollector;
import com.thesis.simulator.agentic.runtime.AgentService;
import com.thesis.simulator.agentic.runtime.Orchestrator;
import com.thesis.simulator.agentic.scheduler.EventScheduler;

import java.io.InputStream;
import java.nio.file.Path;
import java.util.*;

/**
 * Runs the agentic simulation with Poisson traffic generation and
 * probabilistic (weighted-random) decision policy.
 *
 * Loads configuration from JSON and generates multiple concurrent workflows
 * over the simulation duration, then writes trajectory CSV.
 */
public class AgenticSimulationRunner {

    public void run(String configPath) throws Exception {
        System.out.println("=== Starting Agentic Simulation (v2 — Refactored) ===");

        // --- Load config ---
        ObjectMapper mapper = new ObjectMapper();
        InputStream is = getClass().getClassLoader().getResourceAsStream(configPath);
        if (is == null) throw new IllegalArgumentException("Config not found: " + configPath);
        JsonNode root = mapper.readTree(is);

        Topology topology = parseTopology(root);
        JsonNode simNode = root.get("simulation");
        double T = simNode.get("durationSeconds").asDouble() * 1000.0; // convert to ms
        double arrivalRate = simNode.get("arrivalRate").asDouble();
        double userMsgMean = simNode.get("userMessageTokensMean").asDouble();
        double userMsgStdDev = simNode.get("userMessageTokensStdDev").asDouble();
        long seed = simNode.get("seed").asLong();

        Random rng = new Random(seed);

        // --- Build decision policy: weighted random choice ---
        JsonNode weightsNode = root.get("llmModels").get(0).get("decisionWeights");
        Map<String, Double> decisionWeights = new LinkedHashMap<>();
        weightsNode.fields().forEachRemaining(e -> decisionWeights.put(e.getKey(), e.getValue().asDouble()));

        // Get available tool IDs for CALL_TOOL decisions
        List<String> allToolIds = new ArrayList<>(topology.tools().keySet());

        LLMEngine llm = new LLMEngine(seed, (inputTokens, availableTools) -> {
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

        ToolPool tools = new ToolPool(topology.tools(), seed + 1);

        // --- Wire components ---
        EventScheduler scheduler = new EventScheduler();
        TrajectoryCollector trace = new TrajectoryCollector();
        Orchestrator orchestrator = new Orchestrator(topology, scheduler, trace);

        // Register all agents
        for (Map.Entry<String, AgentDefinition> entry : topology.agents().entrySet()) {
            AgentService agent = new AgentService(
                    entry.getValue(), topology, llm, tools, scheduler, trace);
            orchestrator.registerAgent(entry.getKey(), agent);
        }

        printConfig(topology, decisionWeights, T, arrivalRate);

        // --- Generate traffic (Poisson process) ---
        double currentArrivalMs = 0.0;
        int reqId = 1;

        while (currentArrivalMs <= T) {
            int promptTokens = (int) Math.max(10,
                    Math.round(userMsgMean + rng.nextGaussian() * userMsgStdDev));

            orchestrator.submit("wf-" + String.format("%04d", reqId), promptTokens, currentArrivalMs);
            reqId++;

            // Exponential inter-arrival: gap = -ln(U) / lambda
            // arrivalRate is per second, convert to per ms
            double lambdaMs = arrivalRate / 1000.0;
            double u = 1.0 - rng.nextDouble();
            currentArrivalMs += -Math.log(u) / lambdaMs;
        }

        int totalRequests = reqId - 1;
        System.out.println("Generated " + totalRequests + " requests over "
                + String.format("%.0f", T / 1000.0) + "s (lambda=" + arrivalRate + "/s)");

        // --- Run event loop ---
        scheduler.run(orchestrator::process);

        // --- Export ---
        Path traceOut = Path.of("agentic_trajectory.csv");
        trace.writeCsv(traceOut);
        System.out.println("Trajectory saved to " + traceOut.toAbsolutePath());

        // --- Summary ---
        printSummary(trace);
    }

    // ==========================================
    // Config Parsing
    // ==========================================

    private Topology parseTopology(JsonNode root) {
        // Zones
        List<Zone> zones = new ArrayList<>();
        for (JsonNode n : root.get("nodes")) {
            zones.add(new Zone(n.get("zone").asText()));
        }
        // Deduplicate zones
        zones = zones.stream().distinct().toList();

        // Network links
        List<NetworkLink> links = new ArrayList<>();
        for (JsonNode zl : root.get("zonePairLatencies")) {
            links.add(new NetworkLink(
                    zl.get("from").asText(),
                    zl.get("to").asText(),
                    zl.get("latencyMs").asDouble(),
                    zl.has("bandwidthMbps") ? zl.get("bandwidthMbps").asDouble() : 1000.0));
        }

        // LLM profiles
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

        // Tools
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

        // Agents
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
                    a.has("coldStartMs") ? a.get("coldStartMs").asDouble() : 0.0));
        }

        // Workflow spec
        JsonNode simNode = root.get("simulation");
        String entryAgent = agents.keySet().iterator().next();
        WorkflowSpec workflow = new WorkflowSpec(
                entryAgent,
                simNode.has("userMessageTokensMean") ? simNode.get("userMessageTokensMean").asInt() : 500,
                simNode.get("maxStepsPerWorkflow").asInt(),
                simNode.get("maxTokensPerWorkflow").asInt());

        return new Topology(zones, links, llmProfiles, toolProfiles, agents, workflow);
    }

    // ==========================================
    // Output
    // ==========================================

    private void printConfig(Topology topology, Map<String, Double> weights,
                             double durationMs, double arrivalRate) {
        System.out.println("--- Configuration ---");
        System.out.println("Zones: " + topology.zones().stream().map(Zone::id).toList());
        topology.agents().values().forEach(a ->
                System.out.printf("  Agent '%s' | zone=%s | model=%s | concurrency=%d | tools=%s%n",
                        a.id(), a.hostZone(), a.llmProfileId(), a.maxConcurrency(), a.toolIds()));
        topology.llmProfiles().values().forEach(m ->
                System.out.printf("  LLM '%s' | zone=%s | TTFT~Gamma(shape=%.1f,mean=%.0fms) | TPOT~Gamma(shape=%.1f,mean=%.1fms)%n",
                        m.id(), m.hostZone(), m.ttftGammaShape(), m.ttftMeanMs(),
                        m.tpotGammaShape(), m.tpotMeanMs()));
        topology.tools().values().forEach(t ->
                System.out.printf("  Tool '%s' | zone=%s | latency~N(%.0f,%.0f)ms | errorRate=%.1f%%%n",
                        t.id(), t.hostZone(), t.latencyMeanMs(), t.latencyStdMs(), t.errorRate() * 100));
        System.out.println("Decision weights: " + weights);
        System.out.printf("Duration: %.0fs | Arrival rate: %.1f req/s%n",
                durationMs / 1000.0, arrivalRate);
        System.out.println("---------------------");
    }

    private void printSummary(TrajectoryCollector trace) {
        List<TrajectoryCollector.Row> completeRows = trace.rows().stream()
                .filter(r -> "COMPLETE".equals(r.eventType()))
                .toList();

        if (completeRows.isEmpty()) {
            System.out.println("No completed workflows.");
            return;
        }

        DoubleSummaryStatistics latencyStats = completeRows.stream()
                .mapToDouble(r -> ((Number) r.payload().get("total_latency_ms")).doubleValue())
                .summaryStatistics();

        double totalCost = completeRows.stream()
                .mapToDouble(r -> ((Number) r.payload().get("total_cost_usd")).doubleValue())
                .sum();

        long successCount = completeRows.stream()
                .filter(r -> "SUCCESS".equals(r.payload().get("reason")))
                .count();

        int totalSteps = completeRows.stream()
                .mapToInt(r -> ((Number) r.payload().get("steps")).intValue())
                .sum();

        System.out.println("\n=== Agentic Simulation Summary ===");
        System.out.printf(Locale.US, "Completed workflows:  %d%n", completeRows.size());
        System.out.printf(Locale.US, "  Successful:         %d (%.0f%%)%n",
                successCount, 100.0 * successCount / completeRows.size());
        System.out.printf(Locale.US, "Avg latency:          %.1f ms (%.3f s)%n",
                latencyStats.getAverage(), latencyStats.getAverage() / 1000.0);
        System.out.printf(Locale.US, "Max latency:          %.1f ms (%.3f s)%n",
                latencyStats.getMax(), latencyStats.getMax() / 1000.0);
        System.out.printf(Locale.US, "Total cost:           $%.4f%n", totalCost);
        System.out.printf(Locale.US, "Total agent steps:    %d%n", totalSteps);
        System.out.printf(Locale.US, "Total trace events:   %d%n", trace.rows().size());
        System.out.println("==================================");
    }
}
