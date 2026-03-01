#!/bin/bash

# RunPod Dual-GPU Setup Script (2x RTX 6000 Ada / 96GB per GPU)
# Launches two isolated Ollama instances to enable parallel Research and Reflection.

echo "[RUNPOD] Starting Dual-GPU Cluster Setup..."

# 1. Start Primary Ollama (Theorist) on GPU 0 - Port 11434
echo "[RUNPOD] Launching Primary Backend (GPU 0) on Port 11434..."
CUDA_VISIBLE_DEVICES=0 OLLAMA_HOST=0.0.0.0:11434 ollama serve &
PRIMARY_PID=$!

# 2. Wait for primary to initialize
sleep 5

# 3. Start Secondary Ollama (Executioner/Strategist) on GPU 1 - Port 11435
echo "[RUNPOD] Launching Secondary Backend (GPU 1) on Port 11435..."
CUDA_VISIBLE_DEVICES=1 OLLAMA_HOST=0.0.0.0:11435 ollama serve &
SECONDARY_PID=$!

# 4. Pull required models on respective ports
echo "[RUNPOD] Initializing Models..."
# GPU 0: Qwen 72B + 8B Validator
OLLAMA_HOST=0.0.0.0:11434 ollama pull mightykatun/qwen2.5-math:72b
OLLAMA_HOST=0.0.0.0:11434 ollama pull llama3.1:8b

# GPU 1: Llama 70B + DeepSeek 70B
OLLAMA_HOST=0.0.0.0:11435 ollama pull llama3.1:70b
OLLAMA_HOST=0.0.0.0:11435 ollama pull deepseek-r1:70b

echo "[RUNPOD] Cluster Online."
echo "Primary (Active): http://localhost:11434"
echo "Secondary (Reflection): http://localhost:11435"

# Keep script alive
wait $PRIMARY_PID $SECONDARY_PID
