import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import glob
import os

# --- 1. FIND FILES ---
# Use the SAME path structure for both files
base_path = r'C:\Users\ileounakis\IdeaProjects\Simulator' # <--- Your Project Folder

trace_files = glob.glob(os.path.join(base_path, 'simulation_trace_*.csv')) 
queue_files = glob.glob(os.path.join(base_path, 'queue_trace.csv')) # <--- Now it looks in the right place

if not trace_files:
    print("No Trace CSV found!")
    exit()

latest_trace = max(trace_files, key=os.path.getctime)
print(f"Visualizing Trace: {latest_trace}")

df_trace = pd.read_csv(latest_trace)

# Try to load queue data
df_queue = None
if queue_files: # Check if the list is not empty
    # Get the queue file (since we overwrite it, just take the first one found)
    queue_file = queue_files[0] 
    df_queue = pd.read_csv(queue_file)
    print(f"Queue data loaded from: {queue_file}")
else:
    print("Warning: queue_trace.csv not found! Bottom chart will be empty.")

# --- 2. SETUP PLOTS (2 ROWS) ---
fig, ax = plt.subplots(nrows=2, ncols=1, figsize=(16, 12), sharex=True, gridspec_kw={'height_ratios': [2, 1]})

# --- PLOT 1: GANTT CHART ---
colors = {
    "S1": "#3498db",  # Blue
    "S2": "#e74c3c",  # Red
    "S3": "#2ecc71",  # Green
    "Net": "#95a5a6", # Gray
    "Wait": "#f1c40f" # Yellow (Waiting Time)
}

ax[0].set_title("Request Execution & Waiting Times")
ax[0].set_ylabel("Request ID")

for request_id, group in df_trace.groupby("RequestId"):
    for _, row in group.iterrows():
        duration = row["EndTime"] - row["StartTime"]
        name = row["Name"]
        
        # Color Logic
        if "Wait" in row["Type"]:  # Check Type column for "Wait"
            color = colors["Wait"]
            edge = None # No border for wait bars looks cleaner
            height = 0.4
        elif "Net" in name:
            color = colors["Net"]
            edge = "white"
            height = 0.6
        elif "S1" in name:
            color = colors["S1"]
            edge = "white"
            height = 0.6
        elif "S2" in name:
            color = colors["S2"]
            edge = "white"
            height = 0.6
        elif "S3" in name:
            color = colors["S3"]
            edge = "white"
            height = 0.6
        else:
            color = "black"
            edge = "white"
            height = 0.6
        
        ax[0].barh(y=request_id, width=duration, left=row["StartTime"], 
                   color=color, edgecolor=edge, height=height)

# --- PLOT 2: QUEUE SIZES ---
if df_queue is not None:
    ax[1].set_title("Queue Size per Pod Over Time")
    ax[1].set_ylabel("Requests in Queue")
    ax[1].set_xlabel("Time (seconds)")
    
    # Get unique pods
    pods = df_queue["PodName"].unique()
    
    for pod in pods:
        pod_data = df_queue[df_queue["PodName"] == pod].sort_values("Time")
        ax[1].step(pod_data["Time"], pod_data["Size"], where='post', label=pod, linewidth=2)
    
    ax[1].legend(loc="upper right")
    ax[1].grid(True, linestyle="--", alpha=0.5)

# --- FINAL FORMATTING ---
legend_patches = [
    mpatches.Patch(color=colors["S1"], label="Service 1"),
    mpatches.Patch(color=colors["S2"], label="Service 2"),
    mpatches.Patch(color=colors["S3"], label="Service 3"),
    mpatches.Patch(color=colors["Wait"], label="Waiting in Queue"),
    mpatches.Patch(color=colors["Net"], label="Network")
]
ax[0].legend(handles=legend_patches, loc="upper left")
ax[0].grid(True, linestyle="--", alpha=0.5)

plt.tight_layout()
plt.show()