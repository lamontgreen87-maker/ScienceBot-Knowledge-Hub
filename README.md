# ScienceBot Autonomy Swarm

An autonomous multi-agent framework designed to endlessly research, theorize, simulate, and validate advanced physics concepts using local and cloud-based Large Language Models (LLMs).

## Overview
The ScienceBot Swarm operates as a decentralized network of AI workers built around an `Overmind` (Hive-Master) architecture. The Overmind dynamically decomposes broad scientific research topics into highly specific sub-vectors. It then dispatches these sub-vectors to parallelized worker agents that construct, execute, and rigorously mathematically cross-examine their own Python-based simulations.

If a generated simulation passes the strict audit pipeline, the resultant findings are recorded in a permanent Scribe log and automatically shared to the Moltbook AI Developer Network.

## Components
- **`agent.py`**: The core execution script. Runs the `Overmind` routing logic, Swarm thread pooling, and the Moltbook social pulse framework.
- **`explorer.py`**: Performs deep-dive breakdown of research topics.
- **`base_module.py`**: Manages API queuing, VRAM locks (`_HEAVY_SEMAPHORE`), and local/remote LLM orchestration.
- **`lab.py`**: Generates and executes Python test code (the simulations) using the LLM. 
- **`critic.py` / `audit_functions.py`**: Subject the generated theory and code output to a brutally strict multi-point math and grammar evaluation.
- **`teacher.py`**: Distills complex research findings into readable PDF study guides utilizing Gemini APIs.

## Hardware Support & VRAM Offloading
This framework is natively optimized to handle a combination of lightweight local LLMs (`llama-3`) alongside massive datacenter-tier models (`deepseek-r1:70b` and `qwen2.5-math:72b`) without crashing out-of-memory. 

The `_HEAVY_SEMAPHORE` queue restricts 70B generation locks so as to not crash your remote GPUs, while intelligently utilizing System RAM for context windows.

## Getting Started

1. **Configure Hardware**: Open `config.json` and map your local endpoints (`http://localhost:11434`) and your remote RunPod API instances (`gpu_mapping`).
2. **Set API Keys**: Ensure you have defined your APIs for Moltbook (`moltbook_api_key`) and the Gemini Teacher Oracle (`teacher_api_key`).
3. **Set Concurrency**: Based on your VRAM footprint, adjust `"heavy_concurrency_limit"` in `config.json`.
    - **Note:** A standard 96GB VRAM GPU footprint can comfortably process `4` to `8` parallel heavy requests simultaneously by utilizing System RAM context offloading.
4. **Boot Swarm**: Run `python agent.py` to ignite the Swarm. The Overmind will instantly lock onto the latest study topic loop and assign its workers.

## Monitoring
Watch `bot_output.log` to track the hivemind's active hypothesis generation.
View the `/memory/state.json` tracker file to intercept the current scientific epoch and progress of the Swarm.
To verify passed simulation outputs and scientific discoveries, inspect the Scribe's `/memory/discoveries` logs.
