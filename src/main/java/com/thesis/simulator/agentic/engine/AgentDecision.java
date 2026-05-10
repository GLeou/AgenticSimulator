package com.thesis.simulator.agentic.engine;

/** What an LLM call resolved to, sampled stochastically by LLMEngine. */
public record AgentDecision(Kind kind, String targetId, int outputTokens) {

    public enum Kind { GENERATE_TEXT, CALL_TOOL, DELEGATE, FAIL }

    public static AgentDecision text(int outputTokens) {
        return new AgentDecision(Kind.GENERATE_TEXT, null, outputTokens);
    }

    public static AgentDecision tool(String toolId, int outputTokens) {
        return new AgentDecision(Kind.CALL_TOOL, toolId, outputTokens);
    }

    public static AgentDecision delegate(String agentId, int outputTokens) {
        return new AgentDecision(Kind.DELEGATE, agentId, outputTokens);
    }

    public static AgentDecision fail() {
        return new AgentDecision(Kind.FAIL, null, 0);
    }
}
