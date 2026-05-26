package com.thesis.simulator.Application;


import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/** Defines a microservice with its computational cost (total instructions) and node assignment. */
@AllArgsConstructor
@NoArgsConstructor
@Data
@Builder
public class Services {

    private int service_id;
    private long totalInstructions;
    private int nodeId;
}
