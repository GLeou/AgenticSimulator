"""
Visualization script for the agentic simulation (v2) trajectory.
Reads agentic_trajectory.csv and produces per-workload analysis charts.

Usage:
    python visualize_agentic.py

Requirements:
    pip install pandas matplotlib
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import sys

BASE_PATH = r'C:\Users\ileounakis\IdeaProjects\Simulator'
TRAJECTORY_FILE = os.path.join(BASE_PATH, 'exp1a_trajectory.csv')

if not os.path.exists(TRAJECTORY_FILE):
    print(f"Trajectory file not found: {TRAJECTORY_FILE}")
    print("Run the agentic simulation first (pass 'agentic' as argument).")
    sys.exit(1)

df = pd.read_csv(TRAJECTORY_FILE)
print(f"Loaded {len(df)} trace events from {TRAJECTORY_FILE}")

# Extract completed workflows
complete = df[df['event_type'] == 'COMPLETE'].copy()

if complete.empty:
    print("No completed workflows found in trajectory.")
    sys.exit(1)

# Ensure numeric columns
for col in ['total_latency_ms', 'total_cost_usd', 'steps']:
    if col in complete.columns:
        complete[col] = pd.to_numeric(complete[col], errors='coerce')

has_workloads = 'workload' in complete.columns and complete['workload'].nunique() > 1
workload_names = sorted(complete['workload'].unique()) if has_workloads else ['all']

# Color palette for workloads
COLORS = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']
workload_colors = {name: COLORS[i % len(COLORS)] for i, name in enumerate(workload_names)}

# ── Figure 1: Latency Distribution ──────────────────────────────

fig1, axes1 = plt.subplots(1, 2, figsize=(14, 5))
fig1.suptitle('Workflow Latency Analysis', fontsize=14, fontweight='bold')

# 1a: Latency histogram per workload
ax = axes1[0]
if has_workloads:
    for name in workload_names:
        data = complete[complete['workload'] == name]['total_latency_ms'] / 1000.0
        ax.hist(data, bins=20, alpha=0.6, label=name, color=workload_colors[name], edgecolor='white')
    ax.legend()
else:
    ax.hist(complete['total_latency_ms'] / 1000.0, bins=20, alpha=0.7, color=COLORS[0], edgecolor='white')
ax.set_xlabel('Latency (seconds)')
ax.set_ylabel('Workflow Count')
ax.set_title('Latency Distribution')
ax.grid(True, linestyle='--', alpha=0.4)

# 1b: Latency boxplot per workload
ax = axes1[1]
if has_workloads:
    box_data = [complete[complete['workload'] == name]['total_latency_ms'] / 1000.0
                for name in workload_names]
    bp = ax.boxplot(box_data, labels=workload_names, patch_artist=True)
    for patch, name in zip(bp['boxes'], workload_names):
        patch.set_facecolor(workload_colors[name])
        patch.set_alpha(0.6)
else:
    ax.boxplot(complete['total_latency_ms'] / 1000.0, labels=['all'], patch_artist=True)
ax.set_ylabel('Latency (seconds)')
ax.set_title('Latency Boxplot')
ax.grid(True, linestyle='--', alpha=0.4)

fig1.tight_layout()

# ── Figure 2: Cost & Steps ──────────────────────────────────────

fig2, axes2 = plt.subplots(1, 2, figsize=(14, 5))
fig2.suptitle('Cost & Step Analysis', fontsize=14, fontweight='bold')

# 2a: Cost per workflow
ax = axes2[0]
if has_workloads:
    for name in workload_names:
        data = complete[complete['workload'] == name]
        ax.scatter(data['time_ms'] / 1000.0, data['total_cost_usd'] * 1000,
                   alpha=0.5, label=name, color=workload_colors[name], s=20)
    ax.legend()
else:
    ax.scatter(complete['time_ms'] / 1000.0, complete['total_cost_usd'] * 1000,
               alpha=0.5, color=COLORS[0], s=20)
ax.set_xlabel('Completion Time (seconds)')
ax.set_ylabel('Cost (millicents USD)')
ax.set_title('Per-Workflow Cost Over Time')
ax.grid(True, linestyle='--', alpha=0.4)

# 2b: Steps distribution
ax = axes2[1]
if has_workloads:
    for name in workload_names:
        data = complete[complete['workload'] == name]['steps']
        ax.hist(data, bins=range(0, int(data.max()) + 2), alpha=0.6,
                label=name, color=workload_colors[name], edgecolor='white')
    ax.legend()
else:
    ax.hist(complete['steps'], bins=range(0, int(complete['steps'].max()) + 2),
            alpha=0.7, color=COLORS[0], edgecolor='white')
ax.set_xlabel('Agent Steps')
ax.set_ylabel('Workflow Count')
ax.set_title('Steps per Workflow')
ax.grid(True, linestyle='--', alpha=0.4)

fig2.tight_layout()

# ── Figure 3: Timeline & Completion Reasons ─────────────────────

fig3, axes3 = plt.subplots(1, 2, figsize=(14, 5))
fig3.suptitle('Timeline & Outcomes', fontsize=14, fontweight='bold')

# 3a: Workflow completions over time (cumulative)
ax = axes3[0]
if has_workloads:
    for name in workload_names:
        data = complete[complete['workload'] == name].sort_values('time_ms')
        ax.plot(data['time_ms'] / 1000.0, range(1, len(data) + 1),
                label=name, color=workload_colors[name], linewidth=2)
    ax.legend()
else:
    data = complete.sort_values('time_ms')
    ax.plot(data['time_ms'] / 1000.0, range(1, len(data) + 1), color=COLORS[0], linewidth=2)
ax.set_xlabel('Simulation Time (seconds)')
ax.set_ylabel('Cumulative Completions')
ax.set_title('Workflow Completions Over Time')
ax.grid(True, linestyle='--', alpha=0.4)

# 3b: Completion reasons breakdown
ax = axes3[1]
if has_workloads:
    reasons_by_workload = complete.groupby(['workload', 'reason']).size().unstack(fill_value=0)
    reasons_by_workload.plot(kind='bar', ax=ax, edgecolor='white')
    ax.set_xlabel('Workload')
else:
    reasons = complete['reason'].value_counts()
    reasons.plot(kind='bar', ax=ax, color=COLORS[0], edgecolor='white')
    ax.set_xlabel('Reason')
ax.set_ylabel('Count')
ax.set_title('Completion Reasons')
ax.grid(True, linestyle='--', alpha=0.4)
plt.setp(ax.get_xticklabels(), rotation=0)

fig3.tight_layout()

# ── Figure 4: Infrastructure & Queue Analysis ───────────────────

# Extract queue events
queue_enter = df[df['event_type'] == 'QUEUE_ENTER'].copy()
queue_exit = df[df['event_type'] == 'QUEUE_EXIT'].copy()

if not queue_enter.empty or not queue_exit.empty:
    fig4, axes4 = plt.subplots(1, 2, figsize=(14, 5))
    fig4.suptitle('Infrastructure & Queuing', fontsize=14, fontweight='bold')

    # 4a: Queue size over time
    ax = axes4[0]
    if 'queue_size' in queue_enter.columns:
        queue_enter['queue_size'] = pd.to_numeric(queue_enter['queue_size'], errors='coerce')
        agents = queue_enter['entity_id'].unique()
        for agent in agents:
            agent_data = queue_enter[queue_enter['entity_id'] == agent].sort_values('time_ms')
            ax.step(agent_data['time_ms'] / 1000.0, agent_data['queue_size'],
                    where='post', label=agent, linewidth=1.5)
        ax.legend()
    ax.set_xlabel('Simulation Time (seconds)')
    ax.set_ylabel('Queue Depth')
    ax.set_title('Agent Queue Depth Over Time')
    ax.grid(True, linestyle='--', alpha=0.4)

    # 4b: Wait time distribution
    ax = axes4[1]
    if 'waited_ms' in queue_exit.columns:
        queue_exit['waited_ms'] = pd.to_numeric(queue_exit['waited_ms'], errors='coerce')
        ax.hist(queue_exit['waited_ms'], bins=20, alpha=0.7, color='#e74c3c', edgecolor='white')
    ax.set_xlabel('Queue Wait Time (ms)')
    ax.set_ylabel('Count')
    ax.set_title('Queue Wait Time Distribution')
    ax.grid(True, linestyle='--', alpha=0.4)

    fig4.tight_layout()

# ── Figure 5: Infra Latency Breakdown ───────────────────────────

infra_submit = df[df['event_type'] == 'INFRA_SUBMIT'].copy()

if not infra_submit.empty and 'infra_latency_ms' in infra_submit.columns:
    fig5, axes5 = plt.subplots(1, 2, figsize=(14, 5))
    fig5.suptitle('Infrastructure Latency', fontsize=14, fontweight='bold')

    infra_submit['infra_latency_ms'] = pd.to_numeric(infra_submit['infra_latency_ms'], errors='coerce')
    infra_submit['compute_ms'] = pd.to_numeric(infra_submit['compute_ms'], errors='coerce')
    infra_submit['queue_wait_ms'] = pd.to_numeric(infra_submit['queue_wait_ms'], errors='coerce')

    # 5a: Infra latency over time
    ax = axes5[0]
    ax.scatter(infra_submit['time_ms'] / 1000.0, infra_submit['infra_latency_ms'],
               alpha=0.3, s=10, color='#3498db')
    ax.set_xlabel('Simulation Time (seconds)')
    ax.set_ylabel('Infrastructure Latency (ms)')
    ax.set_title('Per-Step Infrastructure Latency')
    ax.grid(True, linestyle='--', alpha=0.4)

    # 5b: Compute vs queue wait breakdown
    ax = axes5[1]
    ax.hist([infra_submit['compute_ms'].dropna(), infra_submit['queue_wait_ms'].dropna()],
            bins=30, alpha=0.6, label=['Compute', 'Queue Wait'],
            color=['#3498db', '#e74c3c'], edgecolor='white')
    ax.set_xlabel('Time (ms)')
    ax.set_ylabel('Count')
    ax.set_title('Compute vs Queue Wait')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.4)

    fig5.tight_layout()

# ── Summary Table ───────────────────────────────────────────────

print("\n=== Visualization Summary ===")
if has_workloads:
    for name in workload_names:
        wl = complete[complete['workload'] == name]
        print(f"\n  {name}:")
        print(f"    Completed: {len(wl)}")
        print(f"    Success:   {len(wl[wl['reason'] == 'SUCCESS'])}")
        print(f"    Avg latency: {wl['total_latency_ms'].mean() / 1000:.2f}s")
        print(f"    Max latency: {wl['total_latency_ms'].max() / 1000:.2f}s")
        print(f"    Total cost:  ${wl['total_cost_usd'].sum():.4f}")
else:
    print(f"  Completed: {len(complete)}")
    print(f"  Avg latency: {complete['total_latency_ms'].mean() / 1000:.2f}s")
    print(f"  Total cost:  ${complete['total_cost_usd'].sum():.4f}")

plt.show()
