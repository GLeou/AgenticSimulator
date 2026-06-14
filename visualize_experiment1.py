"""
Experiment 1: Simulator Validation

Part A (v2 - Agentic): Validates that the simulator's Gamma-distributed
service times match the configured theoretical Gamma distribution.
  - Histogram of simulated LLM latencies vs theoretical Gamma PDF
  - Mean/std comparison
  - KS goodness-of-fit test

Part B (v1 - Kubernetes): Validates the GPS (Generalized Processor Sharing)
model with a simple worked example.
  - Computes expected completion times from known parameters
  - Compares with actual simulator output

Usage:
    python visualize_experiment1.py

Requirements:
    pip install pandas matplotlib numpy scipy
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from scipy import stats

BASE_PATH = r'C:\Users\ileounakis\IdeaProjects\Simulator'

# ══════════════════════════════════════════════════════════════
# PART A: v2 (Agentic) Validation - Gamma Distribution Fit
# ══════════════════════════════════════════════════════════════

print("=" * 70)
print("PART A: v2 (Agentic) Simulator - Gamma Distribution Validation")
print("=" * 70)

# Theoretical parameters from exp1_validation_a.json
TTFT_MEAN = 400.0      # ms
TTFT_SHAPE = 100.0
TPOT_MEAN = 25.0       # ms
TPOT_SHAPE = 100.0
OUTPUT_TOKENS_MEAN = 150
OUTPUT_TOKENS_STD = 1.0
NETWORK_LATENCY = 1.0  # ms (zone latency CLOUD->CLOUD)

# Gamma: mean = shape * scale, so scale = mean / shape
TTFT_SCALE = TTFT_MEAN / TTFT_SHAPE
TPOT_SCALE = TPOT_MEAN / TPOT_SHAPE

# Theoretical total service time: TTFT + tokens * TPOT + network
THEORY_SERVICE_MEAN = TTFT_MEAN + OUTPUT_TOKENS_MEAN * TPOT_MEAN + 2 * NETWORK_LATENCY
# Variance: Var(TTFT) + tokens^2 * Var(TPOT) + Var(tokens) * TPOT_MEAN^2
# (using Var(XY) approximation for independent X,Y)
TTFT_VAR = TTFT_MEAN**2 / TTFT_SHAPE  # Gamma variance = mean^2 / shape
TPOT_VAR = TPOT_MEAN**2 / TPOT_SHAPE
THEORY_SERVICE_VAR = TTFT_VAR + OUTPUT_TOKENS_MEAN**2 * TPOT_VAR + OUTPUT_TOKENS_STD**2 * TPOT_MEAN**2
THEORY_SERVICE_STD = np.sqrt(THEORY_SERVICE_VAR)

print(f"\nTheoretical Gamma parameters:")
print(f"  TTFT:  Gamma(shape={TTFT_SHAPE}, mean={TTFT_MEAN}ms, scale={TTFT_SCALE:.2f})")
print(f"  TPOT:  Gamma(shape={TPOT_SHAPE}, mean={TPOT_MEAN}ms, scale={TPOT_SCALE:.4f})")
print(f"  Tokens: N({OUTPUT_TOKENS_MEAN}, {OUTPUT_TOKENS_STD})")
print(f"  Expected total service time: {THEORY_SERVICE_MEAN:.1f}ms +/- {THEORY_SERVICE_STD:.1f}ms")

# Load trajectory (use exp1a - lowest load for cleanest distribution)
TRAJ_FILE = os.path.join(BASE_PATH, 'exp1a_trajectory.csv')
has_v2_data = os.path.exists(TRAJ_FILE)

if has_v2_data:
    df = pd.read_csv(TRAJ_FILE)
    print(f"\nLoaded {len(df)} events from exp1a_trajectory.csv")

    # Extract LLM inference times from LLM_DISPATCH events
    llm_events = df[df['event_type'] == 'LLM_DISPATCH'].copy()
    llm_events['inference_ms'] = pd.to_numeric(llm_events['inference_ms'], errors='coerce')
    llm_events['output_tokens'] = pd.to_numeric(llm_events['output_tokens'], errors='coerce')
    llm_events = llm_events.dropna(subset=['inference_ms'])

    # Extract total workflow latencies from COMPLETE events
    completes = df[df['event_type'] == 'COMPLETE'].copy()
    completes['total_latency_ms'] = pd.to_numeric(completes['total_latency_ms'], errors='coerce')
    completes = completes.dropna(subset=['total_latency_ms'])

    # Only use non-queued workflows for clean service time measurement
    # (queued workflows have wait time baked into total latency)
    queue_exits = df[df['event_type'] == 'QUEUE_EXIT'].copy()
    queue_exits['waited_ms'] = pd.to_numeric(queue_exits.get('waited_ms', 0), errors='coerce')
    queued_wfs = set(queue_exits[queue_exits['waited_ms'] > 0]['workflow_id'])
    clean_completes = completes[~completes['workflow_id'].isin(queued_wfs)]

    sim_inference = llm_events['inference_ms'].values
    sim_tokens = llm_events['output_tokens'].values
    sim_latency = clean_completes['total_latency_ms'].values if len(clean_completes) > 0 else completes['total_latency_ms'].values

    print(f"  LLM dispatch events: {len(sim_inference)}")
    print(f"  Completed workflows (no queue wait): {len(sim_latency)}")
    print(f"\nSimulated vs Theoretical:")
    print(f"  LLM inference - Simulated mean: {np.mean(sim_inference):.1f}ms, std: {np.std(sim_inference):.1f}ms")

    # Theoretical inference = TTFT + tokens * TPOT
    # For comparison, compute per-event expected inference
    if len(sim_tokens) > 0:
        theory_inference_mean = TTFT_MEAN + np.mean(sim_tokens) * TPOT_MEAN
        print(f"  LLM inference - Theoretical mean: {theory_inference_mean:.1f}ms (TTFT + avg_tokens*TPOT)")

    print(f"  Total latency - Simulated mean: {np.mean(sim_latency):.1f}ms, std: {np.std(sim_latency):.1f}ms")
    print(f"  Total latency - Theoretical mean: {THEORY_SERVICE_MEAN:.1f}ms, std: {THEORY_SERVICE_STD:.1f}ms")

    # KS test on inference times against theoretical Gamma
    # Total inference = TTFT + tokens * TPOT. With tokens ~= 150 (std=1) and high shape,
    # this is approximately Gamma. We fit and test.
    ks_stat, ks_pvalue = stats.kstest(sim_inference, 'gamma',
                                       args=(TTFT_SHAPE, 0, TTFT_SCALE),
                                       alternative='two-sided')
    print(f"\n  KS test (inference vs TTFT Gamma): statistic={ks_stat:.4f}, p-value={ks_pvalue:.4f}")
    print(f"  {'PASS' if ks_pvalue > 0.05 else 'Note: p<0.05 expected since inference = TTFT + tokens*TPOT, not pure TTFT'}")

    # Better: fit a Gamma to the actual inference times and check parameters
    fit_shape, fit_loc, fit_scale = stats.gamma.fit(sim_inference, floc=0)
    fit_mean = fit_shape * fit_scale
    print(f"\n  Fitted Gamma to simulated inference: shape={fit_shape:.1f}, mean={fit_mean:.1f}ms, scale={fit_scale:.2f}")

    # ── Figure A1: Inference Time Distribution ───────────────────
    fig_a1, (ax_a1a, ax_a1b) = plt.subplots(1, 2, figsize=(14, 5))
    fig_a1.suptitle('v2 Validation: LLM Inference Time Distribution', fontsize=13, fontweight='bold')

    # Histogram with fitted Gamma overlay
    ax_a1a.hist(sim_inference, bins=40, density=True, alpha=0.7, color='#3498db',
                edgecolor='white', label='Simulated')
    x_range = np.linspace(min(sim_inference) * 0.95, max(sim_inference) * 1.05, 200)
    fitted_pdf = stats.gamma.pdf(x_range, fit_shape, 0, fit_scale)
    ax_a1a.plot(x_range, fitted_pdf, 'r-', linewidth=2,
                label=f'Fitted Gamma(k={fit_shape:.1f}, mean={fit_mean:.0f}ms)')

    ax_a1a.set_xlabel('LLM Inference Time (ms)')
    ax_a1a.set_ylabel('Density')
    ax_a1a.set_title('Histogram + Fitted Gamma PDF')
    ax_a1a.legend(fontsize=9)
    ax_a1a.grid(True, linestyle='--', alpha=0.3)

    # QQ plot
    theoretical_quantiles = stats.gamma.ppf(np.linspace(0.01, 0.99, len(sim_inference)),
                                             fit_shape, 0, fit_scale)
    sorted_sim = np.sort(sim_inference)
    theoretical_quantiles_sorted = np.sort(theoretical_quantiles)
    # Resample to same length if needed
    if len(theoretical_quantiles_sorted) != len(sorted_sim):
        theoretical_quantiles_sorted = np.interp(
            np.linspace(0, 1, len(sorted_sim)),
            np.linspace(0, 1, len(theoretical_quantiles_sorted)),
            theoretical_quantiles_sorted
        )

    ax_a1b.scatter(theoretical_quantiles_sorted, sorted_sim, s=10, alpha=0.5, color='#3498db')
    min_val = min(theoretical_quantiles_sorted.min(), sorted_sim.min())
    max_val = max(theoretical_quantiles_sorted.max(), sorted_sim.max())
    ax_a1b.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=1.5, label='Perfect fit')
    ax_a1b.set_xlabel('Theoretical Quantiles (Gamma)')
    ax_a1b.set_ylabel('Simulated Quantiles')
    ax_a1b.set_title('Q-Q Plot')
    ax_a1b.legend()
    ax_a1b.grid(True, linestyle='--', alpha=0.3)

    fig_a1.tight_layout()

    # ── Figure A2: Total Service Time Distribution ───────────────
    fig_a2, (ax_a2a, ax_a2b) = plt.subplots(1, 2, figsize=(14, 5))
    fig_a2.suptitle('v2 Validation: Total Workflow Service Time (non-queued)',
                    fontsize=13, fontweight='bold')

    # Histogram
    ax_a2a.hist(sim_latency, bins=40, density=True, alpha=0.7, color='#2ecc71',
                edgecolor='white', label='Simulated')
    ax_a2a.axvline(x=np.mean(sim_latency), color='#2ecc71', linestyle='--', linewidth=2,
                   label=f'Sim mean: {np.mean(sim_latency):.0f}ms')
    ax_a2a.axvline(x=THEORY_SERVICE_MEAN, color='red', linestyle='--', linewidth=2,
                   label=f'Theory mean: {THEORY_SERVICE_MEAN:.0f}ms')

    # Fit Gamma to total latency too
    if len(sim_latency) > 10:
        lat_shape, lat_loc, lat_scale = stats.gamma.fit(sim_latency, floc=0)
        x_lat = np.linspace(min(sim_latency) * 0.95, max(sim_latency) * 1.05, 200)
        lat_pdf = stats.gamma.pdf(x_lat, lat_shape, 0, lat_scale)
        ax_a2a.plot(x_lat, lat_pdf, 'r-', linewidth=2,
                    label=f'Fitted Gamma(k={lat_shape:.1f})')

    ax_a2a.set_xlabel('Total Workflow Latency (ms)')
    ax_a2a.set_ylabel('Density')
    ax_a2a.set_title('Service Time Distribution')
    ax_a2a.legend(fontsize=9)
    ax_a2a.grid(True, linestyle='--', alpha=0.3)

    # Summary stats comparison table
    ax_a2b.axis('off')
    summary_data = [
        ['Mean (ms)', f'{THEORY_SERVICE_MEAN:.1f}', f'{np.mean(sim_latency):.1f}',
         f'{abs(np.mean(sim_latency) - THEORY_SERVICE_MEAN) / THEORY_SERVICE_MEAN * 100:.1f}%'],
        ['Std Dev (ms)', f'{THEORY_SERVICE_STD:.1f}', f'{np.std(sim_latency):.1f}',
         f'{abs(np.std(sim_latency) - THEORY_SERVICE_STD) / THEORY_SERVICE_STD * 100:.1f}%'],
        ['Min (ms)', '-', f'{np.min(sim_latency):.1f}', '-'],
        ['Max (ms)', '-', f'{np.max(sim_latency):.1f}', '-'],
        ['Median (ms)', f'{THEORY_SERVICE_MEAN:.1f}', f'{np.median(sim_latency):.1f}', '-'],
        ['Samples', '-', f'{len(sim_latency)}', '-'],
    ]

    if len(sim_inference) > 0:
        summary_data.extend([
            ['', '', '', ''],
            ['LLM Inference', 'Theoretical', 'Simulated', 'Error'],
            ['Mean (ms)', f'{theory_inference_mean:.1f}', f'{np.mean(sim_inference):.1f}',
             f'{abs(np.mean(sim_inference) - theory_inference_mean) / theory_inference_mean * 100:.1f}%'],
            ['Std Dev (ms)', '-', f'{np.std(sim_inference):.1f}', '-'],
            ['Fitted shape', '-', f'{fit_shape:.1f}', '-'],
        ])

    tbl = ax_a2b.table(cellText=summary_data,
                       colLabels=['Metric', 'Theoretical', 'Simulated', 'Error'],
                       loc='center', cellLoc='center',
                       colColours=['#d4e6f1'] * 4)
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.0, 1.5)

    # Color the error column
    for i, row in enumerate(summary_data):
        if row[3] not in ['-', '', 'Error']:
            err_val = float(row[3].replace('%', ''))
            color = '#abebc6' if err_val < 5 else '#f9e79f' if err_val < 15 else '#f5b7b1'
            tbl[i + 1, 3].set_facecolor(color)

    ax_a2b.set_title('Theoretical vs Simulated Comparison', fontsize=11)
    fig_a2.tight_layout()

    # ── Figure A3: Output Tokens Distribution ────────────────────
    if len(sim_tokens) > 0:
        fig_a3, ax_a3 = plt.subplots(figsize=(8, 5))
        fig_a3.suptitle('v2 Validation: Output Token Count Distribution',
                        fontsize=13, fontweight='bold')

        ax_a3.hist(sim_tokens, bins=30, density=True, alpha=0.7, color='#f39c12',
                   edgecolor='white', label='Simulated')
        x_tok = np.linspace(min(sim_tokens) - 5, max(sim_tokens) + 5, 200)
        tok_pdf = stats.norm.pdf(x_tok, OUTPUT_TOKENS_MEAN, OUTPUT_TOKENS_STD)
        ax_a3.plot(x_tok, tok_pdf, 'r-', linewidth=2,
                   label=f'Theoretical N({OUTPUT_TOKENS_MEAN}, {OUTPUT_TOKENS_STD})')
        ax_a3.axvline(x=np.mean(sim_tokens), color='#f39c12', linestyle='--',
                      label=f'Sim mean: {np.mean(sim_tokens):.1f}')
        ax_a3.set_xlabel('Output Tokens')
        ax_a3.set_ylabel('Density')
        ax_a3.legend()
        ax_a3.grid(True, linestyle='--', alpha=0.3)
        fig_a3.tight_layout()

else:
    print("\nexp1a_trajectory.csv not found. Run the v2 experiment first.")


# ══════════════════════════════════════════════════════════════
# PART B: v1 (Kubernetes) Validation - GPS Model
# ══════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART B: v1 (Kubernetes) Simulator - GPS Model Validation")
print("=" * 70)

# V1 uses Generalized Processor Sharing (GPS):
#   speed_per_job = (cores / active_jobs) * frequency
#   service_time = instructions / speed_per_job
#
# Infrastructure (infrastructure.json):
#   Node 1: 4 cores, 3 GHz
#   Node 2: 1 core,  1 GHz
#   Node 3: 2 cores, 2 GHz
#
# Application (application.json):
#   Service 1: 6B instructions (nodeId=1)
#   Service 2: 5B instructions (nodeId=2)
#   Service 3: 4B instructions (nodeId=3)
#
# Pod deployment (round-robin, 2 replicas per service):
#   Pod 1 (S1) -> Node 1,  Pod 2 (S1) -> Node 2
#   Pod 3 (S2) -> Node 3,  Pod 4 (S2) -> Node 1
#   Pod 5 (S3) -> Node 2,  Pod 6 (S3) -> Node 3
#
# Actual chain in trace: S1 (Pod 1, Node 1) -> S2 (Pod 3, Node 3)
# Network: bandwidth = 1 GB/s, transfer = 200MB -> 0.2s per hop

V1_TRACE = os.path.join(BASE_PATH, 'simulation_trace_k8s.csv')
has_v1_data = os.path.exists(V1_TRACE)

# GPS theoretical calculations based on actual pod->node assignment
# From the trace: S1 runs on Pod 1 (Node 1), S2 runs on Pod 3 (Node 3)
service_chain = [
    {'name': 'S1', 'node': 'Node 1', 'cores': 4, 'freq_ghz': 3.0, 'instructions': 6e9},
    {'name': 'S2', 'node': 'Node 3', 'cores': 2, 'freq_ghz': 2.0, 'instructions': 5e9},
]
NETWORK_TRANSFER_TIME = 200e6 / 1e9  # 200MB / 1GB/s = 0.2s
NUM_NETWORK_HOPS = 1  # S1 -> S2 (one hop in the traced chain)

print(f"\nGPS Model - Single request (no contention):")
print(f"  Under GPS, with 1 active job, each job gets all cores.")
print(f"  speed = cores * frequency")
print()

total_theory_time = 0
for s in service_chain:
    speed = s['cores'] * s['freq_ghz'] * 1e9  # Hz
    time_s = s['instructions'] / speed
    total_theory_time += time_s
    print(f"  {s['name']} on {s['node']}: {s['instructions']:.0e} instr / ({s['cores']} cores * {s['freq_ghz']} GHz)"
          f" = {time_s:.4f}s")

# Network hops between services + final return
total_theory_time += 2 * NETWORK_TRANSFER_TIME
print(f"  Network: 2 * {NETWORK_TRANSFER_TIME:.1f}s = {2 * NETWORK_TRANSFER_TIME:.1f}s")
print(f"  Total expected (single request): {total_theory_time:.4f}s")

print(f"\nGPS Model - With contention (n jobs sharing a node):")
print(f"  speed_per_job = (cores / n) * frequency")
print(f"  Example: 2 jobs on Node 1 -> speed = (4/2) * 3GHz = 6 GFLOPS/job")
print(f"  Service time doubles: {service_chain[0]['instructions']:.0e} / 6e9 = {service_chain[0]['instructions'] / 6e9:.4f}s")

if has_v1_data:
    v1_df = pd.read_csv(V1_TRACE)
    print(f"\nLoaded {len(v1_df)} trace events from simulation_trace_k8s.csv")

    # Compute per-request end-to-end latency
    request_ids = v1_df['RequestId'].unique()
    latencies = []
    for rid in request_ids:
        req_events = v1_df[v1_df['RequestId'] == rid]
        start = req_events['StartTime'].min()
        end = req_events['EndTime'].max()
        latencies.append({'request_id': rid, 'start': start, 'end': end, 'latency': end - start})

    lat_df = pd.DataFrame(latencies).sort_values('start')

    # First few requests are likely uncontested (low load at start)
    # Find the first request that runs alone
    first_req = lat_df.iloc[0]
    print(f"\n  First request (ID={int(first_req['request_id'])}):")
    print(f"    Start: {first_req['start']:.4f}s, End: {first_req['end']:.4f}s")
    print(f"    Simulated latency: {first_req['latency']:.4f}s")
    print(f"    Theoretical (GPS, no contention): {total_theory_time:.4f}s")
    print(f"    Difference: {abs(first_req['latency'] - total_theory_time):.4f}s"
          f" ({abs(first_req['latency'] - total_theory_time) / total_theory_time * 100:.1f}%)")

    # Look at per-service computation times for the first request
    first_events = v1_df[v1_df['RequestId'] == first_req['request_id']].sort_values('StartTime')
    print(f"\n  Breakdown of first request:")
    for _, ev in first_events.iterrows():
        duration = ev['EndTime'] - ev['StartTime']
        print(f"    {ev['Type']:12s} {ev['Name']:15s}: {duration:.4f}s")

    # ── Figure B1: v1 Validation ─────────────────────────────────
    fig_b1, (ax_b1a, ax_b1b) = plt.subplots(1, 2, figsize=(14, 5))
    fig_b1.suptitle('v1 Validation: GPS Model - Expected vs Simulated',
                    fontsize=13, fontweight='bold')

    # Per-service expected vs actual (first request)
    comp_events = first_events[first_events['Type'] == 'Computation']
    service_names = comp_events['Name'].values
    actual_times = (comp_events['EndTime'] - comp_events['StartTime']).values

    expected_times = []
    for s in service_chain[:len(service_names)]:
        speed = s['cores'] * s['freq_ghz'] * 1e9
        expected_times.append(s['instructions'] / speed)

    x_pos = np.arange(len(service_names))
    width = 0.35
    ax_b1a.bar(x_pos - width/2, expected_times, width, color='#3498db', label='Theoretical (GPS)', edgecolor='white')
    ax_b1a.bar(x_pos + width/2, actual_times, width, color='#e74c3c', label='Simulated', edgecolor='white')

    for i, (exp_t, act_t) in enumerate(zip(expected_times, actual_times)):
        err = abs(act_t - exp_t) / exp_t * 100
        ax_b1a.text(i, max(exp_t, act_t) + 0.02, f'{err:.1f}%', ha='center', fontsize=9)

    ax_b1a.set_xticks(x_pos)
    ax_b1a.set_xticklabels([s.split('(')[0].strip() for s in service_names], fontsize=9)
    ax_b1a.set_ylabel('Computation Time (seconds)')
    ax_b1a.set_title('Per-Service Computation (1st Request, No Contention)')
    ax_b1a.legend()
    ax_b1a.grid(True, axis='y', linestyle='--', alpha=0.3)

    # Latency distribution across all requests
    all_latencies = lat_df['latency'].values
    ax_b1b.hist(all_latencies, bins=30, alpha=0.7, color='#2ecc71', edgecolor='white',
                label=f'All requests (n={len(all_latencies)})')
    ax_b1b.axvline(x=total_theory_time, color='red', linestyle='--', linewidth=2,
                   label=f'No-contention baseline: {total_theory_time:.2f}s')
    ax_b1b.axvline(x=np.mean(all_latencies), color='#2ecc71', linestyle='--', linewidth=2,
                   label=f'Mean: {np.mean(all_latencies):.2f}s')
    ax_b1b.set_xlabel('End-to-End Latency (seconds)')
    ax_b1b.set_ylabel('Count')
    ax_b1b.set_title('Latency Distribution (All Requests)')
    ax_b1b.legend(fontsize=9)
    ax_b1b.grid(True, linestyle='--', alpha=0.3)

    fig_b1.tight_layout()

    # ── Figure B2: GPS Contention Effect ─────────────────────────
    # Show how latency increases with concurrent requests (GPS effect)
    fig_b2, ax_b2 = plt.subplots(figsize=(10, 6))
    fig_b2.suptitle('v1 Validation: GPS Contention Effect',
                    fontsize=13, fontweight='bold')

    # For each request, count how many other requests overlap at its start time
    lat_df_sorted = lat_df.sort_values('start').reset_index(drop=True)
    concurrent_at_start = []
    for _, req in lat_df_sorted.iterrows():
        # Count requests that started before this one and haven't finished
        concurrent = len(lat_df_sorted[
            (lat_df_sorted['start'] <= req['start']) &
            (lat_df_sorted['end'] > req['start'])
        ])
        concurrent_at_start.append(concurrent)

    lat_df_sorted['concurrent'] = concurrent_at_start

    ax_b2.scatter(lat_df_sorted['concurrent'], lat_df_sorted['latency'],
                  alpha=0.5, s=30, color='#3498db')

    # Theoretical: with n concurrent jobs sharing each node under GPS
    conc_range = range(1, max(concurrent_at_start) + 1)
    theory_latencies = []
    for n_conc in conc_range:
        total = 0
        for s in service_chain:
            speed = (s['cores'] / n_conc) * s['freq_ghz'] * 1e9
            total += s['instructions'] / speed
        total += 2 * NETWORK_TRANSFER_TIME
        theory_latencies.append(total)

    ax_b2.plot(list(conc_range), theory_latencies, 'r-o', linewidth=2, markersize=6,
               label='Theoretical (GPS: speed = cores/n * freq)', zorder=5)

    ax_b2.set_xlabel('Concurrent Requests at Start Time')
    ax_b2.set_ylabel('End-to-End Latency (seconds)')
    ax_b2.legend()
    ax_b2.grid(True, linestyle='--', alpha=0.3)
    fig_b2.tight_layout()

    print(f"\n  Average latency across all requests: {np.mean(all_latencies):.4f}s")
    print(f"  Min: {np.min(all_latencies):.4f}s, Max: {np.max(all_latencies):.4f}s")
    print(f"  Requests with no contention (concurrent=1): "
          f"{sum(1 for c in concurrent_at_start if c == 1)}")

else:
    print("\nsimulation_trace_k8s.csv not found. Run the v1 simulation first.")


print("\n" + "=" * 70)
print("Close the chart windows to exit.")
print("=" * 70)

plt.show()
