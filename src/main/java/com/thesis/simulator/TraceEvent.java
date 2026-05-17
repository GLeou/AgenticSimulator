package com.thesis.simulator;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class TraceEvent {
    private int requestId;
    private String type;       // "Computation" or "Network"
    private String name;       // "Service 1" or "Net -> S2"
    private double startTime;
    private double endTime;

    public String toCSV() {
        return requestId + "," + type + "," + name + "," + startTime + "," + endTime;
    }
}