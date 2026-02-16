package com.thesis.simulator.Infrastructure;

import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.List;

@Data
@NoArgsConstructor
public class InfrastructureConfig {
    // Matches the JSON key "computingNodes"
    private List<ComputingNodes> computingNodes;
}