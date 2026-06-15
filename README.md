# Kubernetes & Agentic Discrete-Event Simulator

A Java-based discrete-event simulator for modeling microservice and LLM-based agentic workloads on edge/cloud infrastructure. Built with **Java 21** and **Spring Boot**.

---

## What is this?

This simulator models how requests flow through a Kubernetes-like environment -- from arrival, through load balancing and queuing, to execution on shared compute nodes -- using discrete-event simulation. It captures the real performance effects of CPU contention, thread pool limits, and network delays.

On top of that, it adds an **agentic layer** that simulates LLM-powered agents processing those requests. Agents reason step-by-step: they generate text, invoke external tools, delegate to other agents, or fail -- all while consuming tokens, incurring inference latency, and competing for the same underlying infrastructure. This makes it possible to study how agentic AI workloads behave under realistic infrastructure constraints, including cost, latency, queuing, and contention.

The two layers compose: every agent step first goes through the infrastructure simulation (CPU scheduling, queuing) before the LLM call is dispatched. This gives you the full end-to-end picture.

---

## Simulation Modes

**V1 -- Kubernetes Microservices:** Simulates traditional request/response microservices with CPU time-slicing, pod thread pools, request queuing, round-robin load balancing, network latency, and Poisson-distributed traffic generation.

**V2 -- Agentic Simulation:** Extends V1 with LLM-based agentic workflows including stochastic inference latency (Gamma-distributed TTFT/TPOT), tool invocations with error rates, agent decision loops, token-based cost tracking with budget constraints, zone-aware networking (edge/cloud/fog), and multiple concurrent workloads competing on shared infrastructure.

---

## Prerequisites

- **Java 21+**
- **Maven**
- **Lombok** plugin enabled in your IDE
- **Python 3.x** with `pandas` and `matplotlib` for visualization

```bash
pip install pandas matplotlib fpdf2
```

---

## Getting Started

**V1 -- Kubernetes Simulation:**
```bash
mvn spring-boot:run
```

**V2 -- Agentic Simulation:**
```bash
mvn spring-boot:run -Dspring-boot.run.arguments=agentic
```

In IntelliJ IDEA, add `agentic` to **Run Configuration > Program Arguments**.

---

## Configuration

**V1** configs live in `src/main/resources/`:
- `infrastructure.json` -- nodes, cores, frequency, bandwidth
- `application.json` -- services, instructions per request, data transfer sizes

**V2** config lives in `src/main/resources/agentic_config.json` and covers nodes, zone latencies, LLM model profiles, tools, agent services, simulation parameters, and workload definitions.

---

## Output & Visualization

**V1** produces `simulation_trace_k8s.csv` and `queue_trace.csv`. Visualize with:
```bash
python visualize1.py
```

**V2** produces `agentic_trajectory.csv` and a console summary. Visualize with:
```bash
python visualize_agentic.py
```

Additional experiment visualization scripts are included: `visualize_experiment1.py` through `visualize_experiment4.py`.

---

## Project Structure

```
src/main/java/com/thesis/simulator/
  SimulatorApplication.java        -- Entry point (V1 or V2 based on args)
  Simulation.java                  -- V1 discrete-event simulator
  JsonLoader.java                  -- JSON config loader for V1

  Application/                     -- V1 service topology
  Infrastructure/                  -- V1 node definitions

  agentic/                         -- V2 agentic simulation
    AgenticSimulationRunner.java   -- Main runner, config parsing, traffic gen
    config/                        -- Data records (topology, workloads, ...)
    engine/                        -- LLM surrogate, tool calls, decisions
    events/                        -- Sealed event hierarchy
    infra/                         -- CPU time-slicing, pod queuing
    runtime/                       -- Orchestrator, agent loop, messages
    scheduler/                     -- Priority queue event loop
    metrics/                       -- CSV trajectory logger
```

---

*Developed as part of a Master's thesis on agentic simulation of edge/cloud systems.*
