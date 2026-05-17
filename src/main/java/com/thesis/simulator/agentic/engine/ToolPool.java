package com.thesis.simulator.agentic.engine;

import com.thesis.simulator.agentic.config.AgenticConfig.ToolProfile;

import lombok.RequiredArgsConstructor;

import java.util.Map;
import java.util.Random;

/**
 * Stochastic surrogate for external tools / MCP-exposed functions.
 * Samples (latency, response_tokens, error_flag).
 */
@RequiredArgsConstructor
public class ToolPool {

    private final Map<String, ToolProfile> tools;
    private final Random rng;

    public ToolProfile getProfile(String toolId) {
        ToolProfile p = tools.get(toolId);
        if (p == null) throw new IllegalArgumentException("Unknown tool: " + toolId);
        return p;
    }

    public double sampleLatencyMs(String toolId) {
        ToolProfile p = getProfile(toolId);
        double draw = p.latencyMeanMs() + rng.nextGaussian() * p.latencyStdMs();
        return Math.max(0, draw);
    }

    public boolean sampleError(String toolId) {
        return rng.nextDouble() < getProfile(toolId).errorRate();
    }

    public int sampleResponseTokens(String toolId) {
        return getProfile(toolId).responseTokensMean();
    }
}
