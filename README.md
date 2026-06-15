<p align="center">
  <h1 align="center">Kubernetes & Agentic Discrete-Event Simulator</h1>
  <p align="center">
    A research-grade discrete-event simulator for modeling microservice and LLM-based agentic workloads on edge/cloud infrastructure.
    <br />
    Built with <strong>Java 21</strong> and <strong>Spring Boot</strong>.
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Java-21+-blue?logo=openjdk&logoColor=white" alt="Java 21+"/>
  <img src="https://img.shields.io/badge/Spring%20Boot-3.x-6DB33F?logo=springboot&logoColor=white" alt="Spring Boot"/>
  <img src="https://img.shields.io/badge/Build-Maven-C71A36?logo=apachemaven&logoColor=white" alt="Maven"/>
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white" alt="Python 3"/>
</p>

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Output & Visualization](#output--visualization)
- [Experiments](#experiments)
- [Project Structure](#project-structure)

---

## Overview

This simulator provides **two composable simulation layers** designed for studying performance, cost, and scheduling trade-offs in modern distributed systems.

### V1 -- Kubernetes Microservices Simulation

Models traditional request/response microservices running on shared infrastructure:

| Feature | Description |
|---|---|
| **CPU Time-Slicing** | Realistic contention across shared compute nodes |
| **Pod Thread Pools** | Configurable concurrency limits per pod |
| **Request Queuing** | Overflow queuing when pods reach capacity |
| **Load Balancing** | Round-robin distribution across pod replicas |
| **Network Latency** | Inter-service delays based on payload size |
| **Traffic Generation** | Poisson-distributed arrival streams |

### V2 -- Agentic Simulation

Extends V1's infrastructure model with LLM-based agentic workflows:

| Feature | Description |
|---|---|
| **Stochastic LLM Inference** | Gamma-distributed TTFT and TPOT latency |
| **Tool Invocations** | Configurable latency and error rates per tool |
| **Agent Decision Loop** | Generate text, call tools, delegate to sub-agents, or fail |
| **Token-Based Cost Tracking** | Per-token input/output pricing with budget constraints |
| **Zone-Aware Networking** | Edge, cloud, and fog zone latency modeling |
| **Multi-Workload Contention** | Independent arrival rates, token distributions, and budgets competing on shared infrastructure |

> **Key insight:** The two layers compose -- each agent step first incurs infrastructure cost (CPU contention from V1's physics), then dispatches the external LLM call. This captures the full end-to-end latency stack.

---

## Architecture

```
                     +-------------------------------+
                     |         V2 Workloads          |
                     |  (chat-light, tool-heavy, ..) |
                     |  each generates its own        |
                     |  Poisson arrival stream         |
                     +---------------+---------------+
                                     |
                                     v
                     +-------------------------------+
                     |           Agents              |
                     |  LLM calls, tool invocations, |
                     |  decisions, delegations        |
                     |  each step submits CPU work    |
                     +---------------+---------------+
                                     |
                                     v
                     +-------------------------------+
                     |    Infrastructure Layer (V1)   |
                     |  Pods, CPU time-slicing,       |
                     |  queuing, contention           |
                     +-------------------------------+
```

---

## Prerequisites

| Dependency | Version | Purpose |
|---|---|---|
| Java | 21+ | Core simulator runtime |
| Maven | 3.x | Build system |
| Lombok | -- | IDE plugin required |
| Python | 3.x | Visualization scripts |
| pandas | -- | Data analysis (`pip install pandas`) |
| matplotlib | -- | Chart generation (`pip install matplotlib`) |
| fpdf2 | -- | Tutorial PDF generation (`pip install fpdf2`) |

Quick install for Python dependencies:

```bash
pip install pandas matplotlib fpdf2
```

---

## Getting Started

### Run V1: Kubernetes Simulation

```bash
mvn spring-boot:run
```

### Run V2: Agentic Simulation

```bash
mvn spring-boot:run -Dspring-boot.run.arguments=agentic
```

**IntelliJ IDEA:** Add `agentic` to **Run Configuration > Program Arguments**.

---

## Configuration

### V1 Configuration

Located in `src/main/resources/`:

| File | Purpose |
|---|---|
| `infrastructure.json` | Computing nodes -- cores, frequency, bandwidth |
| `application.json` | Services -- instructions per request, service call data transfer sizes |

### V2 Configuration

Located in `src/main/resources/agentic_config.json`:

| Section | Purpose |
|---|---|
| `nodes` | Infrastructure nodes with zone, cores, frequency |
| `zonePairLatencies` | Network latency matrix between zones |
| `llmModels` | LLM profiles -- TTFT/TPOT distributions, token pricing, decision weights |
| `tools` | External tool profiles -- latency, error rate, response tokens |
| `agentServices` | Agent definitions -- LLM, tools, concurrency, replicas, CPU cost per step |
| `simulation` | Global parameters -- duration, random seed |
| `workloads` | Traffic definitions -- arrival rates, token distributions, budgets |

<details>
<summary><strong>Example: Multi-Workload Configuration</strong></summary>

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

Each workload generates an independent Poisson traffic stream. All workloads compete for the same infrastructure, producing realistic contention patterns.

</details>

---

## Output & Visualization

### V1

| Output File | Contents |
|---|---|
| `simulation_trace_k8s.csv` | Execution timeline (Gantt chart data) |
| `queue_trace.csv` | Queue depth per pod over time |

```bash
python visualize1.py
```

Produces a Gantt chart of request execution/wait times and queue depth over time.

### V2

| Output File | Contents |
|---|---|
| `agentic_trajectory.csv` | Full event trajectory with per-workflow metrics and workload tags |
| Console output | Aggregate and per-workload statistics summary |

```bash
python visualize_agentic.py
```

Produces per-workload analysis charts:

- **Latency distribution** -- Histogram and boxplot per workload
- **Cost & steps** -- Per-workflow cost scatter, step count distribution
- **Timeline & outcomes** -- Cumulative completions, completion reason breakdown
- **Infrastructure queuing** -- Agent queue depth, wait time distribution
- **Infrastructure latency** -- Per-step infra latency, compute vs queue wait

---

## Experiments

The repository includes four experiment suites with dedicated visualization scripts:

| Experiment | Script | Focus |
|---|---|---|
| Experiment 1 | `visualize_experiment1.py` | Baseline validation |
| Experiment 2 | `visualize_experiment2.py` | Scaling & contention |
| Experiment 3 | `visualize_experiment3.py` | Multi-workload interaction |
| Experiment 4 | `visualize_experiment4.py` | Advanced scenarios |

Results are stored as `exp*_trajectory.csv` files in the project root.

---

## Project Structure

```
src/main/java/com/thesis/simulator/
|
|-- SimulatorApplication.java             # Entry point (V1 or V2 based on args)
|-- Simulation.java                       # V1 discrete-event simulator
|-- JsonLoader.java                       # JSON config loader for V1
|-- TraceEvent.java, RequestResult.java   # V1 data types
|
|-- Application/                          # V1 service topology
|   |-- ApplicationConfig.java
|   |-- Services.java
|   +-- ServiceCall.java
|
|-- Infrastructure/                       # V1 node definitions
|   |-- InfrastructureConfig.java
|   |-- ComputingNodes.java
|   +-- NetworkNodes.java
|
+-- agentic/                              # V2 agentic simulation
    |-- AgenticSimulationRunner.java      # Main runner, config parsing, traffic gen
    |
    |-- config/
    |   +-- AgenticConfig.java            # All data records (Topology, WorkloadDef, ...)
    |
    |-- engine/
    |   |-- LLMEngine.java               # Stochastic LLM surrogate (Gamma latency)
    |   |-- AgentDecision.java           # Decision enum + record
    |   +-- ToolPool.java                # Stochastic tool calls
    |
    |-- events/
    |   +-- AgenticEvent.java            # Sealed event hierarchy
    |
    |-- infra/
    |   |-- InfrastructureLayer.java     # CPU time-slicing, pod queuing (from V1)
    |   +-- InfraResult.java             # Latency breakdown
    |
    |-- runtime/
    |   |-- Orchestrator.java            # Event dispatcher, workload registry
    |   |-- AgentService.java            # Agent loop with per-workload budgets
    |   +-- Message.java                 # Token-carrying message
    |
    |-- scheduler/
    |   +-- EventScheduler.java          # Priority queue event loop
    |
    +-- metrics/
        +-- TrajectoryCollector.java     # CSV trajectory logger
```

---

<p align="center">
  <sub>Developed as part of a Master's thesis on agentic simulation of edge/cloud systems.</sub>
</p>
