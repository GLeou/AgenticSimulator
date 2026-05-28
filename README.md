# Kubernetes & Agentic Discrete Event Simulator

A Java-based discrete-event simulator for modeling microservice and LLM-based agentic workloads on edge/cloud infrastructure. Built with Spring Boot.

---

## Overview

This project provides two simulation modes:

### V1: Kubernetes Microservices Simulation
Models traditional request/response microservices with:
- CPU time-slicing and contention across shared nodes
- Per-pod thread pools with configurable concurrency limits
- Request queuing when pods are at capacity
- Round-robin load balancing across pod replicas
- Inter-service network latency based on payload size
- Poisson-distributed traffic generation

### V2: Agentic Simulation
Extends v1's infrastructure model with LLM-based agentic workflows:
- Stochastic LLM inference (Gamma-distributed TTFT/TPOT latency)
- Tool invocations with configurable latency and error rates
- Agent decision loop: generate text, call tools, delegate, or fail
- Token-based cost tracking (input/output pricing)
- Zone-aware network latency (edge, cloud, fog)
- **Multiple concurrent workloads** with independent arrival rates, token distributions, and budget constraints competing on the same infrastructure

The two layers compose: each agent step first incurs infrastructure cost (CPU contention from v1's physics), then dispatches the external LLM call.

---

## Architecture

```
V2 Workloads (chat-light, tool-heavy, ...)
  |  each generates its own Poisson arrival stream
  v
Agents (LLM calls, tool invocations, decisions)
  |  each step submits CPU work
  v
Infrastructure Layer (v1 physics)
  pods, CPU time-slicing, queuing, contention
```

---

## Prerequisites

- **Java 21+**
- **Maven**
- **Lombok plugin** enabled in your IDE
- **Python 3.x** with `pandas` and `matplotlib` (for visualization)
  ```
  pip install pandas matplotlib
  ```
- **fpdf2** (for regenerating the tutorial PDF)
  ```
  pip install fpdf2
  ```

---

## Configuration

### V1 Configuration

Located in `src/main/resources/`:

- **`infrastructure.json`** — Defines computing nodes (cores, frequency, bandwidth)
- **`application.json`** — Defines services (instructions per request) and service calls (data transfer size)

### V2 Configuration

Located in `src/main/resources/agentic_config.json`. Key sections:

- **`nodes`** — Infrastructure nodes with zone, cores, frequency
- **`zonePairLatencies`** — Network latency between zones
- **`llmModels`** — LLM profiles (TTFT/TPOT distributions, token pricing, decision weights)
- **`tools`** — External tool profiles (latency, error rate, response tokens)
- **`agentServices`** — Agent definitions (LLM, tools, concurrency, replicas, CPU cost per step)
- **`simulation`** — Global parameters (duration, random seed)
- **`workloads`** — One or more workload definitions:

```json
"workloads": [
  {
    "name": "chat-light",
    "entryAgent": "agent-1",
    "arrivalRate": 0.3,
    "userMessageTokensMean": 50.0,
    "userMessageTokensStdDev": 20.0,
    "maxStepsPerWorkflow": 5,
    "maxTokensPerWorkflow": 4000
  },
  {
    "name": "tool-heavy",
    "entryAgent": "agent-1",
    "arrivalRate": 0.2,
    "userMessageTokensMean": 200.0,
    "userMessageTokensStdDev": 60.0,
    "maxStepsPerWorkflow": 15,
    "maxTokensPerWorkflow": 50000
  }
]
```

Each workload generates an independent Poisson traffic stream. All workloads compete for the same infrastructure, producing realistic contention.

---

## How to Run

### V1: Kubernetes Simulation

```bash
mvn spring-boot:run
```

### V2: Agentic Simulation

```bash
mvn spring-boot:run -Dspring-boot.run.arguments=agentic
```

Or in IntelliJ IDEA: add `agentic` to **Run Configuration > Program Arguments**.

---

## Output

### V1 Output
- `simulation_trace_k8s.csv` — Execution timeline (Gantt chart data)
- `queue_trace.csv` — Queue depth per pod over time

### V2 Output
- `agentic_trajectory.csv` — Full event trajectory with per-workflow metrics, including workload tags
- Console summary with aggregate and per-workload statistics

---

## Visualization

### V1 Visualization
```bash
python visualize2.py
```
Produces a Gantt chart of request execution/wait times and queue depth over time.

### V2 Visualization
```bash
python visualize_agentic.py
```
Produces per-workload analysis charts:
- **Latency distribution** — Histogram and boxplot per workload
- **Cost & steps** — Per-workflow cost scatter, step count distribution
- **Timeline & outcomes** — Cumulative completions, completion reason breakdown
- **Infrastructure queuing** — Agent queue depth, wait time distribution
- **Infrastructure latency** — Per-step infra latency, compute vs queue wait

### Regenerate Tutorial PDF
```bash
python generate_tutorial_pdf.py
```
Generates `Agentic_Simulator_Tutorial.pdf` with full code walkthrough.

---

## Project Structure

```
src/main/java/com/thesis/simulator/
  SimulatorApplication.java          # Entry point (v1 or v2 based on args)
  Simulation.java                    # V1 discrete-event simulator
  JsonLoader.java                    # JSON config loader for v1
  TraceEvent.java, RequestResult.java

  Application/                       # V1 service topology
    ApplicationConfig, Services, ServiceCall

  Infrastructure/                    # V1 node definitions
    InfrastructureConfig, ComputingNodes, NetworkNodes

  agentic/                           # V2 agentic simulation
    AgenticSimulationRunner.java     # Main runner, config parsing, traffic gen
    config/AgenticConfig.java        # All data records (Topology, WorkloadDefinition, ...)
    engine/
      LLMEngine.java                 # Stochastic LLM surrogate (Gamma latency)
      AgentDecision.java             # Decision enum + record
      ToolPool.java                  # Stochastic tool calls
    events/AgenticEvent.java         # Sealed event hierarchy
    infra/
      InfrastructureLayer.java       # CPU time-slicing, pod queuing (from v1)
      InfraResult.java               # Latency breakdown
    runtime/
      Orchestrator.java              # Event dispatcher, workload registry
      AgentService.java              # Agent loop with per-workload budgets
      Message.java                   # Token-carrying message
    scheduler/EventScheduler.java    # Priority queue event loop
    metrics/TrajectoryCollector.java  # CSV trajectory logger
```
