# ScienceBot: Autonomous Scientific Discovery Swarm

ScienceBot is an agentic AI ecosystem designed for high-fidelity, autonomous scientific research. It leverages a tiered model architecture (8B to 70B+) to hypothesize, simulate, and audit complex physical phenomena.

## Core Architecture
- **Explorer (Curiosity Engine)**: Strategizes research directions using long-context history (50+ past cycles).
- **Lab (Mathematical Laboratory)**: Generates high-fidelity Python simulations based on SymPy-ready blueprints.
- **Auditor (Rigor Engine)**: Enforces deterministic constraints (No `.subs()`, mandatory 5-part template, high vocabulary alignment).
- **Teacher (Foundation Layer)**: Compiles multi-model deep-dives into foundational bottlenecks, exporting them as localized PDFs.

## Hardware Scaling
The Swarm is optimized for multi-GPU environments (e.g., RTX 6000 ADA). 
- **`max_swarm_workers`**: Adjusts concurrency of construction waves.
- **`num_ctx`**: Scalable up to 128,000 tokens for deep historical reasoning.
- **`heavy_concurrency_limit`**: Protects VRAM from overflow by serializing heavy 70B model calls.

## Quick Start
1. Configure your Ollama endpoint in `config.json`.
2. Ensure `fpdf2` is installed for Teacher lessons.
3. Run `python agent.py`.

## Commands
- **STOP**: Pause the research loop.
- **CONTINUE**: Resume active exploration.
- **SHUTDOWN**: Emergency graceful stop.
- **[Any Message]**: Instantly triggers the Tutor for a scientific discussion.

---
*Built for the next generation of autonomous discovery.*
