package com.thesis.simulator.agentic.runtime;

import com.thesis.simulator.agentic.config.AgenticConfig.AgentDefinition;
import com.thesis.simulator.agentic.config.AgenticConfig.LLMProfile;
import com.thesis.simulator.agentic.config.AgenticConfig.NetworkLink;
import com.thesis.simulator.agentic.config.AgenticConfig.Topology;
import com.thesis.simulator.agentic.config.AgenticConfig.ToolProfile;
import com.thesis.simulator.agentic.config.AgenticConfig.WorkloadDefinition;
import com.thesis.simulator.agentic.engine.AgentDecision;
import com.thesis.simulator.agentic.engine.LLMEngine;
import com.thesis.simulator.agentic.engine.ToolPool;
import com.thesis.simulator.agentic.events.AgenticEvent;
import com.thesis.simulator.agentic.infra.InfraResult;
import com.thesis.simulator.agentic.infra.InfrastructureLayer;
import com.thesis.simulator.agentic.metrics.TrajectoryCollector;
import com.thesis.simulator.agentic.scheduler.EventScheduler;

import java.util.*;
import java.util.function.Function;

/**
 * Simulated agentic microservice with per-workflow state keyed by workflow ID.
 * <p>
 * Implements the agent processing loop: receive message, build context, dispatch
 * infrastructure compute, invoke the LLM, and branch on the decision (generate text,
 * call a tool, delegate, or fail). Enforces concurrency limits with a FIFO queue,
 * modeling real-world container thread pools.
 * <p>
 * Budget limits (maxSteps, maxTokens) are resolved per-workflow from the workload
 * definition, supporting heterogeneous workloads with different constraints.
 */
public class AgentService {

    private final AgentDefinition def;
    private final Topology topology;
    private final LLMEngine llm;
    private final ToolPool tools;
    private final EventScheduler scheduler;
    private final TrajectoryCollector trace;
    private final InfrastructureLayer infraLayer;
    private final Function<String, WorkloadDefinition> workloadLookup;

    private int activeRequests = 0;
    private final Queue<AgenticEvent.AgentReceive> waitingQueue = new LinkedList<>();

    /** Tracks the original submission time for queued workflows (before dequeue timestamp adjustment). */
    private final Map<String, Double> submissionTimes = new HashMap<>();

    /** Per-workflow ephemeral session. */
    private final Map<String, WorkflowContext> contexts = new HashMap<>();
    private int infraJobCounter = 0;

    public AgentService(AgentDefinition def, Topology topology, LLMEngine llm,
                        ToolPool tools, EventScheduler scheduler, TrajectoryCollector trace,
                        InfrastructureLayer infraLayer, Function<String, WorkloadDefinition> workloadLookup) {
        this.def = def;
        this.topology = topology;
        this.llm = llm;
        this.tools = tools;
        this.scheduler = scheduler;
        this.trace = trace;
        this.infraLayer = infraLayer;
        this.workloadLookup = workloadLookup;
    }

    /**
     * Receives an incoming message. If the agent is at capacity, the request is queued;
     * otherwise it is processed immediately (context building + LLM dispatch).
     */
    public void onReceive(AgenticEvent.AgentReceive ev) {
        // Record original submission time (first time we see this workflow)
        submissionTimes.putIfAbsent(ev.workflowId(), ev.timeMs());

        if (activeRequests >= def.maxConcurrency()) {
            waitingQueue.add(ev);
            trace.log(ev.workflowId(), def.id(), "QUEUE_ENTER", ev.timeMs(),
                    Map.of("queue_size", waitingQueue.size()));
            return;
        }

        activeRequests++;
        processReceive(ev);
    }

    /** Processes the receive event: builds context, samples the LLM decision, and submits to infrastructure. */
    private void processReceive(AgenticEvent.AgentReceive ev) {
        WorkflowContext ctx = contexts.computeIfAbsent(
                ev.workflowId(), wid -> {
                    WorkloadDefinition wl = workloadLookup.apply(wid);
                    int maxSteps = wl != null ? wl.maxStepsPerWorkflow() : 10;
                    int maxTokens = wl != null ? wl.maxTokensPerWorkflow() : 10000;
                    // Use the original submission time, not the (possibly dequeue-adjusted) event time
                    double submitTime = submissionTimes.getOrDefault(wid, ev.timeMs());
                    return new WorkflowContext(wid, submitTime, maxSteps, maxTokens);
                });
        ctx.stepIndex++;
        ctx.accumulatedInputTokens += ev.message().inputTokens();

        trace.log(ev.workflowId(), def.id(), "AGENT_RECEIVE", ev.timeMs(),
                Map.of("step", ctx.stepIndex,
                       "input_tokens", ev.message().inputTokens(),
                       "session_tokens", ctx.accumulatedInputTokens));

        // Enforce per-workload step and token budget limits
        if (ctx.stepIndex > ctx.maxSteps
                || ctx.accumulatedInputTokens > ctx.maxTokens) {
            terminate(ev.workflowId(), ev.timeMs(), "BUDGET_EXHAUSTED", ctx);
            return;
        }

        // Sample LLM decision, latency, and cost
        LLMProfile profile = topology.llmProfiles().get(def.llmProfileId());
        double networkOut = networkLatency(def.hostZone(), profile.hostZone());
        double networkBack = networkLatency(profile.hostZone(), def.hostZone());

        int outputTokens = llm.sampleOutputTokens(profile);
        AgentDecision decision = llm.decide(ctx.accumulatedInputTokens, def.toolIds());
        double inferenceMs = llm.sampleLatencyMs(profile, outputTokens);
        double cost = llm.computeCostUsd(profile, ctx.accumulatedInputTokens, outputTokens);

        ctx.totalCostUsd += cost;
        ctx.accumulatedOutputTokens += outputTokens;

        // Submit to infrastructure layer for local CPU compute (context building, parsing)
        String infraJobId = def.id() + "-infra-" + (++infraJobCounter);
        InfraResult infra = infraLayer.submitJob(def.id(), infraJobId, ev.timeMs(),
                def.instructionsPerStep());

        // LLM call begins only after infrastructure compute completes
        double infraCompleteAt = ev.timeMs() + infra.infraLatencyMs();
        scheduler.schedule(new AgenticEvent.InfraComplete(
                infraCompleteAt, ev.workflowId(), def.id(), infraJobId,
                decision, cost, outputTokens, networkOut, inferenceMs, networkBack));

        trace.log(ev.workflowId(), def.id(), "INFRA_SUBMIT", ev.timeMs(),
                Map.of("infra_job_id", infraJobId,
                       "infra_latency_ms", infra.infraLatencyMs(),
                       "queue_wait_ms", infra.queueWaitMs(),
                       "compute_ms", infra.computeMs(),
                       "output_tokens", outputTokens,
                       "decision", decision.kind().name(),
                       "cost_usd", cost));
    }

