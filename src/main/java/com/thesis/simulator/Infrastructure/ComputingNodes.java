package com.thesis.simulator.Infrastructure;


import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/** Represents a physical computing node with CPU cores, clock frequency, and network bandwidth. */
@AllArgsConstructor
@NoArgsConstructor
@Data
@Builder
public class ComputingNodes {

    private int node_id;
    private int cores;
    private double frequency;
    private double bandwidth;
}
