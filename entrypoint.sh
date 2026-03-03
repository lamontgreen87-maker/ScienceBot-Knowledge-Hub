#!/bin/bash

# Start Ollama with Triple-GPU pooling (288GB VRAM Cluster)
echo "[OLLAMA] Launching Pooled 3-GPU Cluster (0,1,2) with Spreading enabled..."

# Auto-detect persistent volume (RunPod default)
if [ -d "/workspace" ]; then
  # Targeted Model Root Hunt
  echo "[OLLAMA] Scanning /workspace for existing models (Targeting DeepSeek)..."
  FOUND_ROOT=""
  
  # 1. Find all manifest directories
  ALL_MANIFESTS=$(find /workspace -name "manifests" -type d 2>/dev/null)
  
  for m_dir in $ALL_MANIFESTS; do
    # 2. Check if this manifest folder contains 'deepseek-r1'
    if find "$m_dir" -name "*deepseek-r1*" -print -quit 2>/dev/null | grep -q .; then
      FOUND_ROOT=$(dirname "$m_dir")
      echo "[OLLAMA] FOUND DeepSeek manifests at: $FOUND_ROOT"
      break
    fi
  done

  if [ -n "$FOUND_ROOT" ]; then
    export OLLAMA_MODELS="$FOUND_ROOT"
  else
    export OLLAMA_MODELS="/workspace/ollama_models"
    mkdir -p "$OLLAMA_MODELS"
    echo "[OLLAMA] Defaulting to $OLLAMA_MODELS"
  fi
  
  # Sanity Audit: Detect and prune corrupted manifests
  # EOF errors are usually due to empty/truncated manifest files
  echo "[OLLAMA] Running Recursive Model Integrity Audit..."
  # Clean up 0-byte or corrupted manifests (<100 bytes)
  find "$OLLAMA_MODELS/manifests" -type f \( -size 0 -o -size -100c \) -delete 2>/dev/null
  # Also remove any hidden ".partial" files if they exist
  find "$OLLAMA_MODELS" -name "*.partial" -delete 2>/dev/null
  echo "[OLLAMA] Integrity audit complete."
fi

CUDA_VISIBLE_DEVICES=0,1,2 OLLAMA_NUM_PARALLEL=4 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_FLASH_ATTENTION=1 OLLAMA_HOST=0.0.0.0:11434 ollama serve &

# Wait for Ollama to be ready
echo "[OLLAMA] Waiting for server to hydrate..."
while ! ollama list > /dev/null 2>&1; do
  sleep 2
done

# Pull models automatically (Background)
echo "[OLLAMA] Initializing asynchronous model pulls..."
models=("qwen3.5:27b" "qwq:32b" "qwen3.5" "deepseek-r1:8b" "deepseek-r1:70b")

for model in "${models[@]}"; do
  # Use fixed string grep to avoid issues with special characters and slashes
  if ollama list | grep -Fq "$model"; then
    echo "[OLLAMA] $model recognized. Ready."
  else
    echo "[OLLAMA] $model not recognized. Triggering background pull..."
    # Execute pull in background to prevent blocking the entrypoint
    ollama pull "$model" > /dev/null 2>&1 &
  fi
done

echo "[OLLAMA] All models initialized. System ready."

# Keep the background process alive
wait
