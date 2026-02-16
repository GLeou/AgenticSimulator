package com.thesis.simulator;

import com.thesis.simulator.Application.ApplicationConfig;
import com.thesis.simulator.Infrastructure.InfrastructureConfig;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class SimulatorApplication implements CommandLineRunner {

    public static void main(String[] args) {
        SpringApplication.run(SimulatorApplication.class, args);
    }

    @Override
    public void run(String... args) {
        try {
            System.out.println("Loading configuration...");
            InfrastructureConfig infra = JsonLoader.loadInfrastructure("infrastructure.json");
            ApplicationConfig apps = JsonLoader.loadApplication("application.json");

            Simulation sim = new Simulation();

            // Run simulation for T = 10 seconds (as a test)
            // Change 10.0 to 200.0 for a longer run
            sim.runSimulation(
                    infra.getComputingNodes(),
                    apps.getServices(),
                    apps.getServiceCalls(),
                    100.0
            );

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}