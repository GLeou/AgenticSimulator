package com.thesis.simulator.agentic.runtime;

import com.thesis.simulator.agentic.config.AgenticConfig.AgentDefinition;
import com.thesis.simulator.agentic.config.AgenticConfig.LLMProfile;
import com.thesis.simulator.agentic.config.AgenticConfig.NetworkLink;
import com.thesis.simulator.agentic.config.AgenticConfig.Topology;
import com.thesis.simulator.agentic.config.AgenticConfig.ToolProfile;
import com.thesis.simulator.agentic.engine.AgentDecision;
import com.thesis.simulator.agentic.engine.LLMEngine;
import com.thesis.simulator.agentic.engine.ToolPool;
import com.thesis.simulator.agentic.events.AgenticEvent;
import com.thesis.simulator.agentic.metrics.TrajectoryCollector;
import com.thesis.simulator.agentic.scheduler.EventScheduler;

import java.util.*;

/**
 * Stateless agentic microservice. Per-workflow state is keyed by workflowId.
 * Implements the canonical agent step: build context → LLM call → branch on decision.
 *
 * Includes concurrency limits and queuing: when activeRequests ≥ maxConcurrency,
 * incoming requests wait in a FIFO queue and are dequeued when capacity frees up.
 * This models real-world container thread pools (like Tomcat/Jetty in v1 Pods).
 */
public class AgentService {

    private final AgentDefinition def;
    private final Topology topology;
    private final LLMEngine llm;
    private final ToolPool tools;
    private final EventScheduler scheduler;
    private final TrajectoryCollector trace;

    // --- Concurrency control (ported from v1's Pod model) ---
    private int activeRequests = 0;
    private final Queue<AgenticEvent.AgentReceive> waitingQueue = new LinkedList<>();

    /** Per-workflow ephemeral session. */
    private final Map<String, WorkflowContext> contexts = new HashMap<>();

    public AgentService(AgentDefinition def, Topology topology, LLMEngine llm,
                        ToolPool tools, EventScheduler scheduler, TrajectoryCollector trace) {
        this.def = def;
        this.topology = topology;
        this.llm = llm;
        this.tools = tools;
        this.scheduler = scheduler;
        this.trace = trace;
    }

    /**
     * Step 1 + 2: receive message, check concurrency, build context, kick off LLM call.
     * If at capacity, the request is queued and will be processed when a slot frees up.
     */
    public void onReceive(AgenticEvent.AgentReceive ev) {
        if (activeRequests >= def.maxConcurrency()) {
            waitingQueue.add(ev);
            trace.log(ev.workflowId(), def.id(), "QUEUE_ENTER", ev.timeMs(),
                    Map.of("queue_size", waitingQueue.size()));
            return;
        }

        activeRequests++;
        processReceive(ev);
    }

    /** Internal: actually processes the receive event (after capacity check). */
    private void processReceive(AgenticEvent.AgentReceive ev) {
        WorkflowContext ctx = contexts.computeIfAbsent(
                ev.workflowId(), wid -> new WorkflowContext(wid, ev.timeMs()));
        ctx.stepIndex++;
        ctx.accumulatedInputTokens += ev.message().inputTokens();

        trace.log(ev.workflowId(), def.id(), "AGENT_RECEIVE", ev.timeMs(),
                Map.of("step", ctx.stepIndex,
                       "input_tokens", ev.message().inputTokens(),
                       "session_tokens", ctx.accumulatedInputTokens));

        // Budget check
        if (ctx.stepIndex > topology.workflow().maxSteps()
                || ctx.accumulatedInputTokens > topology.workflow().maxTokens()) {
            terminate(ev.workflowId(), ev.timeMs(), "BUDGET_EXHAUSTED", ctx);
            return;
        }

        // Step 3: schedule LLM call.
        // Total wallclock = network(agent → llm) + inference + network(llm → agent)
        LLMProfile profile = topology.llmProfiles().get(def.llmProfileId());
        double networkOut = networkLatency(def.hostZone(), profile.hostZone());
        double networkBack = networkLatency(profile.hostZone(), def.hostZone());

        int outputTokens = llm.sampleOutputTokens(profile);
        AgentDecision decision = llm.decide(ctx.accumulatedInputTokens, def.toolIds());
        double inferenceMs = llm.sampleLatencyMs(profile, outputTokens);
        double cost = llm.computeCostUsd(profile, ctx.accumulatedInputTokens, outputTokens);

        ctx.totalCostUsd += cost;
        ctx.accumulatedOutputTokens += outputTokens;

        double completeAt = ev.timeMs() + networkOut + inferenceMs + networkBack;
        scheduler.schedule(new AgenticEvent.LlmComplete(
                completeAt, ev.workflowId(), def.id(), decision, cost, outputTokens));

        trace.log(ev.workflowId(), def.id(), "LLM_DISPATCH", ev.timeMs(),
                Map.of("network_out_ms", networkOut,
                       "inference_ms", inferenceMs,
                       "network_back_ms", networkBack,
                       "output_tokens", outputTokens,
                       "decision", decision.kind().name(),
                       "cost_usd", cost,
                       "completes_at", completeAt));
    }

