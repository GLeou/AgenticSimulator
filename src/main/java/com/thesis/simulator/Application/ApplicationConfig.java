package com.thesis.simulator.Application;

import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.List;

@Data
@NoArgsConstructor
public class ApplicationConfig {
    private List<Services> services;
    private List<ServiceCall> serviceCalls;
}