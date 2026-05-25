"""
Generates a PDF tutorial for the Agentic Simulation codebase.
Uses fpdf2 (pip install fpdf2).
"""
from fpdf import FPDF

class TutorialPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "Agentic Simulator - Extended Code Tutorial", align="C", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def chapter_title(self, title):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(20, 60, 120)
        self.ln(6)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(20, 60, 120)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def section_title(self, title):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(40, 90, 160)
        self.ln(4)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def subsection_title(self, title):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(60, 60, 60)
        self.ln(2)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def code_block(self, code):
        self.set_font("Courier", "", 8)
        self.set_fill_color(240, 240, 240)
        self.set_text_color(30, 30, 30)
        x = self.get_x()
        self.set_x(x + 4)
        for line in code.strip().split("\n"):
            safe = line.replace("\t", "    ")
            self.cell(180, 4.5, safe, fill=True, new_x="LMARGIN", new_y="NEXT")
            self.set_x(x + 4)
        self.ln(3)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        x = self.get_x()
        self.set_x(x + 6)
        self.cell(4, 5.5, "-")
        self.multi_cell(170, 5.5, text)
        self.ln(1)

    def key_value(self, key, value):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(30, 30, 30)
        x = self.get_x()
        self.set_x(x + 6)
        self.cell(60, 5.5, key)
        self.set_font("Helvetica", "", 10)
        self.multi_cell(120, 5.5, value)
        self.ln(0.5)


pdf = TutorialPDF()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()

