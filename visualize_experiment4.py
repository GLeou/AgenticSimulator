"""
Experiment 4: Isolation & Stress Test
Compares 3 architectures at 3 load levels (9 runs total):
  A: Fully Shared  (1 agent, 1 node 16 cores, maxConcurrency=35)
  B: Agent-Isolated (2 agents, 1 node 16 cores, separate concurrency)
  C: Fully Isolated (2 agents, 2 nodes 8 cores each)

Load levels:
  1: Low    (chat=0.5/s, tool=0.3/s)
  2: Medium (chat=2.0/s, tool=1.3/s)
  3: High   (chat=5.0/s, tool=3.0/s)

Usage:
    python visualize_experiment4.py
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

BASE_PATH = r'C:\Users\ileounakis\IdeaProjects\Simulator'

ARCH_LABELS = {'a': 'Fully Shared', 'b': 'Agent-Isolated', 'c': 'Fully Isolated'}
LOAD_LABELS = {'1': 'Low', '2': 'Medium', '3': 'High'}
LOAD_RATES = {'1': '0.5+0.3', '2': '2.0+1.3', '3': '5.0+3.0'}
ARCH_COLORS = {'a': '#4CAF50', 'b': '#FF9800', 'c': '#2196F3'}
WL_COLORS = {'chat-light': '#2196F3', 'tool-heavy': '#FF9800'}


def load_experiment(arch, load):
    path = os.path.join(BASE_PATH, f'exp4{arch}{load}_trajectory.csv')
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
    print('Experiment 4: Isolation & Stress Test')
    print('3 architectures x 3 load levels = 9 runs')
    print('=' * 60)

    data = {}
    for arch in ['a', 'b', 'c']:
        for load in ['1', '2', '3']:
            key = f'{arch}{load}'
            print(f'\nLoading exp4{key} ({ARCH_LABELS[arch]}, {LOAD_LABELS[load]} load)...')
            df = load_experiment(arch, load)
            if df is not None:
                metrics = extract_metrics(df)
                if metrics:
                    data[key] = metrics
                    print(f'  Workflows: {metrics["total"]["count"]}, '
                          f'Avg latency: {metrics["total"]["avg_latency"]:.0f}ms, '
                          f'Success: {metrics["total"]["success_rate"]:.0f}%')

    if not data:
        print('\nNo data found. Run experiments first.')
        return

    archs = ['a', 'b', 'c']
    loads = ['1', '2', '3']
    x = np.arange(len(loads))
    width = 0.25

    # ── Figure 1: Avg Latency by Architecture across Load Levels ──
    fig1, axes1 = plt.subplots(1, 2, figsize=(15, 6))
    fig1.suptitle('Experiment 4: Latency vs Load Level by Architecture', fontsize=14, fontweight='bold')

    # Overall avg latency
    ax = axes1[0]
    for i, arch in enumerate(archs):
        vals = []
        for load in loads:
            key = f'{arch}{load}'
            vals.append(data[key]['total']['avg_latency'] / 1000 if key in data else 0)
        offset = -width + i * width
        bars = ax.bar(x + offset, vals, width, label=ARCH_LABELS[arch], color=ARCH_COLORS[arch], alpha=0.85)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                        f'{v:.1f}s', ha='center', va='bottom', fontsize=7, rotation=45)
    ax.set_ylabel('Average Latency (seconds)')
    ax.set_title('Average End-to-End Latency')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{LOAD_LABELS[l]}\n({LOAD_RATES[l]}/s)' for l in loads])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # P95 latency
    ax = axes1[1]
    for i, arch in enumerate(archs):
        vals = []
        for load in loads:
            key = f'{arch}{load}'
            vals.append(data[key]['total']['p95_latency'] / 1000 if key in data else 0)
        offset = -width + i * width
        bars = ax.bar(x + offset, vals, width, label=ARCH_LABELS[arch], color=ARCH_COLORS[arch], alpha=0.85)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                        f'{v:.1f}s', ha='center', va='bottom', fontsize=7, rotation=45)
    ax.set_ylabel('P95 Latency (seconds)')
    ax.set_title('P95 End-to-End Latency')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{LOAD_LABELS[l]}\n({LOAD_RATES[l]}/s)' for l in loads])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    fig1.tight_layout()

    # ── Figure 2: Per-Workload Latency (chat vs tool) ──
    fig2, axes2 = plt.subplots(2, 3, figsize=(16, 10))
    fig2.suptitle('Experiment 4: Per-Workload Latency by Architecture & Load', fontsize=14, fontweight='bold')

    for row, wl_name in enumerate(['chat-light', 'tool-heavy']):
        for col, load in enumerate(loads):
            ax = axes2[row][col]
            vals = []
            colors = []
            labels = []
            for arch in archs:
                key = f'{arch}{load}'
                if key in data:
                    wl_data = data[key]['by_workload'].get(wl_name)
                    vals.append(wl_data['avg_latency'] / 1000 if wl_data else 0)
                else:
                    vals.append(0)
                colors.append(ARCH_COLORS[arch])
                labels.append(ARCH_LABELS[arch])

            bars = ax.bar(range(len(archs)), vals, color=colors, alpha=0.85)
            for bar, v in zip(bars, vals):
                if v > 0:
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                            f'{v:.2f}s', ha='center', va='bottom', fontsize=8)
            ax.set_title(f'{wl_name} - {LOAD_LABELS[load]} Load')
            ax.set_xticks(range(len(archs)))
            ax.set_xticklabels([ARCH_LABELS[a] for a in archs], fontsize=8)
            ax.set_ylabel('Avg Latency (s)')
            ax.grid(axis='y', alpha=0.3)
    fig2.tight_layout()

    # ── Figure 3: Contention Indicators ──
    fig3, axes3 = plt.subplots(1, 3, figsize=(16, 5))
    fig3.suptitle('Experiment 4: Contention Indicators', fontsize=14, fontweight='bold')

    # Agent queue events
    ax = axes3[0]
    for i, arch in enumerate(archs):
        vals = [data.get(f'{arch}{l}', {}).get('agent_queue', {}).get('count', 0) for l in loads]
        offset = -width + i * width
        ax.bar(x + offset, vals, width, label=ARCH_LABELS[arch], color=ARCH_COLORS[arch], alpha=0.85)
    ax.set_ylabel('Agent Queue Events')
    ax.set_title('Agent-Level Queuing')
    ax.set_xticks(x)
    ax.set_xticklabels([LOAD_LABELS[l] for l in loads])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Avg CPU queue wait per step
    ax = axes3[1]
    for i, arch in enumerate(archs):
        vals = [data.get(f'{arch}{l}', {}).get('infra', {}).get('avg_queue_wait', 0) for l in loads]
        offset = -width + i * width
        ax.bar(x + offset, vals, width, label=ARCH_LABELS[arch], color=ARCH_COLORS[arch], alpha=0.85)
    ax.set_ylabel('Avg CPU Queue Wait/Step (ms)')
    ax.set_title('Infrastructure CPU Queuing')
    ax.set_xticks(x)
    ax.set_xticklabels([LOAD_LABELS[l] for l in loads])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Success rate
    ax = axes3[2]
    for i, arch in enumerate(archs):
        vals = [data.get(f'{arch}{l}', {}).get('total', {}).get('success_rate', 0) for l in loads]
        offset = -width + i * width
        ax.bar(x + offset, vals, width, label=ARCH_LABELS[arch], color=ARCH_COLORS[arch], alpha=0.85)
    ax.set_ylabel('Success Rate (%)')
    ax.set_title('Workflow Success Rate')
    ax.set_xticks(x)
    ax.set_xticklabels([LOAD_LABELS[l] for l in loads])
    ax.set_ylim(0, 110)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    fig3.tight_layout()

    # ── Figure 4: Heatmap - Avg Latency ──
    fig4, axes4 = plt.subplots(1, 3, figsize=(16, 5))
    fig4.suptitle('Experiment 4: Latency Heatmaps', fontsize=14, fontweight='bold')

    for idx, (metric_name, metric_key, unit) in enumerate([
        ('Avg Latency', lambda d: d['total']['avg_latency'] / 1000, 's'),
        ('P95 Latency', lambda d: d['total']['p95_latency'] / 1000, 's'),
        ('CPU Queue/Step', lambda d: d['infra']['avg_queue_wait'], 'ms'),
    ]):
        ax = axes4[idx]
        matrix = np.zeros((len(archs), len(loads)))
        for i, arch in enumerate(archs):
            for j, load in enumerate(loads):
                key = f'{arch}{load}'
                if key in data:
                    matrix[i, j] = metric_key(data[key])

        im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto')
        ax.set_xticks(range(len(loads)))
        ax.set_xticklabels([LOAD_LABELS[l] for l in loads])
        ax.set_yticks(range(len(archs)))
        ax.set_yticklabels([ARCH_LABELS[a] for a in archs])
        ax.set_title(metric_name)

        for i in range(len(archs)):
            for j in range(len(loads)):
                val = matrix[i, j]
                text_color = 'white' if val > matrix.max() * 0.6 else 'black'
                ax.text(j, i, f'{val:.1f}{unit}', ha='center', va='center',
                        color=text_color, fontsize=9, fontweight='bold')

        plt.colorbar(im, ax=ax, shrink=0.8)
    fig4.tight_layout()

    # ── Figure 5: Comparison Table ──
    fig5, ax5 = plt.subplots(figsize=(18, 10))
    fig5.suptitle('Experiment 4: Full Comparison Table', fontsize=14, fontweight='bold')
    ax5.axis('off')

    col_labels = ['Metric']
    for load in loads:
        for arch in archs:
            col_labels.append(f'{ARCH_LABELS[arch][:7]}\n{LOAD_LABELS[load]}')

    rows = []
    def get_val(arch, load, func, fmt):
        key = f'{arch}{load}'
        if key in data:
            return fmt.format(func(data[key]))
        return 'N/A'

    rows.append(['Completed'] + [get_val(a, l, lambda d: d['total']['count'], '{}') for l in loads for a in archs])
    rows.append(['Success %'] + [get_val(a, l, lambda d: d['total']['success_rate'], '{:.0f}%') for l in loads for a in archs])
    rows.append(['Avg Latency (s)'] + [get_val(a, l, lambda d: d['total']['avg_latency']/1000, '{:.2f}') for l in loads for a in archs])
    rows.append(['P95 Latency (s)'] + [get_val(a, l, lambda d: d['total']['p95_latency']/1000, '{:.2f}') for l in loads for a in archs])
    rows.append(['Max Latency (s)'] + [get_val(a, l, lambda d: d['total']['max_latency']/1000, '{:.1f}') for l in loads for a in archs])
    rows.append(['Avg Steps'] + [get_val(a, l, lambda d: d['total']['avg_steps'], '{:.1f}') for l in loads for a in archs])
    rows.append(['Infra/Step (ms)'] + [get_val(a, l, lambda d: d['infra']['avg_infra_latency'], '{:.1f}') for l in loads for a in archs])
    rows.append(['CPU Queue/Step (ms)'] + [get_val(a, l, lambda d: d['infra']['avg_queue_wait'], '{:.1f}') for l in loads for a in archs])
    rows.append(['Agent Queue Events'] + [get_val(a, l, lambda d: d['agent_queue']['count'], '{}') for l in loads for a in archs])
    rows.append(['Avg Agent Queue (ms)'] + [get_val(a, l, lambda d: d['agent_queue']['avg_wait'], '{:.0f}') for l in loads for a in archs])
    rows.append(['Total Cost ($)'] + [get_val(a, l, lambda d: d['total']['total_cost'], '{:.4f}') for l in loads for a in archs])

    # Chat-light breakdown
    rows.append(['-- chat-light --'] + [''] * (len(loads) * len(archs)))
    rows.append(['  Avg Latency (s)'] + [get_val(a, l, lambda d: d['by_workload'].get('chat-light', {}).get('avg_latency', 0)/1000, '{:.2f}') for l in loads for a in archs])
    rows.append(['  P95 Latency (s)'] + [get_val(a, l, lambda d: d['by_workload'].get('chat-light', {}).get('p95_latency', 0)/1000, '{:.2f}') for l in loads for a in archs])
    rows.append(['  Success %'] + [get_val(a, l, lambda d: d['by_workload'].get('chat-light', {}).get('success_rate', 0), '{:.0f}%') for l in loads for a in archs])

    # Tool-heavy breakdown
    rows.append(['-- tool-heavy --'] + [''] * (len(loads) * len(archs)))
    rows.append(['  Avg Latency (s)'] + [get_val(a, l, lambda d: d['by_workload'].get('tool-heavy', {}).get('avg_latency', 0)/1000, '{:.2f}') for l in loads for a in archs])
    rows.append(['  P95 Latency (s)'] + [get_val(a, l, lambda d: d['by_workload'].get('tool-heavy', {}).get('p95_latency', 0)/1000, '{:.2f}') for l in loads for a in archs])
    rows.append(['  Success %'] + [get_val(a, l, lambda d: d['by_workload'].get('tool-heavy', {}).get('success_rate', 0), '{:.0f}%') for l in loads for a in archs])

    table = ax5.table(cellText=rows, colLabels=col_labels, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(7)
    table.scale(1, 1.3)

    # Color header
    for j in range(len(col_labels)):
        table[0, j].set_facecolor('#E3F2FD')
        table[0, j].set_text_props(fontweight='bold', fontsize=7)

    # Color architecture columns
    for row_idx in range(len(rows)):
        for col_idx in range(1, len(col_labels)):
            arch_idx = (col_idx - 1) % len(archs)
            arch = archs[arch_idx]
            table[row_idx + 1, col_idx].set_facecolor((*[int(ARCH_COLORS[arch][i:i+2], 16)/255 for i in (1,3,5)], 0.1))

    fig5.tight_layout()

    # ── Figure 6: Chat-light Isolation Effect ──
    fig6, axes6 = plt.subplots(1, 2, figsize=(14, 6))
    fig6.suptitle('Experiment 4: Isolation Effect on chat-light Under Stress',
                   fontsize=14, fontweight='bold')

    # Show how chat-light latency changes as tool-heavy load increases
    ax = axes6[0]
    for i, arch in enumerate(archs):
        vals = []
        for load in loads:
            key = f'{arch}{load}'
            if key in data:
                wl = data[key]['by_workload'].get('chat-light')
                vals.append(wl['avg_latency'] / 1000 if wl else 0)
            else:
                vals.append(0)
        ax.plot(range(len(loads)), vals, 'o-', label=ARCH_LABELS[arch],
                color=ARCH_COLORS[arch], linewidth=2, markersize=8)
    ax.set_ylabel('Avg Latency (seconds)')
    ax.set_title('chat-light Avg Latency')
    ax.set_xticks(range(len(loads)))
    ax.set_xticklabels([f'{LOAD_LABELS[l]}\n({LOAD_RATES[l]}/s)' for l in loads])
    ax.legend()
    ax.grid(alpha=0.3)

    ax = axes6[1]
    for i, arch in enumerate(archs):
        vals = []
        for load in loads:
            key = f'{arch}{load}'
            if key in data:
                wl = data[key]['by_workload'].get('chat-light')
                vals.append(wl['p95_latency'] / 1000 if wl else 0)
            else:
                vals.append(0)
        ax.plot(range(len(loads)), vals, 'o-', label=ARCH_LABELS[arch],
                color=ARCH_COLORS[arch], linewidth=2, markersize=8)
    ax.set_ylabel('P95 Latency (seconds)')
    ax.set_title('chat-light P95 Latency')
    ax.set_xticks(range(len(loads)))
    ax.set_xticklabels([f'{LOAD_LABELS[l]}\n({LOAD_RATES[l]}/s)' for l in loads])
    ax.legend()
    ax.grid(alpha=0.3)
    fig6.tight_layout()

    print('\n' + '=' * 60)
    print('Close the chart windows to exit.')
    print('=' * 60)
    plt.show()


if __name__ == '__main__':
    main()
