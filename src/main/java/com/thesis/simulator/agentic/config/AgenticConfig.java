package com.thesis.simulator.agentic.config;

import java.util.List;
import java.util.Map;

/**
 * Configuration records for the agentic simulation layer.
 * Wire these into your existing JSON/YAML loader (Jackson works out of the box on records).
 */
public final class AgenticConfig {

    private AgenticConfig() {}

    /** A logical placement zone (e.g. "edge", "fog", "cloud"). */
    public record Zone(String id) {}

    /** A directed network link between two zones with one-way latency in ms. */
    public record NetworkLink(String fromZone, String toZone, double latencyMs, double bandwidthMbps) {}

    /**
     * Stochastic profile of an LLM model. Times in milliseconds.
     * Token prices in USD-per-token (e.g. 1e-6 = $1 per million tokens).
     *
     * TTFT and TPOT are sampled from Gamma distributions parameterised by
     * (mean, shape). The scale is derived as mean/shape. Gamma is chosen
     * because it is always positive and right-skewed, matching real-world
     * inference latency distributions.
     */
    public record LLMProfile(
            String id,
            double ttftMeanMs,
            double ttftGammaShape,
            double tpotMeanMs,
            double tpotGammaShape,
            int outputTokensMean,
            int outputTokensStd,
            double pricePerInputToken,
            double pricePerOutputToken,
            String hostZone
    ) {}

    /** Stochastic profile of an external tool (or MCP-exposed function). */
    public record ToolProfile(
            String id,
            double latencyMeanMs,
            double latencyStdMs,
            int responseTokensMean,
            double errorRate,
            String hostZone
    ) {}

    /** Physical/virtual infrastructure node. */
    public record InfraNode(int nodeId, String zone, int cores, double frequencyHz, double bandwidthBytesPerSec) {}

    /** An agent definition: which LLM, which tools, which zone, and infra properties. */
    public record AgentDefinition(
            String id,
            String llmProfileId,
            List<String> toolIds,
            String hostZone,
            int maxConcurrency,
            double coldStartMs,
            long instructionsPerStep,
            int replicas
    ) {}

    /** The whole configuration loaded from disk for one experiment. */
    public record Topology(
            List<Zone> zones,
            List<NetworkLink> links,
            Map<String, LLMProfile> llmProfiles,
            Map<String, ToolProfile> tools,
            Map<String, AgentDefinition> agents,
            List<InfraNode> infraNodes,
            WorkflowSpec workflow
    ) {}

    /** Minimal workflow spec for the happy-path demo. */
    public record WorkflowSpec(
            String entryAgent,
            int initialPromptTokens,
            int maxSteps,
            int maxTokens
    ) {}
}
