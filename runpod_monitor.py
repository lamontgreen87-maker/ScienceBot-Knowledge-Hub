import tkinter as tk
from tkinter import ttk
import requests
import json
import subprocess
import threading
import time
import os
import datetime
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation

# --- CONFIGURATION ---
LOCAL_OLLAMA_URL = "http://localhost:11434/api/ps"
REMOTE_OLLAMA_URL = "http://194.68.245.85:22137/api/ps"
SSH_HOST = "e30c2go2kzra44-64411215@ssh.runpod.io"
SSH_KEY = r"C:\Users\Lamont\.ssh\id_ed25519"
SSH_BASE_CMD = [
    "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
    "-o", "BatchMode=yes", "-i", SSH_KEY, SSH_HOST,
    "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits"
]

MAX_POINTS = 60 

# --- GLOBAL STATE ---
data_lock = threading.Lock()
time_data = []
gpu_util_data = {}   
vram_used_data = {}  
vram_total_data = {} 

local_models = []
remote_models = []
ssh_status = "Initializing..."

class MonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RunPod Nexus - Hybrid Performance Monitor")
        self.geometry("1100x950")
        self.configure(bg="#121212")
        
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#121212")
        self.style.configure("TLabel", background="#121212", foreground="#e0e0e0", font=("Segoe UI", 11))
        self.style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#00e676")
        self.style.configure("Status.TLabel", font=("Segoe UI", 9), foreground="#888888")
        
        # --- TOP FRAME: Text Metrics (Local & Remote) ---
        self.top_frame = ttk.Frame(self)
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=15, pady=10)
        
        # Local Header
        self.local_header = ttk.Frame(self.top_frame)
        self.local_header.pack(fill=tk.X)
        ttk.Label(self.local_header, text="Local Swarm Node (8B)", style="Header.TLabel").pack(side=tk.LEFT)
        self.ssh_status_label = ttk.Label(self.local_header, text="SSH: Sleeping", style="Status.TLabel")
        self.ssh_status_label.pack(side=tk.RIGHT)
        
        self.local_details = tk.Text(self.top_frame, height=3, bg="#1a1a1a", fg="#00e676", font=("Consolas", 10), state=tk.DISABLED, padx=10, pady=5)
        self.local_details.pack(fill=tk.X, pady=(5, 10))
        
        # Remote Header
        self.remote_header = ttk.Frame(self.top_frame)
        self.remote_header.pack(fill=tk.X)
        ttk.Label(self.remote_header, text="Remote Pod Cluster (70B+)", style="Header.TLabel", foreground="#2979ff").pack(side=tk.LEFT)
        
        self.remote_details = tk.Text(self.top_frame, height=5, bg="#0a0a0a", fg="#2979ff", font=("Consolas", 10), state=tk.DISABLED, padx=10, pady=5)
        self.remote_details.pack(fill=tk.X, pady=5)
        
        # --- MIDDLE FRAME: Graphs ---
        self.graph_frame = ttk.Frame(self)
        self.graph_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        self.fig = Figure(figsize=(10, 7), facecolor='#121212')
        self.ax1 = self.fig.add_subplot(211) 
        self.ax2 = self.fig.add_subplot(212) 
        
        for ax in [self.ax1, self.ax2]:
            ax.set_facecolor('#1e1e1e')
            ax.tick_params(colors='#e0e0e0')
            ax.spines['bottom'].set_color('#333333')
            ax.grid(True, color='#333333', linestyle='--', alpha=0.3)
        
        self.ax1.set_title('Remote Cluster GPU Utilization (%)', color='#00e676', fontweight='bold')
        self.ax2.set_title('Remote Cluster VRAM Usage (GiB)', color='#2979ff', fontweight='bold')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.fig.tight_layout()
        
        self.running = True
        self.fetch_thread = threading.Thread(target=self.fetch_data_loop, daemon=True)
        self.fetch_thread.start()
        self.ani = animation.FuncAnimation(self.fig, self.update_graphs, interval=2000, save_count=100)
        
    def fetch_data_loop(self):
        while self.running:
            # 1. Fetch Local Ollama
            try:
                l_res = requests.get(LOCAL_OLLAMA_URL, timeout=2)
                if l_res.status_code == 200:
                    with data_lock:
                        global local_models
                        local_models = l_res.json().get('models', [])
            except: 
                with data_lock: local_models = [{"name": "Offline", "error": "Local API not found"}]

            # 2. Fetch Remote Ollama
            try:
                r_res = requests.get(REMOTE_OLLAMA_URL, timeout=2)
                if r_res.status_code == 200:
                    with data_lock:
                        global remote_models
                        remote_models = r_res.json().get('models', [])
            except:
                with data_lock: remote_models = [{"name": "Offline", "error": "Remote API not found"}]
                
            # 3. Fetch Raw Hardware Utilization via SSH
            try:
                global ssh_status
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                result = subprocess.run(SSH_BASE_CMD, capture_output=True, text=True, timeout=12, creationflags=creationflags)
                
                if result.returncode == 0:
                    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
                    now = datetime.datetime.now()
                    with data_lock:
                        ssh_status = f"SSH: Connected ({len(lines)} GPUs)"
                        time_data.append(now)
                        if len(time_data) > MAX_POINTS: time_data.pop(0)
                        
                        for i, line in enumerate(lines):
                            parts = [p.strip() for p in line.split(',')]
                            if len(parts) >= 3:
                                util, used_mib, total_mib = float(parts[0]), float(parts[1]), float(parts[2])
                                if i not in gpu_util_data:
                                    gpu_util_data[i], vram_used_data[i], vram_total_data[i] = [], [], []
                                gpu_util_data[i].append(util)
                                vram_used_data[i].append(used_mib / 1024.0)
                                vram_total_data[i].append(total_mib / 1024.0)
                                if len(gpu_util_data[i]) > MAX_POINTS:
                                    for d in [gpu_util_data[i], vram_used_data[i], vram_total_data[i]]: d.pop(0)
                else:
                    with data_lock: ssh_status = f"SSH Error: {result.stderr.strip()[:60]}"
            except Exception as e:
                with data_lock: ssh_status = f"SSH Failure: {str(e)[:60]}"
            time.sleep(2.5)
            
    def update_graphs(self, frame):
        with data_lock:
            self.ssh_status_label.config(text=ssh_status)
            
            # --- Update Text Widgets ---
            for widget, models, tag in [(self.local_details, local_models, "LOCAL"), (self.remote_details, remote_models, "REMOTE")]:
                widget.config(state=tk.NORMAL)
                widget.delete("1.0", tk.END)
                if not models:
                    widget.insert(tk.END, f"No active models on {tag}.\n")
                elif "Offline" in models[0].get("name", ""):
                    widget.insert(tk.END, f"[!] {tag} API Offline\n")
                else:
                    for m in models:
                        v_gb = m.get('size_vram', 0) / (1024**3)
                        ctx = m.get('context_length', 0)
                        widget.insert(tk.END, f"🚀 {m.get('name','?'):<35} | VRAM: {v_gb:>5.2f} GB | CTX: {ctx}\n")
                widget.config(state=tk.DISABLED)
            
            # --- Update Matplotlib ---
            if not time_data or not gpu_util_data: return
            self.ax1.clear()
            self.ax2.clear()
            for ax in [self.ax1, self.ax2]:
                ax.set_facecolor('#1e1e1e')
                ax.tick_params(colors='#e0e0e0', labelsize=8)
                ax.grid(True, color='#333333', linestyle='--', alpha=0.3)
            
            colors = ['#00e676', '#ff1744', '#2979ff', '#ffeb3b', '#d500f9', '#00e5ff', '#ff9100', '#c6ff00']
            total_u, total_m = 0, 0
            
            for idx, utils in gpu_util_data.items():
                c = colors[idx % len(colors)]
                c_utils = utils[-len(time_data):]
                c_vram = vram_used_data[idx][-len(time_data):]
                if len(c_utils) == len(time_data):
                    self.ax1.plot(time_data, c_utils, label=f"GPU {idx}", color=c, linewidth=1)
                if len(c_vram) == len(time_data):
                    self.ax2.plot(time_data, c_vram, label=f"GPU {idx}", color=c, linewidth=1, alpha=0.7)
                    total_u += c_vram[-1]
                    total_m += vram_total_data[idx][-1]

            self.ax1.set_title('Remote GPU Utilization (%)', color='#00e676', fontsize=11)
            self.ax2.set_title(f'Remote VRAM Usage: {total_u:.1f} / {total_m:.1f} GiB', color='#2979ff', fontsize=11)
            self.ax1.set_ylim(-5, 105)
            self.ax1.legend(loc='upper right', facecolor='#121212', labelcolor='white', framealpha=0.5, fontsize=7)
            self.fig.autofmt_xdate()
            self.canvas.draw()

    def destroy(self):
        self.running = False
        super().destroy()

if __name__ == "__main__":
    MonitorApp().mainloop()
