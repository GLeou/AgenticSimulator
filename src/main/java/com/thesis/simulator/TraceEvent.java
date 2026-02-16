package com.thesis.simulator;

public class TraceEvent {
    public int requestId;
    public String type;       // "Computation" or "Network"
    public String name;       // "Service 1" or "Net -> S2"
    public double startTime;
    public double endTime;

    public TraceEvent(int requestId, String type, String name, double startTime, double endTime) {
        this.requestId = requestId;
        this.type = type;
        this.name = name;
        this.startTime = startTime;
        this.endTime = endTime;
    }

    // Helper to format as CSV line
    public String toCSV() {
        return requestId + "," + type + "," + name + "," + startTime + "," + endTime;
    }
}