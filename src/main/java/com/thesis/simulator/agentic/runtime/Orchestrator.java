package com.thesis.simulator.agentic.runtime;

import com.thesis.simulator.agentic.config.AgenticConfig.Topology;
import com.thesis.simulator.agentic.config.AgenticConfig.WorkloadDefinition;
import com.thesis.simulator.agentic.events.AgenticEvent;
import com.thesis.simulator.agentic.metrics.TrajectoryCollector;
import com.thesis.simulator.agentic.scheduler.EventScheduler;

import lombok.RequiredArgsConstructor;

import java.util.HashMap;
import java.util.Map;

/**
 * Central dispatcher for the agentic simulation. Submits new workflows
 * and routes events to the appropriate {@link AgentService} instance.
 * Maintains a registry of which workload each workflow belongs to.
 */
@RequiredArgsConstructor
public class Orchestrator {

    private final Topology topology;
    private final Map<String, AgentService> agents = new HashMap<>();
    private final EventScheduler scheduler;
    private final TrajectoryCollector trace;

    /** Maps workflowId to its workload definition for budget lookups. */
    private final Map<String, WorkloadDefinition> workloadRegistry = new HashMap<>();

    public void registerAgent(String agentId, AgentService service) {
        agents.put(agentId, service);
    }

    /** Returns the workload definition for a given workflow, or null if unknown. */
    public WorkloadDefinition getWorkload(String workflowId) {
        return workloadRegistry.get(workflowId);
    }

    /** Initiates a new workflow by sending the initial user prompt to the entry agent. */
    public void submit(String workflowId, WorkloadDefinition workload, int promptTokens, double now) {
        workloadRegistry.put(workflowId, workload);

        String entryAgent = workload.entryAgent();
        Message m = Message.create("USER", entryAgent, promptTokens, "user_prompt", now);
        scheduler.schedule(new AgenticEvent.AgentReceive(now, workflowId, entryAgent, m));

        trace.log(workflowId, "ORCHESTRATOR", "SUBMIT", now,
                Map.of("workload", workload.name(),
                       "entry_agent", entryAgent,
                       "prompt_tokens", promptTokens));
    }

    /** Dispatches an event to the appropriate handler based on its type. */
    public void process(AgenticEvent ev) {
        if (ev instanceof AgenticEvent.AgentReceive e) {
            agents.get(e.agentId()).onReceive(e);
        } else if (ev instanceof AgenticEvent.InfraComplete e) {
            agents.get(e.agentId()).onInfraComplete(e);
        } else if (ev instanceof AgenticEvent.LlmComplete e) {
            agents.get(e.agentId()).onLlmComplete(e);
        } else if (ev instanceof AgenticEvent.ToolComplete e) {
            agents.get(e.agentId()).onToolComplete(e);
        } else if (ev instanceof AgenticEvent.WorkflowComplete(
                double timeMs, String workflowId, String reason, double totalLatencyMs, double totalCostUsd,
                int totalSteps
        )) {
            WorkloadDefinition wl = workloadRegistry.remove(workflowId);
            String workloadName = wl != null ? wl.name() : "unknown";
            trace.log(workflowId, "ORCHESTRATOR", "COMPLETE", timeMs,
                    Map.of("workload", workloadName,
                           "reason", reason,
                           "total_latency_ms", totalLatencyMs,
                           "total_cost_usd", totalCostUsd,
                           "steps", totalSteps));
        } else if (ev instanceof AgenticEvent.TaskSubmit) {
            // Reserved for queued submissions; not yet implemented.
        }
    }
}
