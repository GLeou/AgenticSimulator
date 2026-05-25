package com.thesis.simulator.agentic.infra;

/**
 * Result of an infrastructure job submission.
 * Contains the estimated latency breakdown from the physical infrastructure layer.
 */
public record InfraResult(double infraLatencyMs, double queueWaitMs, double computeMs) {}
