#!/bin/bash
# Resilient Swarm Setup (2x 98GB - 196GB VRAM Total)
# Uses nohup and logs to keep servers alive in the background.

echo "[RESILIENT-SWARM] Starting..."

# Function to start the primary cluster
start_cluster() {
    echo "[RUNPOD] Launching Massive Dual-GPU Cluster (0,1) on Port 11434 [196GB VRAM]..."
    # Pooling GPUs to support massive 70B+ model context
    CUDA_VISIBLE_DEVICES=0,1 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_HOST=0.0.0.0:11434 nohup ollama serve > ollama_cluster.log 2>&1 &
}

# Kill any existing ollama processes to start fresh
killall ollama 2>/dev/null
sleep 5

# Launch Consolidated Cluster
start_cluster

echo "[RUNPOD] Waiting for initialization..."
sleep 20

# Initialize Models (Strict 70B Mandate)
echo "[RUNPOD] Checking for existing 70B models..."

ensure_model() {
    local host=$1
    local model=$2
    if OLLAMA_HOST=$host ollama list | grep -q "$model"; then
        echo "[RUNPOD] $model already exists on $host. Skipping pull."
    else
        echo "[RUNPOD] Pulling $model to $host..."
        OLLAMA_HOST=$host ollama pull "$model"
    fi
}

# The 72B model is now pulled locally to utilize pooled VRAM
ensure_model "0.0.0.0:11434" "mightykatun/qwen2.5-math:72b"
ensure_model "0.0.0.0:11434" "deepseek-r1:70b"

echo "[RUNPOD] Checking health..."
curl -s http://localhost:11434/api/tags > /dev/null && echo "GPU CLUSTER (Pro 6000s): ONLINE" || echo "CLUSTER FAILED (Check ollama_cluster.log)"

echo "[RUNPOD] Cluster operational. Logs available in ollama_0.log and ollama_1.log"
