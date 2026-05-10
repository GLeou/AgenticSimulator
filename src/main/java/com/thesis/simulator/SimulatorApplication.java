package com.thesis.simulator;

import com.thesis.simulator.Application.ApplicationConfig;
import com.thesis.simulator.Infrastructure.InfrastructureConfig;
import com.thesis.simulator.agentic.AgenticSimulationRunner;
import java.util.Arrays;
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
            // Check if any argument is "agentic"
            boolean runAgentic = Arrays.stream(args)
                    .anyMatch(a -> "agentic".equalsIgnoreCase(a));

            if (runAgentic) {
                // ===== V2: Agentic Simulation =====
                AgenticSimulationRunner runner = new AgenticSimulationRunner();
                runner.run("agentic_config.json");
            } else {
                // ===== V1: Kubernetes Microservices Simulation =====
                System.out.println("Running Kubernetes Simulation (v1)...");
                System.out.println("(Pass 'agentic' as argument to run v2)");
                System.out.println("Loading configuration...");
                InfrastructureConfig infra = JsonLoader.loadInfrastructure("infrastructure.json");
                ApplicationConfig apps = JsonLoader.loadApplication("application.json");

                Simulation sim = new Simulation();
                sim.runSimulation(
                        infra.getComputingNodes(),
                        apps.getServices(),
                        apps.getServiceCalls(),
                        100.0
                );
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}