    /** Handles infrastructure compute completion and dispatches the LLM API call. */
    public void onInfraComplete(AgenticEvent.InfraComplete ev) {
        infraLayer.releaseJob(ev.infraJobId(), ev.timeMs());

        trace.log(ev.workflowId(), def.id(), "INFRA_COMPLETE", ev.timeMs(),
                Map.of("infra_job_id", ev.infraJobId()));

        // Schedule LLM call: network out + inference + network back
        double completeAt = ev.timeMs() + ev.networkOut() + ev.inferenceMs() + ev.networkBack();
        scheduler.schedule(new AgenticEvent.LlmComplete(
                completeAt, ev.workflowId(), def.id(),
                ev.decision(), ev.cost(), ev.outputTokens()));

        trace.log(ev.workflowId(), def.id(), "LLM_DISPATCH", ev.timeMs(),
                Map.of("network_out_ms", ev.networkOut(),
                       "inference_ms", ev.inferenceMs(),
                       "network_back_ms", ev.networkBack(),
                       "output_tokens", ev.outputTokens(),
                       "decision", ev.decision().kind().name(),
                       "cost_usd", ev.cost(),
                       "completes_at", completeAt));
    }

    /** Branches on the LLM decision: generate text, call tool, delegate, or fail. */
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

    /** Handles tool completion: on success, loops the result back as a new agent step. */
    public void onToolComplete(AgenticEvent.ToolComplete ev) {
        if (ev.errored()) {
            terminate(ev.workflowId(), ev.timeMs(), "TOOL_FAILURE",
                    contexts.get(ev.workflowId()));
            return;
        }
        Message followUp = Message.create(
                ev.toolId(), def.id(), ev.responseTokens(), "tool_result", ev.timeMs());

        // Re-enter directly (this workflow already holds a concurrency slot)
        processReceive(new AgenticEvent.AgentReceive(
                ev.timeMs(), ev.workflowId(), def.id(), followUp));

        trace.log(ev.workflowId(), def.id(), "TOOL_RETURN", ev.timeMs(),
                Map.of("response_tokens", ev.responseTokens()));
    }

    /** Terminates a workflow, frees the concurrency slot, and dequeues the next waiting request. */
    private void terminate(String workflowId, double now, String reason, WorkflowContext ctx) {
        if (ctx == null) ctx = new WorkflowContext(workflowId, now, 10, 10000);
        scheduler.schedule(new AgenticEvent.WorkflowComplete(
                now, workflowId, reason,
                now - ctx.startedAtMs, ctx.totalCostUsd, ctx.stepIndex));
        contexts.remove(workflowId);
        submissionTimes.remove(workflowId);

        // Free concurrency slot and try to process next queued request
        activeRequests--;
        tryDequeue(now);
    }

    /** Drains the waiting queue while concurrency slots are available. */
    private void tryDequeue(double now) {
        while (!waitingQueue.isEmpty() && activeRequests < def.maxConcurrency()) {
            AgenticEvent.AgentReceive queued = waitingQueue.poll();
            activeRequests++;

            trace.log(queued.workflowId(), def.id(), "QUEUE_EXIT", now,
                    Map.of("waited_ms", now - queued.timeMs(),
                           "queue_remaining", waitingQueue.size()));

            // Adjust event timestamp to reflect time spent waiting in queue
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

    /** Per-workflow ephemeral session with workload-specific budget limits. */
    private static class WorkflowContext {
        final String workflowId;
        final double startedAtMs;
        final int maxSteps;
        final int maxTokens;
        int stepIndex = 0;
        int accumulatedInputTokens = 0;
        int accumulatedOutputTokens = 0;
        double totalCostUsd = 0.0;

        WorkflowContext(String workflowId, double startedAtMs, int maxSteps, int maxTokens) {
            this.workflowId = workflowId;
            this.startedAtMs = startedAtMs;
            this.maxSteps = maxSteps;
            this.maxTokens = maxTokens;
        }
    }
}
