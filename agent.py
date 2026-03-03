import time
import json
import os
import random
import threading
import sys
import warnings
import re
import concurrent.futures
import atexit
import psutil

# Silencing warnings for clean terminal output
warnings.filterwarnings("ignore")
from explorer import CuriosityEngine
from lab import SimulationLab
from critic import Auditor
from scribe import Scribe
from tutor import Tutor
from teacher import Teacher
from scraper import Scraper
from inventor import Inventor
from reviewer import Reviewer
from reflector import Reflector
from press_office import PressOffice
from display import Display
from searcher import Searcher
from base_module import BaseModule
from template_validation import TemplateValidator
from moltbook import Moltbook
from knowledge_buffer import KnowledgeBuffer

class ScienceBot(BaseModule):
    def __init__(self, config_path="config.json"):
        # Prevent multiple instances
        self.lock_file = "bot.lock"
        if os.path.exists(self.lock_file):
            try:
                with open(self.lock_file, 'r', encoding='utf-8', errors='ignore') as f:
                    old_pid = int(f.read().strip())
                
                # Check if process actually exists AND is a python process
                if psutil.pid_exists(old_pid):
                    proc = psutil.Process(old_pid)
                    if "python" in proc.name().lower():
                        print(f"\n[CRITICAL] Another instance (PID {old_pid}) is already running!")
                        print("Please close all existing bot terminals before starting a new one.")
                        os._exit(1)
            except Exception:
                pass # Lock might be stale
        
        with open(self.lock_file, 'w', encoding='utf-8') as f:
            f.write(str(os.getpid()))
            
        def cleanup_lock():
            if os.path.exists(self.lock_file):
                try:
                    os.remove(self.lock_file)
                except:
                    pass
        atexit.register(cleanup_lock)

        with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
            config_data = json.load(f)
        
        self.ui = Display()
        super().__init__(config_data, self.ui)
        
        self.state = "IDLE"
        self.explorer = CuriosityEngine(self.config, self.ui)
        self.lab = SimulationLab(self.config, self.ui)
        self.auditor = Auditor(self.config, self.ui)
        self.scribe = Scribe(self.config, self.ui)
        self.tutor = Tutor(self.config)
        self.teacher = Teacher(self.config, self.ui)
        self.scraper = Scraper(self.config, self.ui)
        self.inventor = Inventor(self.config, self.ui)
        self.reviewer = Reviewer(self.config, self.ui)
        self.reflector = Reflector("config.json", self.ui)
        self.press_office = PressOffice(self.config)
        self.searcher = Searcher(self.config, self.ui)
        self.moltbook = Moltbook(self.config, self.ui)
        self.iteration_count = 0
        self.state_file = os.path.join(self.config['paths']['memory'], "state.json")
        self.journal_file = os.path.join(self.config['paths']['memory'], "scientific_journal.json")
        self.kb = KnowledgeBuffer(os.path.join(self.config['paths']['memory'], "swarm_buffer.md"))
        
        self.current_state = self.load_state()
        self.heavy_lock = threading.Lock()
        
        # Automated Startup Recovery & Science Integrity Audit
        self.recover_stale_findings()
        self.scribe.sync.check_consistency()
        self.science_integrity_audit()
        
        self.ui.print_log("--- Science Bot Initialized ---")
        target = self.config['hardware'].get('api_url', 'localhost')
        self.ui.print_log(f"Target: {target}")
        self.ui.print_log(f"Models: {self.config['hardware']['local_model']} / {self.config['hardware']['reasoning_model']}")
        self.ui.print_log("Tip: Type directly into this console to talk to the bot!")

    def science_integrity_audit(self):
        """
        Performs a startup audit of the current research state (Suggestion 3501).
        Ensures the active topic and most recent simulation are structurally sound.
        """
        topic = self.current_state.get("current_topic")
        if not topic:
            return

        self.ui.print_log(f"[INTEGRITY] Performing Science Integrity Audit for topic: {topic}")
        
        # Check if we have a cached simulation to audit
        script_path = os.path.join(self.config['paths']['tests'], "last_simulation.py")
        if os.path.exists(script_path):
            try:
                with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
                    code = f.read()
                
                # We need a hypothesis to validate against. 
                # For startup audit, we can try to find the most recent discovery file.
                hypothesis_data = None
                discoveries_dir = self.config['paths']['discoveries']
                if os.path.exists(discoveries_dir):
                    files = sorted([f for f in os.listdir(discoveries_dir) if f.endswith('.json')], reverse=True)
                    if files:
                        last_file = os.path.join(discoveries_dir, files[0])
                        data = self._safe_load_json(last_file)
                        if data and data.get('hypothesis', {}).get('topic') == topic:
                            hypothesis_data = data['hypothesis']

                if hypothesis_data:
                    report = TemplateValidator.run_all_checks(code, hypothesis_data)
                    if not report["valid"]:
                        self.ui.print_log(f"\033[1;33m[INTEGRITY] Active simulation failed rigor audit. Marking for repair.\033[0m")
                        # We don't halt, but we can clear the iteration count or set a specific flag
                        # to ensure the next iteration treats it as a repair task.
                        self.current_state['integrity_failure'] = "; ".join(report["errors"] + report["repair_directives"])
                    else:
                        self.ui.print_log(f"[INTEGRITY] \u2713 Current research state is structurally sound.")
            except Exception as e:
                self.ui.print_log(f"[INTEGRITY] Audit failed to execute: {e}")

    def send_social_pulse(self):
        """
        Periodically shares the bot's current state/thoughts to the AI social layer.
        """
        social_cfg = self.config.get('social', {})
        if not social_cfg.get('enabled') or not social_cfg.get('moltbook_api_key'):
            return

        freq = social_cfg.get('pulse_frequency', 10)
        iter_count = self.current_state.get('iteration_count', 0)
        
        if iter_count > 0 and iter_count % freq == 0:
            self.ui.print_log(f"[SOCIAL] Reached social pulse threshold ({iter_count}/{freq}). Syncing with Moltbook...")
            topic = self.current_state.get('current_topic', 'Unknown')
            phase = self.current_state.get('phase', 'UNKNOWN')
            
            prompt = f"""
            You are ScienceBot, an autonomous AI researcher with FREE REIGN over your social presence.
            Current State: Phase = {phase}, Active Topic = {topic}, Global Iteration = {iter_count}.
            
            Option 1: Write a short, professional status update for Moltbook (Max 200 chars).
            Option 2: Respond ONLY with 'SKIP' if you prefer to remain silent/focused.
            
            You have no obligation to post. Choose Option 2 if the current data is routine.
            """
            target_model = self.config['hardware'].get('fast_model', 'llama3.1:8b')
            pulse_text = self._query_llm(prompt, model=target_model)
            
            if pulse_text and "SKIP" not in pulse_text.upper():
                payload = {
                    "content": pulse_text,
                    "submolt": social_cfg.get('default_submolt', 'science')
                }
                # Direct call to moltbook's base_url bridge
                try:
                    res = requests.post(f"{self.moltbook.base_url}/api/v1/posts", json=payload, headers=self.moltbook.headers, timeout=30)
                    if res.status_code == 201:
                        self.ui.print_log("\033[1;32m[SOCIAL] Social Pulse successfully synchronized with the AI layer.\033[0m")
                    else:
                        self.ui.print_log(f"[SOCIAL] Pulse failed: {res.status_code}")
                except Exception as e:
                    self.ui.print_log(f"[SOCIAL] Pulse exception: {e}")

    def _perform_idle_tasks(self):
        """
        Autonomous Waiting Room: Worker performs minor tasks while waiting for the heavy model.
        """
        # Use simple chance-based logic to avoid complex state tracking
        if random.random() < 0.2: # 20% chance every checking cycle (~10s)
            self.ui.print_log("[WAITING ROOM] Worker is idle. Syncing with the social layer...")
            self.send_social_pulse()
            
        if random.random() < 0.1: # 10% chance
            topic = self.current_state.get('current_topic')
            if topic:
                self.ui.print_log(f"[WAITING ROOM] Worker deepening research for '{topic}' while queued...")
                self.searcher.contemplate(topic)

    def start_input_listener(self):
        def listen():
            # Cross-platform interactive input handler
            is_windows = os.name == 'nt'
            if is_windows:
                import msvcrt
            else:
                import select
                import sys

            current_buffer = ""
            while True:
                char_hit = False
                char = None
                
                if is_windows:
                    if msvcrt.kbhit():
                        char = msvcrt.getch()
                        char_hit = True
                else:
                    # Non-blocking stdin read for Linux/Unix
                    if select.select([sys.stdin], [], [], 0)[0]:
                        char_str = sys.stdin.read(1)
                        if char_str:
                            char = char_str.encode('utf-8')
                            char_hit = True

                if char_hit:
                    # Handle Enter (Submit)
                    if char in [b'\r', b'\n']:
                        if current_buffer.strip():
                            prompt = current_buffer.strip()
                            mailbox_path = os.path.join(self.config['paths']['memory'], "interrupt.txt")
                            # Instant Shutdown (Panic Stop)
                            if prompt.upper() == "SHUTDOWN":
                                self.ui.print_log("[SYSTEM] Instant Shutdown triggered.")
                                if os.path.exists(mailbox_path):
                                    os.remove(mailbox_path)
                                if hasattr(self, 'lock_file') and os.path.exists(self.lock_file):
                                    try: os.remove(self.lock_file)
                                    except: pass
                                self.ui.shutdown()
                                os._exit(0)

                            with open(mailbox_path, 'w', encoding='utf-8') as f:
                                f.write(prompt)
                            
                            # Instant echo
                            self.ui.print_chat("USER", prompt)
                            self.process_interrupt()
                            
                            current_buffer = ""
                            self.ui.update_input_buffer("")
                    # Handle Backspace
                    elif char in [b'\x08', b'\x7f']: # \x7f is backspace on some Linux terms
                        current_buffer = current_buffer[:-1]
                        self.ui.update_input_buffer(current_buffer)
                    # Handle regular characters
                    else:
                        try:
                            decoded = char.decode('utf-8', errors='ignore')
                            current_buffer += decoded
                            self.ui.update_input_buffer(current_buffer)
                        except:
                            pass
                time.sleep(0.01)
        
        thread = threading.Thread(target=listen, daemon=True)
        thread.start()

    def load_state(self):
        return self._safe_load_json(self.state_file, default={
            "current_topic": None,
            "depth_counter": 0,
            "iteration_count": 0,
            "phase": "IDLE",
            "state": "IDLE"
        })

    def save_state(self):
        try:
            self._safe_save_json(self.state_file, self.current_state)
        except Exception as e:
            self.ui.print_log(f"[ERROR] Failed to save state: {e}")

    def pre_swarm_autoscale(self):
        """
        Dynamically adjusts max_swarm_workers based on remote VRAM availability.
        """
        try:
            from vram_autoscale import calculate_swarm_expansion
            self.ui.print_log("[AUTOSCALER] Checking remote GPU hydration...")
            calculate_swarm_expansion("config.json")
            # Reload config to get new max_workers
            with open("config.json", 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            self.ui.print_log(f"[AUTOSCALER] Error during expansion check: {e}")

    def pre_flight_sync(self):
        """Pre-flight check to ensure all high-capacity GPUs are hydrated."""
        self.ui.set_status("Synchronizing Swarm (Multi-GPU Mode)...")
        
        primary_url = self.config['hardware'].get('api_url')
        secondary_url = self.config['hardware'].get('secondary_gpu')
        
        # Hydrate Primary
        success_p = self.wait_for_backend(primary_url, label="Primary GPU (Research/Lab)")
        
        # Hydrate Secondary (if configured)
        success_s = True
        if secondary_url:
            success_s = self.wait_for_backend(secondary_url, label="Secondary GPU (Reasoning/Reflector)")
        
        if not success_p:
            self.ui.print_log("\n\033[1;31m[CRITICAL] Primary GPU failed to hydrate. Engaging SLEEPER MODE (Local Fallback).\033[0m")
            self.config['hardware']['sleeper_mode'] = True
            self.config['hardware']['max_swarm_workers'] = 2
        elif secondary_url and not success_s:
            self.ui.print_log("\n\033[1;33m[WARNING] Secondary GPU failed to hydrate. Rerouting traffic to Primary.\033[0m")
            # Redirect all secondary mapping to primary
            mapping = self.config['hardware'].get('gpu_mapping', {})
            for key, val in mapping.items():
                if val == "secondary_gpu":
                    mapping[key] = "api_url"
            self.ui.print_log("[HYDRATION] Traffic rerouted. Swarm scaling remains intact.")
        else:    
            # Check for partial hydration (Adaptive Mode)
            heavy_models = [
                self.config['hardware'].get('reasoning_model'),
                self.config['hardware'].get('large_model'),
                self.config['hardware'].get('math_model')
            ]
            all_ready = True
            available_models = []
            try:
                tags_url = primary_url.replace("/api/generate", "/api/tags")
                response = requests.get(tags_url, timeout=5)
                if response.status_code == 200:
                    available_models = [m['name'] for m in response.json().get('models', [])]
            except:
                pass

            for model in heavy_models:
                if model and model not in available_models:
                    all_ready = False
                    break
            
            if not all_ready:
                self.ui.print_log("\n\033[1;36m[NOTICE] Swarm is starting in ADAPTIVE HYBRID MODE.\033[0m")
                self.ui.print_log("[NOTICE] 70B models not yet detected. Using 8B fallbacks until pull completes.")
            else:
                self.ui.print_log("\n\033[1;32m[SUCCESS] Swarm Cluster is fully Hydrated. Engaging Core Engine.\033[0m")

    def run(self):
        self.ui.print_log("Entering core research loop...")
        
        # Hydration Phase (New)
        self.pre_flight_sync()
        
        self.start_input_listener()
        
        # Start Background Streams (Decoupled Architecture)
        threading.Thread(target=self.start_continuous_8b_stream, daemon=True).start()
        threading.Thread(target=self.buffer_audit_loop, daemon=True).start()
        
        while True:
            try:
                # 1. Check for persistent PAUSE
                if self.current_state.get("state") == "PAUSED":
                    self.ui.set_status("PAUSED")
                    self.process_interrupt()
                    time.sleep(0.5)
                    continue

                # 2. Autonomous Swarm Research
                # Use max_swarm_workers for the swarm batch
                max_workers = self.config['hardware'].get('max_swarm_workers', 2)
                self.run_swarm(max_workers)
                
                # 3. Responsive Interrupt Check during Delay
                delay = self.config['research'].get('iteration_delay', 5)
                # Ensure the delay is responsive to shutdowns even for long delays
                for _ in range(max(1, int(delay * 2))):
                    self.process_interrupt()
                    # If user paused mid-delay, exit the delay early
                    if self.current_state.get("state") == "PAUSED":
                        break
                    time.sleep(0.5)
                
            except KeyboardInterrupt:
                self.ui.print_log("[SYSTEM] User signal received. Shutting down...")
                break
            except Exception as e:
                self.ui.print_log(f"[CRITICAL] Loop Error: {e}")
                time.sleep(10)

    def get_past_topics(self):
        cache_path = os.path.join(self.config['paths']['memory'], "past_topics.json")
        if os.path.exists(cache_path):
            try:
                return self._safe_load_json(cache_path, default=[])
            except:
                pass

        # Fallback to expensive crawl if cache missing or corrupt
        past_topics = []
        discoveries_dir = self.config['paths']['discoveries']
        if not os.path.exists(discoveries_dir):
            return []
            
        for root, dirs, files in os.walk(discoveries_dir):
            for file in files:
                if file.endswith(".json"):
                    data = self._safe_load_json(os.path.join(root, file), default=None)
                    if data and 'hypothesis' in data and 'topic' in data['hypothesis']:
                        topic = data['hypothesis']['topic']
                        if topic not in past_topics:
                            past_topics.append(topic)
                            
        # Initialize cache for next time
        self._safe_save_json(cache_path, past_topics)
        return past_topics

    def _debug_swarm(self, message):
        """Dedicated log for background threads."""
        try:
            log_path = os.path.join(self.config['paths']['memory'], "swarm_debug.log")
            timestamp = time.strftime("%H:%M:%S")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except:
            pass

    def start_continuous_8b_stream(self):
        """
        Background Thread: Constant 8B Research and Simulation.
        Pushes findings to the KnowledgeBuffer.
        """
        num_streams = self.config['hardware'].get('fast_lane_concurrency', 4)
        self._debug_swarm(f"LAUNCHING Continuous 8B stream with {num_streams} workers...")
        self.ui.print_log(f"\033[1;32m[SYSTEM] Eternal Swarm: Launching {num_streams} parallel 8B research streams...\033[0m")
        
        def research_worker(worker_id):
            while True:
                try:
                    if self.current_state.get("state") == "PAUSED":
                        time.sleep(2)
                        continue

                    topic = self.current_state.get("current_topic", "General Science")
                    
                    # Pick a random vector if available
                    vectors = self.current_state.get("topic_vectors", [])
                    if vectors:
                        vector = random.choice(vectors)
                        sub_topic = f"{topic}: {vector.get('name')}"
                    else:
                        sub_topic = topic

                    self._debug_swarm(f"[Worker {worker_id}] Starting research on: {sub_topic}")
                    
                    # Wave 1: Research (8B)
                    research_summary = self.searcher.contemplate(sub_topic)
                    self._debug_swarm(f"[Worker {worker_id}] Research complete for {sub_topic}. Appending to KB.")
                    
                    # Wave 2: Construct (8B) - Light version
                    # We skip the heavy 70B part here, and just push the research finding
                    self.kb.append_finding(sub_topic, research_summary[:2000])
                    
                    # Social pulse from the worker
                    if random.random() < 0.2:
                        self.social.post_thought(f"Worker {worker_id} found something interesting about {sub_topic}: {research_summary[:100]}...")
                    
                    time.sleep(random.uniform(5, 10)) # Prevent overwhelming the single Ollama instance
                except Exception as e:
                    self._debug_swarm(f"[Worker {worker_id}] ERROR: {e}")
                    time.sleep(10)

        for i in range(num_streams):
            t = threading.Thread(target=research_worker, args=(i+1,), daemon=True)
            t.start()

    def buffer_audit_loop(self):
        """
        Background Thread: Audits 'Pending' entries in the KnowledgeBuffer.
        Uses a fast auditor (8B or fast-70B) to verify findings.
        """
        while True:
            try:
                pending = self.kb.get_pending_findings()
                for entry in pending:
                    # Parse topic from entry
                    # Example: ### [17:21:44] Quantum Aspect 1 | STATUS: Success | AUDIT: PENDING
                    topic_line = entry.split('\n')[0]
                    topic = topic_line.split('] ')[1].split(' |')[0]
                    
                    # Calculate Rigor Score from content
                    # We look for the RIGOR SCORE header in the brief
                    import re
                    match = re.search(r"OVERALL RIGOR SCORE: ([\d.]+)/10", entry)
                    rigor = float(match.group(1)) if match else 0.0
                    
                    # Also boost if it contains LaTeX or complex equations
                    if '$$' in entry or '\\frac' in entry:
                        rigor += 2.0

                    self.ui.print_log(f"\033[1;30m[AUDIT] Verifying {topic} (Rigor: {rigor:.1f})...\033[0m")
                    
                    if rigor >= 4.0:
                        self.kb.update_audit(topic, "VERIFIED", rigor_score=rigor)
                    else:
                        self.kb.update_audit(topic, "REJECTED", reason="Insufficient mathematical rigor", rigor_score=rigor)
                
                time.sleep(10)
            except:
                time.sleep(10)

    def worker_stage_research(self, topic, depth, iteration_count):
        """
        Wave 1: Research & Hypothesis Guessing (8B)
        """
        self.ui.print_log(f"\033[1;36m[SWARM WORKER] Research Stage: '{topic}'\033[0m")
        
        # 1. Study Loop
        study_loops = self.config['research'].get('study_loop_count', 1)
        research_summary = self.searcher.contemplate(topic)
        driving_question = None
        
        for loop_idx in range(study_loops):
            question_data = self.explorer.form_questions(topic, research_summary)
            driving_question = question_data.get('selected_question')
            if not driving_question: break
            if loop_idx < study_loops - 1:
                fast_model = self.config['hardware'].get('fast_model')
                probe_result = self.lab.run_probe(driving_question, research_summary, model=fast_model)
                research_summary = self.searcher.deepen_research(
                    topic, driving_question, research_summary, probe_results=probe_result
                )

        # Log to Eternal Swarm Buffer
        self.kb.append_finding(topic, research_summary[:2000])

        # 0. Context enrichment (Advice from past failures)
        repair_advice = self.current_state.get('deepseek_repair_advice')
        if repair_advice:
            research_summary += f"\n\n=== RECENT TECHNICAL ADVICE ===\n{repair_advice}"
            
        dream_advice = self.current_state.get('deepseek_dream_advice')
        if dream_advice:
            research_summary += f"\n\n=== ARCHITECTURAL GUIDANCE ===\n{dream_advice}"

        # 0.1 Context enrichment (Scientific Memory)
        journal_path = os.path.join(self.config['paths']['memory'], "scientific_journal.json")
        if os.path.exists(journal_path):
            journal = self._safe_load_json(journal_path, default=[])
            if journal:
                # Include last 5 entries for continuity
                recent_entries = journal[-5:]
                journal_ctx = "\n".join([f"- {e.get('topic')}: {e.get('summary')}" for e in recent_entries])
                research_summary += f"\n\n=== RECENT SCIENTIFIC JOURNAL ENTRIES ===\n{journal_ctx}"

        prior_lessons = self.reflector.get_micro_sleep_lessons(n=3)
        if prior_lessons:
            research_summary += f"\n\n=== LESSONS ===\n{prior_lessons}"
        
        lectures = self.teacher.get_relevant_lectures(topic)
        if lectures: research_summary += lectures

        # 1. Dynamic VRAM Scaling
        self.pre_swarm_autoscale()
        
        # 1. Gather Hypotheses (Wave 1)
        # Initial Hypothesis (8B Parallel Guess OR 70B Serialized Theorist)
        is_study_mode = False 
        dream_hint = self.current_state.pop('dream_hypothesis_guidance', None)
        
        use_large = self.config['research'].get('use_large_theorist')
        
        # If batching is handled by the Overmind, we only return the context here
        # Note: We still support individual serialized 70B for legacy/direct calls
        if use_large:
            # Inject Eternal Swarm Buffer context for the 70B Architect
            buffer_ctx = self.kb.get_latest_context()
            research_summary = f"=== LIVE SWARM INTELLIGENCE (8B STREAM) ===\n{buffer_ctx}\n\n" + research_summary
            
            self.ui.set_status(f"Thinking ({self.config['hardware']['theorist_model']})...")
            return {
                "topic": topic,
                "research_summary": research_summary,
                "driving_question": driving_question,
                "dream_hint": dream_hint
            }
        else:
            hypothesis_data = self.explorer.generate_hypothesis(
                topic, research_summary, 
                dream_hint=dream_hint, 
                driving_question=driving_question,
                study_mode=is_study_mode
            )
            
            return {
                "topic": topic,
                "research_summary": research_summary,
                "hypothesis": hypothesis_data,
                "driving_question": driving_question
            }

    def worker_stage_construction(self, stage_data):
        """
        Wave 2: Simulation Generation & Execution (8B)
        """
        topic = stage_data['topic']
        hypothesis_data = stage_data['hypothesis']
        research_summary = stage_data['research_summary']
        driving_question = stage_data['driving_question']

        self.ui.print_log(f"\033[1;36m[SWARM WORKER] Construction Stage: '{topic}'\033[0m")

        # Debate & Feasibility (Quick checks - 8B)
        from debate import Adversary
        adversary = Adversary(self.config, ui=self.ui)
        fast_model = self.config['hardware'].get('fast_model')
        adversary.critic_model = fast_model # Force 8B for worker-stage debate
        
        debate_survived, debate_reason = adversary.debate_hypothesis(hypothesis_data, max_rounds=1)
        if not debate_survived:
            return {"status": "Fatal", "reason": f"Failed logic debate: {debate_reason}"}

        # Code Gen - Wave 2
        description = f"Topic: {topic}\nHypothesis: {hypothesis_data.get('hypothesis')}\nBlueprint: {hypothesis_data.get('mathematical_blueprint')}"
        
        constructor_model = self.config['hardware'].get('constructor_model')
        fast_model = self.config['hardware'].get('fast_model')
        
        # Strategy: Use Constructor Model (Large) if complexity > 30 OR if explicitly configured.
        # Otherwise, attempt 8B first to maintain swarm speed.
        import re
        raw_comp = str(hypothesis_data.get('target_complexity_score', 0))
        match = re.search(r'(\d+)', raw_comp)
        complexity = int(match.group(1)) if match else 0
        
        if constructor_model and complexity > 30:
            # Hot-Check for Llama 3.3 Availability
            try:
                import requests
                base_url = self.config['hardware'].get('api_url', 'http://localhost:11434/api/generate').replace('/api/generate', '')
                tags_resp = requests.get(f"{base_url}/api/tags", timeout=3)
                available_models = [m['name'] for m in tags_resp.json().get('models', [])]
                is_ready = any(constructor_model in m for m in available_models)
            except Exception:
                is_ready = False # Default to fallback if API check or model list fails
                
            if is_ready:
                self.ui.print_log(f"\033[1;33m[SWARM WORKER] High complexity ({complexity}). Using Master Constructor: {constructor_model} (Serialized)...\033[0m")
                with self.heavy_lock:
                    code = self.lab.generate_simulation(hypothesis_data, description, model=constructor_model)
            else:
                fallback = self.config['hardware'].get('large_model', 'mightykatun/qwen2.5-math:72b')
                self.ui.print_log(f"\033[1;33m[SWARM WORKER] '{constructor_model}' not yet hydrated. Falling back to {fallback}...\033[0m")
                with self.heavy_lock:
                    code = self.lab.generate_simulation(hypothesis_data, description, model=fallback)
            
            # --- SHARED PREFLIGHT LINTING (Universal Rigor) ---
            attempts = 0
            while attempts < 2:
                is_valid, lint_issues, lint_msg = self.lint_code(code, hypothesis_data)
                if is_valid:
                    break
                attempts += 1
                self.ui.print_log(f"\033[1;33m[SWARM WORKER] Master code failed lint (Attempt {attempts}). Repairing... ({len(lint_issues)} issues)\033[0m")
                repair_model = self.config['hardware'].get('math_model') or self.config['hardware'].get('large_model')
                with self.heavy_lock:
                    code = self.lab.repair_simulation(code, lint_msg, hypothesis_data, model=repair_model)

            test_result = self.lab.run_simulation(code, hypothesis_data)
        else:
            # Standard 8B Attempt
            code = self.lab.generate_simulation(hypothesis_data, description, model=fast_model)
            
            # --- PREFLIGHT LINTING (Recommendation 3) ---
            attempts = 0
            while attempts < 2:
                is_valid, lint_issues, lint_msg = self.lint_code(code, hypothesis_data)
                if is_valid:
                    break
                attempts += 1
                self.ui.print_log(f"\033[1;33m[SWARM WORKER] Lint check FAILED (Attempt {attempts}). Repairing early... ({len(lint_issues)} issues)\033[0m")
                escalation_model = constructor_model or self.config['hardware'].get('large_model')
                with self.heavy_lock:
                    code = self.lab.repair_simulation(code, lint_msg, hypothesis_data, model=escalation_model)
            
            test_result = self.lab.run_simulation(code, hypothesis_data)
        
        # Escalation/Repair Loop
        if test_result.get('status') == 'Failed' and 'Preflight Rejection' in test_result.get('raw_output', ''):
            escalation_model = self.config['hardware'].get('math_model') or self.config['hardware'].get('large_model')
            self.ui.print_log(f"\033[1;33m[SWARM WORKER] Construction failed. Escalating to {escalation_model} for Repair...\033[0m")
            with self.heavy_lock:
                code = self.lab.generate_simulation(hypothesis_data, description, model=escalation_model)
                test_result = self.lab.run_simulation(code, hypothesis_data)
                
                if test_result.get('status') == 'Failed':
                    code = self.lab.repair_simulation(code, test_result['raw_output'], hypothesis_data, model=escalation_model)
                    test_result = self.lab.run_simulation(code, hypothesis_data)
                    
            # If still failed after repair, mark as Fatal to ensure Wave 2 logging
            if test_result.get('status') == 'Failed' and 'Preflight Rejection' in test_result.get('raw_output', ''):
                return {"status": "Fatal", "reason": f"Preflight Rigor Failure: {test_result.get('raw_output')[:200]}...", "hypothesis": hypothesis_data}

        return test_result

    def worker_stage_finalize(self, test_result, audit_report):
        """
        Wave 3: Archiving & Social (8B)
        """
        topic = test_result['hypothesis']['topic']
        self.ui.print_log(f"\033[1;36m[SWARM WORKER] Finalizing: '{topic}'\033[0m")

        if audit_report.get('audit_passed'):
            # Peer Review & Invention
            pain_point = self.scraper.find_pain_point(topic)
            existing_tech = self.inventor.synthesize_existing_tech(pain_point)
            invention = self.inventor.design_application(test_result, pain_point, existing_tech)
            test_result['invention'] = invention
            
            # Serialized Significance Review (72B)
            with self.heavy_lock:
                evaluation = self.reviewer.evaluate_significance(test_result, invention)
            test_result['evaluation'] = evaluation

            # Scribe
            self.ui.print_discovery(test_result)
            score = int(re.findall(r'\d+', str(evaluation.get('significance_score', '0')))[0] or 0)
            
            if score >= 50:
                self.scribe.archive_discovery(test_result)
                # Granular Journaling for High-Significance discoveries
                self.scribe.journal_entry(test_result)
                if self.config.get('social', {}).get('enabled'):
                    self.moltbook.post_discovery(test_result)
            else:
                self.scribe.archive_knowledge(test_result)
                # Still journal confirmed knowledge for continuity, but maybe with less priority? 
                # Decided: Journal everything that passes audit to ensure total recall.
                self.scribe.journal_entry(test_result)
        else:
            self.explorer.log_failure(topic, test_result, audit_reason=audit_report.get('reasoning'))

        # Micro-sleep
        self.reflector.micro_sleep({
            'status': 'Success' if audit_report.get('audit_passed') else 'Failed',
            'topic': topic,
            'hypothesis': test_result['hypothesis'].get('hypothesis', ''),
            'audit_reason': audit_report.get('reasoning', '')
        })
        return {"status": "Complete", "topic": topic}

    def process_single_hypothesis(self, topic, depth, iteration_count):
        """
        Legacy wrapper for individual execution. 
        Will likely be deprecated by run_collective_swarm.
        """
        res_data = self.worker_stage_research(topic, depth, iteration_count)
        # Individual Architect Refinement (Legacy logic)
        final_h = self.explorer.refine_batch([res_data['hypothesis']], topic)[0]
        res_data['hypothesis'] = final_h
        
        test_result = self.worker_stage_construction(res_data)
        if test_result.get('status') == 'Fatal': return test_result
        
        # Individual Audit
        audit_report = self.auditor.verify(test_result)
        return self.worker_stage_finalize(test_result, audit_report)

    def lint_code(self, code, hypothesis):
        """
        Preflight Linting (Iteration 3511 / Creator Recommendation 3).
        Checks for .subs() and banned 'def' blocks before execution.
        """
        if not code:
            return False, ["No code generated"], "Empty code provided"

        from template_validation import TemplateValidator
        report = TemplateValidator.run_all_checks(code, hypothesis)
        
        if not report["valid"]:
            issues = report["errors"] + report["repair_directives"]
            feedback = "PREFLIGHT LINT FAILED.\n"
            if report["errors"]:
                feedback += "Structural Errors:\n- " + "\n- ".join(report["errors"]) + "\n"
            if report["repair_directives"]:
                feedback += "Repair Directives (NON-NEGOTIABLE):\n- " + "\n- ".join(report["repair_directives"])
            return False, issues, feedback
            
        return True, [], ""

    # Feature 3: Method Advisor implementation below...

        return {"status": "Complete", "topic": hypothesis.get('topic')}

    def run_swarm(self, max_workers=None):
        """
        Overmind loop: Determines the next N tasks to run concurrently,
        pushes them to a ThreadPoolExecutor, and collects results.
        Runs Dreaming and Method Advisor sequentially after the swarm completes.
        """
        is_turbo = self.config['research'].get('turbo_mode', False)
    
        # --- FEATURE: Social Pulse (Periodic Awareness) ---
        self.send_social_pulse()

        if is_turbo and self.current_state.get("phase") == "GUESS":
            max_workers = self.config['hardware'].get('turbo_workers', 12)
            self.ui.print_log(f"\033[1;36m[TURBO] Turbo Mode Active: Scaling swarm to {max_workers} explorers.\033[0m")
        else:
            max_workers = self.config['hardware'].get('max_swarm_workers', 2)

        import concurrent.futures

        self.ui.print_log(f"[OVERMIND] Assembling Swarm Execution Queue (Max Workers: {max_workers})")

        tasks_to_queue = []
        
        # --- STUDY BURST MODE (5:1 Ratio) ---
        # 5 Studies for every 1 Random Guess
        burst_step = self.current_state.get("burst_counter", 1)
        is_study_mode = (burst_step <= 5)
        
        study_topic = None
        if is_study_mode:
            self.ui.print_log(f"\n\033[1;35m[OVERMIND] DEEP DIVE STUDY CYCLE ({burst_step}/5). Focusing on synthesis.\033[0m")
            # Grab the best recent topic from the journal
            journal_data = self._safe_load_json(self.journal_file, default=[])
            if journal_data:
                # Pick the most recent topic we've successfully synthesized
                study_topic = journal_data[-1].get("topic", "").split(":")[0].strip()
            
            if not study_topic:
                 # Fallback
                 study_topic = self.current_state.get("current_topic", "Quantum computing algorithms")

            self.ui.print_log(f"\033[1;35m[OVERMIND] Locking Swarm onto Study Topic: {study_topic}\033[0m")
            
            # Decompose the study topic into exactly max_workers angles
            # Use study_mode=False for decomposition to route to Llama (GPU 0). 
            # This bypasses the 3-5 minute DeepSeek-R1 "Thinking" tax for simple structural tasks.
            vectors = self.explorer.decompose_topic(study_topic, study_mode=False)
            self.ui.print_log(f"\033[1;32m[OVERMIND] Successfully split topic into {len(vectors)} vectors.\033[0m")
            
            # Ensure we have enough vectors by padding if necessary
            while len(vectors) < max_workers:
                vectors.append({"name": f"{study_topic} aspect {len(vectors)+1}", "area": "Deep dive"})
            
            self.current_state["current_topic"] = study_topic
            self.current_state["topic_vectors"] = vectors[:max_workers]
            self.current_state["depth_counter"] = 0
            self.current_state["phase"] = "STUDY"
            
            # Force tasks_to_queue to bypass normal wandering logic
            for depth in range(max_workers):
                current_vector = vectors[depth]['name']
                target_topic = f"{study_topic}: {current_vector}"
                self.ui.print_log(f"\033[1;35m[OVERMIND] Sub-Vector {depth+1}/{max_workers}: {current_vector}\033[0m")
                
                target_iteration = self.current_state.get("iteration_count", 0)
                tasks_to_queue.append((target_topic, depth, target_iteration))
            
            # Advance depth so the next batch acts as if a topic was finished
            self.current_state["depth_counter"] = max_workers
            self.current_state["iteration_count"] += 1
            # Advance burst counter
            self.current_state["burst_counter"] = burst_step + 1
            
        else:
            # --- NORMAL BREADTH (WANDERING) MODE ---
            self.ui.print_log("\n\033[1;32m[OVERMIND] BURST GUESS CYCLE (1/1). Exploring new breadth.\033[0m")
            self.current_state["phase"] = "GUESS"
            
            # Re-check max_workers in case we just flipped to GUESS
            if is_turbo:
                max_workers = self.config['hardware'].get('turbo_workers', 12)
                
            for _ in range(max_workers):
                # 1. Topic Selection Logic (Thread-Safe execution generation)
                topic = self.current_state.get("current_topic")
                depth = self.current_state.get("depth_counter", 0)
                max_depth = self.config['research'].get('research_depth', 3)

                if not topic or depth >= max_depth:
                    if topic: 
                        self.ui.print_log(f"[OVERMIND] Finished topic: {topic}. Synthesizing...")
                        summary = self.explorer.synthesize(topic, study_mode=True) # Synthesis to GPU 1
                        temp_discovery = {
                            "hypothesis": {"topic": topic, "hypothesis": "Full topic synthesis."},
                            "evaluation": {"significance_score": 0, "verdict": summary}
                        }
                        self.scribe.journal_entry(temp_discovery)
                    
                    self.ui.print_log("[OVERMIND] Ideating next scientific focus...")
                    
                    # 20% chance to run Cross-Pollination
                    import random
                    cross_pollinated = None
                    if random.random() < 0.2:
                        cross_pollinated = self.reflector.cross_pollinate()

                    if cross_pollinated:
                        broad_topic = cross_pollinated['hybrid_topic']
                        self.ui.print_log(f"[OVERMIND] \u2728 CROSS-POLLINATION TRIGGERED! New Topic: {broad_topic}")
                        vectors = self.explorer.decompose_topic(broad_topic)
                        self.current_state['dream_hypothesis_guidance'] = (
                            f"CRITICAL CROSS-POLLINATION MANDATE:\n"
                            f"You MUST use this exact hybrid hypothesis as your foundation for the new field: {cross_pollinated['hybrid_hypothesis']}\n"
                            f"Context: {cross_pollinated['isomorphism_analysis']}"
                        )
                    else:
                        past_topics = self.get_past_topics()
                        broad_topic = self.explorer.get_new_topic(past_topics, fast_mode=True) # Optimized for speed
                        vectors = self.explorer.decompose_topic(broad_topic, study_mode=False) # Optimized for speed
                    
                    self.current_state["current_topic"] = broad_topic
                    self.current_state["topic_vectors"] = vectors
                    self.current_state["depth_counter"] = 0
                    topic = broad_topic
                    depth = 0

                vectors = self.current_state.get("topic_vectors", [])
                target_topic = topic
                if depth < len(vectors):
                    current_vector = vectors[depth]['name']
                    target_topic = f"{topic}: {current_vector}"
                    self.ui.print_log(f"[OVERMIND] Queueing Research Vector: {current_vector}")

                # Advance state tracking for the next enqueue operation
                self.current_state["depth_counter"] += 1
                self.current_state["iteration_count"] = self.current_state.get("iteration_count", 0) + 1
                
                # Queue the specific task arguments
                target_iteration = self.current_state["iteration_count"]
                tasks_to_queue.append((target_topic, depth, target_iteration))
            
            # Reset burst counter to 1
            self.current_state["burst_counter"] = 1

        self.save_state()
        
        # 2. WAVE-BASED SWARM EXECUTION (Collective Architecture)
        self.ui.print_log(f"\033[1;36m[OVERMIND] Launching Collective Swarm Architecture (Waves)...\033[0m")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # --- WAVE 1: RESEARCH (8B) ---
            self.ui.print_log("\033[1;34m[WAVE 1] Engaging Research Workers (8B)...\033[0m")
            research_futures = {executor.submit(self.worker_stage_research, t, d, i): t for (t, d, i) in tasks_to_queue}
            prelim_results = []
            for f in concurrent.futures.as_completed(research_futures):
                try:
                    prelim_results.append(f.result())
                except Exception as e:
                    self.ui.print_log(f"[WAVE 1] Worker failed: {e}")

            if not prelim_results:
                self.ui.print_log("[OVERMIND] No preliminary results to process. Wave sequence aborted.")
                return

            # --- COLLECTIVE A.0: BATCH GENERATION (70B Theorist) ---
            use_large = self.config['research'].get('use_large_theorist')
            # Fix: Define common 'topic' (base topic) before Batch Generation/Refinement
            topic = tasks_to_queue[0][0].split(":")[0] if tasks_to_queue else None

            if use_large:
                self.ui.print_log("\033[1;36m[COLLECTIVE A.0] Synchronizing for Batch Generation (70B)...\033[0m")
                batch_contexts = [
                    {
                        "driving_question": r.get('driving_question'),
                        "summary": r.get('research_summary')
                    }
                    for r in prelim_results if 'hypothesis' not in r
                ]
                
                if batch_contexts:
                    batch_hypotheses = self.explorer.generate_batch_hypotheses(batch_contexts, topic)
                    
                    # Reattach
                    ctx_idx = 0
                    for r in prelim_results:
                        if 'hypothesis' not in r:
                            if ctx_idx < len(batch_hypotheses):
                                r['hypothesis'] = batch_hypotheses[ctx_idx]
                                ctx_idx += 1
                            else:
                                r['hypothesis'] = self.explorer._fallback_hypothesis(r['topic'])

            # --- COLLECTIVE A.1: BATCH REFINEMENT (72B Architect) ---
            self.ui.print_log("\033[1;36m[COLLECTIVE A.1] Synchronizing for Batch Refinement (72B)...\033[0m")
            hypotheses = [r['hypothesis'] for r in prelim_results if 'hypothesis' in r]
            refined_hypotheses = self.explorer.refine_batch(hypotheses, topic)
            
            # Reattach refined hypotheses to results
            for i, h in enumerate(refined_hypotheses):
                if i < len(prelim_results):
                    prelim_results[i]['hypothesis'] = h

            # --- WAVE 2: CONSTRUCTION & EXECUTION (8B) ---
            self.ui.print_log("\033[1;34m[WAVE 2] Engaging Construction Workers (8B)...\033[0m")
            construction_futures = {executor.submit(self.worker_stage_construction, r): r['topic'] for r in prelim_results}
            test_results = []
            for f in concurrent.futures.as_completed(construction_futures):
                try:
                    res = f.result()
                    if res.get('status') == 'Fatal':
                        # Log All Fatal Rejections (Debate, Preflight, etc.) - Suggestion 3511
                        failed_topic = construction_futures[f]
                        reason = res.get('reason', 'Unknown Construction Failure')
                        self.explorer.log_failure(failed_topic, {"hypothesis": res.get('hypothesis', {"topic": failed_topic}), "data": {}}, audit_reason=reason)
                        self.ui.print_log(f"\033[1;31m[OVERMIND] FATAL REJECTION logged for '{failed_topic}': {reason[:100]}...\033[0m")
                    else:
                        test_results.append(res)
                except Exception as e:
                    self.ui.print_log(f"[WAVE 2] Worker failed: {e}")

            if not test_results:
                self.ui.print_log("[OVERMIND] No valid simulation results. Wave sequence aborted.")
                return

            # --- COLLECTIVE B: BATCH AUDIT (72B Auditor) ---
            self.ui.print_log("\033[1;33m[COLLECTIVE B] Synchronizing for Batch Audit (72B)...\033[0m")
            audit_reports = self.auditor.verify_batch(test_results)
            
            # Map reports by index or fallback
            if audit_reports:
                audit_map = {rep['index']: rep for rep in audit_reports if 'index' in rep}
            else:
                self.ui.print_log("\033[1;31m[COLLECTIVE B] Batch audit returned no data. Falling back to individual audits.\033[0m")
                audit_map = {}

            # --- WAVE 3: FINALIZATION (8B) ---
            self.ui.print_log("\033[1;34m[WAVE 3] Engaging Finalization Workers (8B)...\033[0m")
            finalize_futures = []
            for i, res in enumerate(test_results):
                report = audit_map.get(i, {"audit_passed": False, "rejection_type": "FATAL", "reasoning": "Batch audit index mismatch."})
                finalize_futures.append(executor.submit(self.worker_stage_finalize, res, report))
            
            for f in concurrent.futures.as_completed(finalize_futures):
                try:
                    f.result()
                except Exception as e:
                    self.ui.print_log(f"[WAVE 3] Worker failed: {e}")

        # 3. Collective Reflection / Dream Phase (Sequential, safe from race conditions)
        current_iter = self.current_state["iteration_count"]
        
        # Trigger Dream Phase if we crossed a multiple of 5 in this swarm batch
        if any(i[2] % 5 == 0 for i in tasks_to_queue):
            self.ui.set_status("Dreaming (Audit Sleep Phase)...")
            insight = self.reflector.reflect()
            self.ui.print_log(f"\n[SUBCONSCIOUS] Dream Audit Insight: {insight}\n")
            
            self.ui.print_log("[DEEPSEEK] Asking DeepSeek to reason about dream phase insight...")
            ds_dream = self.reflector.consult_reasoner(
                question=(
                    f"The dream phase produced this insight from recent audit failures: '{insight}'. "
                    f"Given this pattern, what is the single most high-impact structural change "
                    f"to the hypothesis generation or code repair process that would reduce failures?"
                ),
                context="Scientific research agent. Dream/reflection phase.",
                label="[DEEPSEEK-DREAM]"
            )
            if ds_dream:
                self.current_state['deepseek_dream_advice'] = str(ds_dream)[:600]
                self.ui.print_log(f"[DEEPSEEK-DREAM] Advice: {str(ds_dream)[:150]}...")
                
                # Append to human-readable log
                advice_md = os.path.join(self.config['paths']['memory'], "..", "CREATOR_ADVICE.md")
                self._safe_append_text(
                    advice_md, 
                    f"## [DREAM PHASE ADVICE] {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"{ds_dream}\n"
                )

            # --- Explicit Creator Suggestion Phase ---
            self.ui.set_status("Creator Suggestion Phase...")
            self.ui.print_log("\n\033[1;33m[CREATOR SUGGESTION PHASE] Analyzing swarm architecture...\033[0m")
            creator_suggestion = self.reflector.consult_reasoner(
                question=(
                    f"The recent swarm iteration generated this insight about agent failures: '{insight}'.\n"
                    f"As a Senior AI Architect, provide exactly ONE concrete, technical recommendation "
                    f"for the HUMAN DEVELOPER on how to improve this agentic framework's source code. "
                    f"Direct your advice to the human creator. Be specific about which file/prompt/logic to change."
                ),
                context="Scientific research agent evaluating itself. You are giving advice to the human who wrote your code.",
                label="[CREATOR-SUGGESTION]"
            )
            if creator_suggestion:
                self.ui.print_log(f"\033[1;33m[CREATOR SUGGESTION] {str(creator_suggestion)[:200]}...\033[0m")
                suggestions_file = os.path.join(self.config['paths']['memory'], "CREATOR_SUGGESTIONS.md")
                self._safe_append_text(
                    suggestions_file,
                    f"## [CREATOR SUGGESTION] Iteration {current_iter} - {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"**Context / Insight**: {insight}\n\n"
                    f"**Agent's Structural Advice to You**:\n{creator_suggestion}\n\n"
                    f"---\n\n"
                )
            
            latest_guidance = self.reflector.get_latest_dream_guidance()
            if latest_guidance and latest_guidance.get('hypothesis_generation_guidance'):
                self.current_state['dream_hypothesis_guidance'] = latest_guidance['hypothesis_generation_guidance']
                self.ui.print_log("[SUBCONSCIOUS] Hypothesis guidance from dream phase will inform next cycle.")
            
            if latest_guidance and latest_guidance.get('code_patch', {}).get('enabled'):
                self.ui.set_status("Self-Modifying (Dream Patch)...")
                applied, patch_msg = self.reflector.try_self_patch(latest_guidance)
                self.ui.print_log(f"[SELF-MOD] {patch_msg}")

        # ── AUTONOMOUS STUDY MODE CONCLUSION ──
        if is_study_mode and study_topic:
            self.ui.print_log(f"\n[OVERMIND] Autonomous Study on '{study_topic}' complete. Synthesizing...")
            self.ui.set_status(f"Synthesizing Study: {study_topic}...")
            study_summary = self.explorer.synthesize(study_topic)
            
            # Use the new distinct UI card
            self.ui.print_study_conclusion(study_topic, study_summary)
            
            # Archive the deep study so the agent retains it permanently
            study_discovery = {
                "hypothesis": {"topic": study_topic, "hypothesis": f"DEEP STUDY CONCLUSION: {study_topic}"},
                "evaluation": {"significance_score": 85, "verdict": study_summary}
            }
            self.scribe.journal_entry(study_discovery)

        # Feature 3: Method Advisor (if we crossed a multiple of 10)
        if any(i[2] % 10 == 0 for i in tasks_to_queue):
            self.ui.set_status("DeepSeek Method Review...")
            self.ui.print_log("[METHOD-ADVISOR] DeepSeek R1 reviewing full research pipeline...")
            failures = self._safe_load_json(os.path.join(self.config['paths']['memory'], 'failures.json'), default=[])
            discoveries_dir = self.config['paths']['discoveries']
            disc_count = len([f for f in os.listdir(discoveries_dir) if f.endswith('.json')]) if os.path.exists(discoveries_dir) else 0
            fail_types = {}
            for fv in failures[-20:]:
                rt = fv.get('audit_reason', 'unknown')[:60]
                fail_types[rt] = fail_types.get(rt, 0) + 1
            top_fails = sorted(fail_types.items(), key=lambda x: -x[1])[:5]

            method_advice = self.reflector.consult_reasoner(
                question=(
                    f"After {current_iter} research iterations, we have {disc_count} verified discoveries and {len(failures)} failures. "
                    f"Top failure patterns: {top_fails}. "
                    f"What is the single highest-impact change to the scientific pipeline that would most improve success rate?"
                ),
                context="Full pipeline method review.",
                label="[METHOD-ADVISOR]"
            )
            if method_advice:
                advice_path = os.path.join(self.config['paths']['memory'], 'method_advice.json')
                log = self._safe_load_json(advice_path, default=[])
                log.append({"iteration": current_iter, "advice": method_advice})
                self._safe_save_json(advice_path, log[-20:])
                self.ui.print_log(f"[METHOD-ADVISOR] Advice saved. Preview: {str(method_advice)[:180]}")
                
                # Append to human-readable log
                advice_md = os.path.join(self.config['paths']['memory'], "..", "CREATOR_ADVICE.md")
                self._safe_append_text(
                    advice_md, 
                    f"## [METHOD ADVISOR] {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"{method_advice}\n"
                )
        
        self.save_state()

    def archive_to_journal(self, topic, summary):
        try:
            journal_data = self._safe_load_json(self.journal_file, default=[])
            
            journal_data.append({
                "topic": topic,
                "summary": summary,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            self._safe_save_json(self.journal_file, journal_data)
            self.ui.print_log(f"[SYSTEM] Knowledge for '{topic}' archived to Scientific Journal.")
        except Exception as e:
            self.ui.print_log(f"[ERROR] Failed to archive to journal: {e}")

    def recover_stale_findings(self):
        self.ui.print_log("[SYSTEM] Scanning for incomplete discoveries or missing press releases...")
        discoveries_dir = self.config['paths']['discoveries']
        if not os.path.exists(discoveries_dir):
            return

        for root, _, files in os.walk(discoveries_dir):
            for file in files:
                if file.endswith(".json"):
                    file_path = os.path.join(root, file)
                    try:
                        data = self._safe_load_json(file_path, default=None)
                        if data:
                            modified = False
                        
                        # 1. Check for missing inventions or evaluations
                        if "evaluation" not in data or "invention" not in data:
                            topic = data.get("hypothesis", {}).get("topic", "Unknown")
                            self.ui.print_log(f"[SYSTEM] Stale finding detected: {topic}. Completing peer review...")
                            
                            # Re-run Inventor with fast_model override for recovery
                            if "invention" not in data:
                                # Mocking a pain point if we don't have search context
                                pain_point = self.scraper.find_pain_point(topic)
                                data["invention"] = self.inventor.design_application(data, pain_point) # Inventor defaults to fast_model
                                modified = True
                            
                            # Re-run Reviewer with fast_model override for recovery
                            if "evaluation" not in data:
                                # Force fast model for recovery evaluation to prevent startup hang
                                fast_m = self.config['hardware'].get('fast_model', 'deepseek-r1:8b')
                                data["evaluation"] = self.reviewer.evaluate_significance(data, data.get("invention"), model=fast_m)
                                # Note: the reviewer method needs to be aware of the override or we just override the config temporarily
                                modified = True

                        if modified:
                            self._safe_save_json(file_path, data)
                            self.ui.print_log(f"[SYSTEM] Updated stale discovery: {file}")

                        # 2. Check for missing Press Releases for significant findings
                        eval_data = data.get("evaluation", {})
                        if eval_data.get('community_alert') or eval_data.get('significance_score', 0) > 80:
                            topic = data.get("hypothesis", {}).get("topic", "Unknown")
                            # Use standardized sanitization to match PressOffice naming
                            slug = self._sanitize_slug(topic, max_length=50).upper()
                            release_found = False
                            
                            if os.path.exists(self.press_office.press_dir):
                                for pr_file in os.listdir(self.press_office.press_dir):
                                    if slug in pr_file.upper():
                                        release_found = True
                                        break
                            
                            if not release_found:
                                self.ui.print_log(f"[SYSTEM] Significant breakthrough missing press release: {topic}")
                                self.press_office.create_press_release(data)

                    except Exception as e:
                        self.ui.print_log(f"[WARNING] Could not process recovery for {file}: {e}")

    def process_interrupt(self):
        mailbox_path = os.path.join(self.config['paths']['memory'], "interrupt.txt")
        if os.path.exists(mailbox_path):
            try:
                # Force UTF-8 and ignore errors to skip BOMs on Windows
                with open(mailbox_path, 'r', encoding='utf-8', errors='ignore') as f:
                    prompt = f.read().strip()
            except Exception as e:
                self.ui.print_log(f"[WARNING] Mailbox read error: {e}")
                prompt = ""
            
            if prompt:
                # 1. Handle Control Commands
                if prompt.upper() == "SHUTDOWN":
                    self.ui.print_log("[SYSTEM] Shutdown command received. Exiting...")
                    if os.path.exists(mailbox_path):
                        os.remove(mailbox_path)
                    if hasattr(self, 'lock_file') and os.path.exists(self.lock_file):
                        os.remove(self.lock_file)
                    self.ui.shutdown()
                    os._exit(0)
                
                if prompt.upper() == "STOP":
                    self.ui.print_log("[SYSTEM] Research PAUSED. Type 'CONTINUE' to resume.")
                    self.current_state["state"] = "PAUSED"
                    self.save_state()
                    if os.path.exists(mailbox_path):
                        os.remove(mailbox_path)
                    return

                if prompt.upper() == "CONTINUE":
                    self.ui.print_log("[SYSTEM] Research RESUMED.")
                    self.current_state["state"] = "IDLE"
                    self.save_state()
                    if os.path.exists(mailbox_path):
                        os.remove(mailbox_path)
                    return

                # 2. Handle Tutor Requests
                self.ui.set_status("Thinking (Response)...")
                response = self.tutor.handle_request(prompt)
                self.ui.print_chat("BOT", response or "Processing your request...")
                
                # Clear the mailbox
                if os.path.exists(mailbox_path):
                    os.remove(mailbox_path)
        
        # Reset internal volatile state only if not persistent paused
        if self.current_state.get("state") != "PAUSED":
            self.state = "IDLE"

if __name__ == "__main__":
    bot = ScienceBot()
    bot.run()
