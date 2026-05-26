package com.thesis.simulator;

import lombok.AllArgsConstructor;
import lombok.Data;

/** A single entry in the simulation execution trace, used for Gantt chart visualization. */
@Data
@AllArgsConstructor
public class TraceEvent {
    private int requestId;
    private String type;       // e.g. "Computation", "Network", "Wait"
    private String name;       // e.g. "S1 (Pod 2)", "Net"
    private double startTime;
    private double endTime;

    public String toCSV() {
        return requestId + "," + type + "," + name + "," + startTime + "," + endTime;
    }
}