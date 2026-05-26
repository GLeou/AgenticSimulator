package com.thesis.simulator.Infrastructure;

import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.List;

/** Wrapper for deserializing the infrastructure configuration JSON. */
@Data
@NoArgsConstructor
public class InfrastructureConfig {
    private List<ComputingNodes> computingNodes;
}