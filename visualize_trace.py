"""
Trace visualization for the agentic simulation (v2).
Shows agents running concurrently with workflows flowing through them.

Figures:
  1. Agent Concurrency Timeline - horizontal lanes per agent showing concurrent
     workflow slots filled over time, with phase coloring
  2. Workflow Gantt - individual workflow timelines showing all phases
  3. Active Workflows Over Time - stacked area showing concurrent load per agent

Usage:
    python visualize_trace.py
    python visualize_trace.py --workflows 40
    python visualize_trace.py --start 0 --end 15000

Requirements:
    pip install pandas matplotlib
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import os
import sys
import argparse

BASE_PATH = r'C:\Users\ileounakis\IdeaProjects\Simulator'
TRAJECTORY_FILE = os.path.join(BASE_PATH, 'exp1a_trajectory.csv')

if not os.path.exists(TRAJECTORY_FILE):
    print(f"Trajectory file not found: {TRAJECTORY_FILE}")
    print("Run the agentic simulation first (pass 'agentic' as argument).")
    sys.exit(1)

parser = argparse.ArgumentParser()
parser.add_argument('--workflows', type=int, default=30, help='Max workflows to show per agent')
parser.add_argument('--start', type=float, default=None, help='Start time (ms)')
parser.add_argument('--end', type=float, default=None, help='End time (ms)')
args = parser.parse_args()

df = pd.read_csv(TRAJECTORY_FILE)
print(f"Loaded {len(df)} trace events")

for col in ['time_ms', 'inference_ms', 'tool_ms', 'compute_ms', 'queue_wait_ms',
            'infra_latency_ms', 'network_out_ms', 'network_back_ms', 'waited_ms']:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Phase colors
C = {
    'queue':   '#e74c3c',
    'infra':   '#f39c12',
    'llm':     '#3498db',
    'tool':    '#2ecc71',
    'network': '#bdc3c7',
}
WL_C = {'chat-light': '#3498db', 'tool-heavy': '#e74c3c'}

# Detect agents (excluding ORCHESTRATOR)
all_agents = sorted([a for a in df['entity_id'].unique() if a != 'ORCHESTRATOR'])
print(f"Agents found: {all_agents}")

# Workload per workflow
wf_workload = {}
for _, row in df[df['event_type'] == 'SUBMIT'].iterrows():
    wl = row.get('workload', '')
    wf_workload[row['workflow_id']] = wl if pd.notna(wl) and wl != '' else 'unknown'

# Helper: draw phase bars for a set of events on an axis
def draw_bars(ax, events, y, bar_height=0.7):
    count = 0
    for _, ev in events.iterrows():
        etype = ev['event_type']
        t = ev['time_ms']

        if etype == 'QUEUE_EXIT' and pd.notna(ev.get('waited_ms')) and ev['waited_ms'] > 0:
            ax.barh(y, ev['waited_ms'], left=t - ev['waited_ms'], height=bar_height,
                    color=C['queue'], alpha=0.85, edgecolor='white', linewidth=0.3)
            count += 1

        if etype == 'INFRA_SUBMIT' and pd.notna(ev.get('compute_ms')) and ev['compute_ms'] > 0:
            ax.barh(y, ev['compute_ms'], left=t, height=bar_height,
                    color=C['infra'], alpha=0.85, edgecolor='white', linewidth=0.3)
            count += 1

        if etype == 'LLM_DISPATCH' and pd.notna(ev.get('inference_ms')) and ev['inference_ms'] > 0:
            net = ev['network_out_ms'] if pd.notna(ev.get('network_out_ms')) else 0
            if net > 0:
                ax.barh(y, net, left=t, height=bar_height,
                        color=C['network'], alpha=0.5, edgecolor='white', linewidth=0.3)
            ax.barh(y, ev['inference_ms'], left=t + net, height=bar_height,
                    color=C['llm'], alpha=0.85, edgecolor='white', linewidth=0.3)
            count += 1

        if etype == 'TOOL_DISPATCH' and pd.notna(ev.get('tool_ms')) and ev['tool_ms'] > 0:
            net = ev['network_out_ms'] if pd.notna(ev.get('network_out_ms')) else 0
            if net > 0:
                ax.barh(y, net, left=t, height=bar_height,
                        color=C['network'], alpha=0.5, edgecolor='white', linewidth=0.3)
            ax.barh(y, ev['tool_ms'], left=t + net, height=bar_height,
                    color=C['tool'], alpha=0.85, edgecolor='white', linewidth=0.3)
            count += 1
    return count


# ── Figure 1: Side-by-Side Agent Panels ───────────────────────
# Each agent gets a subplot. Within each, workflows are stacked vertically.
# You can see which workflows overlap in time = running concurrently.

fig1, axes1 = plt.subplots(len(all_agents), 1,
                            figsize=(20, max(6, 4 * len(all_agents))),
                            sharex=True, squeeze=False)
fig1.suptitle('Agent Concurrency View - Workflows Running in Parallel',
              fontsize=14, fontweight='bold')

for idx, agent_id in enumerate(all_agents):
    ax = axes1[idx][0]
    agent_ev = df[df['entity_id'] == agent_id].copy()

    # Get workflows touching this agent, sorted by arrival time
    agent_wfs = agent_ev['workflow_id'].unique()
    wf_start = df[df['workflow_id'].isin(agent_wfs)].groupby('workflow_id')['time_ms'].min()
    wf_start = wf_start.sort_values()

    # Apply time filter
    if args.start is not None:
        wf_start = wf_start[wf_start >= args.start]
    if args.end is not None:
        wf_start = wf_start[wf_start <= args.end]

    wf_list = wf_start.head(args.workflows).index.tolist()
    wf_map = {wf: i for i, wf in enumerate(wf_list)}

    total_bars = 0
    for wf_id in wf_list:
        wf_events = agent_ev[agent_ev['workflow_id'] == wf_id].sort_values('time_ms')
        total_bars += draw_bars(ax, wf_events, wf_map[wf_id], bar_height=0.8)

    # Draw workflow start/end markers
    for wf_id in wf_list:
        y = wf_map[wf_id]
        wf_all = df[df['workflow_id'] == wf_id]
        t_start = wf_all['time_ms'].min()
        t_end = wf_all['time_ms'].max()
        wl = wf_workload.get(wf_id, 'unknown')
        marker_color = WL_C.get(wl, '#333')
        ax.plot(t_start, y, '|', color=marker_color, markersize=10, markeredgewidth=2)
        ax.plot(t_end, y, 'x', color=marker_color, markersize=6, markeredgewidth=1.5)

    # Labels
    ax.set_yticks(range(len(wf_list)))
    labels = []
    for wf_id in wf_list:
        wl = wf_workload.get(wf_id, '')
        short = wf_id.replace('wf-', '')
        labels.append(short)
    ax.set_yticklabels(labels, fontsize=6)
    for i, wf_id in enumerate(wf_list):
        wl = wf_workload.get(wf_id, 'unknown')
        ax.get_yticklabels()[i].set_color(WL_C.get(wl, '#333'))

    ax.set_title(f'{agent_id}  ({len(wf_list)} workflows shown)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Workflow')
    ax.invert_yaxis()
    ax.grid(True, axis='x', linestyle='--', alpha=0.3)

axes1[-1][0].set_xlabel('Simulation Time (ms)')

# Legend
legend_patches = [
    mpatches.Patch(color=C['queue'], label='Queue Wait'),
    mpatches.Patch(color=C['infra'], label='Infra Compute (CPU)'),
    mpatches.Patch(color=C['llm'], label='LLM Inference'),
    mpatches.Patch(color=C['tool'], label='Tool Call'),
    mpatches.Patch(color=C['network'], label='Network', alpha=0.5),
    mlines.Line2D([], [], color='black', marker='|', linestyle='None',
                  markersize=10, markeredgewidth=2, label='Workflow Start'),
    mlines.Line2D([], [], color='black', marker='x', linestyle='None',
                  markersize=6, markeredgewidth=1.5, label='Workflow End'),
]
axes1[0][0].legend(handles=legend_patches, loc='upper right', fontsize=8, ncol=2)
fig1.tight_layout()


# ── Figure 2: Active Workflows Per Agent Over Time ────────────
# Shows how many workflows each agent is processing simultaneously.

fig2, ax2 = plt.subplots(figsize=(16, 6))
fig2.suptitle('Concurrent Active Workflows Per Agent', fontsize=14, fontweight='bold')

agent_colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']

for idx, agent_id in enumerate(all_agents):
    # Find workflows handled by this agent
    agent_wfs = df[df['entity_id'] == agent_id]['workflow_id'].unique()

    # SUBMIT = workflow starts, COMPLETE = workflow ends
    wf_submits = df[(df['workflow_id'].isin(agent_wfs)) & (df['event_type'] == 'SUBMIT')]
    wf_completes = df[(df['workflow_id'].isin(agent_wfs)) & (df['event_type'] == 'COMPLETE')]

    events = []
    for _, row in wf_submits.iterrows():
        events.append((row['time_ms'], +1))
    for _, row in wf_completes.iterrows():
        events.append((row['time_ms'], -1))
    events.sort(key=lambda x: x[0])

    times, counts = [], []
    current = 0
    for t, delta in events:
        current += delta
        times.append(t / 1000.0)
        counts.append(current)

    color = agent_colors[idx % len(agent_colors)]
    ax2.step(times, counts, where='post', label=agent_id, color=color, linewidth=2, alpha=0.85)
    ax2.fill_between(times, counts, step='post', color=color, alpha=0.15)

# Total across all agents
all_submits = df[df['event_type'] == 'SUBMIT']
all_completes = df[df['event_type'] == 'COMPLETE']
events = []
for _, row in all_submits.iterrows():
    events.append((row['time_ms'], +1))
for _, row in all_completes.iterrows():
    events.append((row['time_ms'], -1))
events.sort(key=lambda x: x[0])
times, counts = [], []
current = 0
for t, delta in events:
    current += delta
    times.append(t / 1000.0)
    counts.append(current)
ax2.step(times, counts, where='post', label='Total', color='#333',
         linewidth=2.5, alpha=0.5, linestyle='--')

ax2.set_xlabel('Simulation Time (seconds)')
ax2.set_ylabel('Active Workflows')
ax2.legend(fontsize=10)
ax2.grid(True, linestyle='--', alpha=0.4)
fig2.tight_layout()


# ── Figure 3: Zoomed Gantt (first 10 seconds) ────────────────
# Shows both agents' workflows interleaved on one chart so you can see
# exactly which workflows overlap across agents.

zoom_end = 15000  # first 15 seconds
if args.end is not None:
    zoom_end = args.end
zoom_start = args.start if args.start is not None else 0

zoom_wfs = df[(df['event_type'] == 'SUBMIT') & (df['time_ms'] >= zoom_start) &
              (df['time_ms'] <= zoom_end)].sort_values('time_ms')
zoom_wf_ids = zoom_wfs['workflow_id'].head(40).tolist()

if zoom_wf_ids:
    zoom_df = df[df['workflow_id'].isin(zoom_wf_ids)]

    # Group by agent, assign Y positions with agent grouping
    y_pos = {}
    y_labels = []
    y_colors = []
    current_y = 0
    agent_y_ranges = {}

    for agent_id in all_agents:
        agent_wfs_in_zoom = [wf for wf in zoom_wf_ids
                             if wf in zoom_df[zoom_df['entity_id'] == agent_id]['workflow_id'].values]
        if not agent_wfs_in_zoom:
            continue

        start_y = current_y
        for wf_id in agent_wfs_in_zoom:
            y_pos[wf_id] = current_y
            wl = wf_workload.get(wf_id, 'unknown')
            y_labels.append(f"{wf_id.replace('wf-', '')}  [{agent_id}]")
            y_colors.append(WL_C.get(wl, '#333'))
            current_y += 1
        agent_y_ranges[agent_id] = (start_y, current_y - 1)
        current_y += 1  # gap between agents

    if y_pos:
        fig3, ax3 = plt.subplots(figsize=(20, max(8, current_y * 0.35)))
        fig3.suptitle(f'Combined Agent View (first {zoom_end/1000:.0f}s) - Workflows Across Agents',
                      fontsize=14, fontweight='bold')

        for wf_id in zoom_wf_ids:
            if wf_id not in y_pos:
                continue
            y = y_pos[wf_id]
            wf_events = zoom_df[zoom_df['workflow_id'] == wf_id].sort_values('time_ms')
            draw_bars(ax3, wf_events, y, bar_height=0.8)

        # Draw agent group separators and labels
        for agent_id, (y_start, y_end) in agent_y_ranges.items():
            mid = (y_start + y_end) / 2
            ax3.axhspan(y_start - 0.5, y_end + 0.5, alpha=0.04,
                        color=agent_colors[all_agents.index(agent_id) % len(agent_colors)])
            ax3.text(-0.01, mid, agent_id, transform=ax3.get_yaxis_transform(),
                     fontsize=9, fontweight='bold', ha='right', va='center',
                     color=agent_colors[all_agents.index(agent_id) % len(agent_colors)])

        ax3.set_yticks(list(y_pos.values()))
        ax3.set_yticklabels(y_labels, fontsize=6)
        for i, color in enumerate(y_colors):
            ax3.get_yticklabels()[i].set_color(color)

        ax3.set_xlabel('Simulation Time (ms)')
        ax3.set_ylabel('Workflow')
        ax3.invert_yaxis()
        ax3.grid(True, axis='x', linestyle='--', alpha=0.3)

        legend_patches = [
            mpatches.Patch(color=C['queue'], label='Queue Wait'),
            mpatches.Patch(color=C['infra'], label='Infra Compute'),
            mpatches.Patch(color=C['llm'], label='LLM Inference'),
            mpatches.Patch(color=C['tool'], label='Tool Call'),
        ]
        ax3.legend(handles=legend_patches, loc='lower right', fontsize=9)
        fig3.tight_layout()

print("\nClose the windows to exit.")
plt.show()
