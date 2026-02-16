package com.thesis.simulator.Application;


import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@AllArgsConstructor
@NoArgsConstructor
@Data
@Builder
public class Services {

    private int service_id;
    private long totalInstructions;
    private int nodeId;
}
