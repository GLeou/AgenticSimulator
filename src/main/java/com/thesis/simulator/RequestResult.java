package com.thesis.simulator;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;

/** End-to-end result of a completed request, including timing and latency metrics. */
@Data
@AllArgsConstructor
@Builder
public class RequestResult {

    private final int requestId;
    private final double arrivalTime;
    private final double startTime;
    private final double finishTime;
    private final double latency;
}