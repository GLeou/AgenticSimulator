package com.thesis.simulator.agentic.runtime;

import java.util.concurrent.atomic.AtomicLong;

/**
 * The data unit exchanged between simulator entities.
 * Carries token counts (not bytes) — this is the agentic substitute for v1's ServiceCall.
 */
public record Message(
        long id,
        String fromAgent,
        String toAgent,
        int inputTokens,
        Object payload,        // type-erased: tool result, user prompt, etc.
        double createdAtMs
) {
    private static final AtomicLong COUNTER = new AtomicLong(0);

    public static Message create(String from, String to, int tokens, Object payload, double now) {
        return new Message(COUNTER.incrementAndGet(), from, to, tokens, payload, now);
    }
}
