package com.thesis.simulator.Application;

import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.List;

/** Wrapper for deserializing the application-layer configuration JSON. */
@Data
@NoArgsConstructor
public class ApplicationConfig {
    private List<Services> services;
    private List<ServiceCall> serviceCalls;
}