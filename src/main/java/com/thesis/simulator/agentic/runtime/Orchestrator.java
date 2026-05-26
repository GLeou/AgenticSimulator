package com.thesis.simulator.agentic.runtime;

import com.thesis.simulator.agentic.config.AgenticConfig.Topology;
import com.thesis.simulator.agentic.events.AgenticEvent;
import com.thesis.simulator.agentic.metrics.TrajectoryCollector;
import com.thesis.simulator.agentic.scheduler.EventScheduler;

import lombok.RequiredArgsConstructor;

import java.util.HashMap;
import java.util.Map;

/**
 * Central dispatcher for the agentic simulation. Submits new workflows
 * and routes events to the appropriate {@link AgentService} instance.
 */
@RequiredArgsConstructor
public class Orchestrator {

    private final Topology topology;
    private final Map<String, AgentService> agents = new HashMap<>();
    private final EventScheduler scheduler;
    private final TrajectoryCollector trace;

    public void registerAgent(String agentId, AgentService service) {
        agents.put(agentId, service);
    }

    /** Initiates a new workflow by sending the initial user prompt to the entry agent. */
    public void submit(String workflowId, int promptTokens, double now) {
        var spec = topology.workflow();
        Message m = Message.create(
                "USER", spec.entryAgent(), promptTokens, "user_prompt", now);
        scheduler.schedule(new AgenticEvent.AgentReceive(now, workflowId, spec.entryAgent(), m));

        trace.log(workflowId, "ORCHESTRATOR", "SUBMIT", now,
                Map.of("entry_agent", spec.entryAgent(),
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
        } else if (ev instanceof AgenticEvent.WorkflowComplete e) {
            trace.log(e.workflowId(), "ORCHESTRATOR", "COMPLETE", e.timeMs(),
                    Map.of("reason", e.reason(),
                           "total_latency_ms", e.totalLatencyMs(),
                           "total_cost_usd", e.totalCostUsd(),
                           "steps", e.totalSteps()));
        } else if (ev instanceof AgenticEvent.TaskSubmit) {
            // Reserved for queued submissions; not yet implemented.
        }
    }
}
