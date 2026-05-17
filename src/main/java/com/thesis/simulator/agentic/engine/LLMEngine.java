package com.thesis.simulator.agentic.engine;

import com.thesis.simulator.agentic.config.AgenticConfig.LLMProfile;

import lombok.RequiredArgsConstructor;

import java.util.List;
import java.util.Random;
import java.util.function.BiFunction;

/**
 * Stochastic surrogate for a real LLM API.
 * Samples (decision, latency, cost) — does NOT call any real model.
 *
 * Latency model:  latency = TTFT + output_tokens × TPOT
 *   - TTFT sampled from Gamma(shape, scale=mean/shape) — always positive, right-skewed
 *   - TPOT sampled from Gamma(shape, scale=mean/shape)
 *   - output_tokens sampled from Gaussian(mean, std), clamped ≥ 1
 *
 * Decision model: pluggable BiFunction policy. Use a scripted policy for
 * deterministic debugging, swap to weighted-random for experiments.
 */
@RequiredArgsConstructor
public class LLMEngine {

    private final Random rng;
    private final BiFunction<Integer, List<String>, AgentDecision> decisionPolicy;

    /** Sample inference latency in ms: TTFT + output_tokens × TPOT. */
    public double sampleLatencyMs(LLMProfile profile, int outputTokens) {
        double ttft = sampleGamma(profile.ttftGammaShape(), profile.ttftMeanMs());
        double tpot = sampleGamma(profile.tpotGammaShape(), profile.tpotMeanMs());
        return ttft + tpot * outputTokens;
    }

    /** Sample how many tokens this call will produce. */
    public int sampleOutputTokens(LLMProfile profile) {
        double draw = profile.outputTokensMean() + rng.nextGaussian() * profile.outputTokensStd();
        return Math.max(1, (int) Math.round(draw));
    }

    /** Apply the configured decision policy. */
    public AgentDecision decide(int inputTokens, List<String> availableTools) {
        return decisionPolicy.apply(inputTokens, availableTools);
    }

    /** Compute the dollar cost of one call. */
    public double computeCostUsd(LLMProfile profile, int inputTokens, int outputTokens) {
        return inputTokens * profile.pricePerInputToken()
             + outputTokens * profile.pricePerOutputToken();
    }

    // =========================================
    // Gamma Distribution Sampler
    // Marsaglia & Tsang's method (2000)
    // Gamma is used instead of Gaussian because:
    //  - It is always positive (latency can't be negative)
    //  - It is right-skewed (occasional high-latency outliers)
    //  - It matches empirical LLM latency distributions
    // =========================================

    /**
     * Sample from Gamma distribution with the given shape and mean.
     * Scale is derived as mean/shape.
     * @return sample value, guaranteed ≥ 0.001
     */
    private double sampleGamma(double shape, double mean) {
        double scale = mean / shape;
        double sample;

        if (shape < 1.0) {
            // Ahrens-Dieter boost: Gamma(shape) = Gamma(shape+1) * U^(1/shape)
            sample = sampleGammaShapeGeq1(shape + 1.0) * Math.pow(rng.nextDouble(), 1.0 / shape);
        } else {
            sample = sampleGammaShapeGeq1(shape);
        }

        return Math.max(0.001, sample * scale);
    }

    /**
     * Marsaglia & Tsang's method for Gamma(shape, 1) where shape ≥ 1.
     */
    private double sampleGammaShapeGeq1(double shape) {
        double d = shape - 1.0 / 3.0;
        double c = 1.0 / Math.sqrt(9.0 * d);

        while (true) {
            double x, v;
            do {
                x = rng.nextGaussian();
                v = 1.0 + c * x;
            } while (v <= 0.0);

            v = v * v * v;
            double u = rng.nextDouble();

            if (u < 1.0 - 0.0331 * (x * x) * (x * x)) {
                return d * v;
            }
            if (Math.log(u) < 0.5 * x * x + d * (1.0 - v + Math.log(v))) {
                return d * v;
            }
        }
    }
}
