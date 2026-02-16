package com.thesis.simulator.Application;


import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;


@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder

public class ServiceCall {
    private int callerId;
    private int calleeId;
    private long bytes;


}