# =============================================
# COVER / INTRO
# =============================================
pdf.set_font("Helvetica", "B", 26)
pdf.set_text_color(20, 60, 120)
pdf.ln(30)
pdf.cell(0, 15, "Agentic Simulator", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 16)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 10, "Extended Code Tutorial", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(10)
pdf.set_font("Helvetica", "", 11)
pdf.set_text_color(60, 60, 60)
pdf.cell(0, 7, "A Discrete Event Simulator for LLM-Based Agentic Workloads", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 7, "on Edge / Cloud Infrastructure", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(20)
pdf.set_font("Helvetica", "I", 10)
pdf.cell(0, 7, "Thesis Project - Master's Degree", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 7, "May 2026", align="C", new_x="LMARGIN", new_y="NEXT")


# =============================================
# TABLE OF CONTENTS
# =============================================
pdf.add_page()
pdf.chapter_title("Table of Contents")
toc = [
    "1. Overview & Motivation",
    "2. Architecture at a Glance",
    "3. Package Structure",
    "4. Configuration Layer (config/AgenticConfig.java)",
    "5. JSON Configuration File (agentic_config.json)",
    "6. Event System (events/AgenticEvent.java)",
    "7. Event Scheduler (scheduler/EventScheduler.java)",
    "8. Stochastic LLM Engine (engine/LLMEngine.java)",
    "9. Agent Decision Model (engine/AgentDecision.java)",
    "10. Tool Pool (engine/ToolPool.java)",
    "11. Infrastructure Layer (infra/InfrastructureLayer.java)",
    "12. Agent Service (runtime/AgentService.java)",
    "13. Orchestrator (runtime/Orchestrator.java)",
    "14. Message Record (runtime/Message.java)",
    "15. Trajectory Collector (metrics/TrajectoryCollector.java)",
    "16. Simulation Runner (AgenticSimulationRunner.java)",
    "17. Entry Point (SimulatorApplication.java)",
    "18. End-to-End Flow Example",
    "19. Key Design Decisions",
]
for item in toc:
    pdf.bullet(item)


# =============================================
# 1. OVERVIEW
# =============================================
pdf.add_page()
pdf.chapter_title("1. Overview & Motivation")
pdf.body_text(
    "This project is a Discrete Event Simulator (DES) that models the behavior of "
    "LLM-based agentic systems running on edge/cloud infrastructure. Instead of calling "
    "real LLM APIs (which would be expensive and slow), it uses stochastic models to "
    "simulate realistic latency, cost, and decision-making behavior."
)
pdf.body_text(
    "The simulator answers questions like:\n"
    "- How does placing an agent on the edge vs. cloud affect end-to-end latency?\n"
    "- What is the cost of running N concurrent agentic workflows per second?\n"
    "- How do concurrency limits and queuing affect tail latency?\n"
    "- What happens when tools fail or have high latency?"
)
pdf.body_text(
    "It is the v2 evolution of a Kubernetes microservice simulator (v1). While v1 modeled "
    "traditional request/response microservices with CPU time-slicing, v2 models agentic "
    "workflows where an LLM makes decisions in a loop: generate text, call tools, or delegate."
)

pdf.section_title("What makes it 'agentic'?")
pdf.body_text(
    "In a traditional microservice, the request follows a fixed path (Service A -> Service B -> C). "
    "In an agentic system, the LLM DECIDES the next step at each iteration. It might:\n"
    "  1. Generate a final text response (workflow completes)\n"
    "  2. Call an external tool (search, database, API) and loop back\n"
    "  3. Delegate to another agent\n"
    "  4. Fail\n\n"
    "This creates a variable-length, non-deterministic execution path that the simulator models "
    "using weighted random decisions and stochastic latency sampling."
)


# =============================================
# 2. ARCHITECTURE
# =============================================
pdf.add_page()
pdf.chapter_title("2. Architecture at a Glance")
pdf.body_text(
    "The simulator follows a classic Discrete Event Simulation pattern:\n\n"
    "1. A priority queue (min-heap) holds future events sorted by time.\n"
    "2. The event loop pops the earliest event and dispatches it.\n"
    "3. Processing an event may schedule new future events.\n"
    "4. Time is simulated (not real) - it jumps from event to event.\n\n"
    "This is single-threaded and deterministic given the same random seed."
)

pdf.section_title("Component Wiring Diagram")
pdf.code_block(
    "AgenticSimulationRunner\n"
    "  |-- loads JSON config --> Topology\n"
    "  |-- creates LLMEngine (stochastic LLM surrogate)\n"
    "  |-- creates ToolPool  (stochastic tool surrogate)\n"
    "  |-- creates InfrastructureLayer (v1 CPU/queue model)\n"
    "  |-- creates EventScheduler (priority queue)\n"
    "  |-- creates TrajectoryCollector (CSV logger)\n"
    "  |-- creates Orchestrator (event router)\n"
    "  |      |-- registers AgentService(s)\n"
    "  |\n"
    "  |-- generates Poisson traffic (workflow submissions)\n"
    "  |-- runs event loop: scheduler.run(orchestrator::process)\n"
    "  |-- exports trajectory CSV"
)

pdf.section_title("Two-Layer Architecture")
pdf.body_text(
    "The simulator uses a two-layer latency model:\n\n"
    "  Application Layer (v2): LLM inference, tool calls, agent decisions\n"
    "  Infrastructure Layer (v1): CPU time-slicing, pod queuing, contention\n\n"
    "When an agent processes a step, it first goes through the infrastructure layer "
    "(local CPU compute: context building, prompt formatting, response parsing), "
    "then dispatches the external LLM call. There is NO network cost between "
    "the two layers because they run on the same machine."
)
pdf.code_block(
    "Total step latency = infraLatencyMs + networkOut + inferenceMs + networkBack\n"
    "                     ^^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n"
    "                     from v1 (CPU)   from v2 (external LLM API call)"
)

pdf.section_title("Event Flow")
pdf.code_block(
    "User Request (Poisson)\n"
    "  --> [SUBMIT] Orchestrator schedules AgentReceive\n"
    "  --> [AGENT_RECEIVE] AgentService builds context\n"
    "      --> submits job to InfrastructureLayer (CPU compute)\n"
    "      --> schedules InfraComplete (after CPU + queue latency)\n"
    "  --> [INFRA_COMPLETE] CPU compute done, dispatch LLM call\n"
    "      --> schedules LlmComplete (after network + inference)\n"
    "  --> [LLM_COMPLETE] Branch on decision:\n"
    "      GENERATE_TEXT --> workflow SUCCESS, terminate\n"
    "      CALL_TOOL     --> schedule ToolComplete\n"
    "      DELEGATE      --> (reserved for multi-agent)\n"
    "      FAIL          --> workflow FAIL, terminate\n"
    "  --> [TOOL_COMPLETE] Result feeds back as new AgentReceive\n"
    "      --> loop continues until text/fail/budget exhausted"
)


# =============================================
# 3. PACKAGE STRUCTURE
# =============================================
pdf.add_page()
pdf.chapter_title("3. Package Structure")
pdf.code_block(
    "com.thesis.simulator.agentic/\n"
    "  |-- AgenticSimulationRunner.java   (main runner, wiring, traffic gen)\n"
    "  |\n"
    "  |-- config/\n"
    "  |     +-- AgenticConfig.java       (all data records: Topology, Zone,\n"
    "  |                                    LLMProfile, ToolProfile, InfraNode, etc.)\n"
    "  |-- engine/\n"
    "  |     +-- LLMEngine.java           (stochastic LLM: latency, cost, decisions)\n"
    "  |     +-- AgentDecision.java        (decision enum + record)\n"
    "  |     +-- ToolPool.java            (stochastic tool calls)\n"
    "  |\n"
    "  |-- infra/\n"
    "  |     +-- InfrastructureLayer.java  (v1 CPU model: time-slicing, queuing)\n"
    "  |     +-- InfraResult.java          (latency breakdown record)\n"
    "  |\n"
    "  |-- events/\n"
    "  |     +-- AgenticEvent.java        (sealed event hierarchy)\n"
    "  |\n"
    "  |-- runtime/\n"
    "  |     +-- Orchestrator.java        (event dispatcher + workflow submission)\n"
    "  |     +-- AgentService.java        (the agent loop: receive->infra->LLM->branch)\n"
    "  |     +-- Message.java             (token-carrying message record)\n"
    "  |\n"
    "  |-- scheduler/\n"
    "  |     +-- EventScheduler.java      (priority queue event loop)\n"
    "  |\n"
    "  +-- metrics/\n"
    "        +-- TrajectoryCollector.java  (in-memory log, CSV export)"
)

pdf.body_text(
    "The separation is intentional:\n"
    "- 'config' holds pure data (records) with no behavior.\n"
    "- 'engine' holds the stochastic models (LLM, tools) - the 'math'.\n"
    "- 'infra' holds the infrastructure layer (CPU contention, pod queuing) - ported from v1.\n"
    "- 'events' defines the message types flowing through the system.\n"
    "- 'runtime' holds the processing logic (agent loop, orchestrator).\n"
    "- 'scheduler' is the DES engine itself (reusable, generic).\n"
    "- 'metrics' handles observability and output."
)


# =============================================
# 4. CONFIG LAYER
# =============================================
pdf.add_page()
pdf.chapter_title("4. Configuration Layer")
pdf.body_text("File: config/AgenticConfig.java")
pdf.body_text(
    "This file contains only Java records (immutable data classes). No behavior, "
    "just structure. It defines the entire topology of a simulation experiment."
)

pdf.section_title("Zone")
pdf.code_block('public record Zone(String id) {}')
pdf.body_text(
    'A logical placement zone like "CLOUD", "EDGE", or "FOG". '
    "Agents, LLMs, and tools are each hosted in a zone. Network latency depends "
    "on zone pairs."
)

pdf.section_title("NetworkLink")
pdf.code_block(
    "public record NetworkLink(\n"
    "    String fromZone, String toZone,\n"
    "    double latencyMs, double bandwidthMbps\n"
    ") {}"
)
pdf.body_text(
    "A directed network link. When an agent in zone A calls an LLM in zone B, "
    "the simulator looks up the (A->B) link to add network latency. "
    "Every cross-zone call pays round-trip: A->B + B->A."
)

pdf.section_title("LLMProfile")
pdf.code_block(
    "public record LLMProfile(\n"
    "    String id,\n"
    "    double ttftMeanMs,        // Time To First Token (mean)\n"
    "    double ttftGammaShape,    // Gamma distribution shape param\n"
    "    double tpotMeanMs,        // Time Per Output Token (mean)\n"
    "    double tpotGammaShape,    // Gamma distribution shape param\n"
    "    int outputTokensMean,     // How many tokens per response\n"
    "    int outputTokensStd,\n"
    "    double pricePerInputToken,\n"
    "    double pricePerOutputToken,\n"
    "    String hostZone\n"
    ") {}"
)
pdf.body_text(
    "Stochastic profile of an LLM model. The key insight: real LLM inference latency "
    "follows a Gamma distribution (always positive, right-skewed with occasional outliers). "
    "Total latency = TTFT + outputTokens * TPOT.\n\n"
    "TTFT (Time To First Token) is the startup delay before streaming begins. "
    "TPOT (Time Per Output Token) is the per-token generation speed. "
    "Both are sampled from Gamma(shape, scale=mean/shape)."
)

pdf.section_title("ToolProfile")
pdf.code_block(
    "public record ToolProfile(\n"
    "    String id,\n"
    "    double latencyMeanMs, double latencyStdMs,\n"
    "    int responseTokensMean,\n"
    "    double errorRate,\n"
    "    String hostZone\n"
    ") {}"
)
pdf.body_text(
    "Profile for external tools (search APIs, databases, MCP functions). "
    "Latency is Gaussian. Tools can fail with a configurable error rate."
)

pdf.section_title("InfraNode")
pdf.code_block(
    "public record InfraNode(\n"
    "    int nodeId, String zone,\n"
    "    int cores, double frequencyHz,\n"
    "    double bandwidthBytesPerSec\n"
    ") {}"
)
pdf.body_text(
    "Physical/virtual infrastructure node. Used by the InfrastructureLayer to model "
    "CPU time-slicing and contention. When multiple jobs run on the same node, "
    "each gets a share: speedPerJob = (cores / activeJobCount) * frequencyHz."
)

pdf.section_title("AgentDefinition")
pdf.code_block(
    "public record AgentDefinition(\n"
    "    String id,\n"
    "    String llmProfileId,       // which LLM this agent uses\n"
    "    List<String> toolIds,      // which tools are available\n"
    "    String hostZone,\n"
    "    int maxConcurrency,        // thread pool size\n"
    "    double coldStartMs,        // container startup penalty\n"
    "    long instructionsPerStep,  // CPU work per agent step\n"
    "    int replicas               // number of pod replicas\n"
    ") {}"
)
pdf.body_text(
    "Defines an agent service. Each agent is hosted in a zone, uses a specific LLM, "
    "has access to certain tools, and has a concurrency limit (like a Pod's thread pool). "
    "When all slots are busy, new requests queue up.\n\n"
    "instructionsPerStep defines how much CPU work each agent step requires "
    "(context building, prompt formatting, response parsing). This is processed by the "
    "infrastructure layer before the LLM call. replicas sets how many pod instances "
    "are deployed (round-robin across nodes), matching v1's pod deployment model."
)

pdf.section_title("Topology & WorkflowSpec")
pdf.code_block(
    "public record Topology(\n"
    "    List<Zone> zones,\n"
    "    List<NetworkLink> links,\n"
    "    Map<String, LLMProfile> llmProfiles,\n"
    "    Map<String, ToolProfile> tools,\n"
    "    Map<String, AgentDefinition> agents,\n"
    "    List<InfraNode> infraNodes,\n"
    "    WorkflowSpec workflow\n"
    ") {}\n\n"
    "public record WorkflowSpec(\n"
    "    String entryAgent, int initialPromptTokens,\n"
    "    int maxSteps, int maxTokens\n"
    ") {}"
)
pdf.body_text(
    "Topology bundles the entire experiment configuration including infrastructure nodes. "
    "WorkflowSpec defines safety limits: "
    "max steps per workflow (prevents infinite loops) and max tokens (budget cap)."
)


# =============================================
# 5. JSON CONFIG
# =============================================
pdf.add_page()
pdf.chapter_title("5. JSON Configuration File")
pdf.body_text("File: src/main/resources/agentic_config.json")
pdf.body_text(
    "This JSON drives the entire simulation. Here is the current config with explanations:"
)

pdf.section_title("Nodes & Zones")
pdf.code_block(
    '"nodes": [{\n'
    '  "nodeId": 1, "zone": "CLOUD",\n'
    '  "cores": 8, "frequencyHz": 3e9,\n'
    '  "vramGB": 80, "bandwidthBytesPerSec": 1.25e9\n'
    '}]'
)
pdf.body_text(
    "Defines physical/virtual nodes. Each node belongs to a zone (CLOUD, EDGE, etc.). "
    "These specs are used by both the zone system (for network latency) and the "
    "InfrastructureLayer (for CPU time-slicing and contention modeling)."
)

pdf.section_title("Zone Pair Latencies")
pdf.code_block('"zonePairLatencies": [\n  { "from": "CLOUD", "to": "CLOUD", "latencyMs": 1.0 }\n]')
pdf.body_text(
    "Network latency between zones. CLOUD->CLOUD is 1ms (intra-datacenter). "
    "For multi-zone experiments, you would add entries like "
    'EDGE->CLOUD: 50ms, CLOUD->EDGE: 50ms.'
)

pdf.section_title("LLM Models")
pdf.code_block(
    '"llmModels": [{\n'
    '  "modelId": "gpt-4o",\n'
    '  "ttftMeanMs": 400.0, "ttftGammaShape": 4.0,\n'
    '  "tpotMeanMs": 25.0,  "tpotGammaShape": 10.0,\n'
    '  "outputTokensMean": 150.0, "outputTokensStdDev": 50.0,\n'
    '  "costPerInputToken": 0.0000025,\n'
    '  "costPerOutputToken": 0.00001,\n'
    '  "hostZone": "CLOUD",\n'
    '  "decisionWeights": { "generate_text": 0.4, "call_tool": 0.6 }\n'
    '}]'
)
pdf.body_text(
    "This defines a GPT-4o-like model with:\n"
    "- TTFT ~ Gamma(shape=4, mean=400ms) -> typical range: 100-800ms\n"
    "- TPOT ~ Gamma(shape=10, mean=25ms) -> typical range: 15-40ms per token\n"
    "- Output length ~ Gaussian(mean=150, std=50) tokens\n"
    "- Cost: $2.50/M input tokens, $10/M output tokens\n"
    "- Decision weights: 60% chance to call a tool, 40% to generate final text"
)

pdf.section_title("Tools")
pdf.code_block(
    '"tools": [{\n'
    '  "toolId": "search-tool",\n'
    '  "latencyMeanMs": 200.0, "latencyStdDevMs": 50.0,\n'
    '  "resultTokensMean": 300,\n'
    '  "errorRate": 0.0,\n'
    '  "hostZone": "CLOUD"\n'
    '}]'
)
pdf.body_text("A search tool with ~200ms latency returning ~300 tokens. 0% error rate.")

pdf.section_title("Agent Services")
pdf.code_block(
    '"agentServices": [{\n'
    '  "serviceId": "agent-1",\n'
    '  "nodeId": 1, "modelId": "gpt-4o",\n'
    '  "maxConcurrency": 10, "hostZone": "CLOUD",\n'
    '  "instructionsPerStep": 50000000,\n'
    '  "replicas": 2\n'
    '}]'
)
pdf.body_text(
    "Each agent has infrastructure properties:\n"
    "- instructionsPerStep: 50M instructions of CPU work per step (context building, "
    "prompt formatting, response parsing). On an 8-core 3GHz node with no contention, "
    "this takes ~2ms. Under heavy load with CPU sharing, it takes longer.\n"
    "- replicas: 2 pod instances deployed round-robin across infrastructure nodes."
)

pdf.section_title("Simulation Parameters")
pdf.code_block(
    '"simulation": {\n'
    '  "durationSeconds": 100.0,\n'
    '  "arrivalRate": 0.5,\n'
    '  "userMessageTokensMean": 50.0,\n'
    '  "userMessageTokensStdDev": 20.0,\n'
    '  "maxStepsPerWorkflow": 10,\n'
    '  "maxTokensPerWorkflow": 10000,\n'
    '  "seed": 42\n'
    '}'
)
pdf.body_text(
    "Run for 100 seconds of simulated time. Users arrive at 0.5 requests/second "
    "(Poisson process). Each user message is ~50 tokens. Workflows are capped at "
    "10 agent steps or 10,000 tokens. Seed=42 for reproducibility."
)


# =============================================
# 6. EVENTS
# =============================================
pdf.add_page()
pdf.chapter_title("6. Event System")
pdf.body_text("File: events/AgenticEvent.java")
pdf.body_text(
    "This uses Java's sealed interface + records for type-safe, exhaustive event types. "
    "Every event has a timeMs() and is Comparable (sorted by time in the priority queue)."
)

pdf.section_title("Event Types")

pdf.subsection_title("TaskSubmit")
pdf.body_text("Reserved placeholder for queued submissions. Not used in the current flow.")

pdf.subsection_title("AgentReceive")
pdf.code_block(
    "record AgentReceive(double timeMs, String workflowId,\n"
    "                    String agentId, Message message)"
)
pdf.body_text(
    "A message has arrived at an agent and is ready for processing. This is the entry "
    "point for every agent step. Carries the input tokens via Message."
)

pdf.subsection_title("InfraComplete")
pdf.code_block(
    "record InfraComplete(double timeMs, String workflowId,\n"
    "    String agentId, String infraJobId,\n"
    "    AgentDecision decision, double cost,\n"
    "    int outputTokens, double networkOut,\n"
    "    double inferenceMs, double networkBack)"
)
pdf.body_text(
    "The infrastructure compute (CPU work) has completed. The agent can now dispatch "
    "the external LLM call. This event carries forward all the pre-sampled LLM values "
    "(decision, cost, tokens, latency) so the LLM call can be scheduled immediately. "
    "On firing, the infrastructure resources are released (CPU slot freed, next queued "
    "job dequeued)."
)

pdf.subsection_title("LlmComplete")
pdf.code_block(
    "record LlmComplete(double timeMs, String workflowId,\n"
    "    String agentId, AgentDecision decision,\n"
    "    double costAccrued, int outputTokens)"
)
pdf.body_text(
    "The LLM has finished generating. The decision field tells the agent what to do next: "
    "generate text (finish), call a tool (loop), delegate, or fail."
)

pdf.subsection_title("ToolComplete")
pdf.code_block(
    "record ToolComplete(double timeMs, String workflowId,\n"
    "    String agentId, String toolId,\n"
    "    int responseTokens, boolean errored)"
)
pdf.body_text(
    "A tool call has returned. If errored=true, the workflow terminates. "
    "Otherwise, the response tokens feed back as a new AgentReceive."
)

pdf.subsection_title("WorkflowComplete")
pdf.code_block(
    "record WorkflowComplete(double timeMs, String workflowId,\n"
    "    String reason, double totalLatencyMs,\n"
    "    double totalCostUsd, int totalSteps)"
)
pdf.body_text(
    "Terminal event. Reason can be: SUCCESS, BUDGET_EXHAUSTED, TOOL_FAILURE, or LLM_FAIL."
)


# =============================================
# 7. SCHEDULER
# =============================================
pdf.add_page()
pdf.chapter_title("7. Event Scheduler")
pdf.body_text("File: scheduler/EventScheduler.java")
pdf.body_text(
    "The heart of any DES. This is intentionally minimal - just a priority queue wrapper."
)
pdf.code_block(
    "public class EventScheduler {\n"
    "    private final PriorityQueue<AgenticEvent> queue = new PriorityQueue<>();\n"
    "    private double now = 0.0;\n\n"
    "    public void schedule(AgenticEvent ev) {\n"
    "        // Cannot schedule events in the past\n"
    "        if (ev.timeMs() < now) throw ...;\n"
    "        queue.offer(ev);\n"
    "    }\n\n"
    "    public void run(Consumer<AgenticEvent> handler) {\n"
    "        while (!queue.isEmpty()) {\n"
    "            AgenticEvent ev = queue.poll();  // earliest event\n"
    "            now = ev.timeMs();               // advance clock\n"
    "            handler.accept(ev);              // process it\n"
    "        }\n"
    "    }\n"
    "}"
)
pdf.body_text(
    "Key points:\n"
    "- PriorityQueue sorts events by timeMs() (via Comparable).\n"
    "- The run() loop is the main simulation loop - it processes ALL events.\n"
    "- Processing one event (e.g., AgentReceive) typically schedules new future events "
    "(e.g., LlmComplete at time now + latency). This is how the simulation progresses.\n"
    "- Single-threaded: no real concurrency, just simulated time."
)


# =============================================
# 8. LLM ENGINE
# =============================================
pdf.add_page()
pdf.chapter_title("8. Stochastic LLM Engine")
pdf.body_text("File: engine/LLMEngine.java")
pdf.body_text(
    "This is the mathematical core. It does NOT call any real LLM API. Instead, it "
    "samples from probability distributions that match real-world LLM behavior."
)

pdf.section_title("Latency Model")
pdf.code_block(
    "latency = TTFT + outputTokens * TPOT\n\n"
    "TTFT ~ Gamma(shape, scale = mean/shape)\n"
    "TPOT ~ Gamma(shape, scale = mean/shape)"
)
pdf.body_text(
    "Why Gamma distribution?\n"
    "- Always positive (latency cannot be negative)\n"
    "- Right-skewed (occasional high-latency outliers, matching real LLM behavior)\n"
    "- Two-parameter: shape controls the 'spread', mean sets the center\n"
    "- When shape is large (e.g., 10), Gamma approaches Gaussian\n"
    "- When shape is small (e.g., 2), there's a long right tail\n\n"
    "The implementation uses Marsaglia & Tsang's (2000) rejection sampling method, "
    "which is the standard efficient algorithm for Gamma sampling."
)

pdf.section_title("Decision Model")
pdf.code_block(
    "public AgentDecision decide(int inputTokens, List<String> availableTools) {\n"
    "    return decisionPolicy.apply(inputTokens, availableTools);\n"
    "}"
)
pdf.body_text(
    "The decision policy is a pluggable BiFunction injected via the constructor. "
    "The current implementation is a weighted random chooser:\n"
    "  - Roll a random number [0, 1)\n"
    "  - Walk through the cumulative weights (e.g., call_tool=0.6, generate_text=0.4)\n"
    "  - Return the first action whose cumulative weight exceeds the roll\n\n"
    "This means with the default config: 60% of LLM steps call a tool, 40% finish."
)

pdf.section_title("Cost Model")
pdf.code_block("cost = inputTokens * pricePerInputToken + outputTokens * pricePerOutputToken")
pdf.body_text("Straightforward token-based pricing. Accumulated per workflow.")


# =============================================
# 9. AGENT DECISION
# =============================================
pdf.add_page()
pdf.chapter_title("9. Agent Decision Model")
pdf.body_text("File: engine/AgentDecision.java")
pdf.code_block(
    "public record AgentDecision(Kind kind, String targetId, int outputTokens) {\n"
    "    public enum Kind {\n"
    "        GENERATE_TEXT,  // Final answer -> workflow completes\n"
    "        CALL_TOOL,      // Invoke a tool -> loop back\n"
    "        DELEGATE,       // Hand off to another agent\n"
    "        FAIL            // LLM failure\n"
    "    }\n"
    "}"
)
pdf.body_text(
    "Simple value object representing what the LLM decided to do:\n"
    "- GENERATE_TEXT: The agent produces a final answer. targetId is null.\n"
    "- CALL_TOOL: targetId = the tool ID (e.g., 'search-tool').\n"
    "- DELEGATE: targetId = another agent's ID. (Not yet implemented in v2.)\n"
    "- FAIL: Simulates LLM failure/hallucination.\n\n"
    "Factory methods (text(), tool(), delegate(), fail()) create instances cleanly."
)


# =============================================
# 10. TOOL POOL
# =============================================
pdf.chapter_title("10. Tool Pool")
pdf.body_text("File: engine/ToolPool.java")
pdf.body_text(
    "Stochastic surrogate for external tool calls. Much simpler than LLMEngine."
)
pdf.code_block(
    "sampleLatencyMs(toolId):\n"
    "  latency ~ Gaussian(mean, stdDev), clamped >= 0\n\n"
    "sampleError(toolId):\n"
    "  return random() < errorRate\n\n"
    "sampleResponseTokens(toolId):\n"
    "  return profile.responseTokensMean  (fixed, not random)"
)
pdf.body_text(
    "Tool latency uses Gaussian (can go near zero, unlike LLM which uses Gamma). "
    "Error sampling is a simple Bernoulli trial. Response tokens are currently fixed "
    "(could be made stochastic in a future version)."
)


# =============================================
# 11. INFRASTRUCTURE LAYER
# =============================================
pdf.add_page()
pdf.chapter_title("11. Infrastructure Layer")
pdf.body_text("File: infra/InfrastructureLayer.java")
pdf.body_text(
    "This class bridges v1 (Kubernetes simulator) and v2 (agentic simulator). It models "
    "the physical infrastructure that agents run on: CPU time-slicing, pod queuing, "
    "and contention effects. The math is ported directly from v1's Simulation.java."
)

pdf.section_title("Why Two Layers?")
pdf.body_text(
    "In v2, agents are microservices running on physical hardware. When an agent "
    "processes a step (builds context, formats prompt, parses response), that work "
    "requires CPU time on a real node. If multiple workflows hit the same node "
    "simultaneously, they share CPU and each gets slower.\n\n"
    "Previously, v2 only modeled application-level latency (LLM inference, tool calls). "
    "Now the infrastructure layer adds the hardware cost on top, giving realistic "
    "contention effects under load."
)

pdf.section_title("State (persists across calls)")
pdf.code_block(
    "Map<String, List<Pod>> agentToPods       // pods per agent\n"
    "Map<Integer, List<ActiveJob>> nodeActiveJobs  // CPU jobs per node\n"
    "Map<Integer, InfraNode> nodeMap           // node specs\n"
    "Map<String, ActiveJob> jobIndex           // lookup by job ID"
)

pdf.section_title("Inner Classes")
pdf.subsection_title("Pod")
pdf.body_text(
    "Same concept as v1's Pod: a container replica with a thread pool. "
    "Has activeRequests counter, maxConcurrency limit, and a request queue."
)
pdf.subsection_title("ActiveJob")
pdf.body_text(
    "Tracks a running job on a CPU: remaining instructions, current speed "
    "(recalculated when jobs arrive/depart), and the pod it belongs to."
)

pdf.section_title("submitJob(agentId, jobId, nowMs, instructions)")
pdf.body_text(
    "Called when an agent step begins. Returns estimated infrastructure latency:\n\n"
    "1. Pick pod via round-robin load balancing\n"
    "2. If pod at capacity: estimate queue wait from earliest-finishing job\n"
    "3. updateProgress(): settle all running jobs to current time\n"
    "4. Add new ActiveJob to the node\n"
    "5. rescheduleNode(): recalculate speeds for all jobs on the node\n"
    "   speedPerJob = (cores / totalActiveJobs) * frequencyHz\n"
    "6. computeTimeMs = (instructions / speedPerJob) * 1000\n"
    "7. Return InfraResult(queueWaitMs + computeTimeMs)"
)

pdf.section_title("releaseJob(jobId, nowMs)")
pdf.body_text(
    "Called when infrastructure compute completes (InfraComplete event fires):\n\n"
    "1. Update progress on all node jobs\n"
    "2. Remove completed job from active list\n"
    "3. Free pod thread (activeRequests--)\n"
    "4. Dequeue next waiting job if any\n"
    "5. Recalculate speeds (remaining jobs speed up)"
)

pdf.section_title("Contention Example")
pdf.body_text(
    "Node: 8 cores, 3GHz. Agent step: 50M instructions.\n\n"
    "1 concurrent job:  speed = 8 * 3GHz = 24GHz  ->  50M/24G = 2.1ms\n"
    "5 concurrent jobs: speed = 1.6 * 3GHz = 4.8GHz -> 50M/4.8G = 10.4ms\n"
    "10 concurrent jobs: speed = 0.8 * 3GHz = 2.4GHz -> 50M/2.4G = 20.8ms\n\n"
    "Under heavy load, infrastructure latency grows 10x. This is the whole point "
    "of integrating v1's model."
)

pdf.section_title("InfraResult")
pdf.code_block(
    "public record InfraResult(\n"
    "    double infraLatencyMs,  // total: queue + compute\n"
    "    double queueWaitMs,     // time spent waiting for pod capacity\n"
    "    double computeMs        // time spent on CPU\n"
    ") {}"
)


# =============================================
# 12. AGENT SERVICE
# =============================================
pdf.add_page()
pdf.chapter_title("12. Agent Service - The Agent Loop")
pdf.body_text("File: runtime/AgentService.java")
pdf.body_text(
    "This is the most complex class - it implements the full agentic processing loop. "
    "Think of it as a simulated microservice container running an LLM agent."
)

pdf.section_title("Concurrency Model")
pdf.code_block(
    "private int activeRequests = 0;\n"
    "private final Queue<AgenticEvent.AgentReceive> waitingQueue = new LinkedList<>();"
)
pdf.body_text(
    "Each agent has maxConcurrency slots (like a thread pool). When all slots are busy, "
    "new requests enter a FIFO queue. When a workflow completes, it frees a slot and the "
    "next queued request is dequeued. This mirrors real container behavior "
    "(Tomcat/Jetty thread pools in Kubernetes Pods)."
)

pdf.section_title("Per-Workflow State: WorkflowContext")
pdf.code_block(
    "private static class WorkflowContext {\n"
    "    final String workflowId;\n"
    "    final double startedAtMs;\n"
    "    int stepIndex = 0;\n"
    "    int accumulatedInputTokens = 0;\n"
    "    int accumulatedOutputTokens = 0;\n"
    "    double totalCostUsd = 0.0;\n"
    "}"
)
pdf.body_text(
    "Each workflow gets its own context tracking: step count, accumulated tokens, "
    "and cost. This is keyed by workflowId in a HashMap. Context is created on first "
    "receive and destroyed on termination."
)

pdf.section_title("Step-by-Step Processing")

pdf.subsection_title("Step 1: onReceive(AgentReceive)")
pdf.body_text(
    "Entry point. Checks concurrency:\n"
    "- If at capacity: queue the request, log QUEUE_ENTER, return.\n"
    "- Otherwise: increment activeRequests, proceed to processReceive()."
)

pdf.subsection_title("Step 2: processReceive()")
pdf.body_text(
    "- Get or create WorkflowContext for this workflowId.\n"
    "- Increment step counter, accumulate input tokens.\n"
    "- Budget check: if steps > maxSteps or tokens > maxTokens, terminate.\n"
    "- Look up the LLM profile (from agent's llmProfileId).\n"
    "- Calculate network latency: agent zone -> LLM zone -> agent zone.\n"
    "- Sample output tokens, decision, inference latency, and cost from LLMEngine.\n"
    "- Submit job to InfrastructureLayer (CPU compute for context building).\n"
    "- Schedule InfraComplete at time: now + infraLatencyMs.\n"
    "  (carries forward all LLM values for the next step)"
)

pdf.subsection_title("Step 3: onInfraComplete(InfraComplete)")
pdf.body_text(
    "Infrastructure CPU compute has finished:\n"
    "- Release infrastructure resources (infraLayer.releaseJob).\n"
    "- Now schedule the external LLM call.\n"
    "- Schedule LlmComplete at time: now + networkOut + inference + networkBack."
)

pdf.subsection_title("Step 4: onLlmComplete(LlmComplete)")
pdf.body_text(
    "The LLM has responded. Branch on the decision:\n"
    "- GENERATE_TEXT -> terminate with SUCCESS\n"
    "- CALL_TOOL -> dispatchTool()\n"
    "- DELEGATE -> terminate with DELEGATE_NOT_IMPLEMENTED\n"
    "- FAIL -> terminate with LLM_FAIL"
)

pdf.subsection_title("Step 5: dispatchTool()")
pdf.body_text(
    "- Look up tool profile for network zone.\n"
    "- Calculate network latency: agent zone -> tool zone -> agent zone.\n"
    "- Sample tool latency and error flag.\n"
    "- Schedule ToolComplete at time: now + networkOut + toolMs + networkBack."
)

pdf.subsection_title("Step 6: onToolComplete(ToolComplete)")
pdf.body_text(
    "- If errored: terminate with TOOL_FAILURE.\n"
    "- Otherwise: create a follow-up Message with the tool's response tokens.\n"
    "- Call processReceive() directly (no re-check concurrency - this workflow already "
    "holds a slot). This creates the LOOP back to Step 2."
)

pdf.subsection_title("Termination: terminate()")
pdf.body_text(
    "- Schedule WorkflowComplete event with total latency, cost, and step count.\n"
    "- Remove WorkflowContext.\n"
    "- Decrement activeRequests (free concurrency slot).\n"
    "- Call tryDequeue() to process waiting requests."
)


# =============================================
# 13. ORCHESTRATOR
# =============================================
pdf.add_page()
pdf.chapter_title("13. Orchestrator")
pdf.body_text("File: runtime/Orchestrator.java")
pdf.body_text(
    "Simple event router and workflow entry point. Two responsibilities:"
)

pdf.section_title("1. submit(workflowId, promptTokens, now)")
pdf.body_text(
    "Creates the initial Message (from 'USER' to the entry agent) and schedules "
    "the first AgentReceive event. This is how workflows enter the system."
)

pdf.section_title("2. process(AgenticEvent)")
pdf.body_text(
    "Central dispatch method wired into the scheduler's main loop. Uses Java's "
    "pattern matching (instanceof) to route each event type to the correct AgentService method:"
)
pdf.code_block(
    "AgentReceive   -> agents.get(agentId).onReceive()\n"
    "InfraComplete  -> agents.get(agentId).onInfraComplete()\n"
    "LlmComplete    -> agents.get(agentId).onLlmComplete()\n"
    "ToolComplete   -> agents.get(agentId).onToolComplete()\n"
    "WorkflowComplete -> log final metrics to TrajectoryCollector"
)


# =============================================
# 14. MESSAGE
# =============================================
pdf.chapter_title("14. Message Record")
pdf.body_text("File: runtime/Message.java")
pdf.code_block(
    "public record Message(\n"
    "    long id,           // auto-incrementing\n"
    "    String fromAgent,  // sender ('USER', 'search-tool', etc.)\n"
    "    String toAgent,    // receiver (agent ID)\n"
    "    int inputTokens,   // token count (not bytes)\n"
    "    Object payload,    // type-erased content\n"
    "    double createdAtMs // timestamp\n"
    ") {}"
)
pdf.body_text(
    "The data unit exchanged between entities. Key difference from v1's ServiceCall: "
    "it carries TOKEN counts, not byte counts. This is the fundamental unit of "
    "agentic workloads - everything is measured in tokens."
)


# =============================================
# 15. TRAJECTORY COLLECTOR
# =============================================
pdf.add_page()
pdf.chapter_title("15. Trajectory Collector")
pdf.body_text("File: metrics/TrajectoryCollector.java")
pdf.body_text(
    "In-memory event log that writes to CSV. Every significant event in the simulation "
    "is recorded with a flexible key-value payload."
)
pdf.code_block(
    "void log(workflowId, entityId, eventType, timeMs, Map<String, Object> payload)\n\n"
    "// Creates a Row(workflowId, entityId, eventType, timeMs, payload)\n"
    "// Payload keys are dynamic (different per event type)"
)
pdf.body_text(
    "The writeCsv() method discovers ALL payload keys across ALL rows and writes them "
    "as columns. This means the CSV schema is self-adapting: adding new payload fields "
    "in the code automatically creates new CSV columns.\n\n"
    "Example output columns:\n"
    "time_ms, workflow_id, entity_id, event_type, step, input_tokens, decision, "
    "cost_usd, network_out_ms, inference_ms, ..."
)


# =============================================
# 16. SIMULATION RUNNER
# =============================================
pdf.add_page()
pdf.chapter_title("16. Simulation Runner")
pdf.body_text("File: AgenticSimulationRunner.java")
pdf.body_text(
    "The main orchestration class. It wires everything together and runs the simulation. "
    "Here is what run(configPath) does, step by step:"
)

pdf.section_title("Phase 1: Load Configuration")
pdf.body_text(
    "Reads the JSON config file using Jackson. Parses it into a Topology object "
    "containing all zones, links, LLM profiles, tool profiles, and agent definitions."
)

pdf.section_title("Phase 2: Build Decision Policy")
pdf.body_text(
    "Creates the weighted random decision function from the config's decisionWeights. "
    "This is a lambda/BiFunction that, given (inputTokens, availableTools), "
    "rolls a random number and picks call_tool, generate_text, delegate, or fail "
    "based on cumulative probabilities."
)

pdf.section_title("Phase 3: Create Components")
pdf.code_block(
    "LLMEngine llm = new LLMEngine(new Random(seed), decisionPolicy);\n"
    "ToolPool tools = new ToolPool(topology.tools(), new Random(seed+1));\n"
    "InfrastructureLayer infraLayer = new InfrastructureLayer(\n"
    "    topology.infraNodes(), topology.agents());\n"
    "EventScheduler scheduler = new EventScheduler();\n"
    "TrajectoryCollector trace = new TrajectoryCollector();\n"
    "Orchestrator orchestrator = new Orchestrator(topology, scheduler, trace);\n\n"
    "// Register all agents\n"
    "for each agent in topology:\n"
    "    AgentService agent = new AgentService(\n"
    "        def, topology, llm, tools, scheduler, trace, infraLayer);\n"
    "    orchestrator.registerAgent(agentId, agent);"
)

pdf.section_title("Phase 4: Generate Traffic (Poisson Process)")
pdf.code_block(
    "while (currentArrivalMs <= totalDuration) {\n"
    "    promptTokens = Gaussian(mean=50, std=20);\n"
    "    orchestrator.submit('wf-NNNN', promptTokens, currentArrivalMs);\n\n"
    "    // Exponential inter-arrival time\n"
    "    gap = -ln(U) / lambda;  // U ~ Uniform(0,1)\n"
    "    currentArrivalMs += gap;\n"
    "}"
)
pdf.body_text(
    "Poisson process: events arrive at random intervals where the gaps follow an "
    "exponential distribution. With lambda=0.5/s over 100s, this generates ~50 workflows. "
    "The exact count varies due to randomness."
)

pdf.section_title("Phase 5: Run Event Loop")
pdf.code_block("scheduler.run(orchestrator::process);")
pdf.body_text(
    "One line, but this IS the entire simulation. The scheduler drains its priority queue, "
    "calling orchestrator.process() for each event. Processing events schedules new events. "
    "The loop runs until no more events exist."
)

pdf.section_title("Phase 6: Export & Summary")
pdf.body_text(
    "Writes trajectory CSV and prints summary statistics: completed workflows, "
    "success rate, average/max latency, total cost, total steps."
)


# =============================================
# 17. ENTRY POINT
# =============================================
pdf.add_page()
pdf.chapter_title("17. Entry Point")
pdf.body_text("File: SimulatorApplication.java")
pdf.body_text(
    "Spring Boot application with two modes:\n"
    "- Default (no args): runs v1 Kubernetes microservice simulation.\n"
    '- With "agentic" argument: runs v2 agentic simulation.\n\n'
    "The agentic path simply creates an AgenticSimulationRunner and calls run()."
)
pdf.code_block(
    'if (args contains "agentic") {\n'
    "    new AgenticSimulationRunner().run(\"agentic_config.json\");\n"
    "} else {\n"
    "    // v1 Kubernetes simulation\n"
    "}"
)


# =============================================
# 18. END-TO-END FLOW
# =============================================
pdf.add_page()
pdf.chapter_title("18. End-to-End Flow Example")
pdf.body_text(
    "Let's trace a single workflow through the entire system with the default config: "
    "1 agent (agent-1) in CLOUD with 2 replicas, 1 LLM (gpt-4o) in CLOUD, "
    "1 tool (search-tool) in CLOUD, intra-cloud latency = 1ms, "
    "node: 8 cores @ 3GHz, agent: 50M instructions/step."
)

pdf.section_title("t=0.000ms: Workflow Submitted")
pdf.body_text(
    "Poisson traffic generator creates workflow 'wf-0001' with 50 prompt tokens. "
    "Orchestrator creates Message(USER -> agent-1, 50 tokens) and schedules AgentReceive at t=0."
)

pdf.section_title("t=0.000ms: Agent Receives Message (Step 1)")
pdf.body_text(
    "AgentService.onReceive() checks concurrency: 0 active < 10 max. Passes.\n"
    "processReceive():\n"
    "  - Creates WorkflowContext(startedAt=0)\n"
    "  - stepIndex = 1, accumulatedInputTokens = 50\n"
    "  - Budget check: 1 <= 10 steps, 50 <= 10000 tokens. OK.\n"
    "  - Samples outputTokens ~ Gaussian(150, 50) = e.g., 142\n"
    "  - Samples decision: roll=0.35 < 0.6 (call_tool weight) -> CALL_TOOL('search-tool')\n"
    "  - Samples TTFT ~ Gamma(4, 400) = e.g., 380ms\n"
    "  - Samples TPOT ~ Gamma(10, 25) = e.g., 24ms\n"
    "  - Inference = 380 + 142 * 24 = 3788ms\n"
    "  - Cost = 50 * $2.5e-6 + 142 * $10e-6 = $0.001545"
)

pdf.section_title("t=0.000ms: Infrastructure Compute (INFRA_SUBMIT)")
pdf.body_text(
    "Before dispatching the LLM call, the agent does local CPU work "
    "(context building, prompt formatting). This goes through the infrastructure layer:\n"
    "  - infraLayer.submitJob('agent-1', jobId, 0ms, 50M instructions)\n"
    "  - Node: 8 cores, 3GHz, 0 other active jobs\n"
    "  - speedPerJob = (8/1) * 3GHz = 24GHz\n"
    "  - computeMs = (50M / 24G) * 1000 = 2.08ms\n"
    "  - queueWaitMs = 0 (pod has capacity)\n"
    "  - Schedules InfraComplete at t = 0 + 2.08 = 2.08ms"
)

pdf.section_title("t=2.08ms: Infrastructure Complete (INFRA_COMPLETE)")
pdf.body_text(
    "CPU compute done. infraLayer.releaseJob() frees the CPU slot.\n"
    "Now the agent dispatches the external LLM call:\n"
    "  - Network: CLOUD->CLOUD = 1ms out + 1ms back = 2ms\n"
    "  - Schedules LlmComplete at t = 2.08 + 1 + 3788 + 1 = 3792.08ms"
)

pdf.section_title("t=3792ms: LLM Completes")
pdf.body_text(
    "Decision was CALL_TOOL('search-tool'). Agent dispatches tool call (external API):\n"
    "  - Tool profile: search-tool in CLOUD\n"
    "  - Network: 1ms + 1ms = 2ms\n"
    "  - Tool latency ~ Gaussian(200, 50) = e.g., 185ms\n"
    "  - Error check: random() = 0.72 >= 0.0 (errorRate) -> no error\n"
    "  - Response tokens = 300\n"
    "  - Schedules ToolComplete at t = 3792 + 1 + 185 + 1 = 3979ms\n\n"
    "Note: No infrastructure cost for tool calls - tools are external APIs."
)

pdf.section_title("t=3979ms: Tool Completes")
pdf.body_text(
    "Tool succeeded. Creates follow-up Message(search-tool -> agent-1, 300 tokens). "
    "Calls processReceive() directly (reuses concurrency slot)."
)

pdf.section_title("t=3979ms: Agent Receives Tool Result (Step 2)")
pdf.body_text(
    "The tool result arrives back at the agent. processReceive() is called again, "
    "which triggers a NEW LLM call (LLM call #2) so the LLM can evaluate the tool "
    "result and decide what to do next. First, the LLM parameters are sampled:\n"
    "  - stepIndex = 2, accumulatedInputTokens = 50 + 300 = 350\n"
    "  - Budget check: 2 <= 10, 350 <= 10000. OK.\n"
    "  - Samples outputTokens ~ Gaussian(150, 50) = e.g., 168\n"
    "  - Samples decision: roll=0.71 >= 0.6 -> GENERATE_TEXT\n"
    "  - Samples TTFT ~ Gamma(4, 400) = e.g., 390ms\n"
    "  - Samples TPOT ~ Gamma(10, 25) = e.g., 24ms\n"
    "  - Inference = 390 + 168 * 24 = 4422ms\n"
    "  - Cost = 350 * $2.5e-6 + 168 * $10e-6 = $0.002555\n\n"
    "These values are carried forward through the infrastructure step and used "
    "when the actual LLM call is dispatched after infra compute completes."
)

pdf.section_title("t=3979ms: Infrastructure Compute #2 (INFRA_SUBMIT)")
pdf.body_text(
    "Same as Step 1  - agent does local CPU work before the LLM call:\n"
    "  - infraLayer.submitJob('agent-1', jobId, 3979ms, 50M instructions)\n"
    "  - Node may have other active jobs now (depends on concurrent workflows)\n"
    "  - If 1 other job active: speed = (8/2) * 3GHz = 12GHz\n"
    "    -> computeMs = (50M / 12G) * 1000 = 4.17ms\n"
    "  - If unloaded: computeMs = 2.08ms (same as Step 1)\n"
    "  - Schedules InfraComplete at t = 3979 + 2.08 = 3981.08ms"
)

pdf.section_title("t=3981ms: Infrastructure Complete -> LLM Call #2 Dispatched")
pdf.body_text(
    "CPU compute done. Release infra resources. Dispatch LLM call:\n"
    "  - Schedules LlmComplete at t = 3981 + 1 + 4422 + 1 = 8405ms"
)

pdf.section_title("t=8405ms: LLM Completes -> SUCCESS")
pdf.body_text(
    "The LLM's decision is GENERATE_TEXT. Workflow terminates:\n"
    "  - Total latency: 8405 - 0 = 8405ms (8.4 seconds)\n"
    "  - Total cost: $0.001545 + $0.002555 = $0.0041\n"
    "  - Total steps: 2\n"
    "  - Reason: SUCCESS\n\n"
    "If the decision had been CALL_TOOL instead, the agent would have dispatched "
    "another tool call and the loop would continue (Step 3, Step 4, etc.) until "
    "the LLM finally decides GENERATE_TEXT or the budget is exhausted.\n\n"
    "Concurrency slot freed. Next queued workflow (if any) is dequeued."
)

pdf.section_title("t=8405ms: Orchestrator Logs COMPLETE")
pdf.body_text(
    "TrajectoryCollector records the final row with all metrics. "
    "This workflow generated ~14 trace events total:\n\n"
    "  1. SUBMIT              - workflow enters the system\n"
    "  2. AGENT_RECEIVE       - agent gets user message\n"
    "  3. INFRA_SUBMIT        - infra compute #1 starts (CPU work)\n"
    "  4. INFRA_COMPLETE      - infra compute #1 done\n"
    "  5. LLM_DISPATCH        - LLM call #1 sent (agent -> LLM)\n"
    "  6. LLM_COMPLETE        - LLM call #1 returns: CALL_TOOL\n"
    "  7. TOOL_DISPATCH       - tool call sent (agent -> tool)\n"
    "  8. TOOL_RETURN         - tool result comes back\n"
    "  9. AGENT_RECEIVE       - agent receives tool result\n"
    "  10. INFRA_SUBMIT       - infra compute #2 starts\n"
    "  11. INFRA_COMPLETE     - infra compute #2 done\n"
    "  12. LLM_DISPATCH       - LLM call #2 sent (agent -> LLM)\n"
    "  13. LLM_COMPLETE       - LLM call #2 returns: GENERATE_TEXT\n"
    "  14. COMPLETE            - workflow finished\n\n"
    "Notice the two-layer pattern: every agent step goes through INFRA first "
    "(CPU compute), then LLM (external API). The infra latency is small (~2ms) when "
    "unloaded, but grows under contention as concurrent workflows share CPU resources."
)


# =============================================
# 19. KEY DESIGN DECISIONS
# =============================================
pdf.add_page()
pdf.chapter_title("19. Key Design Decisions")

pdf.section_title("Why Discrete Event Simulation?")
pdf.body_text(
    "DES is the gold standard for modeling queuing systems. It is:\n"
    "- Exact: no approximation errors from time-stepping\n"
    "- Fast: jumps between events, doesn't tick through empty time\n"
    "- Deterministic: same seed = same results = reproducible experiments\n"
    "- Scalable: can simulate thousands of workflows in seconds"
)

pdf.section_title("Why Gamma for LLM Latency?")
pdf.body_text(
    "Real LLM inference latency measurements show:\n"
    "1. Always positive (no negative latency)\n"
    "2. Right-skewed (most calls are fast, some are slow)\n"
    "3. The tail varies by model/provider\n\n"
    "Gamma distribution matches all three properties. The shape parameter controls "
    "the tail: low shape = heavy tail (more outliers), high shape = Gaussian-like."
)

pdf.section_title("Why Token-Based (Not Byte-Based)?")
pdf.body_text(
    "In agentic systems, the fundamental unit is the TOKEN:\n"
    "- LLM latency scales with output tokens\n"
    "- Cost is per-token\n"
    "- Context window limits are in tokens\n"
    "- Tool results are measured in tokens\n\n"
    "v1 used bytes (for network bandwidth simulation). v2 uses tokens throughout."
)

pdf.section_title("Why Sealed Events?")
pdf.body_text(
    "Java sealed interfaces guarantee exhaustive matching. If you add a new event type, "
    "the compiler forces you to handle it everywhere. This prevents bugs where a new "
    "event type silently falls through."
)

pdf.section_title("Why Pluggable Decision Policy?")
pdf.body_text(
    "The LLMEngine takes a BiFunction for decisions, not a hardcoded strategy. This lets you:\n"
    "- Use weighted random for statistical experiments\n"
    "- Use scripted sequences for debugging (e.g., 'always call tool twice then finish')\n"
    "- Swap in ML-based policies in the future\n"
    "- Test edge cases (e.g., 'always fail')"
)

pdf.section_title("Why Two Layers? (v1 + v2 Integration)")
pdf.body_text(
    "The simulator uses a two-layer architecture:\n"
    "- Application layer (v2): models what the agent DOES (LLM calls, tool calls, decisions)\n"
    "- Infrastructure layer (v1): models what the agent RUNS ON (CPU, pods, contention)\n\n"
    "This separation exists because:\n"
    "1. LLM inference is an external API call  - latency depends on the model provider, "
    "not the local hardware.\n"
    "2. But the agent's local work (context building, prompt formatting, response parsing) "
    "runs on physical CPUs and IS affected by hardware contention.\n"
    "3. Under light load, the infra cost is negligible (~2ms). Under heavy load with "
    "many concurrent workflows sharing the same node, it can grow to 20ms+ and "
    "queue waits add even more.\n"
    "4. There is NO network cost between the layers  - they run on the same machine. "
    "The agent doesn't 'call' the infrastructure over a network.\n\n"
    "The infrastructure layer is a live, stateful service. Each call sees the current "
    "system state (active jobs, queue sizes) and returns an estimate that reflects "
    "real contention at that moment."
)

pdf.section_title("Concurrency = Queuing Theory")
pdf.body_text(
    "The maxConcurrency + queue model is a direct M/M/c queue:\n"
    "- M: Poisson arrivals (Markovian)\n"
    "- M: Exponential service times (approximately)\n"
    "- c: number of servers (maxConcurrency)\n\n"
    "This lets you study queue buildup, tail latency under load, and optimal "
    "concurrency settings for different arrival rates."
)


# =============================================
# SAVE
# =============================================
output_path = "C:/Users/ileounakis/IdeaProjects/Simulator/Agentic_Simulator_Tutorial.pdf"
pdf.output(output_path)
print(f"PDF saved to: {output_path}")