"""
Experiment 1: Simulator Validation Against M/M/c Queuing Theory

Reads trajectory CSVs from all 5 sub-experiments (exp1a through exp1e),
computes measured metrics, and plots them against M/M/c theoretical predictions.

Usage:
    1. Run each sub-experiment and save the trajectory:
       - Run with exp1_validation_a.json, rename agentic_trajectory.csv to exp1a_trajectory.csv
       - Repeat for b, c, d, e
    2. python visualize_experiment1.py

Requirements:
    pip install pandas matplotlib numpy scipy
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import sys
from math import factorial, exp

BASE_PATH = r'C:\Users\ileounakis\IdeaProjects\Simulator'

# ── M/M/c Theoretical Model ──────────────────────────────────

def erlang_c(c, rho_total):
    """Compute the Erlang C probability (probability of queuing) for M/M/c."""
    if rho_total >= c:
        return 1.0  # unstable
    rho_per_server = rho_total  # rho_total = lambda / mu
    a = rho_total  # offered load = lambda / mu

    # P(0) computation
    sum_part = sum((a ** k) / factorial(k) for k in range(c))
    last_term = ((a ** c) / factorial(c)) * (c / (c - rho_total))
    p0 = 1.0 / (sum_part + last_term)

    # Erlang C = P(queuing)
    pc = ((a ** c) / factorial(c)) * (c / (c - rho_total)) * p0
    return pc


def mmc_metrics(lambda_rate, mu_rate, c):
    """Compute M/M/c theoretical metrics."""
    rho_total = lambda_rate / mu_rate  # offered load
    rho = rho_total / c  # utilization per server

    if rho >= 1.0:
        return {
            'rho': rho,
            'wq_ms': float('inf'),
            'lq': float('inf'),
            'w_ms': float('inf'),
            'p_queue': 1.0,
            'stable': False,
        }

    pc = erlang_c(c, rho_total)

    # Average queue wait time
    wq = pc / (c * mu_rate * (1 - rho))
    wq_ms = wq * 1000.0

    # Average number in queue
    lq = pc * rho / (1 - rho)

    # Average total time in system (wait + service)
    w = wq + (1.0 / mu_rate)
    w_ms = w * 1000.0

    return {
        'rho': rho,
        'wq_ms': wq_ms,
        'lq': lq,
        'w_ms': w_ms,
        'p_queue': pc,
        'stable': True,
    }


# ── System Parameters ─────────────────────────────────────────

C_SERVERS = 5  # maxConcurrency
SERVICE_TIME_MS = 400.0 + 150 * 25.0 + 2.0  # TTFT + tokens*TPOT + network = 4152ms
SERVICE_TIME_S = SERVICE_TIME_MS / 1000.0
MU = 1.0 / SERVICE_TIME_S  # service rate per server

# Sub-experiments
RUNS = [
    {'name': '1a', 'file': 'exp1a_trajectory.csv', 'lambda': 0.3},
    {'name': '1b', 'file': 'exp1b_trajectory.csv', 'lambda': 0.6},
    {'name': '1c', 'file': 'exp1c_trajectory.csv', 'lambda': 0.9},
    {'name': '1d', 'file': 'exp1d_trajectory.csv', 'lambda': 1.1},
    {'name': '1e', 'file': 'exp1e_trajectory.csv', 'lambda': 1.2},
]


# ── Load & Measure ────────────────────────────────────────────

print("=" * 60)
print("Experiment 1: Simulator Validation vs M/M/c Theory")
print(f"System: c={C_SERVERS}, service_time={SERVICE_TIME_MS:.0f}ms, mu={MU:.4f}/s")
print(f"Max stable arrival rate: c*mu = {C_SERVERS * MU:.3f}/s")
print("=" * 60)

results = []

for run in RUNS:
    filepath = os.path.join(BASE_PATH, run['file'])
    theory = mmc_metrics(run['lambda'], MU, C_SERVERS)

    entry = {
        'name': run['name'],
        'lambda': run['lambda'],
        'rho': theory['rho'],
        'theory_wq_ms': theory['wq_ms'],
        'theory_lq': theory['lq'],
        'theory_w_ms': theory['w_ms'],
        'theory_p_queue': theory['p_queue'],
        'stable': theory['stable'],
    }

    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        print(f"\nRun {run['name']} (lambda={run['lambda']}/s): loaded {len(df)} events")

        # Measured: queue wait from QUEUE_EXIT events
        queue_exits = df[df['event_type'] == 'QUEUE_EXIT'].copy()
        if 'waited_ms' in queue_exits.columns:
            queue_exits['waited_ms'] = pd.to_numeric(queue_exits['waited_ms'], errors='coerce')

        # Measured: total workflow latency from COMPLETE events
        completes = df[df['event_type'] == 'COMPLETE'].copy()
        if 'total_latency_ms' in completes.columns:
            completes['total_latency_ms'] = pd.to_numeric(completes['total_latency_ms'], errors='coerce')

        # Count how many workflows queued vs went straight through
        total_workflows = len(df[df['event_type'] == 'SUBMIT'])
        queued_workflows = len(queue_exits)

        # Average queue wait (include 0 for workflows that didn't queue)
        if not queue_exits.empty:
            total_queue_wait = queue_exits['waited_ms'].sum()
            measured_avg_wq = total_queue_wait / total_workflows  # averaged over ALL workflows
            measured_max_wq = queue_exits['waited_ms'].max()
        else:
            measured_avg_wq = 0.0
            measured_max_wq = 0.0

        measured_p_queue = queued_workflows / total_workflows if total_workflows > 0 else 0

        # Average total latency
        if not completes.empty:
            measured_avg_latency = completes['total_latency_ms'].mean()
            measured_p99_latency = completes['total_latency_ms'].quantile(0.99)
        else:
            measured_avg_latency = 0.0
            measured_p99_latency = 0.0

        # Queue depth from QUEUE_ENTER events
        if 'queue_size' in df.columns:
            queue_enters = df[df['event_type'] == 'QUEUE_ENTER'].copy()
            queue_enters['queue_size'] = pd.to_numeric(queue_enters['queue_size'], errors='coerce')
            measured_avg_lq = queue_enters['queue_size'].mean() if not queue_enters.empty else 0
        else:
            measured_avg_lq = 0

        entry['measured_wq_ms'] = measured_avg_wq
        entry['measured_max_wq_ms'] = measured_max_wq
        entry['measured_p_queue'] = measured_p_queue
        entry['measured_latency_ms'] = measured_avg_latency
        entry['measured_p99_ms'] = measured_p99_latency
        entry['measured_lq'] = measured_avg_lq
        entry['total_workflows'] = total_workflows
        entry['completed'] = len(completes)
        entry['has_data'] = True

        print(f"  Workflows: {total_workflows} submitted, {len(completes)} completed")
        print(f"  Utilization (rho): {theory['rho']:.3f}")
        print(f"  Queue wait  - Theory: {theory['wq_ms']:>10.1f}ms | Measured: {measured_avg_wq:>10.1f}ms")
        print(f"  P(queue)    - Theory: {theory['p_queue']:>10.3f}   | Measured: {measured_p_queue:>10.3f}")
        print(f"  Avg latency - Theory: {theory['w_ms']:>10.1f}ms | Measured: {measured_avg_latency:>10.1f}ms")
    else:
        entry['has_data'] = False
        print(f"\nRun {run['name']} (lambda={run['lambda']}/s): FILE NOT FOUND ({run['file']})")
        print(f"  Theory: rho={theory['rho']:.3f}, Wq={theory['wq_ms']:.1f}ms, P(queue)={theory['p_queue']:.3f}")

    results.append(entry)

# Check if we have any data
has_any_data = any(r.get('has_data', False) for r in results)

if not has_any_data:
    print("\n" + "=" * 60)
    print("No trajectory files found. Run the experiments first:")
    print("  1. Run with experiments/exp1_validation_a.json")
    print("  2. Rename agentic_trajectory.csv to exp1a_trajectory.csv")
    print("  3. Repeat for b, c, d, e")
    print("=" * 60)
    print("\nShowing theoretical predictions only...")


# ── Plotting ──────────────────────────────────────────────────

lambdas = [r['lambda'] for r in results]
rhos = [r['rho'] for r in results]

# Generate smooth theoretical curve
lambda_smooth = np.linspace(0.05, C_SERVERS * MU * 0.99, 200)
theory_smooth_wq = []
theory_smooth_w = []
theory_smooth_pq = []
theory_smooth_lq = []
for lam in lambda_smooth:
    t = mmc_metrics(lam, MU, C_SERVERS)
    theory_smooth_wq.append(t['wq_ms'])
    theory_smooth_w.append(t['w_ms'])
    theory_smooth_pq.append(t['p_queue'])
    theory_smooth_lq.append(t['lq'])

theory_wq = [r['theory_wq_ms'] if r['stable'] else None for r in results]
theory_w = [r['theory_w_ms'] if r['stable'] else None for r in results]
theory_pq = [r['theory_p_queue'] for r in results]

measured_wq = [r.get('measured_wq_ms') for r in results]
measured_w = [r.get('measured_latency_ms') for r in results]
measured_pq = [r.get('measured_p_queue') for r in results]
measured_lq = [r.get('measured_lq') for r in results]


# ── Figure 1: Queue Wait Time ─────────────────────────────────

fig1, ax1 = plt.subplots(figsize=(10, 6))
fig1.suptitle('Experiment 1: Average Queue Wait Time - Simulator vs M/M/c Theory',
              fontsize=13, fontweight='bold')

ax1.plot(lambda_smooth, theory_smooth_wq, 'b-', linewidth=2, label='M/M/c Theory', alpha=0.7)

# Theory points
theory_wq_valid = [(l, w) for l, w in zip(lambdas, theory_wq) if w is not None]
if theory_wq_valid:
    ax1.scatter([x[0] for x in theory_wq_valid], [x[1] for x in theory_wq_valid],
                color='blue', s=80, zorder=5, marker='o', edgecolor='white', linewidth=1.5)

# Measured points
if has_any_data:
    meas_valid = [(l, w) for l, w in zip(lambdas, measured_wq) if w is not None]
    if meas_valid:
        ax1.scatter([x[0] for x in meas_valid], [x[1] for x in meas_valid],
                    color='red', s=100, zorder=6, marker='x', linewidth=2.5,
                    label='Simulator Measured')

ax1.set_xlabel('Arrival Rate (lambda, requests/s)', fontsize=11)
ax1.set_ylabel('Average Queue Wait Time (ms)', fontsize=11)
ax1.set_yscale('log')
ax1.set_ylim(bottom=0.1)
ax1.axvline(x=C_SERVERS * MU, color='gray', linestyle='--', alpha=0.5, label=f'Max capacity ({C_SERVERS*MU:.2f}/s)')
ax1.legend(fontsize=10)
ax1.grid(True, linestyle='--', alpha=0.4)
fig1.tight_layout()


# ── Figure 2: Total Workflow Latency ──────────────────────────

fig2, ax2 = plt.subplots(figsize=(10, 6))
fig2.suptitle('Experiment 1: Average Workflow Latency - Simulator vs M/M/c Theory',
              fontsize=13, fontweight='bold')

# Convert to seconds for readability
ax2.plot(lambda_smooth, [w / 1000 for w in theory_smooth_w], 'b-', linewidth=2,
         label='M/M/c Theory (Wq + service)', alpha=0.7)
ax2.axhline(y=SERVICE_TIME_S, color='green', linestyle=':', alpha=0.5,
            label=f'Service time only ({SERVICE_TIME_S:.2f}s)')

theory_w_valid = [(l, w) for l, w in zip(lambdas, theory_w) if w is not None]
if theory_w_valid:
    ax2.scatter([x[0] for x in theory_w_valid], [x[1] / 1000 for x in theory_w_valid],
                color='blue', s=80, zorder=5, marker='o', edgecolor='white', linewidth=1.5)

if has_any_data:
    meas_w_valid = [(l, w) for l, w in zip(lambdas, measured_w) if w is not None]
    if meas_w_valid:
        ax2.scatter([x[0] for x in meas_w_valid], [x[1] / 1000 for x in meas_w_valid],
                    color='red', s=100, zorder=6, marker='x', linewidth=2.5,
                    label='Simulator Measured')

ax2.set_xlabel('Arrival Rate (lambda, requests/s)', fontsize=11)
ax2.set_ylabel('Average Workflow Latency (seconds)', fontsize=11)
ax2.axvline(x=C_SERVERS * MU, color='gray', linestyle='--', alpha=0.5, label=f'Max capacity ({C_SERVERS*MU:.2f}/s)')
ax2.legend(fontsize=10)
ax2.grid(True, linestyle='--', alpha=0.4)
fig2.tight_layout()


# ── Figure 3: Probability of Queuing ─────────────────────────

fig3, ax3 = plt.subplots(figsize=(10, 6))
fig3.suptitle('Experiment 1: Probability of Queuing - Simulator vs M/M/c Theory',
              fontsize=13, fontweight='bold')

ax3.plot(lambda_smooth, theory_smooth_pq, 'b-', linewidth=2, label='M/M/c Theory (Erlang C)', alpha=0.7)
ax3.scatter(lambdas, theory_pq, color='blue', s=80, zorder=5, marker='o',
            edgecolor='white', linewidth=1.5)

if has_any_data:
    meas_pq_valid = [(l, p) for l, p in zip(lambdas, measured_pq) if p is not None]
    if meas_pq_valid:
        ax3.scatter([x[0] for x in meas_pq_valid], [x[1] for x in meas_pq_valid],
                    color='red', s=100, zorder=6, marker='x', linewidth=2.5,
                    label='Simulator Measured')

ax3.set_xlabel('Arrival Rate (lambda, requests/s)', fontsize=11)
ax3.set_ylabel('P(queuing)', fontsize=11)
ax3.axvline(x=C_SERVERS * MU, color='gray', linestyle='--', alpha=0.5, label=f'Max capacity ({C_SERVERS*MU:.2f}/s)')
ax3.set_ylim(-0.05, 1.05)
ax3.legend(fontsize=10)
ax3.grid(True, linestyle='--', alpha=0.4)
fig3.tight_layout()


# ── Figure 4: Comparison Table ────────────────────────────────

fig4, ax4 = plt.subplots(figsize=(14, 4))
fig4.suptitle('Experiment 1: Numerical Comparison', fontsize=13, fontweight='bold')
ax4.axis('off')

headers = ['Run', 'Lambda', 'Rho', 'Theory Wq', 'Measured Wq', 'Theory P(q)', 'Measured P(q)',
           'Theory W', 'Measured W']
table_data = []

for r in results:
    row = [
        r['name'],
        f"{r['lambda']:.1f}/s",
        f"{r['rho']:.3f}",
        f"{r['theory_wq_ms']:.0f}ms" if r['stable'] else "unstable",
        f"{r.get('measured_wq_ms', '-'):.0f}ms" if r.get('has_data') else "-",
        f"{r['theory_p_queue']:.3f}",
        f"{r.get('measured_p_queue', '-'):.3f}" if r.get('has_data') else "-",
        f"{r['theory_w_ms']:.0f}ms" if r['stable'] else "unstable",
        f"{r.get('measured_latency_ms', '-'):.0f}ms" if r.get('has_data') else "-",
    ]
    table_data.append(row)

table = ax4.table(cellText=table_data, colLabels=headers, loc='center',
                  cellLoc='center', colColours=['#d4e6f1'] * len(headers))
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1.0, 1.6)

# Color cells based on match quality
if has_any_data:
    for i, r in enumerate(results):
        if r.get('has_data') and r['stable']:
            # Color Wq comparison
            theory_val = r['theory_wq_ms']
            meas_val = r.get('measured_wq_ms', 0)
            if theory_val > 0:
                error = abs(meas_val - theory_val) / theory_val
                color = '#abebc6' if error < 0.3 else '#f9e79f' if error < 0.6 else '#f5b7b1'
                table[i + 1, 4].set_facecolor(color)

fig4.tight_layout()


# ── Figure 5: Error Analysis ─────────────────────────────────

if has_any_data:
    fig5, (ax5a, ax5b) = plt.subplots(1, 2, figsize=(14, 5))
    fig5.suptitle('Experiment 1: Theory vs Measured - Error Analysis',
                  fontsize=13, fontweight='bold')

    valid_results = [r for r in results if r.get('has_data') and r['stable']]

    if valid_results:
        # 5a: Scatter plot - theory vs measured Wq
        t_wq = [r['theory_wq_ms'] for r in valid_results]
        m_wq = [r['measured_wq_ms'] for r in valid_results]

        max_val = max(max(t_wq), max(m_wq)) * 1.2 if t_wq and m_wq else 100
        ax5a.plot([0, max_val], [0, max_val], 'k--', alpha=0.3, label='Perfect match')
        ax5a.scatter(t_wq, m_wq, color='#e74c3c', s=100, zorder=5, edgecolor='white', linewidth=1.5)

        for r in valid_results:
            ax5a.annotate(f"  {r['name']} (rho={r['rho']:.2f})",
                         (r['theory_wq_ms'], r['measured_wq_ms']), fontsize=8)

        ax5a.set_xlabel('M/M/c Theoretical Wq (ms)', fontsize=11)
        ax5a.set_ylabel('Simulator Measured Wq (ms)', fontsize=11)
        ax5a.set_title('Queue Wait: Theory vs Measured')
        ax5a.legend()
        ax5a.grid(True, linestyle='--', alpha=0.4)

        # 5b: Relative error bar chart
        names = [r['name'] for r in valid_results]
        errors_wq = []
        for r in valid_results:
            if r['theory_wq_ms'] > 1:  # avoid division by near-zero
                errors_wq.append((r['measured_wq_ms'] - r['theory_wq_ms']) / r['theory_wq_ms'] * 100)
            else:
                errors_wq.append(0)

        colors = ['#abebc6' if abs(e) < 30 else '#f9e79f' if abs(e) < 60 else '#f5b7b1' for e in errors_wq]
        ax5b.bar(names, errors_wq, color=colors, edgecolor='white', linewidth=1.5)
        ax5b.axhline(y=0, color='black', linewidth=0.5)
        ax5b.axhline(y=30, color='green', linewidth=0.5, linestyle='--', alpha=0.5, label='+/- 30%')
        ax5b.axhline(y=-30, color='green', linewidth=0.5, linestyle='--', alpha=0.5)

        ax5b.set_xlabel('Run', fontsize=11)
        ax5b.set_ylabel('Relative Error (%)', fontsize=11)
        ax5b.set_title('Queue Wait Relative Error')
        ax5b.legend()
        ax5b.grid(True, linestyle='--', alpha=0.4)

    fig5.tight_layout()


print("\n" + "=" * 60)
print("Close the chart windows to exit.")
print("=" * 60)

plt.show()
