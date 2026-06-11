"""
Experiment 3: Edge/Cloud Agent Placement
Compares three placement strategies:
  a: All Cloud  (both agents on CLOUD node, 16 cores)
  b: Hybrid     (chat on EDGE 4 cores, tool on CLOUD 16 cores)
  c: All Edge   (both agents on EDGE node, 4 cores)

Network: EDGE<->CLOUD = 40ms one-way latency
LLM + Tool always hosted in CLOUD

Usage:
    python visualize_experiment3.py
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

BASE_PATH = r'C:\Users\ileounakis\IdeaProjects\Simulator'

LABELS = {
    'a': 'All Cloud',
    'b': 'Hybrid\n(chat@Edge)',
    'c': 'All Edge',
}
COLORS_WL = {'chat-light': '#2196F3', 'tool-heavy': '#FF9800'}
COLORS_PLACEMENT = {'a': '#4CAF50', 'b': '#FF9800', 'c': '#F44336'}

def load_experiment(letter):
    path = os.path.join(BASE_PATH, f'exp3{letter}_trajectory.csv')
    if not os.path.exists(path):
        print(f'  WARNING: {path} not found')
        return None
    return pd.read_csv(path)

def extract_metrics(df):
    completes = df[df['event_type'] == 'COMPLETE'].copy()
    if completes.empty:
        return None

    infra_events = df[df['event_type'] == 'INFRA_SUBMIT'].copy()
    queue_exits = df[df['event_type'] == 'QUEUE_EXIT'].copy()
    llm_dispatches = df[df['event_type'] == 'LLM_DISPATCH'].copy()

    metrics = {
        'total': {
            'count': len(completes),
            'avg_latency': completes['total_latency_ms'].mean(),
            'p50_latency': completes['total_latency_ms'].median(),
            'p95_latency': completes['total_latency_ms'].quantile(0.95),
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
        'network': {
            'avg_network_out': llm_dispatches['network_out_ms'].mean() if len(llm_dispatches) > 0 else 0,
            'avg_network_back': llm_dispatches['network_back_ms'].mean() if len(llm_dispatches) > 0 else 0,
            'total_network': (llm_dispatches['network_out_ms'].mean() + llm_dispatches['network_back_ms'].mean()) if len(llm_dispatches) > 0 else 0,
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
    print('Experiment 3: Edge/Cloud Agent Placement')
    print('=' * 60)

    data = {}
    for letter in ['a', 'b', 'c']:
        print(f'\nLoading exp3{letter} ({LABELS[letter].replace(chr(10), " ")})...')
        df = load_experiment(letter)
        if df is not None:
            metrics = extract_metrics(df)
            if metrics:
                data[letter] = metrics
                print(f'  Workflows: {metrics["total"]["count"]}, '
                      f'Avg latency: {metrics["total"]["avg_latency"]:.0f}ms, '
                      f'Avg network/step: {metrics["network"]["total_network"]:.1f}ms')

    if not data:
        print('\nNo data found. Run experiments first.')
        return

    letters = sorted(data.keys())
    x = np.arange(len(letters))
    width = 0.3

    # ── Figure 1: End-to-End Latency by Workload ──
    fig1, axes1 = plt.subplots(1, 2, figsize=(14, 6))
    fig1.suptitle('Experiment 3: Latency vs Agent Placement', fontsize=14, fontweight='bold')

    ax = axes1[0]
    for i, wl_name in enumerate(['chat-light', 'tool-heavy']):
        vals = [data[l]['by_workload'].get(wl_name, {}).get('avg_latency', 0) / 1000 for l in letters]
        offset = -width/2 + i * width
        bars = ax.bar(x + offset, vals, width, label=wl_name, color=COLORS_WL[wl_name], alpha=0.85)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                        f'{v:.2f}s', ha='center', va='bottom', fontsize=8)
    ax.set_ylabel('Average Latency (seconds)')
    ax.set_title('Average End-to-End Latency')
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[l] for l in letters])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    ax = axes1[1]
    for i, wl_name in enumerate(['chat-light', 'tool-heavy']):
        vals = [data[l]['by_workload'].get(wl_name, {}).get('p95_latency', 0) / 1000 for l in letters]
        offset = -width/2 + i * width
        bars = ax.bar(x + offset, vals, width, label=wl_name, color=COLORS_WL[wl_name], alpha=0.85)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                        f'{v:.2f}s', ha='center', va='bottom', fontsize=8)
    ax.set_ylabel('P95 Latency (seconds)')
    ax.set_title('P95 End-to-End Latency')
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[l] for l in letters])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    fig1.tight_layout()

    # ── Figure 2: Latency Breakdown ──
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    fig2.suptitle('Experiment 3: Latency Breakdown by Component', fontsize=14, fontweight='bold')

    agent_queue = []
    infra_total = []
    network_total = []
    llm_remainder = []

    for l in letters:
        d = data[l]
        aq = d['agent_queue']['avg_wait'] * (d['agent_queue']['count'] / max(d['total']['count'], 1))
        inf = (d['infra']['avg_infra_latency']) * d['total']['avg_steps']
        net = d['network']['total_network'] * d['total']['avg_steps']
        total = d['total']['avg_latency']
        llm = max(0, total - aq - inf - net)

        agent_queue.append(aq / 1000)
        infra_total.append(inf / 1000)
        network_total.append(net / 1000)
        llm_remainder.append(llm / 1000)

    bottom = np.zeros(len(letters))
    components = [
        ('Agent Queue Wait', agent_queue, '#F44336'),
        ('Infrastructure (CPU)', infra_total, '#FFC107'),
        ('Network Latency', network_total, '#9C27B0'),
        ('LLM Inference + Tool', llm_remainder, '#2196F3'),
    ]

    for label, vals, color in components:
        ax2.bar(x, vals, 0.5, bottom=bottom, label=label, color=color, alpha=0.85)
        bottom += np.array(vals)

    for i, l in enumerate(letters):
        ax2.text(i, bottom[i] + 0.05, f'{bottom[i]:.2f}s', ha='center', fontsize=9, fontweight='bold')

    ax2.set_ylabel('Average Latency (seconds)')
    ax2.set_title('Where Time Is Spent')
    ax2.set_xticks(x)
    ax2.set_xticklabels([LABELS[l] for l in letters])
    ax2.legend(loc='upper left')
    ax2.grid(axis='y', alpha=0.3)
    fig2.tight_layout()

    # ── Figure 3: Network vs Infra vs Agent Queue ──
    fig3, axes3 = plt.subplots(1, 3, figsize=(16, 5))
    fig3.suptitle('Experiment 3: Component-Level Comparison', fontsize=14, fontweight='bold')

    # Network per step
    ax = axes3[0]
    net_vals = [data[l]['network']['total_network'] for l in letters]
    bars = ax.bar(x, net_vals, 0.4, color=['#9C27B0'] * len(letters), alpha=0.85)
    for bar, v in zip(bars, net_vals):
        ax.text(bar.get_x() + bar.get_width()/2, v + 0.5, f'{v:.1f}ms', ha='center', fontsize=9)
    ax.set_ylabel('Network Latency per Step (ms)')
    ax.set_title('Network Overhead per LLM Call')
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[l] for l in letters])
    ax.grid(axis='y', alpha=0.3)

    # Infra per step
    ax = axes3[1]
    compute_vals = [data[l]['infra']['avg_compute'] for l in letters]
    queue_vals = [data[l]['infra']['avg_queue_wait'] for l in letters]
    ax.bar(x, compute_vals, 0.4, label='CPU Compute', color='#FFC107', alpha=0.85)
    ax.bar(x, queue_vals, 0.4, bottom=compute_vals, label='CPU Queue Wait', color='#FF9800', alpha=0.85)
    ax.set_ylabel('Avg Infra Latency per Step (ms)')
    ax.set_title('Infrastructure Contention')
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[l] for l in letters])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Success rate
    ax = axes3[2]
    for i, wl_name in enumerate(['chat-light', 'tool-heavy']):
        vals = [data[l]['by_workload'].get(wl_name, {}).get('success_rate', 0) for l in letters]
        offset = -width/2 + i * width
        ax.bar(x + offset, vals, width, label=wl_name, color=COLORS_WL[wl_name], alpha=0.85)
    ax.set_ylabel('Success Rate (%)')
    ax.set_title('Workflow Success Rate')
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[l] for l in letters])
    ax.set_ylim(0, 110)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    fig3.tight_layout()

    # ── Figure 4: Comparison Table ──
    fig4, ax4 = plt.subplots(figsize=(14, 7))
    fig4.suptitle('Experiment 3: Summary Comparison Table', fontsize=14, fontweight='bold')
    ax4.axis('off')

    headers = ['Metric'] + [LABELS[l].replace('\n', ' ') for l in letters]
    rows = []

    rows.append(['Placement'] + [
        'Both CLOUD', 'Chat EDGE / Tool CLOUD', 'Both EDGE'
    ][:len(letters)])
    rows.append(['Completed Workflows'] + [f'{data[l]["total"]["count"]}' for l in letters])
    rows.append(['Success Rate'] + [f'{data[l]["total"]["success_rate"]:.0f}%' for l in letters])
    rows.append(['Avg Latency (s)'] + [f'{data[l]["total"]["avg_latency"]/1000:.2f}' for l in letters])
    rows.append(['P95 Latency (s)'] + [f'{data[l]["total"]["p95_latency"]/1000:.2f}' for l in letters])
    rows.append(['Max Latency (s)'] + [f'{data[l]["total"]["max_latency"]/1000:.2f}' for l in letters])
    rows.append(['Avg Steps'] + [f'{data[l]["total"]["avg_steps"]:.1f}' for l in letters])
    rows.append(['Network/Step (ms)'] + [f'{data[l]["network"]["total_network"]:.1f}' for l in letters])
    rows.append(['Infra/Step (ms)'] + [f'{data[l]["infra"]["avg_infra_latency"]:.1f}' for l in letters])
    rows.append(['CPU Queue/Step (ms)'] + [f'{data[l]["infra"]["avg_queue_wait"]:.1f}' for l in letters])
    rows.append(['Agent Queue Events'] + [f'{data[l]["agent_queue"]["count"]}' for l in letters])
    rows.append(['Avg Agent Queue (ms)'] + [f'{data[l]["agent_queue"]["avg_wait"]:.0f}' for l in letters])
    rows.append(['Total Cost ($)'] + [f'{data[l]["total"]["total_cost"]:.4f}' for l in letters])

    # Chat-light breakdown
    rows.append(['--- chat-light ---'] + [''] * len(letters))
    for l_idx, l in enumerate(letters):
        wl = data[l]['by_workload'].get('chat-light')
        if wl and l_idx == 0:
            rows.append(['  Chat Avg Latency (s)'] + [
                f'{data[ll]["by_workload"].get("chat-light", {}).get("avg_latency", 0)/1000:.2f}' for ll in letters])
            rows.append(['  Chat P95 Latency (s)'] + [
                f'{data[ll]["by_workload"].get("chat-light", {}).get("p95_latency", 0)/1000:.2f}' for ll in letters])
            break

    # Tool-heavy breakdown
    rows.append(['--- tool-heavy ---'] + [''] * len(letters))
    for l_idx, l in enumerate(letters):
        wl = data[l]['by_workload'].get('tool-heavy')
        if wl and l_idx == 0:
            rows.append(['  Tool Avg Latency (s)'] + [
                f'{data[ll]["by_workload"].get("tool-heavy", {}).get("avg_latency", 0)/1000:.2f}' for ll in letters])
            rows.append(['  Tool P95 Latency (s)'] + [
                f'{data[ll]["by_workload"].get("tool-heavy", {}).get("p95_latency", 0)/1000:.2f}' for ll in letters])
            break

    table = ax4.table(cellText=rows, colLabels=headers, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.4)

    for j in range(len(headers)):
        table[0, j].set_facecolor('#E3F2FD')
        table[0, j].set_text_props(fontweight='bold')

    # Color latency rows
    if len(letters) > 1:
        for row_idx in [3, 4, 5]:
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

    # ── Figure 5: Latency Distributions ──
    fig5, axes5 = plt.subplots(1, 3, figsize=(16, 5))
    fig5.suptitle('Experiment 3: Latency Distributions by Placement', fontsize=14, fontweight='bold')

    for idx, letter in enumerate(letters[:3]):
        ax = axes5[idx]
        df = load_experiment(letter)
        if df is None:
            continue
        completes = df[df['event_type'] == 'COMPLETE'].copy()

        for wl_name in ['chat-light', 'tool-heavy']:
            wl = completes[completes['workload'] == wl_name]
            if not wl.empty:
                ax.hist(wl['total_latency_ms'] / 1000, bins=40, alpha=0.6,
                        label=wl_name, color=COLORS_WL[wl_name])

        ax.set_title(f'{LABELS[letter].replace(chr(10), " ")}')
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
