package com.thesis.simulator;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.simulator.Application.ApplicationConfig;
import com.thesis.simulator.Infrastructure.InfrastructureConfig;
import org.springframework.core.io.ClassPathResource;
import java.io.IOException;

public class JsonLoader {
    private static final ObjectMapper mapper = new ObjectMapper();

    public static InfrastructureConfig loadInfrastructure(String filename) throws IOException {
        // Reads "infrastructure.json" -> Maps to the wrapper class containing the list
        return mapper.readValue(new ClassPathResource(filename).getFile(), InfrastructureConfig.class);
    }

    public static ApplicationConfig loadApplication(String filename) throws IOException {
        // Reads "application.json" -> Maps to the wrapper class containing the lists
        return mapper.readValue(new ClassPathResource(filename).getFile(), ApplicationConfig.class);
    }
}