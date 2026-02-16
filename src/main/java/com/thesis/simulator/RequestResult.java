package com.thesis.simulator;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;

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