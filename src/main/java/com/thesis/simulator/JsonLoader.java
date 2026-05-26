package com.thesis.simulator;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.simulator.Application.ApplicationConfig;
import com.thesis.simulator.Infrastructure.InfrastructureConfig;
import org.springframework.core.io.ClassPathResource;
import java.io.IOException;

/**
 * Loads simulation configuration from JSON classpath resources
 * and deserializes them into their respective configuration objects.
 */
public class JsonLoader {
    private static final ObjectMapper mapper = new ObjectMapper();

    public static InfrastructureConfig loadInfrastructure(String filename) throws IOException {
        return mapper.readValue(new ClassPathResource(filename).getFile(), InfrastructureConfig.class);
    }

    public static ApplicationConfig loadApplication(String filename) throws IOException {
        return mapper.readValue(new ClassPathResource(filename).getFile(), ApplicationConfig.class);
    }
}