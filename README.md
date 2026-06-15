# Kubernetes & Agentic Discrete-Event Simulator

This project is a Java-based, event-driven simulator built with Spring Boot. It models the behavior of microservices deployed in a Kubernetes-like environment, simulating realistic system dynamics such as CPU time-slicing, thread pool exhaustion, request queuing, and network latency. A second simulation mode extends this foundation with LLM-based agentic workflows.

---

## Simulation Modes

### V1: Kubernetes Microservices Simulation

Models traditional request/response microservices running on shared infrastructure. By establishing a strict event loop, explicit state tracking, and a realistic environment, this layer provides the deterministic foundation for the agentic simulation built on top.

### V2: Agentic Simulation

Extends V1's infrastructure model with LLM-based agentic workflows. Agents reason step-by-step: they generate text, invoke external tools, delegate to other agents, or fail -- all while consuming tokens, incurring inference latency, and competing for the same underlying infrastructure. Every agent step first goes through V1's infrastructure simulation (CPU scheduling, queuing) before the LLM call is dispatched, giving you the full end-to-end picture.

---

## Key Features

**Event-Driven Architecture:** The simulation jumps precisely from event to event (Arrivals, Pod Finishes, Network Transfers) using a Priority Queue, ensuring high performance.

**Concurrency & Time-Slicing:** Multiple requests run on the CPU simultaneously. The simulator dynamically adjusts the processing speed per job based on the number of active jobs sharing the node's CPU cores and frequency.

**Thread Pools & Queuing:** Pods act like real web servers with a maximum concurrency limit. Incoming requests are placed in a waiting queue if a Pod is at capacity.

**Load Balancing:** Deploys multiple replicas (Pods) per service and routes traffic using a Round-Robin strategy.

**Realistic Traffic Generation:** Simulates incoming user traffic using a Poisson Process (Exponential Distribution) for random, realistic arrival gaps.

**Stochastic LLM Inference (V2):** Gamma-distributed TTFT and TPOT latency modeling with per-token input/output pricing and budget constraints.

**Agent Decision Loop (V2):** Agents generate text, call tools with configurable latency and error rates, delegate to sub-agents, or fail -- with token-based cost tracking throughout.

**Multi-Workload Contention (V2):** Multiple concurrent workloads with independent arrival rates, token distributions, and budget constraints competing on the same infrastructure.

**Zone-Aware Networking (V2):** Edge, cloud, and fog zone latency modeling for realistic distributed deployments.

**Metrics & Tracing:** Automatically tracks metrics for requests and exports data to CSV files for visualization and analysis.

---

## Architecture Overview

The simulation is broken down into two main configuration domains:

**Infrastructure:** Defines the physical/virtual hardware constraints.
- `ComputingNodes`: Represents servers with specific core counts, CPU frequencies, and network bandwidth limits.

**Application:** Defines the software topology.
- `Services`: Represents microservices with a specific workload (total instructions to execute).
- `ServiceCalls`: Represents the communication edges between services, including the payload size (bytes) transferred over the network.

**Agentic Layer (V2):** Defines the agent topology.
- `LLM Models`: Inference profiles with latency distributions and token pricing.
- `Tools`: External tool profiles with latency and error rates.
- `Agent Services`: Agent definitions with LLM, tools, concurrency, and CPU cost per step.
- `Workloads`: Traffic definitions with arrival rates, token distributions, and budgets.

---

## Prerequisites

- **Java 21+**
- **Maven**
- **Lombok** plugin installed and enabled in your IDE to process the `@Data` and `@Builder` annotations.
- **Python 3.x** with required plotting libraries:

```bash
pip install pandas matplotlib fpdf2
```

---

## Configuration

The simulator relies on Spring Boot properties and JSON configuration files. Ensure these are placed in your `src/main/resources` directory.

### 1. `application.properties`

Sets the Spring application name.

```properties
spring.application.name=Simulator
```

### 2. `infrastructure.json` (V1)

Defines the cluster's nodes, including their cores, frequency, and bandwidth.

```json
{
  "computingNodes": [
    {
      "node_id": 1,
      "cores": 4,
      "frequency": 3000000000.0,
      "bandwidth": 1000000000.0
    }
  ]
}
```

### 3. `application.json` (V1)

Defines the services (instructions per request) and how they communicate (bytes transferred).

```json
{
  "services": [
    {
      "service_id": 1,
      "totalInstructions": 6000000000,
      "nodeId": 1
    }
  ],
  "serviceCalls": [
    {
      "callerId": 1,
      "calleeId": 2,
      "bytes": 200000000
    }
  ]
}
```

### 4. `agentic_config.json` (V2)

Defines the full agentic simulation: nodes, zone latencies, LLM model profiles, tools, agent services, simulation parameters, and workload definitions.

---

## How to Run

You can run the simulator either through an IDE or directly from your terminal.

### Option A: Running via Command Line (Maven)

**V1 -- Kubernetes Simulation:**
```bash
mvn spring-boot:run
```

**V2 -- Agentic Simulation:**
```bash
mvn spring-boot:run -Dspring-boot.run.arguments=agentic
```

### Option B: Running in IntelliJ IDEA

1. **Open the Project:** Launch IntelliJ IDEA, click Open, and select the root folder of your project.
2. **Enable Annotation Processing:** Go to File > Settings, navigate to Build, Execution, Deployment > Compiler > Annotation Processors, and check the box for Enable annotation processing.
3. **Locate the Main Class:** Navigate to `src/main/java/com/thesis/simulator/` and find `SimulatorApplication.java`.
4. **Run the Application:** Right-click on `SimulatorApplication.java` and select Run. For V2, add `agentic` to **Run Configuration > Program Arguments**.

---

## Simulation Outputs & Visualization

Upon completion, the simulator generates CSV files in the root directory of your project.

### V1 Output

- `simulation_trace_k8s.csv` -- Timeline of events for every request (RequestId, Type, Name, StartTime, EndTime).
- `queue_trace.csv` -- Size of every Pod's waiting queue at specific timestamps.

### V2 Output

- `agentic_trajectory.csv` -- Full event trajectory with per-workflow metrics and workload tags.
- Console summary with aggregate and per-workload statistics.

### Generating Visualizations

**V1:**
```bash
python visualize1.py
```

**V2:**
```bash
python visualize_agentic.py
```

Additional experiment visualization scripts are included: `visualize_experiment1.py` through `visualize_experiment4.py`.

> **Note:** Ensure you have your Python environment set up with the necessary libraries before running the scripts.

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