    /** Step 4: branch on the LLM's decision. */
    public void onLlmComplete(AgenticEvent.LlmComplete ev) {
        WorkflowContext ctx = contexts.get(ev.workflowId());
        AgentDecision d = ev.decision();

        trace.log(ev.workflowId(), def.id(), "LLM_COMPLETE", ev.timeMs(),
                Map.of("decision", d.kind().name(),
                       "target", d.targetId() == null ? "" : d.targetId(),
                       "output_tokens", ev.outputTokens()));

        switch (d.kind()) {
            case GENERATE_TEXT -> terminate(ev.workflowId(), ev.timeMs(), "SUCCESS", ctx);
            case CALL_TOOL -> dispatchTool(ev, d.targetId(), ctx);
            case DELEGATE ->
                    terminate(ev.workflowId(), ev.timeMs(), "DELEGATE_NOT_IMPLEMENTED", ctx);
            case FAIL -> terminate(ev.workflowId(), ev.timeMs(), "LLM_FAIL", ctx);
        }
    }

    private void dispatchTool(AgenticEvent.LlmComplete ev, String toolId, WorkflowContext ctx) {
        ToolProfile tp = tools.getProfile(toolId);
        double networkOut = networkLatency(def.hostZone(), tp.hostZone());
        double networkBack = networkLatency(tp.hostZone(), def.hostZone());
        double toolMs = tools.sampleLatencyMs(toolId);
        boolean errored = tools.sampleError(toolId);
        int respTokens = errored ? 0 : tools.sampleResponseTokens(toolId);

        double completeAt = ev.timeMs() + networkOut + toolMs + networkBack;
        scheduler.schedule(new AgenticEvent.ToolComplete(
                completeAt, ev.workflowId(), def.id(), toolId, respTokens, errored));

        trace.log(ev.workflowId(), def.id(), "TOOL_DISPATCH", ev.timeMs(),
                Map.of("tool", toolId,
                       "network_out_ms", networkOut,
                       "tool_ms", toolMs,
                       "network_back_ms", networkBack,
                       "errored", errored,
                       "completes_at", completeAt));
    }

    /** Step 5: tool returns → loop back as a new AgentReceive (recursive step). */
    public void onToolComplete(AgenticEvent.ToolComplete ev) {
        if (ev.errored()) {
            terminate(ev.workflowId(), ev.timeMs(), "TOOL_FAILURE",
                    contexts.get(ev.workflowId()));
            return;
        }
        Message followUp = Message.create(
                ev.toolId(), def.id(), ev.responseTokens(), "tool_result", ev.timeMs());

        // Tool result loops back into the same agent — re-enter via processReceive
        // (no need to re-check concurrency, this workflow already holds a slot)
        processReceive(new AgenticEvent.AgentReceive(
                ev.timeMs(), ev.workflowId(), def.id(), followUp));

        trace.log(ev.workflowId(), def.id(), "TOOL_RETURN", ev.timeMs(),
                Map.of("response_tokens", ev.responseTokens()));
    }

    /**
     * Terminate a workflow: record completion, free concurrency slot,
     * and try to dequeue the next waiting request.
     */
    private void terminate(String workflowId, double now, String reason, WorkflowContext ctx) {
        if (ctx == null) ctx = new WorkflowContext(workflowId, now);
        scheduler.schedule(new AgenticEvent.WorkflowComplete(
                now, workflowId, reason,
                now - ctx.startedAtMs, ctx.totalCostUsd, ctx.stepIndex));
        contexts.remove(workflowId);

        // Free concurrency slot and try to process next queued request
        activeRequests--;
        tryDequeue(now);
    }

    /**
     * If there are queued requests and we have capacity, dequeue and process.
     * Mirrors v1's trySchedulePod() pattern.
     */
    private void tryDequeue(double now) {
        while (!waitingQueue.isEmpty() && activeRequests < def.maxConcurrency()) {
            AgenticEvent.AgentReceive queued = waitingQueue.poll();
            activeRequests++;

            trace.log(queued.workflowId(), def.id(), "QUEUE_EXIT", now,
                    Map.of("waited_ms", now - queued.timeMs(),
                           "queue_remaining", waitingQueue.size()));

            // Re-create the event at current time (it waited in queue)
            AgenticEvent.AgentReceive updated = new AgenticEvent.AgentReceive(
                    now, queued.workflowId(), queued.agentId(), queued.message());
            processReceive(updated);
        }
    }

    private double networkLatency(String fromZone, String toZone) {
        if (fromZone.equals(toZone)) return 0.0;
        return topology.links().stream()
                .filter(l -> l.fromZone().equals(fromZone) && l.toZone().equals(toZone))
                .findFirst()
                .map(NetworkLink::latencyMs)
                .orElseThrow(() -> new IllegalStateException(
                        "No link from " + fromZone + " to " + toZone));
    }

    /** Per-workflow ephemeral session. */
    private static class WorkflowContext {
        final String workflowId;
        final double startedAtMs;
        int stepIndex = 0;
        int accumulatedInputTokens = 0;
        int accumulatedOutputTokens = 0;
        double totalCostUsd = 0.0;

        WorkflowContext(String workflowId, double startedAtMs) {
            this.workflowId = workflowId;
            this.startedAtMs = startedAtMs;
        }
    }
}
