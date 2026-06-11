"""
Experiment 2: Two-Layer Architecture Value
Shows how increasing instructionsPerStep (CPU load per agent step) causes
infrastructure contention that compounds with LLM latency and agent queuing.

Reads exp2a through exp2d trajectory CSVs.
  a: 1M   instructions/step (~0.3ms CPU)
  b: 50M  instructions/step (~17ms CPU)
  c: 200M instructions/step (~67ms CPU)
  d: 500M instructions/step (~167ms CPU)

Usage:
    python visualize_experiment2.py

Requirements:
    pip install pandas matplotlib numpy
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

BASE_PATH = r'C:\Users\ileounakis\IdeaProjects\Simulator'

LABELS = {
    'a': '1M instr\n(~0.3ms)',
    'b': '50M instr\n(~17ms)',
    'c': '200M instr\n(~67ms)',
    'd': '500M instr\n(~167ms)',
}
INSTRUCTIONS = {'a': 1e6, 'b': 50e6, 'c': 200e6, 'd': 500e6}
COLORS = {'chat-light': '#2196F3', 'tool-heavy': '#FF9800'}

def load_experiment(letter):
    """Load a trajectory CSV and return parsed DataFrame, or None."""
    path = os.path.join(BASE_PATH, f'exp2{letter}_trajectory.csv')
    if not os.path.exists(path):
        print(f'  WARNING: {path} not found')
        return None
    df = pd.read_csv(path)
    return df

def extract_metrics(df):
    """Extract per-workload and aggregate metrics from a trajectory DataFrame."""
    completes = df[df['event_type'] == 'COMPLETE'].copy()
    if completes.empty:
        return None

    # Infrastructure metrics from INFRA_SUBMIT events
    infra_events = df[df['event_type'] == 'INFRA_SUBMIT'].copy()

    # Queue wait from QUEUE_EXIT events (agent-level queuing)
    queue_exits = df[df['event_type'] == 'QUEUE_EXIT'].copy()

    metrics = {
        'total': {
            'count': len(completes),
            'avg_latency': completes['total_latency_ms'].mean(),
            'p50_latency': completes['total_latency_ms'].median(),
            'p95_latency': completes['total_latency_ms'].quantile(0.95),
            'p99_latency': completes['total_latency_ms'].quantile(0.99),
            'max_latency': completes['total_latency_ms'].max(),
            'success_rate': (completes['reason'] == 'SUCCESS').mean() * 100,
            'avg_steps': completes['steps'].mean(),
            'total_cost': completes['total_cost_usd'].sum(),
        },
        'infra': {
            'avg_infra_latency': infra_events['infra_latency_ms'].mean() if len(infra_events) > 0 else 0,
            'avg_queue_wait': infra_events['queue_wait_ms'].mean() if len(infra_events) > 0 else 0,
            'avg_compute': infra_events['compute_ms'].mean() if len(infra_events) > 0 else 0,
            'p95_infra_latency': infra_events['infra_latency_ms'].quantile(0.95) if len(infra_events) > 0 else 0,
        },
        'agent_queue': {
            'count': len(queue_exits),
            'avg_wait': queue_exits['waited_ms'].mean() if len(queue_exits) > 0 else 0,
            'p95_wait': queue_exits['waited_ms'].quantile(0.95) if len(queue_exits) > 0 else 0,
        },
        'by_workload': {},
    }

    for wl_name in completes['workload'].dropna().unique():
        wl = completes[completes['workload'] == wl_name]
        metrics['by_workload'][wl_name] = {
            'count': len(wl),
            'avg_latency': wl['total_latency_ms'].mean(),
            'p50_latency': wl['total_latency_ms'].median(),
            'p95_latency': wl['total_latency_ms'].quantile(0.95),
            'max_latency': wl['total_latency_ms'].max(),
            'success_rate': (wl['reason'] == 'SUCCESS').mean() * 100,
            'avg_steps': wl['steps'].mean(),
        }

    return metrics


def main():
    print('=' * 60)
    print('Experiment 2: Two-Layer Architecture Value')
    print('Varying instructionsPerStep to show CPU contention impact')
    print('=' * 60)

    # Load all experiments
    data = {}
    for letter in ['a', 'b', 'c', 'd']:
        print(f'\nLoading exp2{letter}...')
        df = load_experiment(letter)
        if df is not None:
            metrics = extract_metrics(df)
            if metrics:
                data[letter] = metrics
                print(f'  Workflows: {metrics["total"]["count"]}, '
                      f'Avg latency: {metrics["total"]["avg_latency"]:.0f}ms, '
                      f'Avg infra: {metrics["infra"]["avg_infra_latency"]:.1f}ms')

    if not data:
        print('\nNo data found. Run experiments first.')
        return

    letters = sorted(data.keys())
    x = np.arange(len(letters))
    width = 0.35

    # ── Figure 1: End-to-End Latency by Workload ──
    fig1, axes1 = plt.subplots(1, 2, figsize=(14, 6))
    fig1.suptitle('Experiment 2: End-to-End Latency vs Infrastructure Load', fontsize=14, fontweight='bold')

    # Left: average latency per workload
    ax = axes1[0]
    for i, wl_name in enumerate(['chat-light', 'tool-heavy']):
        vals = []
        for l in letters:
            wl_data = data[l]['by_workload'].get(wl_name)
            vals.append(wl_data['avg_latency'] / 1000 if wl_data else 0)
        offset = -width/2 + i * width
        bars = ax.bar(x + offset, vals, width, label=wl_name, color=COLORS[wl_name], alpha=0.85)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                        f'{v:.1f}s', ha='center', va='bottom', fontsize=8)
    ax.set_xlabel('Instructions per Step')
    ax.set_ylabel('Average Latency (seconds)')
    ax.set_title('Average End-to-End Latency')
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[l] for l in letters])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Right: P95 latency per workload
    ax = axes1[1]
    for i, wl_name in enumerate(['chat-light', 'tool-heavy']):
        vals = []
        for l in letters:
            wl_data = data[l]['by_workload'].get(wl_name)
            vals.append(wl_data['p95_latency'] / 1000 if wl_data else 0)
        offset = -width/2 + i * width
        bars = ax.bar(x + offset, vals, width, label=wl_name, color=COLORS[wl_name], alpha=0.85)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                        f'{v:.1f}s', ha='center', va='bottom', fontsize=8)
    ax.set_xlabel('Instructions per Step')
    ax.set_ylabel('P95 Latency (seconds)')
    ax.set_title('P95 End-to-End Latency')
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[l] for l in letters])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    fig1.tight_layout()

    # ── Figure 2: Latency Breakdown (stacked bar) ──
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    fig2.suptitle('Experiment 2: Latency Breakdown by Component', fontsize=14, fontweight='bold')

    # Components: Agent Queue Wait, Infra Queue, Infra Compute, LLM (remainder)
    agent_queue = []
    infra_queue = []
    infra_compute = []
    llm_remainder = []

    for l in letters:
        d = data[l]
        aq = d['agent_queue']['avg_wait'] * (d['agent_queue']['count'] / max(d['total']['count'], 1))
        iq = d['infra']['avg_queue_wait'] * d['total']['avg_steps']
        ic = d['infra']['avg_compute'] * d['total']['avg_steps']
        total = d['total']['avg_latency']
        llm = max(0, total - aq - iq - ic)

        agent_queue.append(aq / 1000)
        infra_queue.append(iq / 1000)
        infra_compute.append(ic / 1000)
        llm_remainder.append(llm / 1000)

    bottom = np.zeros(len(letters))
    components = [
        ('Agent Queue Wait', agent_queue, '#F44336'),
        ('Infra CPU Queue', infra_queue, '#FF9800'),
        ('Infra CPU Compute', infra_compute, '#FFC107'),
        ('LLM + Network + Tool', llm_remainder, '#2196F3'),
    ]

    for label, vals, color in components:
        ax2.bar(x, vals, 0.5, bottom=bottom, label=label, color=color, alpha=0.85)
        bottom += np.array(vals)

    # Add total on top
    for i, l in enumerate(letters):
        ax2.text(i, bottom[i] + 0.1, f'{bottom[i]:.1f}s', ha='center', fontsize=9, fontweight='bold')

    ax2.set_xlabel('Instructions per Step')
    ax2.set_ylabel('Average Latency (seconds)')
    ax2.set_title('Where Time Is Spent (average across all workflows)')
    ax2.set_xticks(x)
    ax2.set_xticklabels([LABELS[l] for l in letters])
    ax2.legend(loc='upper left')
    ax2.grid(axis='y', alpha=0.3)
    fig2.tight_layout()

    # ── Figure 3: Infrastructure Contention Detail ──
    fig3, axes3 = plt.subplots(1, 3, figsize=(16, 5))
    fig3.suptitle('Experiment 2: Infrastructure Layer Contention', fontsize=14, fontweight='bold')

    # Left: avg infra latency (compute + queue)
    ax = axes3[0]
    compute_vals = [data[l]['infra']['avg_compute'] for l in letters]
    queue_vals = [data[l]['infra']['avg_queue_wait'] for l in letters]
    ax.bar(x, compute_vals, 0.4, label='CPU Compute', color='#FFC107', alpha=0.85)
    ax.bar(x, queue_vals, 0.4, bottom=compute_vals, label='CPU Queue Wait', color='#FF9800', alpha=0.85)
    ax.set_xlabel('Instructions per Step')
    ax.set_ylabel('Avg Infra Latency (ms)')
    ax.set_title('Per-Step Infrastructure Latency')
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[l] for l in letters])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Middle: P95 infra latency
    ax = axes3[1]
    p95_vals = [data[l]['infra']['p95_infra_latency'] for l in letters]
    ax.bar(x, p95_vals, 0.4, color='#E91E63', alpha=0.85)
    for i, v in enumerate(p95_vals):
        ax.text(i, v + 1, f'{v:.0f}ms', ha='center', fontsize=9)
    ax.set_xlabel('Instructions per Step')
    ax.set_ylabel('P95 Infra Latency (ms)')
    ax.set_title('P95 Infrastructure Latency')
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[l] for l in letters])
    ax.grid(axis='y', alpha=0.3)

    # Right: success rate
    ax = axes3[2]
    for i, wl_name in enumerate(['chat-light', 'tool-heavy']):
        vals = []
        for l in letters:
            wl_data = data[l]['by_workload'].get(wl_name)
            vals.append(wl_data['success_rate'] if wl_data else 0)
        offset = -width/2 + i * width
        ax.bar(x + offset, vals, width, label=wl_name, color=COLORS[wl_name], alpha=0.85)
    ax.set_xlabel('Instructions per Step')
    ax.set_ylabel('Success Rate (%)')
    ax.set_title('Workflow Success Rate')
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[l] for l in letters])
    ax.set_ylim(0, 110)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    fig3.tight_layout()

    # ── Figure 4: Comparison Table ──
    fig4, ax4 = plt.subplots(figsize=(14, 6))
    fig4.suptitle('Experiment 2: Summary Comparison Table', fontsize=14, fontweight='bold')
    ax4.axis('off')

    headers = ['Metric'] + [LABELS[l].replace('\n', ' ') for l in letters]
    rows = []

    rows.append(['Completed Workflows'] + [f'{data[l]["total"]["count"]}' for l in letters])
    rows.append(['Success Rate'] + [f'{data[l]["total"]["success_rate"]:.0f}%' for l in letters])
    rows.append(['Avg Latency (s)'] + [f'{data[l]["total"]["avg_latency"]/1000:.2f}' for l in letters])
    rows.append(['P95 Latency (s)'] + [f'{data[l]["total"]["p95_latency"]/1000:.2f}' for l in letters])
    rows.append(['Max Latency (s)'] + [f'{data[l]["total"]["max_latency"]/1000:.2f}' for l in letters])
    rows.append(['Avg Steps'] + [f'{data[l]["total"]["avg_steps"]:.1f}' for l in letters])
    rows.append(['Avg Infra/Step (ms)'] + [f'{data[l]["infra"]["avg_infra_latency"]:.1f}' for l in letters])
    rows.append(['Avg CPU Queue/Step (ms)'] + [f'{data[l]["infra"]["avg_queue_wait"]:.1f}' for l in letters])
    rows.append(['Agent Queue Events'] + [f'{data[l]["agent_queue"]["count"]}' for l in letters])
    rows.append(['Avg Agent Queue Wait (ms)'] + [f'{data[l]["agent_queue"]["avg_wait"]:.0f}' for l in letters])
    rows.append(['Total Cost ($)'] + [f'{data[l]["total"]["total_cost"]:.4f}' for l in letters])

    # Color code: green for low latency, red for high
    table = ax4.table(cellText=rows, colLabels=headers, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.5)

    # Color header
    for j in range(len(headers)):
        table[0, j].set_facecolor('#E3F2FD')
        table[0, j].set_text_props(fontweight='bold')

    # Color latency cells (rows 2-4, columns 1+)
    if len(letters) > 1:
        for row_idx in [2, 3, 4]:  # avg, p95, max latency rows
            vals = [float(rows[row_idx][col+1]) for col in range(len(letters))]
            min_val, max_val = min(vals), max(vals)
            for col in range(len(letters)):
                if max_val > min_val:
                    ratio = (vals[col] - min_val) / (max_val - min_val)
                    r = 0.6 + 0.4 * ratio
                    g = 0.9 - 0.3 * ratio
                    b = 0.6 - 0.2 * ratio
                    table[row_idx + 1, col + 1].set_facecolor((r, g, b, 0.4))

    fig4.tight_layout()

    # ── Figure 5: Latency Distribution ──
    fig5, axes5 = plt.subplots(2, 2, figsize=(14, 10))
    fig5.suptitle('Experiment 2: Latency Distributions', fontsize=14, fontweight='bold')

    for idx, letter in enumerate(letters[:4]):
        ax = axes5[idx // 2][idx % 2]
        df = load_experiment(letter)
        if df is None:
            continue
        completes = df[df['event_type'] == 'COMPLETE'].copy()

        for wl_name in ['chat-light', 'tool-heavy']:
            wl = completes[completes['workload'] == wl_name]
            if not wl.empty:
                ax.hist(wl['total_latency_ms'] / 1000, bins=40, alpha=0.6,
                        label=wl_name, color=COLORS[wl_name])

        ax.set_title(f'exp2{letter}: {LABELS[letter].replace(chr(10), " ")}')
        ax.set_xlabel('End-to-End Latency (seconds)')
        ax.set_ylabel('Count')
        ax.legend()
        ax.grid(alpha=0.3)

    fig5.tight_layout()

    print('\n' + '=' * 60)
    print('Close the chart windows to exit.')
    print('=' * 60)
    plt.show()


if __name__ == '__main__':
    main()
