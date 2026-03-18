# Kubernetes Microservices Discrete Event Simulator (v1)

This project is a Java-based, event-driven simulator built with Spring Boot. It models the behavior of microservices deployed in a Kubernetes-like environment, simulating realistic system dynamics such as CPU time-slicing, thread pool exhaustion, request queuing, and network latency.

> **🚀 The Vision: An Agentic Simulator** This v1 release lays the deterministic foundation for what will become a fully **Agentic Simulator**. By establishing a strict event loop, explicit state tracking, and a realistic environment, future iterations will introduce AI agents capable of observing the system state and making dynamic, intelligent decisions in real-time (e.g., intelligent load balancing, predictive auto-scaling, and chaos engineering).

* * *

## Key Features

-   **Event-Driven Architecture:** The simulation jumps precisely from event to event (Arrivals, Pod Finishes, Network Transfers) using a Priority Queue, ensuring high performance.

-   **Concurrency & Time-Slicing:** Multiple requests run on the CPU simultaneously. The simulator dynamically adjusts the processing speed per job based on the number of active jobs sharing the node's CPU cores and frequency.

-   **Thread Pools & Queuing:** Pods act like real web servers with a maximum concurrency limit. Incoming requests are placed in a waiting queue if a Pod is at capacity.

-   **Load Balancing:** Deploys multiple replicas (Pods) per service and routes traffic using a Round-Robin strategy.

-   **Realistic Traffic Generation:** Simulates incoming user traffic using a Poisson Process (Exponential Distribution) for random, realistic arrival gaps.

-   **Metrics & Tracing:** Automatically tracks stopwatch metrics for requests and exports data to CSV files for Gantt chart visualization and queue monitoring.


* * *

## Architecture Overview

The simulation is broken down into two main configuration domains:

1.  **Infrastructure:** Defines the physical/virtual hardware constraints.

    -   `ComputingNodes`: Represents servers with specific core counts, CPU frequencies, and network bandwidth limits.

2.  **Application:** Defines the software topology.

    -   `Services`: Represents microservices with a specific workload (total instructions to execute).

    -   `ServiceCalls`: Represents the communication edges between services, including the payload size (bytes) transferred over the network.


* * *

## Prerequisites

-   **Java 17+** (or compatible version)

-   **Maven** (if running via command line)

-   **IntelliJ IDEA** (Optional, but recommended. Community or Ultimate edition)

-   **Lombok plugin** installed and enabled in your IDE to process the `@Data` and `@Builder` annotations.

-   **Python 3.x** (for running the visualization script) along with required plotting libraries (e.g., `pip install pandas matplotlib`).


* * *

## Configuration

The simulator relies on Spring Boot properties and two JSON files. Ensure these are placed in your `src/main/resources` directory.

### 1\. `application.properties`

Sets the Spring application name.

Properties

    spring.application.name=Simulator

### 2\. `infrastructure.json`

Defines the cluster's nodes, including their cores, frequency, and bandwidth.

JSON

    {
      "computingNodes": [
        {
          "node_id": 1,
          "cores": 4,
          "frequency": 3000000000.0,
          "bandwidth": 1000000000.0
        },
        {
          "node_id": 2,
          "cores": 1,
          "frequency": 1000000000.0,
          "bandwidth": 1000000000.0
        },
        {
          "node_id": 3,
          "cores": 2,
          "frequency": 2000000000.0,
          "bandwidth": 1000000000.0
        }
      ]
    }

### 3\. `application.json`

Defines the services (instructions per request) and how they communicate (bytes transferred).

JSON

    {
      "services": [
        {
          "service_id": 1,
          "totalInstructions": 6000000000,
          "nodeId": 1
        },
        {
          "service_id": 2,
          "totalInstructions": 5000000000,
          "nodeId": 2
        },
        {
          "service_id": 3,
          "totalInstructions": 4000000000,
          "nodeId": 3
        }
      ],
      "serviceCalls": [
        {
          "callerId": 1,
          "calleeId": 2,
          "bytes": 200000000
        },
        {
          "callerId": 2,
          "calleeId": 3,
          "bytes": 200000000
        }
      ]
    }

* * *

## How to Run

You can run the simulator either through an IDE or directly from your terminal. By default, the simulation runs for `T = 100.0` seconds. You can change this value inside the `run` method of `SimulatorApplication.java`.

### Option A: Running via Command Line (Maven)

If you prefer not to use an IDE, you can easily run the application using Maven:

1.  Open your terminal or command prompt.

2.  Navigate to the root directory of the project (where the `pom.xml` file is located).

3.  Execute the following Spring Boot command:

    Bash

        mvn spring-boot:run

4.  The project will compile, and you will see the simulation logs outputting directly in your terminal.


### Option B: Running in IntelliJ IDEA

1.  **Open the Project:** Launch IntelliJ IDEA, click **Open**, and select the root folder of your project.

2.  **Enable Annotation Processing:** Because the project uses Lombok, go to **File > Settings** (or **IntelliJ IDEA > Settings** on Mac), navigate to **Build, Execution, Deployment > Compiler > Annotation Processors**, and check the box for **Enable annotation processing**.

3.  **Locate the Main Class:** In the Project tool window (left side), navigate to `src/main/java/com/thesis/simulator/` and find `SimulatorApplication.java`.

4.  **Run the Application:** Right-click on `SimulatorApplication.java` and select **Run 'SimulatorApplication.main()'**.


* * *

## Simulation Outputs & Visualization

Upon completion, the simulator generates two CSV files in the root directory of your project:

-   **`simulation_trace_k8s.csv`**: Contains the timeline of events for every request (`RequestId`, `Type`, `Name`, `StartTime`, `EndTime`).

-   **`queue_trace.csv`**: Logs the exact size of every Pod's waiting queue at specific timestamps.


### Generating Visualizations

We use a Python script (`visualize2.py`) to parse these generated CSVs and output visual representations of the system's behavior.

To generate the graphs, open your terminal in the project root directory and run:

Bash

    python visualize2.py

_Note: Ensure you have your Python environment set up with the necessary data manipulation and plotting libraries (like `pandas` and `matplotlib`) before running the script._