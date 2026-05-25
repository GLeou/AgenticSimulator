package com.thesis.simulator.agentic.events;

import com.thesis.simulator.agentic.engine.AgentDecision;
import com.thesis.simulator.agentic.runtime.Message;

/**
 * Base interface for all events that flow through the simulator's priority queue.
 * Every event has a scheduled simulation time and processing an event may schedule new events.
 *
 * Uses Java sealed interface + records for exhaustive pattern matching.
 */
public sealed interface AgenticEvent
        extends Comparable<AgenticEvent>
        permits AgenticEvent.TaskSubmit,
                AgenticEvent.AgentReceive,
                AgenticEvent.InfraComplete,
                AgenticEvent.LlmComplete,
                AgenticEvent.ToolComplete,
                AgenticEvent.WorkflowComplete {

    double timeMs();

    @Override
    default int compareTo(AgenticEvent other) {
        return Double.compare(this.timeMs(), other.timeMs());
    }

    /** User submits a task to the orchestrator (placeholder for queued submissions). */
    record TaskSubmit(double timeMs, String workflowId, String entryAgent, int promptTokens)
            implements AgenticEvent {}

    /** A message has finished traversing the network and is ready for the agent to process. */
    record AgentReceive(double timeMs, String workflowId, String agentId, Message message)
            implements AgenticEvent {}

    /** Infrastructure compute has completed; the agent can now dispatch the LLM call. */
    record InfraComplete(double timeMs, String workflowId, String agentId, String infraJobId,
                         AgentDecision decision, double cost, int outputTokens,
                         double networkOut, double inferenceMs, double networkBack)
            implements AgenticEvent {}

    /** An LLM call has finished generating; the decision is now known. */
    record LlmComplete(double timeMs, String workflowId, String agentId,
                       AgentDecision decision, double costAccrued, int outputTokens)
            implements AgenticEvent {}

    /** A tool invocation has finished. */
    record ToolComplete(double timeMs, String workflowId, String agentId,
                        String toolId, int responseTokens, boolean errored)
            implements AgenticEvent {}

    /** The whole workflow has terminated (success or budget exhausted). */
    record WorkflowComplete(double timeMs, String workflowId, String reason,
                            double totalLatencyMs, double totalCostUsd, int totalSteps)
            implements AgenticEvent {}
}
