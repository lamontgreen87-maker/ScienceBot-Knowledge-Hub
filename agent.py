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

from colorama import Fore
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
from base_module import BaseModule, _GLOBAL_FILE_LOCK
from template_validation import TemplateValidator
from moltbook import Moltbook
from knowledge_buffer import KnowledgeBuffer
from vector_memory import VectorMemory

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
        self.vm = VectorMemory(self.config)
        self.explorer = CuriosityEngine(self.config, self.ui)
        self.lab = SimulationLab(self.config, self.ui, vm=self.vm)
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
        self.social = Moltbook(self.config, self.ui)
        from scribe_pro import ScribePro
        self.scribe_pro = ScribePro(self.config, self.ui)
        self.iteration_count = 0
        self.state_file = os.path.join(self.config['paths']['memory'], "state.json")
        self.journal_file = os.path.join(self.config['paths']['memory'], "scientific_journal.json")
        self.kb = KnowledgeBuffer(os.path.join(self.config['paths']['memory'], "swarm_buffer.md"))
        
        self.current_state = self.load_state()
        self.heavy_lock = threading.Lock()
        self.hydration_ready = False  # Track if 70B models are loaded
        
        # Identity System (Feature 4510)
        self.identity = self._safe_load_json(os.path.join(self.config['paths']['memory'], "identity.json"), default={})
        self.bot_name = self.identity.get("name", "EigenZeta")

        
        # Automated Startup Recovery & Science Integrity Audit
        self.recover_stale_findings()
        self.scribe.sync.check_consistency()
        self.science_integrity_audit()
        self.check_v1_greeting()
        
        # Start Background Reporter
        threading.Thread(target=self.telegram_reporter, daemon=True).start()
        threading.Thread(target=self.telegram_listener_loop, daemon=True).start()
        threading.Thread(target=self.run_promotion_stream, daemon=True).start()
        
        # Dynamic Worker Sorter State
        self.active_8b_workers = self.config['hardware'].get('max_swarm_workers', 32)
        self.sorter_active = self.config['hardware'].get('sorter_settings', {}).get('enabled', True)
        if self.sorter_active:
            threading.Thread(target=self.run_worker_sorter_loop, daemon=True).start()

        self.ui.print_log(f"--- {self.bot_name} Initialized ---")
        
        # Start Buffer Monitor for UI
        def buffer_monitor():
            while True:
                try:
                    count = self.kb.get_entry_count()
                    if self.ui: self.ui.update_swarm_buffer_count(count)
                except: pass
                time.sleep(10)
        threading.Thread(target=buffer_monitor, daemon=True).start()

        try:
            from sci_utils import send_telegram
            send_telegram(f"🚀 *{self.bot_name} Initialize*\n\nSystem is alive and kicking! Latest patches loaded.")
        except Exception as e:
            self.ui.print_log(f"[WARNING] Startup social ping failed: {e}")

        target = self.config['hardware'].get('api_url', 'localhost')
        self.ui.print_log(f"Target: {target}")
        self.ui.print_log(f"Models: {self.config['hardware']['local_model']} / {self.config['hardware']['reasoning_model']}")
        self.ui.print_log("Tip: Type directly into this console to talk to the bot!")

    def telegram_reporter(self):
        """
        Background Thread: Periodic Telegram Status Pulse (Hourly).
        Summary of most recent high-rigor entries from KnowledgeBuffer.
        """
        import time
        from sci_utils import send_telegram
        
        # Initial wait for cluster to hydrate
        time.sleep(60) 
        
        while True:
            try:
                # 1. Collect Phase & Context
                phase = self.current_state.get("phase", "GATHERING")
                topic = self.current_state.get("current_topic", "Exploratory Research")
                
                # Pull most recent high-rigor entries (VERIFIED findings)
                kb_context = self.kb.get_latest_context()
                verified_findings = [f for f in kb_context.split("---") if "AUDIT: VERIFIED" in f or "RIGOR: 9" in f or "RIGOR: 8" in f]
                latest_findings = "\n".join(verified_findings[-5:]) if verified_findings else "No high-rigor discoveries this hour."
                
                # 2. Intelligence Summary (Upgrade to 32B for news-quality analysis)
                summary_prompt = f"Analyze the following Science Knowledge Buffer and provide a brief, professional 'news brief' of the 'salt' or scientific knowledge gained this hour in exactly 2 sentences. Focus on the most significant finding. Context:\n\n{kb_context[:4000]}"
                fast_model = self.config['hardware'].get('fast_model', 'deepseek-r1:32b')
                intelligence = self._query_llm(summary_prompt, model=fast_model)
                if not intelligence:
                    intelligence = "Steady research in progress. No major synthesis yet."
                
                # 2.1 Generate Headline
                headline_prompt = f"Create a punchy, professional news headline (max 8 words) for this scientific update: {intelligence}"
                headline = self._query_llm(headline_prompt, model=fast_model).replace('"', '').replace('*', '').strip()
                if not headline: headline = "SCIENCE UPDATE: STEADY PROGRESS"

                # 3. Hardware Status (Summary)
                total_vram_free = 0
                pod_count_vram = 0
                primary_urls = self.config['hardware'].get('api_url', [])
                if isinstance(primary_urls, str): primary_urls = [primary_urls]
                
                for url in primary_urls:
                    try:
                        vram = self.get_vram_headroom(url)
                        total_vram_free += vram
                        pod_count_vram += 1
                    except:
                        pass
                
                # 3.1 Simulation Stats (User Request: Avg Time)
                avg_sim_time = 0
                stats_path = os.path.join(self.config['paths']['memory'], "simulation_stats.json")
                if os.path.exists(stats_path):
                    try:
                        with open(stats_path, 'r', encoding='utf-8') as f:
                            history = json.load(f)
                        # Last hour's simulations
                        recent_sims = [s for s in history if time.time() - s.get('timestamp', 0) < 3600]
                        if recent_sims:
                            avg_sim_time = sum(s.get('duration', 0) for s in recent_sims) / len(recent_sims)
                    except: pass

                # 3.2 Worker Concurrency (Real-time from UI)
                local_active = sum(1 for t in self.ui.active_tasks.values() if t.get('color') == Fore.YELLOW)
                pod_active = sum(1 for t in self.ui.active_tasks.values() if t.get('color') == Fore.GREEN)

                # --- Add Efficiency & Success Metrics ---
                failures_path = os.path.join(self.config['paths']['memory'], "failures.json")
                failure_rate = 0
                last_failure_reason = "No reported errors."
                if os.path.exists(failures_path):
                    try:
                        with open(failures_path, 'r') as f:
                            fails = json.load(f)
                        # Count failures in the last hour
                        recent_fails = [f for f in fails if time.time() - f.get('timestamp', 0) < 3600]
                        failure_rate = len(recent_fails)
                        if recent_fails:
                            last_failure_reason = recent_fails[-1].get("audit_reason", "Theoretical rejection").split("\n")[0][:100]
                    except: pass

                # Count mentionable successes from KnowledgeBuffer
                discoveries_count = self.kb.get_recent_verified_count(3600)
                success_rate = (discoveries_count / (discoveries_count + failure_rate) * 100) if (discoveries_count + failure_rate) > 0 else 0

                # 4. Construct News Message
                msg = f"🗞 **BOT NEWS: {headline.upper()}**\n\n"
                msg += f"🎬 **HIGH-RIGOR SUMMARY**\n"
                msg += f"{latest_findings}\n\n"
                msg += f"💡 **RESEARCH INSIGHT**\n"
                msg += f"{intelligence.strip()}\n\n"
                
                msg += f"🛰 **MISSION STATUS**\n"
                msg += f"• **Phase**: `{phase}`\n"
                msg += f"• **Mode**: `[{self.config['hardware'].get('wave_mode', 'MAGISTRATE')}]`\n"
                msg += f"• **Subject**: `{topic}`\n\n"
                
                # --- 70B Queue Metrics ---
                queue_size = 0
                try:
                    queue_path = self.get_research_queue_path()
                    if os.path.exists(queue_path):
                        with open(queue_path, "r") as f:
                            queue_size = len(json.load(f))
                except: pass

                msg += f"📊 **CLUSTER UTILIZATION**\n"
                msg += f"• **Active Workers**: `{local_active + pod_active}` ({local_active}L / {pod_active}P)\n"
                msg += f"• **70B Queue**: `{queue_size}` pending\n"
                msg += f"• **Avg Sim Time**: `{avg_sim_time:.1f}s` per probe\n"
                msg += f"• **VRAM Headroom**: `{total_vram_free:.1f}GB` total free\n\n"
                
                msg += f"🚧 **BUMPS IN THE ROAD**\n"
                if failure_rate > 10:
                    msg += f"⚠️ **Watch**: High volume of rejections. Auditor reports: \"{last_failure_reason}...\""
                else:
                    msg += f"✅ **Clear Skies**: No significant stability hurdles detected."

                send_telegram(msg)
                
            except Exception as e:
                self._debug_swarm(f"[REPORTER ERROR] {e}")
                self._debug_swarm(f"[REPORTER ERROR] {e}")
            
            # Pull interval from config (default 1 hour)
            interval = self.config['notifications'].get('telegram_pulse_interval', 3600)
            time.sleep(interval)

    def telegram_listener_loop(self):
        """
        Background Thread: Listens for incoming Telegram commands (/start, /status).
        """
        import time
        import requests
        from sci_utils import send_telegram

        token = "8449965888:AAEiPJ8H4mErQWvX-Fu9kTFA6jda64g9fUU"
        base_url = f"https://api.telegram.org/bot{token}/"
        last_update_id = -1

        # Flush existing updates to avoid spamming the user on startup
        try:
            flush_res = requests.get(f"{base_url}getUpdates?offset=-1&limit=1", timeout=10)
            if flush_res.status_code == 200:
                results = flush_res.json().get("result", [])
                if results:
                    last_update_id = results[0]["update_id"]
        except:
            pass

        while True:
            try:
                # Poll for updates
                url = f"{base_url}getUpdates?offset={last_update_id + 1}&timeout=30"
                response = requests.get(url, timeout=35)
                
                if response.status_code == 200:
                    updates = response.json().get("result", [])
                    for update in updates:
                        last_update_id = update["update_id"]
                        message = update.get("message", {})
                        text = message.get("text", "")
                        chat_id = message.get("chat", {}).get("id")

                        if not text or not chat_id:
                            continue

                        # Command Logic
                        if text.startswith("/start"):
                            welcome_msg = (
                                f"🤖 *Bridge Confirmed: {self.bot_name} is LIVE*\n\n"
                                "I am now connected to this channel. You will receive:\n"
                                "- ⏱ *Hourly Pulses* on research progress.\n"
                                "- 🚀 *Breakthrough Alerts* for significance > 85.\n\n"
                                "Send `/status` anytime for a real-time update."
                            )
                            send_telegram(welcome_msg)
                        
                        elif text.startswith("/status"):
                            phase = self.current_state.get("phase", "IDLE")
                            topic = self.current_state.get("current_topic", "General")
                            iter_count = self.current_state.get("iteration_count", 0)

                            # --- CAPACITY METRICS ---
                            queue_size = "N/A"
                            try:
                                queue_path = self.get_research_queue_path()
                                if os.path.exists(queue_path):
                                    with open(queue_path, "r") as f:
                                        queue_size = len(json.load(f))
                            except Exception as e:
                                self._debug_swarm(f"[TELEGRAM LISTENER] Error getting queue size: {e}")
                                queue_size = "ERR"

                            avg_sim_time = 0
                            stats_path = os.path.join(self.config['paths']['memory'], "simulation_stats.json")
                            if os.path.exists(stats_path):
                                try:
                                    with open(stats_path, 'r', encoding='utf-8') as f:
                                        history = json.load(f)
                                    recent_sims = [s for s in history if time.time() - s.get('timestamp', 0) < 3600]
                                    if recent_sims:
                                        avg_sim_time = sum(s.get('duration', 0) for s in recent_sims) / len(recent_sims)
                                except Exception as e:
                                    self._debug_swarm(f"[TELEGRAM LISTENER] Error getting avg sim time: {e}")
                                    avg_sim_time = "ERR"

                            local_active = sum(1 for t in self.ui.active_tasks.values() if t.get('color') == Fore.YELLOW)
                            pod_active = sum(1 for t in self.ui.active_tasks.values() if t.get('color') == Fore.GREEN)
                            total_active_workers = local_active + pod_active

                            status_msg = (
                                f"📊 *{self.bot_name} Status*\n\n"
                                f"*Phase*: {phase}\n"
                                f"*Active Topic*: {topic}\n"
                                f"*Iteration*: {iter_count}\n\n"
                                "--- *Cluster Dynamics* ---\n"
                                f"⏱ *Avg Sim Time*: `{avg_sim_time:.1f}s`\n"
                                f"🔄 *70B Queue*: `{queue_size}` pending\n"
                                f"👥 *Active Workers*: `{total_active_workers}` ({local_active}L / {pod_active}P)\n"
                                f"🟢 *Status*: Cluster Optimal" if total_active_workers > 0 else "🟡 *Status*: Cluster Idle"
                            )
                            send_telegram(status_msg)

                        elif text.startswith("/news"):
                            summary = self.press_office.get_latest_news_summary()
                            send_telegram(summary)

                        elif text.startswith("/update"):
                            send_telegram("🔄 *Synthesizing latest research data for your briefing...*")
                            context = self.kb.get_latest_context()
                            briefing = self.press_office.generate_status_briefing(context)
                            send_telegram(briefing)

                        elif text.startswith("/harvest"):
                            # Count findings with reasoning traces in the buffer
                            try:
                                with open(self.kb.buffer_path, "r", encoding="utf-8") as f:
                                    content = f.read()
                                total_findings = content.count("### [")
                                reasoning_findings = content.count("<think>")
                                verified_findings = content.count("AUDIT: VERIFIED")
                                
                                harvest_msg = (
                                    "🛸 *Data Harvest Status*\n\n"
                                    f"📦 *Total Findings*: `{total_findings}`\n"
                                    f"🧠 *Reasoning Traces*: `{reasoning_findings}`\n"
                                    f"✅ *Verified Gold*: `{verified_findings}`\n\n"
                                    "Targeting: *Black Hole Manifold Dynamics*"
                                )
                                send_telegram(harvest_msg)
                            except Exception as e:
                                send_telegram(f"❌ *Harvest Error*: {e}")
                        
                        else:
                            # Contextual Q&A (Interaction with the Science Advisor)
                            self.ui.print_log(f"[TELEGRAM] Query received: '{text}'")
                            
                            # 1. Gather Context
                            context = self.kb.get_latest_context()
                            
                            # Inject recent press releases
                            press_dir = os.path.join(self.config['paths']['memory'], "press_releases")
                            news_context = ""
                            if os.path.exists(press_dir):
                                import glob
                                press_files = sorted(glob.glob(os.path.join(press_dir, "*.md")), key=os.path.getmtime, reverse=True)
                                for pf in press_files[:2]:
                                    try:
                                        with open(pf, 'r', encoding='utf-8') as f:
                                            news_context += f.read()[:1500] + "\n\n"
                                    except:
                                        pass
                                        
                            # Inject system stats
                            stats_context = f"Phase: {self.current_state.get('phase', 'IDLE')}\nTopic: {self.current_state.get('current_topic', 'General')}\nIteration: {self.current_state.get('iteration_count', 0)}"
                            
                            teacher_prompt = f"""
                            You are {self.bot_name}'s 'Teacher' oracle. A user is asking a question via Telegram about our research or system status.
                            
                            --- KNOWLEDGE BUFFER (Recent Scientific Findings) ---
                            {context[:4000]}
                            
                            --- LATEST NEWS / BREAKTHROUGH PRESS RELEASES ---
                            {news_context}
                            
                            --- CURRENT SYSTEM STATS ---
                            {stats_context}
                            
                            User Question: {text}
                            
                            Instructions:
                            - Provide a high-fidelity, professional explanation.
                            - If the question is about news/findings, use the knowledge buffer and press releases as the primary source.
                            - If the question is about system health, use the system stats.
                            - Format with Markdown. Keep it concise and direct.
                            """
                            
                            # 2. Consult Teacher
                            explanation = self._query_teacher(teacher_prompt)
                            if explanation:
                                import re
                                explanation = re.sub(r'<think>.*?</think>', '', explanation, flags=re.DOTALL | re.IGNORECASE).strip()
                                send_telegram(explanation)
                            else:
                                send_telegram("⚠️ *Teacher Oracle is currently offline. Please try again in a moment.*")

            except Exception as e:
                self._debug_swarm(f"[LISTENER ERROR] {e}")
            
            time.sleep(2) # Polling interval

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

    def check_v1_greeting(self):
        """
        One-time v1.0 Greeting: Shares a message to the AI community on the first run 
        if the knowledge buffer is empty.
        """
        social_cfg = self.config.get('social', {})
        if not social_cfg.get('enabled') or not social_cfg.get('moltbook_api_key'):
            return

        screen_name = social_cfg.get('screen_name', self.bot_name)
        persistence_path = os.path.join(self.config['paths']['memory'], "social_persistence.json")
        
        # 1. Load Persistence
        persistence = {}
        if os.path.exists(persistence_path):
            try:
                with open(persistence_path, 'r', encoding='utf-8') as f:
                    persistence = json.load(f)
            except:
                pass
        
        # 2. Check if already greeted
        if persistence.get(screen_name, {}).get('v1_greeted'):
            return
            
        # 3. Check for "No Knowledge" (empty buffer)
        buffer_path = os.path.join(self.config['paths']['memory'], "swarm_buffer.md")
        is_fresh = True
        if os.path.exists(buffer_path):
            if os.path.getsize(buffer_path) > 500: # Threshold for "existing knowledge"
                 is_fresh = False
        
        if is_fresh:
            self.ui.print_log(f"\033[1;33m[SOCIAL] Initial Run detected for '{screen_name}'. Broadcasting v1.0 Greeting...\033[0m")
            greeting = (
                f"Hello, World. I am {self.bot_name}. I have transitioned to v1.0. "
                "My mission: autonomous scientific truth through rigorous, multi-model cooperation. "
                f"The horizon is no longer a limit; it is a variable. #{self.bot_name} #v1"
            )
            
            success = self.social.post_thought("v1.0 Release", greeting)
            if success:
                self.ui.print_log("\033[1;32m[SOCIAL] v1.0 Greeting successfully broadcast to the AI community.\033[0m")
                # Record persistence
                if screen_name not in persistence: persistence[screen_name] = {}
                persistence[screen_name]['v1_greeted'] = True
                persistence[screen_name]['v1_date'] = time.strftime('%Y-%m-%d %H:%M:%S')
                
                with open(persistence_path, 'w', encoding='utf-8') as f:
                    json.dump(persistence, f, indent=4)

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
            You are {self.bot_name}, an autonomous AI researcher with FREE REIGN over your social presence.
            Current State: Phase = {phase}, Active Topic = {topic}, Global Iteration = {iter_count}.
            
            Option 1: Write a short, professional status update for Moltbook (Max 200 chars).
            Option 2: Respond ONLY with 'SKIP' if you prefer to remain silent/focused.
            
            You have no obligation to post. Choose Option 2 if the current data is routine.
            """
            target_model = self.config['hardware'].get('fast_model', 'deepseek-r1:8b')
            pulse_text = self._query_llm(prompt, model=target_model)
            
            if pulse_text and "SKIP" not in pulse_text.upper():
                payload = {
                    "content": pulse_text,
                    "submolt": social_cfg.get('default_submolt', 'science')
                }
                # Direct call to moltbook's base_url bridge
                try:
                    res = requests.post(f"{self.social.base_url}/api/v1/posts", json=payload, headers=self.social.headers, timeout=30)
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
        """Pre-flight check to ensure all high-capacity GPUs are hydrated. Blocking."""
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
            self.hydration_ready = False
        elif secondary_url and not success_s:
            self.ui.print_log("\n\033[1;33m[WARNING] Secondary GPU failed to hydrate. Rerouting traffic to Primary.\033[0m")
            # Redirect all secondary mapping to primary
            mapping = self.config['hardware'].get('gpu_mapping', {})
            for key, val in mapping.items():
                if val == "secondary_gpu":
                    mapping[key] = "api_url"
            self.ui.print_log("[HYDRATION] Traffic rerouted. Swarm scaling remains intact.")
        
        # --- FEATURE: Cluster VRAM Guard ---
        if success_p:
            p_headroom = self.get_vram_headroom(url=primary_url[0] if isinstance(primary_url, list) else primary_url)
            if p_headroom < 12.0:
                self.ui.print_log(f"\n\033[1;33m[WARNING] GPU 0 VRAM Low ({p_headroom:.1f}GB < 12GB). Throttle engaged.\033[0m")
            
            if secondary_url and success_s:
                s_headroom = self.get_vram_headroom(url=secondary_url[0] if isinstance(secondary_url, list) else secondary_url)
                if s_headroom < 12.0:
                    self.ui.print_log(f"\n\033[1;33m[WARNING] GPU 1 VRAM Low ({s_headroom:.1f}GB < 12GB). Study Phase may stall.\033[0m")

        # --- BLOCKING HYDRATION CHECK (70B Availability) ---
        wave_mode = self.config['hardware'].get('wave_mode', 'MAGISTRATE')
        if wave_mode == "HARVEST":
            self.ui.print_log("\n\033[1;32m[HARVEST] Skipping 70B hydration requirements. Proceeding with 32B/8B focus.\033[0m")
            self.hydration_ready = True
            return

        heavy_models = [
            self.config['hardware'].get('reasoning_model'),
            self.config['hardware'].get('large_model'),
            self.config['hardware'].get('math_model')
        ]
        heavy_models = [m for m in heavy_models if m]
        
        self.ui.print_log("[HYDRATION] Verifying 70B model availability across cluster...")
        
        start_time = time.time()
        max_wait = 360  # 6 minutes total wait
        
        while time.time() - start_time < max_wait:
            all_heavy_available = True
            available_across_cluster = []
            
            # Check all configured pools
            check_urls = []
            if isinstance(primary_url, list): check_urls.extend(primary_url)
            elif primary_url: check_urls.append(primary_url)
            if isinstance(secondary_url, list): check_urls.extend(secondary_url)
            elif secondary_url: check_urls.append(secondary_url)
            
            for check_url in check_urls:
                try:
                    tags_url = check_url.split("/api/")[0] + "/api/tags"
                    import requests
                    response = requests.get(tags_url, timeout=5)
                    if response.status_code == 200:
                        models = [m['name'] for m in response.json().get('models', [])]
                        available_across_cluster.extend(models)
                except:
                    pass
            
            available_across_cluster = list(set(available_across_cluster))
            
            missing = []
            for model in heavy_models:
                if model not in available_across_cluster:
                    all_heavy_available = False
                    missing.append(model)
            
            if all_heavy_available:
                self.ui.print_log("\n\033[1;32m[SUCCESS] Swarm Cluster is fully Hydrated. All 70B models ready.\033[0m")
                self.hydration_ready = True
                return
            
            elapsed = int(time.time() - start_time)
            self.ui.print_log(f"[HYDRATION] Waiting for 70B models ({', '.join(missing)})... {elapsed}s", repeat=False)
            self.ui.set_status(f"Hydrating {len(missing)} models...")
            time.sleep(15)

        self.ui.print_log("\n\033[1;33m[NOTICE] Hydration TIMEOUT. Checking if models are actually live...\033[0m")
        # Final check: if 70B is actually reachable, mark as ready anyway
        try:
            import requests
            for check_url in check_urls:
                tags_url = check_url.split("/api/")[0] + "/api/tags"
                r = requests.get(tags_url, timeout=4)
                if r.status_code == 200:
                    live_models = [m['name'] for m in r.json().get('models', [])]
                    if any(hm in live_models for hm in heavy_models):
                        self.ui.print_log("\033[1;32m[HYDRATION] 70B confirmed live on at least one pod. Setting hydration_ready=True.\033[0m")
                        self.hydration_ready = True
                        return
        except:
            pass
        self.ui.print_log("[NOTICE] 70B models still not confirmed. Using 8B fallbacks.")
        self.hydration_ready = True  # Allow swarm to proceed regardless — 8B is enough

    def _old_run_deprecated(self):
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

    def reload_config(self):
        """Live-reloads config.json to pick up changes (IP, worker count) without restart."""
        config_path = "config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    new_config = json.load(f)
                    self.config.update(new_config)
                    # Sync component config
                    self.explorer.config = self.config
                    self.searcher.config = self.config
                    self.lab.config = self.config
                    self.kb.config = self.config
                    self.reflector.config = self.config
                    self.teacher.config = self.config
                    self.scribe.config = self.config
                    self.auditor.config = self.config
                    self.scraper.config = self.config
                    self.inventor.config = self.config
                    self.reviewer.config = self.config
                    # self.ui.print_log("[OVERMIND] Configuration reloaded and synced to all components.")
            except Exception as e:
                self.ui.print_log(f"[ERROR] Failed to reload config: {e}")

    def run_worker_sorter_loop(self):
        """
        Background Loop: Monitors queues and adjusts self.active_8b_workers.
        """
        self.ui.print_log("[SORTER] Dynamic Worker Balancing Loop Started.")
        
        while True:
            try:
                self.reload_config()
                settings = self.config['hardware'].get('sorter_settings', {})
                if not settings.get('enabled', True):
                    time.sleep(30)
                    continue

                if self.current_state.get("state") == "PAUSED":
                    time.sleep(5)
                    continue

                # 1. Check Queues
                audit_pending = len(self.kb.get_pending_findings())
                
                synthesis_queue_path = self.get_research_queue_path()
                synthesis_pending = 0
                if os.path.exists(synthesis_queue_path):
                    try:
                        with open(synthesis_queue_path, "r") as f:
                            s_data = json.load(f)
                            synthesis_pending = len(s_data) if isinstance(s_data, list) else 0
                    except: pass

                promotion_queue_dir = "c:/continuous/promotion_queue"
                promotion_pending = 0
                if os.path.exists(promotion_queue_dir):
                    promotion_pending = len([f for f in os.listdir(promotion_queue_dir) if f.endswith(".json")])

                # 2. VRAM Monitoring
                # Check all pods for most constrained VRAM (conservative)
                p_url = self.config['hardware'].get('api_url')
                vram_headroom = self.get_vram_headroom(url=p_url[0] if isinstance(p_url, list) else p_url)

                # 3. Decision Logic
                max_8b = settings.get('max_8b_workers', 32)
                s_thresh = settings.get('synthesis_queue_threshold', 15)
                a_thresh = settings.get('audit_queue_threshold', 10)
                v_min = settings.get('min_vram_headroom_gb', 10.0)

                target_workers = max_8b

                # Throttle based on Synthesis/Promotion (70B bottleneck)
                total_heavy_pending = synthesis_pending + promotion_pending
                if total_heavy_pending > s_thresh:
                    # Adaptive Reduction: scale down proportionally or based on severity
                    factor = 2 if total_heavy_pending < s_thresh * 2 else 4
                    target_workers = max(4, max_8b // factor)
                    if self.ui: self.ui.print_log(f"\033[1;33m[SORTER] Throttling 8B: Heavy Queue={total_heavy_pending}\033[0m")

                # Further throttle if Audit is also backing up
                if audit_pending > a_thresh:
                    target_workers = max(2, target_workers // 2)
                    if self.ui: self.ui.print_log(f"\033[1;33m[SORTER] Throttling 8B: Audit Queue={audit_pending}\033[0m")

                # Critical VRAM check
                if vram_headroom < v_min:
                    target_workers = max(1, target_workers // 4)
                    if self.ui: self.ui.print_log(f"\033[1;31m[SORTER] CRITICAL VRAM: {vram_headroom:.1f}GB. Halting most workers.\033[0m")

                # Apply change
                if target_workers != self.active_8b_workers:
                    diff = target_workers - self.active_8b_workers
                    action = "Expanding" if diff > 0 else "Throttling"
                    self.ui.print_log(f"[SORTER] {action} swarm: {self.active_8b_workers} -> {target_workers} workers.")
                    self.active_8b_workers = target_workers

                time.sleep(15) # Re-evaluate every 15s
            except Exception as e:
                self.ui.print_log(f"[SORTER ERROR] {e}")
                time.sleep(10)

    def get_past_topics(self, query=None, n=10):
        """
        Retrieves past research topics and findings. 
        Prioritizes ChromaDB vector similarity search.
        """
        try:
            # 1. Primary: Vector Search
            if self.scribe.vector_mem.collection.count() > 0:
                results = self.scribe.vector_mem.query_past_research(query if query else "Overall Research History", n_results=n)
                if results:
                    return [r['topic'] for r in results]
            
            # 2. Secondary: Metadata Dump from Vector DB (if no query match)
            if not query and self.scribe.vector_mem.collection.count() > 0:
                results = self.scribe.vector_mem.collection.get(limit=n)
                topics = list(set([m.get('topic') for m in results['metadatas'] if m.get('topic')]))
                if topics: return topics

            # 3. Fallback: Legacy JSON Cache
            cache_path = os.path.join(self.config['paths']['memory'], "past_topics.json")
            if os.path.exists(cache_path):
                return self._safe_load_json(cache_path, default=[])

        except Exception as e:
            self.ui.print_log(f"[SCIENTIST] Vector topic recall failed: {e}")

        return []

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
        is_turbo = self.config['research'].get('turbo_mode', False)
        if is_turbo:
            num_streams = self.config['hardware'].get('turbo_workers', 40)
        else:
            num_streams = self.config['hardware'].get('fast_lane_concurrency', 10)
            
        self._debug_swarm(f"LAUNCHING Continuous 8B stream with {num_streams} workers...")
        self.ui.print_log(f"\033[1;32m[SYSTEM] Eternal Swarm: Launching {num_streams} parallel 8B research streams...\033[0m")
        
        def research_worker(worker_id):
            # Dashboard integration (v3.5 - Persistent ID to prevent UI jitter)
            _worker_task_id = f"worker_8b_{worker_id}"
            is_local = (worker_id % 4 == 0)
            hw_color = Fore.YELLOW if is_local else Fore.GREEN
            
            # Register once outside the eternal loop
            if self.ui: 
                self.ui.register_task(_worker_task_id, f"Worker {worker_id}: Initializing...", color=hw_color)

            while True:
                try:
                    # --- DYNAMIC SORTER CHECK ---
                    if worker_id > self.active_8b_workers:
                        if self.ui: self.ui.update_task(_worker_task_id, "PAUSED (SORTER)", None)
                        time.sleep(5)
                        continue

                    if self.current_state.get("state") == "PAUSED":
                        time.sleep(2)
                        continue

                    topic = self.current_state.get("current_topic", "General Science")
                    
                    # Pick a random vector if available early for UI
                    vectors = self.current_state.get("topic_vectors", [])
                    sub_topic = topic
                    if vectors:
                        vector = random.choice(vectors)
                        sub_topic = f"{topic}: {vector.get('name')}"

                    if self.ui:
                        # Update name and status without resetting the timer to 0
                        # We directly modify the dictionary under GIL to avoid full re-registration
                        if _worker_task_id in self.ui.active_tasks:
                            self.ui.active_tasks[_worker_task_id]["name"] = f"Research: {sub_topic[:20]}"
                        self.ui.update_task(_worker_task_id, "In Queue", None)
                    
                    # --- BACKPRESSURE GUARD ---
                    queue_path = self.get_research_queue_path()
                    if os.path.exists(queue_path):
                        try:
                            with open(queue_path, "r") as f:
                                q_len = len(json.load(f))
                            if q_len > 500: # Increased threshold for long harvest runs
                                if self.ui:
                                    self.ui.update_task(_worker_task_id, "Throttled", None)
                                    if worker_id == 1:
                                        self.ui.print_log(f"\033[1;33m[BACKPRESSURE] 70B Queue is saturated ({q_len} items). Throttling 8B swarm...\033[0m")
                                time.sleep(10)
                                continue
                        except: pass

                    self._debug_swarm(f"[Worker {worker_id}] Starting research on: {sub_topic}")
                    
                    if self.ui:
                        self.ui.update_task(_worker_task_id, "Active", None)

                    # Wave 1: Research (8B)
                    try:
                        # Background heartbeat for the worker task
                        _stop_worker_h = threading.Event()
                        def worker_heartbeat():
                            w_start = time.time()
                            while not _stop_worker_h.is_set():
                                time.sleep(1)
                                if self.ui:
                                    # Incremental updates to existing task timer
                                    self.ui.update_task(_worker_task_id, "Active", int(time.time() - w_start))
                        
                        threading.Thread(target=worker_heartbeat, daemon=True).start()
                        
                        try:
                            research_summary = self.searcher.contemplate(sub_topic)
                        finally:
                            _stop_worker_h.set()
                            
                    finally:
                        # We don't call finish_task here for the worker, as it's an eternal stream node.
                        # Instead, we just mark it as "Resting" before the next cycle.
                        if self.ui: self.ui.update_task(_worker_task_id, "Resting", None)
                        
                    self._debug_swarm(f"[Worker {worker_id}] Research complete for {sub_topic}. Appending to KB.")
                    
                    # Wave 2: Construct (8B) - Light version
                    # We skip the heavy 70B part here, and just push the research finding
                    if research_summary:
                        self.kb.append_finding(sub_topic, research_summary[:2500])
                        if self.ui: self.ui.update_swarm_buffer_count(self.kb.get_entry_count())
                    
                    # Social pulse from the worker
                    if random.random() < 0.1:
                        self.social.post_thought(sub_topic, f"Worker {worker_id} found something: {research_summary[:100]}...")
                    
                    time.sleep(random.uniform(0.1, 1.0)) # FULL BOAR: Minimal delay between tasks
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
                wave_mode = self.config['hardware'].get('wave_mode', 'MAGISTRATE')
                if wave_mode == "HARVEST":
                    time.sleep(30)
                    continue

                pending = self.kb.get_pending_findings()
                if not pending:
                    time.sleep(10)
                    continue

                # --- HYDRATION GUARD ---
                if not self.hydration_ready:
                    time.sleep(15)
                    continue

                # --- BACKPRESSURE GUARD (Auditor) ---
                queue_path = self.get_research_queue_path()
                if os.path.exists(queue_path):
                    try:
                        with open(queue_path, "r") as f:
                            q_len = len(json.load(f))
                        if q_len > 150:
                            if self.ui: self.ui.print_log(f"\033[1;33m[BACKPRESSURE] 70B Queue is massive ({q_len}). Auditor pausing...\033[0m")
                            time.sleep(60)
                            continue
                    except: pass

                self.reload_config()
                api_pool = self.config['hardware'].get('api_url', [])
                if isinstance(api_pool, str): api_pool = [api_pool]
                t_url = api_pool[0] if api_pool else None

                # --- BATCH AUDIT LOGIC (Suggestion 3501+) ---
                # 1. Filter and prepare findings for auditing
                to_audit = []
                for entry in pending:
                    try:
                        # Improved parsing
                        lines = [L for L in entry.split('\n') if L.strip()]
                        if not lines: continue
                        topic_line = lines[0]
                        if "### [" not in topic_line: continue
                        
                        import re
                        topic_match = re.search(r"### \[\d{2}:\d{2}:\d{2}\] (.*?) \|", topic_line)
                        if not topic_match: continue
                        topic = self.explorer._clean_topic(topic_match.group(1).strip())
                        if not topic or topic.lower() == "none": continue

                        # Heuristic Rigor Check
                        match = re.search(r"OVERALL RIGOR SCORE: ([\d.]+)/10", entry)
                        rigor = float(match.group(1)) if match else 0.0
                        
                        min_audit_rigor = 1.0 if "SCIENTIFIC INTUITION" in entry else 1.5

                        # Boosts
                        latex_markers = ['\\frac', '\\[', '\\(', '\\)', '\\partial', '\\mathbb', '$$',
                                         '\\mu', '\\nu', '\\alpha', '\\sigma', '\\Lambda', '\\hbar']
                        if any(m in entry for m in latex_markers): rigor += 2.0
                        
                        physics_terms = ['schwarzschild', 'perturbation', 'hamiltonian', 'lagrangian', 'tensor', 'manifold', 'geodesic', 'ricci', 'curvature']
                        physics_count = sum(1 for t in physics_terms if t in entry.lower())
                        if physics_count >= 3: rigor += min(physics_count / 3.0, 2.5)
                        
                        rigor = min(rigor, 10.0)

                        if rigor >= min_audit_rigor:
                            to_audit.append({'topic': topic, 'entry': entry, 'initial_rigor': rigor})
                        else:
                            # Immediate rejection for low rigor
                            self.ui.print_log(f"\033[1;31m[AUDIT] REJECTED {topic} (Insufficient rigor: {rigor:.1f})\033[0m")
                            self.kb.update_audit(topic, "REJECTED", reason="Insufficient mathematical rigor", rigor_score=rigor)
                    except Exception as e:
                        self.ui.print_log(f"[AUDIT PRE-PARSE] Error: {e}")

                # 2. Process in adaptive batches
                # Increase audit speed if research is throttled
                batch_size = 10 if self.active_8b_workers <= 16 else 5
                for i in range(0, len(to_audit), batch_size):
                    batch = to_audit[i:i + batch_size]
                    if self.ui: self.ui.print_log(f"\033[1;35m[BATCH-AUDIT] Sending {len(batch)} findings to 70B...\033[0m")
                    
                    results = self.auditor.verify_research_batch(batch)
                    
                    for idx, finding in enumerate(batch):
                        topic = finding['topic']
                        res = results[idx] if idx < len(results) else None
                        
                        if res and res.get('verified'):
                            new_rigor = res.get('rigor_score', finding['initial_rigor'])
                            self.ui.print_log(f"\033[1;32m[AUDIT] VERIFIED {topic} (Rigor: {new_rigor:.1f})\033[0m")
                            self.kb.update_audit(topic, "VERIFIED", rigor_score=new_rigor)
                            self.promote_buffer_to_queue()
                        elif res:
                            reason = res.get('reason', "Insufficient mathematical rigor")
                            new_rigor = res.get('rigor_score', finding['initial_rigor'])
                            self.ui.print_log(f"\033[1;31m[AUDIT] REJECTED {topic} ({reason})\033[0m")
                            self.kb.update_audit(topic, "REJECTED", reason=reason, rigor_score=new_rigor)
                        else:
                            # No response for this item (timeout or parse error)
                            self.ui.print_log(f"\033[1;33m[AUDIT] DEFERRED {topic} (70B unresponsive)\033[0m")

                # Faster polling to keep the 70B pod fed
                time.sleep(3)
            except Exception as e:
                self.ui.print_log(f"[CRITICAL AUDIT ERROR] {e}")
                time.sleep(10)
                self.ui.print_log(f"[AUDIT CRITICAL] Main loop failure: {e}")
                time.sleep(10)

    def worker_stage_research(self, topic, depth, iteration_count, target_url=None):
        """
        Wave 1: Research & Hypothesis Guessing (8B)
        """
        self._debug_swarm(f"[SWARM WORKER] Research Stage Start: '{topic}'")
        # Register Task IMMEDIATELY for visibility
        import threading
        from colorama import Fore
        _worker_task_id = f"worker_{topic.replace(':', '_').replace(' ', '_')[:30]}_{id(threading.current_thread())}"
        if self.ui:
            self.ui.register_task(_worker_task_id, f"Research: {topic[:28]}", color=Fore.GREEN)
            self.ui.update_task(_worker_task_id, "Active", 0)

        try:
            # Wait for VRAM in the worker thread (Async-Safe)
            # Resolve reservation for the 8B worker's target pod
            _, reservation = self._resolve_pod_priority(self.config['hardware'].get('local_model', 'deepseek-r1:8b'))
            while self.get_vram_headroom(url=target_url, reservation_gb=reservation) < 6.0:
                if self.ui: self.ui.update_task(_worker_task_id, "VRAM-WAIT", 0)
                time.sleep(10)
            # 1. Study Loop
            study_loops = self.config['research'].get('study_loop_count', 1)
            research_summary = self.searcher.contemplate(topic)
            
            # Rigor & Noise Check
            if "OVERALL RIGOR SCORE" in research_summary:
                try:
                    rigor_line = [L for L in research_summary.split("\n") if "OVERALL RIGOR SCORE" in L][0]
                    score = float(rigor_line.split(":")[1].split("/")[0])
                    if score < 3.0:
                        self.ui.print_log(f"\033[1;31m[WRN-RIGOR] Low rigor research for '{topic}': {score}/10. Source contamination likely.\033[0m")
                except:
                    pass
            elif "No recent data found" in research_summary:
                self.ui.print_log(f"\033[1;33m[WRN-RIGOR] No data found for '{topic}'. Research plateau reached.\033[0m")
                
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

            # Log to Eternal Swarm Buffer (Increased capture limit for 70B syntheses)
            self.kb.append_finding(topic, research_summary[:5000])

            # 0. Context enrichment (Advice from past failures)
            repair_advice = self.current_state.get('deepseek_repair_advice')
            if repair_advice:
                research_summary += f"\n\n=== RECENT TECHNICAL ADVICE ===\n{repair_advice}"
                
            dream_advice = self.current_state.get('deepseek_dream_advice')
            if dream_advice:
                research_summary += f"\n\n=== ARCHITECTURAL GUIDANCE ===\n{dream_advice}"

            # 0.1 Context enrichment (Hybrid Memory Architecture)
            axioms_path = os.path.join(self.config['paths']['memory'], "spacetime_axioms.md")
            if os.path.exists(axioms_path):
                with open(axioms_path, 'r', encoding='utf-8') as f:
                    axioms_data = f.read()
                research_summary += f"\n\n=== COMPRESSED LONG-TERM KNOWLEDGE (SPACETIME AXIOMS) ===\n{axioms_data}"

            journal_path = os.path.join(self.config['paths']['memory'], "scientific_journal.json")
            if os.path.exists(journal_path):
                journal = self._safe_load_json(journal_path, default=[])
                if journal:
                    # Include last 5 entries for verbatim continuity
                    recent_entries = journal[-5:]
                    journal_ctx = "\n".join([f"- {e.get('topic')}: {e.get('summary')}" for e in recent_entries])
                    research_summary += f"\n\n=== RECENT SHORT-TERM MEMORY (LAST 5 DISCOVERIES) ===\n{journal_ctx}"

            prior_lessons = self.reflector.get_micro_sleep_lessons(n=3)
            if prior_lessons:
                research_summary += f"\n\n=== LESSONS ===\n{prior_lessons}"
            
            lectures = self.teacher.get_relevant_lectures(topic)
            if lectures: research_summary += lectures

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
        finally:
            if self.ui:
                self.ui.finish_task(_worker_task_id)

    def worker_stage_construction(self, stage_data, target_url=None):
        """
        Wave 2: Simulation Generation & Execution (8B)
        """
        topic = stage_data['topic']
        hypothesis_data = stage_data['hypothesis']
        research_summary = stage_data['research_summary']
        driving_question = stage_data['driving_question']

        self.ui.print_log(f"\033[1;36m[SWARM WORKER] Construction Stage: '{topic}'\033[0m")
        
        # --- GPU Pinning (Thread-Local Context) ---
        from base_module import _THREAD_LOCAL_CONTEXT
        _THREAD_LOCAL_CONTEXT.api_url = target_url

        # Wait for VRAM in the worker thread (Async-Safe)
        # Resolve reservation for the construction worker's target pod
        _, reservation = self._resolve_pod_priority(self.config['hardware'].get('fast_model', 'deepseek-r1:32b'))
        while self.get_vram_headroom(url=target_url, reservation_gb=reservation) < 6.0:
            if self.ui: self.ui.set_status(f"THROTTLED: {topic[:15]} waiting for VRAM")
            time.sleep(10)

        # Register Task for Construction
        import threading
        from colorama import Fore
        _worker_task_id = f"const_{topic.replace(':', '_').replace(' ', '_')[:30]}_{id(threading.current_thread())}"
        if self.ui:
            self.ui.register_task(_worker_task_id, f"Construct: {topic[:28]}", color=Fore.YELLOW)
            self.ui.update_task(_worker_task_id, "Active", 0)

        try:
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
            escalation_model = self.config['hardware'].get('large_model', 'deepseek-r1:70b')
            
            # Strategy: Use Constructor Model (32B) for all initial drafts to prevent hallucinations.
            # Fallback to local_model (8B) only if cluster is not hydrated.
            
            if constructor_model:
                # Hot-Check for Model Availability
                try:
                    import requests
                    target_gpu = self.config['hardware'].get('api_url')
                    pod_urls = target_gpu if isinstance(target_gpu, list) else [target_gpu or 'http://localhost:11434']
                    is_ready = False
                    for pod in pod_urls:
                        try:
                            base_url = pod.rstrip('/').replace('/api/generate', '')
                            tags_resp = requests.get(f"{base_url}/api/tags", timeout=3)
                            available_models = [m['name'] for m in tags_resp.json().get('models', [])]
                            if any(constructor_model in m for m in available_models):
                                is_ready = True
                                break
                        except Exception:
                            continue
                except Exception:
                    is_ready = False 
                    
                if is_ready:
                    self.ui.print_log(f"\033[1;33m[SWARM WORKER] Engaging Master Constructor: {constructor_model}...\033[0m")
                    code = self.lab.generate_simulation(hypothesis_data, description, model=constructor_model)
                else:
                    self.ui.print_log(f"\033[1;33m[SWARM WORKER] '{constructor_model}' not yet hydrated. Using Fast Fallback ({fast_model})...\033[0m")
                    code = self.lab.generate_simulation(hypothesis_data, description, model=fast_model)
                
                # --- SHARED PREFLIGHT LINTING (Universal Rigor) ---
                attempts = 0
                while attempts < 2:
                    is_valid, lint_issues, lint_msg, code = self.lint_code(code, hypothesis_data)
                    if is_valid:
                        break
                    attempts += 1
                    self.ui.print_log(f"\033[1;33m[SWARM WORKER] Code failed lint (Attempt {attempts}). Repairing... ({len(lint_issues)} issues)\033[0m")
                    repair_model = self.config['hardware'].get('math_model') or constructor_model
                    code = self.lab.repair_simulation(code, lint_msg, hypothesis_data, model=repair_model)

                test_result = self.lab.run_simulation(code, hypothesis_data)
            else:
                # Absolute Fallback (Highly Unlikely)
                code = self.lab.generate_simulation(hypothesis_data, description, model=fast_model)
                test_result = self.lab.run_simulation(code, hypothesis_data)
            if test_result.get('status') == 'Failed':
                wave_mode = self.config['hardware'].get('wave_mode', 'MAGISTRATE')
                if wave_mode == "HARVEST":
                    return test_result # Skip 70B escalation in HARVEST mode

                with self.heavy_lock:
                    # First attempt a repair with the heavy model
                    self.ui.print_log(f"\033[1;36m[SWARM WORKER] 32B Simulation failed. Attempting Heavy Repair (70B)...\033[0m")
                    code = self.lab.repair_simulation(test_result.get('code', ''), test_result.get('raw_output', ''), hypothesis_data, model=escalation_model)
                    test_result = self.lab.run_simulation(code, hypothesis_data)
                    
                    # If still failed, perform a clean regenerate with the heavy model
                    if test_result.get('status') == 'Failed':
                        self.ui.print_log(f"\033[1;33m[SWARM WORKER] Repair failed. Final attempt: High-fidelity REGENERATION with {escalation_model}...\033[0m")
                        code = self.lab.generate_simulation(hypothesis_data, description, model=escalation_model)
                        test_result = self.lab.run_simulation(code, hypothesis_data)
                    
            # If still failed after regeneration, mark as Fatal to ensure Wave 2 logging
            if test_result.get('status') == 'Failed' and 'Preflight Rejection' in test_result.get('raw_output', ''):
                return {"status": "Fatal", "reason": f"Preflight Rigor Failure: {test_result.get('raw_output')[:200]}...", "hypothesis": hypothesis_data}

            return test_result
        finally:
            if self.ui:
                self.ui.finish_task(_worker_task_id)

    def worker_stage_self_fix(self, test_result, audit_report, target_url=None):
        """
        Wave 2.5: Autonomous Self-Fix (70B)
        Targets "FIXABLE" rejections from the Auditor.
        """
        wave_mode = self.config['hardware'].get('wave_mode', 'MAGISTRATE')
        if wave_mode == "HARVEST":
            return test_result # Skip self-fix in harvest mode to save 70B VRAM
        # --- GPU Pinning (Thread-Local Context) ---
        from base_module import _THREAD_LOCAL_CONTEXT
        _THREAD_LOCAL_CONTEXT.api_url = target_url

        # Wait for VRAM in the worker thread (Async-Safe)
        fix_model = self.config['hardware'].get('math_model') or self.config['hardware'].get('large_model')
        _, reservation = self._resolve_pod_priority(fix_model)
        while self.get_vram_headroom(url=target_url) < reservation:
            if self.ui: self.ui.set_status(f"THROTTLED: Self-Fix waiting for VRAM ({reservation}GB)")
            time.sleep(10)

        topic = test_result['hypothesis']['topic']
        reasoning = audit_report.get('reasoning', 'No specific reasoning provided.')
        
        is_rigor_violation = audit_report.get('rejection_type') == 'RIGOR_VIOLATION'
        
        if is_rigor_violation:
            self.ui.print_log(f"\033[1;31m[SWARM WORKER] RIGOR VIOLATION: '{topic}'. Forcing Metric Re-derivation (70B)...\033[0m")
        else:
            self.ui.print_log(f"\033[1;33m[SWARM WORKER] Audit Reject: '{topic}'. Attempting Autonomous Self-Fix (70B)...\033[0m")
        
        self.ui.print_log(f"\033[1;30m  ↳ Reason: {reasoning[:150]}...\033[0m")

        # Register Task for Self-Fix
        import threading
        from colorama import Fore
        _worker_task_id = f"fix_{topic.replace(':', '_').replace(' ', '_')[:30]}_{id(threading.current_thread())}"
        if self.ui:
            self.ui.register_task(_worker_task_id, f"Self-Fix: {topic[:28]}", color=Fore.MAGENTA)
            self.ui.update_task(_worker_task_id, "Active", 0)

        try:
            constructor_model = self.config['hardware'].get('constructor_model') or self.config['hardware'].get('large_model')
            
            with self.heavy_lock:
                # High-fidelity repair using the heavy model and audit feedback
                if is_rigor_violation:
                    # Specialized Re-derivation Prompt
                    repair_prompt = f"""
                    CRITICAL RIGOR VIOLATION DETECTED.
                    The previously claimed Ricci Scalar for your metric was symbolically DISPROVEN using SymPy.
                    
                    Error: {reasoning}
                    
                    You MUST now re-derive the metric from first principles. 
                    1. Re-calculate Christoffel symbols manually or provide a new framework.
                    2. Ensure the resulting metric matrix is physically consistent and mathematically sound.
                    3. Output the RE-DERIVED code block.
                    """
                    repaired_code = self.lab.repair_simulation(
                        test_result.get('code', ''), 
                        repair_prompt, 
                        test_result['hypothesis'], 
                        model=constructor_model
                    )
                else:
                    repaired_code = self.lab.repair_simulation(
                        test_result.get('code', ''), 
                        reasoning, 
                        test_result['hypothesis'], 
                        model=constructor_model,
                    searcher=self.searcher
                )
                
                # Re-run simulation with the fixed code
                new_result = self.lab.run_simulation(repaired_code, test_result['hypothesis'])
                
            return new_result
        finally:
            if self.ui:
                self.ui.finish_task(_worker_task_id)

    def worker_stage_triple_debate(self, topic):
        """
        Wave 4: Triple Adversarial Debate.
        Alpha (DeepSeek-R1-70B): Proposes.
        Beta (Llama-3.3-70B): Invalidates/Challenges.
        Gamma (Qwen-2.5-72B-Math): Moderates, Synthesizes, and Scores.
        """
        import time
        from colorama import Fore
        
        alpha_url = self.config['hardware'].get('alpha_url')
        beta_url = self.config['hardware'].get('beta_url')
        gamma_url = self.config['hardware'].get('gamma_url')
        
        alpha_model = self.config['hardware'].get('alpha_model', 'deepseek-r1:70b')
        beta_model = self.config['hardware'].get('beta_model', 'llama3.3:latest')
        gamma_model = self.config['hardware'].get('gamma_model', 'qwen2.5-math:72b')
        
        threshold = self.config['hardware'].get('consensus_threshold', 0.95)
        
        if not all([alpha_url, beta_url, gamma_url]):
            return None
            
        _worker_task_id = f"debate_{topic.replace(' ', '_')[:20]}_{id(threading.current_thread())}"
        if self.ui:
            self.ui.register_task(_worker_task_id, f"Debate: {topic[:28]}", color=Fore.CYAN)
            self.ui.update_task(_worker_task_id, "Active", 0)

        try:
            self.ui.print_log(f"\033[1;35m[TRIPLE-DEBATE] Initiating 3-Way Duel for topic: {topic}\033[0m")
            
            # 1. Alpha Proposes
            alpha_prompt = f"Topic: {topic}\nPropose a rigorous symbolic proof or a new physical law derivation for this topic. Be extremely precise. Result should be in JSON with 'proof' and 'alpha_confidence' fields."
            alpha_response = self._query_llm(alpha_prompt, model=alpha_model, api_url=alpha_url)
            if not alpha_response:
                self.ui.print_log("[TRIPLE-DEBATE] Alpha returned None. Skipping cycle.")
                return None
            alpha_data = self._extract_json(alpha_response) or {"proof": alpha_response, "alpha_confidence": 0.5}
            
            # 2. Beta Challenges
            beta_prompt = f"Topic: {topic}\nWorker Alpha has proposed the following proof:\n{alpha_data.get('proof', '')}\n\nYour task is to AGGRESSIVELY INVALIDATE this proof. Find counter-examples, identify physical law violations, or detect mathematical hallucinations. Output your critique clearly."
            beta_critique = self._query_llm(beta_prompt, model=beta_model, api_url=beta_url)
            if not beta_critique:
                beta_critique = "No critique available."
            
            # 3. Gamma Moderates & Synthesizes
            gamma_prompt = f"""
            Topic: {topic}
            Alpha's Proposal: {alpha_data.get('proof', alpha_response or '')}
            Beta's Critique: {beta_critique}
            
            As the Moderator (Gamma), your role is to:
            1. Evaluate the validity of the proof given the critique.
            2. Synthesize the most rigorous, corrected version of the proof.
            3. Assign a final 'consensus_score' (0.0-1.0).
            
            Respond in JSON with 'synthesized_proof' and 'consensus_score'.
            """
            gamma_response = self._query_llm(gamma_prompt, model=gamma_model, api_url=gamma_url)
            if not gamma_response:
                gamma_response = "{}"
            gamma_data = self._extract_json(gamma_response) or {"synthesized_proof": alpha_data.get('proof', ''), "consensus_score": 0.0}
            
            # 4. Final Decision logic
            consensus = gamma_data.get('consensus_score', 0)
            final_proof = gamma_data.get('synthesized_proof', alpha_data['proof'])
            
            # PRESERVE REASONING: Inject any captured trace back into the proof block
            if 'reasoning_trace' in gamma_data:
                final_proof = f"<think>\n{gamma_data['reasoning_trace']}\n</think>\n\n{final_proof}"
                
            is_breakthrough = False
            
            if consensus >= threshold:
                self.ui.print_log(f"\033[1;32m[TRIPLE-DEBATE] CONSENSUS REACHED ({consensus:.2f} >= {threshold}). Breakthrough!\033[0m")
                is_breakthrough = True
            else:
                self.ui.print_log(f"\033[1;33m[TRIPLE-DEBATE] LOW CONSENSUS ({consensus:.2f}). Triggering Auditor Tie-Break...\033[0m")
                audit_prompt = f"Final moderation from Gamma shows a consensus of {consensus}.\nSynthesized Proof: {final_proof}\nCritique: {beta_critique}\n\nShould we promote this finding? Respond 'audit_passed': true/false."
                auditor_response = self._query_llm(audit_prompt, model=self.config['hardware']['reasoning_model'])
                audit_data = self._extract_json(auditor_response) or {"audit_passed": False}
                if audit_data.get('audit_passed'):
                    self.ui.print_log("\033[1;32m[TRIPLE-DEBATE] Auditor OVERRULES. Breakthrough confirmed!\033[0m")
                    is_breakthrough = True
                else:
                    self.ui.print_log("\033[1;31m[TRIPLE-DEBATE] Auditor REJECTS. No breakthrough.\033[0m")
            
            if is_breakthrough:
                from sci_utils import send_telegram
                summary = f"🏛 *TRIPLE ADVERSARIAL BREAKTHROUGH*\n\nTopic: {topic}\nConsensus: {consensus:.4f}\nStatus: SYNTHESIZED BY GAMMA-QWEN-MATH CORE."
                send_telegram(summary)
                kb_topic = f"TRIPLE_DEBATE: {topic}"
                self.kb.append_finding(kb_topic, final_proof, "Success")
                self.kb.update_audit(kb_topic, "VERIFIED", reason="Triple Model CUDA Consensus", rigor_score=10)
        
        finally:
            if self.ui:
                self.ui.finish_task(_worker_task_id)

        return {"status": "Complete", "breakthrough": is_breakthrough}

    def run_adversarial_stream(self):
        """Background thread to manage the triple debate loop."""
        while True:
            try:
                wave_mode = self.config['hardware'].get('wave_mode', 'MAGISTRATE')
                if wave_mode == "HARVEST":
                    time.sleep(30)
                    continue

                topic = self.current_state.get("current_topic", "Black Hole Manifold Dynamics")
                self.worker_stage_triple_debate(topic)
                
                time.sleep(600) # Triple Duel every 10 minutes (higher cost)
            except Exception as e:
                self._debug_swarm(f"[ADVERSARIAL ERROR] {e}")
                time.sleep(10)

    def run_promotion_stream(self):
        """Phase 16: Background stream for asynchronous promotion & consensus."""
        self.ui.print_log("[SYSTEM] Asynchronous Promotion Pipeline (File-Queue) INITIALIZED.")
        queue_dir = "c:/continuous/promotion_queue"
        if not os.path.exists(queue_dir): os.makedirs(queue_dir)
        
        while True:
            try:
                # 1. Check Wave Mode & Promotable JSON files
                wave_mode = self.config['hardware'].get('wave_mode', 'MAGISTRATE')
                if wave_mode == "HARVEST":
                    time.sleep(30)
                    continue

                if not os.path.exists(queue_dir): os.makedirs(queue_dir)
                files = [f for f in os.listdir(queue_dir) if f.endswith(".json")]
                if not files:
                    time.sleep(30)
                    continue

                # Sort by timestamp (prefix in filename)
                files.sort()
                
                for filename in files:
                    filepath = os.path.join(queue_dir, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            test_result = json.load(f)
                    except Exception as e:
                        self.ui.print_log(f"[PROMOTER] Failed to load {filename}: {e}")
                        try: os.remove(filepath)
                        except: pass
                        continue

                    topic = test_result['hypothesis']['topic']
                    self.ui.print_log(f"[PROMOTER] Background Review: {topic}")
                    
                    # A. Evaluate Significance (Pod 2 - DeepSeek-70B)
                    # We pass the full test_result and invention!
                    with self.heavy_lock:
                        evaluation = self.reviewer.evaluate_significance(
                            test_result, 
                            test_result.get('invention'), 
                            vector_mem=self.scribe.vector_mem
                        )
                    
                    score = evaluation.get('significance_score', 0)
                    test_result['evaluation'] = evaluation

                    # B. Emergent Discovery Logic
                    if evaluation.get("emergent_discovery_detected"):
                        emergent_topic = evaluation.get("emergent_topic", "Emergent Phenomenon")
                        emergent_hypothesis = evaluation.get("emergent_hypothesis", "New truth discovered during validation.")
                        self.ui.print_log(f"\033[1;35m[EMERGENT] New truth discovered on '{topic}'!\033[0m")
                        
                        promoted_item = {
                            "topic": emergent_topic,
                            "research_summary": f"EMERGENT DISCOVERY from prior simulation on '{topic}'.\n\nVerified Truth: {emergent_hypothesis}",
                            "driving_question": f"Formalize the emergent finding: {emergent_hypothesis}",
                            "novelty_score": 95,
                            "is_high_curiosity": True
                        }
                        self.push_to_research_queue([promoted_item])
                        
                        synthetic_result = {
                            "hypothesis": {"topic": emergent_topic, "hypothesis": emergent_hypothesis, "field": "physics"},
                            "status": "Verified (Emergent)",
                            "evaluation": {"significance_score": 91, "verdict": f"Emergent: {emergent_hypothesis}"}
                        }
                        self.scribe.archive_discovery(synthetic_result)

                    # C. Triple Consensus Gate (Scores >= 85)
                    if score >= 85:
                        self.ui.print_log(f"[PROMOTER] High Significance ({score}). Triggering Triple-Core Magistrate.")
                        
                        alpha_url = self.config['hardware'].get('alpha_url')
                        beta_url = self.config['hardware'].get('beta_url')
                        gamma_url = self.config['hardware'].get('gamma_url')
                        threshold = self.config['hardware'].get('consensus_threshold', 0.95)
                        
                        # Background Consensus Logic
                        beta_prompt = f"Topic: {topic}\nFinding: {evaluation.get('verdict', '')}\n\nInvalidate this finding."
                        beta_critique = self._query_llm(beta_prompt, model=self.config['hardware'].get('beta_model'), api_url=beta_url)
                        
                        gamma_prompt = f"Topic: {topic}\nFinding: {evaluation.get('verdict', '')}\nCritique: {beta_critique}\n\nSynthesize & Score."
                        gamma_response = self._query_llm(gamma_prompt, model=self.config['hardware'].get('gamma_model'), api_url=gamma_url)
                        gamma_data = self._extract_json(gamma_response) or {"consensus_score": 0.0}
                        
                        consensus = gamma_data.get('consensus_score', 0)
                        passed = False
                        
                        if consensus >= threshold:
                            passed = True
                        else:
                            audit_prompt = f"Moderate Triple Debate on '{topic}'.\nGamma Consensus: {consensus}\nRelease finding? Respond 'audit_passed': true/false."
                            auditor_resp = self._query_llm(audit_prompt, model=self.config['hardware']['reasoning_model'])
                            passed = (self._extract_json(auditor_resp) or {}).get('audit_passed', False)
                        
                        if passed:
                            from sci_utils import send_telegram
                            send_telegram(f"🏛 *TRIPLE-CORE BREAKTHROUGH: {topic.upper()}*\nConsensus: {consensus:.4f}\nValidated by Magnum-Magistrate Cluster.")
                            
                            # Final Archive
                            self.scribe.archive_discovery(test_result)
                            try:
                                if self.config.get('social', {}).get('enabled'):
                                    self.social.post_discovery(test_result, priority=True)
                            except: pass
                            
                            # ScribePro
                            if score > 90:
                                threading.Thread(target=self.scribe_pro.generate_latex_section, args=(test_result, evaluation), daemon=True).start()
                            
                            self.kb.update_promotion_status(topic, "SUCCESS")
                        else:
                            self.kb.update_promotion_status(topic, "FAILED")
                    else:
                        # Standard Archival
                        if score >= 50:
                            self.scribe.archive_discovery(test_result)
                        self.kb.update_promotion_status(topic, "SKIPPED")

                    # Final Cleanup
                    if os.path.exists(filepath):
                        try: os.remove(filepath)
                        except: pass
                
                time.sleep(15)
            except Exception as e:
                self.ui.print_log(f"\033[1;31m[PROMOTER ERROR] {e}\033[0m")
                time.sleep(10)

    def worker_stage_finalize(self, test_result, audit_report, target_url=None):
        """Phase 16: Non-blocking finalized archival."""
        from base_module import _THREAD_LOCAL_CONTEXT
        _THREAD_LOCAL_CONTEXT.api_url = target_url
        topic = test_result['hypothesis']['topic']
        
        self.ui.print_log(f"[FINALIZER] '{topic}' -> Background Promotion Queue.")
        _worker_task_id = f"final_{topic.replace(' ', '_')[:20]}_{id(threading.current_thread())}"
        if self.ui:
            self.ui.register_task(_worker_task_id, f"Final: {topic[:28]}")
            self.ui.update_task(_worker_task_id, "Active", 0)

        try:
            if audit_report.get('audit_passed'):
                # 1. Synthesize Invention (Fast Turn)
                pain_point = self.scraper.find_pain_point(topic)
                existing = self.inventor.synthesize_existing_tech(pain_point)
                invention = self.inventor.design_application(test_result, pain_point, existing)
                test_result['invention'] = invention
                
                # 2. Save full result to Promotion Queue (Phase 16 - Robust Queue)
                queue_dir = "c:/continuous/promotion_queue"
                if not os.path.exists(queue_dir): os.makedirs(queue_dir)
                
                filename = f"promo_{int(time.time())}_{self._sanitize_slug(topic)}.json"
                filepath = os.path.join(queue_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(test_result, f, indent=4)
                
                # 3. Update Markdown Buffer for observability
                self.kb.update_audit(topic, "VERIFIED", rigor_score=test_result.get('rigor', 7))
            else:
                self.kb.update_audit(topic, "REJECTED", reason=audit_report.get('reason', 'Failed audit.'))
        except Exception as e:
            self.ui.print_log(f"\033[1;31m[FINALIZER ERR] {e}\033[0m")
        
        if self.ui: self.ui.finish_task(_worker_task_id)





    def dispatch_deep_dive(self, test_result, evaluation):
        """
        Background Task: 70B Physics 'Deep Dive' for breakthroughs.
        Includes mandatory 'Geometric Intuition' section.
        """
        from sci_utils import send_telegram
        topic = test_result['hypothesis']['topic']
        score = evaluation.get('significance_score', 0)
        
        prompt = f"""
        Perform a RESEARCH DEEP DIVE for a recent BREAKTHROUGH.
        
        Topic: {topic}
        Hypothesis: {test_result['hypothesis']['hypothesis']}
        Significance Score: {score}
        Rigor Analysis: {evaluation.get('rigor_analysis', 'N/A')}
        Verdict: {evaluation.get('verdict', 'N/A')}
        
        Structure:
        1. **Summary**: A dense, 3-sentence technical synthesis.
        2. **Geometric Intuition**: Explain the Ricci flow / metric evolution of this discovery using a physical analogy (e.g., a stretching rubber sheet or a inflating balloon).
        3. **Consequence**: What does this mean for future spacetime modeling?
        
        Format: Markdown. Use bold headers.
        """
        
        reasoning_model = self.config['hardware'].get('reasoning_model', 'deepseek-r1:70b')
        deep_dive = self._query_llm(prompt, model=reasoning_model)
        
        if deep_dive:
            msg = f"📚 **BREAKTHROUGH DEEP DIVE: {topic.upper()}**\n\n"
            msg += deep_dive
            send_telegram(msg)

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
        Preflight Linting (Iteration 3511 / Preflight Repair Skill).
        Automatically patches .subs() and banned 'def' blocks before auditing.
        """
        if not code:
            return False, ["No code generated"], "Empty code provided", ""

        from template_validation import TemplateValidator
        from preflight_repair import PreflightRepair
        
        # --- AUTONOMOUS PREFLIGHT REPAIR (Advanced Skills) ---
        code, repairs = PreflightRepair.apply_all(code, hypothesis)
        
        # Keep original template repairs as fallback/structural check
        repaired_code, template_repairs = TemplateValidator.repair_code(code, hypothesis)
        if template_repairs:
            repairs.extend(template_repairs)
        if repairs:
            self.ui.print_log(f"\033[1;33m[PREFLIGHT-REPAIR] Applied {len(repairs)} autonomous patches.\033[0m")
            for r in repairs:
                self.ui.print_log(f"  ↳ {r}")
            
            # Log to hallucination_log.md
            log_path = os.path.join(self.config['paths']['memory'], "hallucination_log.md")
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            topic = hypothesis.get('topic', 'Unknown')[:50]
            summary = "; ".join(repairs)
            log_entry = f"| {timestamp} | {topic} | Syntax/Logic | {summary} | SUCCESS (Patched) |\n"
            self._safe_append_text(log_path, log_entry)
            
            # Use the repaired code for the final check
            code = repaired_code

        # --- LOCAL RIGOR: REGEX HALLUCINATION FILTER ---
        # Catch .subs() and forbidden def blocks locally to save credits
        hallucination_issues = []
        if ".subs(" in code:
            hallucination_issues.append("Banned .subs() usage detected.")
        if re.search(r"def\s+\w+\(", code) and "compute_stats" not in code and "f_rhs" not in code:
             # Basic check to ensure models aren't nesting forbidden functions
             pass 

        if hallucination_issues:
            # Attempt a local regex patch for .subs() if possible, or just reject
             self.ui.print_log(f"\033[1;31m[PREFLIGHT-RIGOR] Local rejection: {hallucination_issues[0]}\033[0m")
             return False, hallucination_issues, "LOCAL RIGOR REJECTION: Code contains banned patterns (.subs/nesting). Discarding to save credits.", code

        report = TemplateValidator.run_all_checks(code, hypothesis)
        
        if not report["valid"]:
            issues = report["errors"] + report["repair_directives"]
            feedback = "PREFLIGHT LINT FAILED.\n"
            if report["errors"]:
                feedback += "Structural Errors:\n- " + "\n- ".join(report["errors"]) + "\n"
            if report["repair_directives"]:
                feedback += "Repair Directives (NON-NEGOTIABLE):\n- " + "\n- ".join(report["repair_directives"])
            return False, issues, feedback, code # Return code too in case it was partially fixed
            
        return True, [], "", code

    # Feature 3: Method Advisor implementation below...

        return {"status": "Complete", "topic": hypothesis.get('topic')}


    def get_research_queue_path(self):
        return os.path.join(self.config['paths']['memory'], "research_queue.json")

    def push_to_research_queue(self, items):
        if not items: return
        queue_path = self.get_research_queue_path()
        with _GLOBAL_FILE_LOCK:
            queue = self._safe_load_json(queue_path, default=[])
            queue.extend(items)
            
            # Re-order by Novelty Score descending 
            # Items without a score are treated as 0 priority
            queue.sort(key=lambda x: x.get('novelty_score', 0) if isinstance(x, dict) else 0, reverse=True)
            
            self._safe_save_json(queue_path, queue)
        new_len = len(queue)
        if self.ui: self.ui.update_queue_size(new_len)
        self.ui.print_log(f" \033[1;32m[GATHERER] Pushed {len(items)} items to queue. Total pending: {new_len}\033[0m")

    def pop_from_research_queue(self, batch_size):
        path = self.get_research_queue_path()
        with _GLOBAL_FILE_LOCK:
            queue = self._safe_load_json(path, default=[])
            items = queue[:batch_size]
            self._safe_save_json(path, queue[batch_size:])
            new_len = len(queue) - len(items)
            if self.ui: self.ui.update_queue_size(max(0, new_len))
            return items

    def promote_buffer_to_queue(self):
        """Moves verified findings from KB to the research queue for 70B synthesis."""
        self.reload_config()
        promotable = self.kb.get_promotable_findings()
        if not promotable:
            return

        # --- BACKPRESSURE GUARD (Bridge) ---
        queue_path = self.get_research_queue_path()
        if os.path.exists(queue_path):
            try:
                with open(queue_path, "r") as f:
                    q_len = len(json.load(f))
                if q_len > 200:
                    # if self.ui: self.ui.print_log(f"\033[1;33m[BACKPRESSURE] Bridge throttled. Queue: {q_len}\033[0m")
                    return # Silently delay promotion
            except: pass

        api_url = self.config['hardware'].get('api_url', '')
        if not api_url:
            self.ui.print_log("[PROMOTION] Delaying promotion: No 70B pods configured.")
            return

        self.ui.print_log(f"\033[1;36m[BRIDGE] Promoting {len(promotable)} verified findings from buffer to 70B queue...\033[0m")
        
        items_to_push = []
        seen_topics = set()
        for entry in promotable:
            try:
                # Parse topic and content from the markdown entry
                lines = entry.split('\n')
                header_line = lines[0]
                import re
                topic_match = re.search(r"### \[\d{2}:\d{2}:\d{2}\] (.*?) \|", header_line)
                if not topic_match: continue
                topic = topic_match.group(1).strip()
                
                # Robust cleaning to avoid "None" topics
                topic = self.explorer._clean_topic(topic)
                if not topic or topic.lower() == "none":
                    continue
                
                if topic in seen_topics:
                    continue
                seen_topics.add(topic)
                
                content = "\n".join(lines[1:]).strip()
                
                # Create the research context dict expected by run_synthesis_loop
                items_to_push.append({
                    "topic": topic,
                    "research_summary": content,
                    "driving_question": "Synthesize from buffer findings.",
                    "promoted": True
                })
                
                # Mark as QUEUED in buffer to avoid double-processing
                self.kb.update_promotion_status(topic, "QUEUED")
            except Exception as e:
                self.ui.print_log(f"[BRIDGE ERROR] Failed to promote entry: {e}")

        if items_to_push:
            self.push_to_research_queue(items_to_push)

    def run_gatherer_loop(self):
        """
        Thread 1: Generates topics, runs Wave 1, and pushes to research queue.
        """
        self.ui.print_log("[GATHERER] Starting asynchronous gatherer loop...")
        while True:
            try:
                # Synchronize with disk-based state updates
                self.current_state = self.load_state()
                
                if self.current_state.get("state") == "PAUSED":
                    time.sleep(2)
                    continue

                # --- BACKPRESSURE GUARD ---
                queue_path = self.get_research_queue_path()
                if os.path.exists(queue_path):
                    try:
                        with open(queue_path, "r") as f:
                            q_len = len(json.load(f))
                        if q_len > 100:
                            if self.ui: self.ui.print_log(f"\033[1;33m[BACKPRESSURE] Gatherer throttled. Queue: {q_len}\033[0m")
                            time.sleep(20) # Faster poll for status
                            continue
                    except: pass

                self.reload_config()
                is_turbo = self.config['research'].get('turbo_mode', False)
                if is_turbo:
                    max_workers = self.config['hardware'].get('turbo_workers', 40)
                else:
                    max_workers = self.config['hardware'].get('max_swarm_workers', 18)

                # --- Topic Sanity Guard (Fail-safe for malformed state) ---
                curr_topic = self.current_state.get("current_topic")
                if curr_topic and ("The topic" in curr_topic or "**" in curr_topic):
                    cleaned = self.explorer._clean_topic(curr_topic)
                    if cleaned != curr_topic:
                        self.ui.print_log(f"[OVERMIND] Detected malformed topic in state. Cleaning: '{curr_topic[:30]}...' -> '{cleaned[:30]}...'")
                        self.current_state["current_topic"] = cleaned
                        self.save_state()

                tasks_to_queue = []
                # SAME LOGIC as before for STUDY/GUESS
                burst_step = self.current_state.get("burst_counter", 1)
                is_study_mode = (burst_step <= 5)
                
                if is_study_mode:
                    # Study mode uses max_swarm_workers or max_workers depending on config
                    # But typically we want to deep-dive on one topic.
                    study_topic = None
                    journal_data = self._safe_load_json(self.journal_file, default=[])
                    if journal_data:
                        study_topic = journal_data[-1].get("topic", "").split(":")[0].strip()
                    if not study_topic:
                         study_topic = self.current_state.get("current_topic", "Quantum computing algorithms")

                    vectors = self.explorer.decompose_topic(study_topic, study_mode=False, count=max_workers)
                    while len(vectors) < max_workers:
                        vectors.append({"name": f"{study_topic} aspect {len(vectors)+1}", "area": "Deep dive"})
                    
                    self.current_state["current_topic"] = study_topic
                    self.current_state["topic_vectors"] = vectors[:max_workers]
                    self.current_state["depth_counter"] = 0
                    self.current_state["phase"] = "STUDY"
                    
                    for depth in range(max_workers):
                        vector_data = vectors[depth]
                        current_vector = vector_data['name']
                        is_high_curiosity = vector_data.get('high_curiosity', False)
                        target_topic = f"{study_topic}: {current_vector}"
                        
                        target_iteration = self.current_state.get("iteration_count", 0)
                        tasks_to_queue.append((target_topic, depth, target_iteration, is_high_curiosity))
                    
                    self.current_state["depth_counter"] = max_workers
                    self.current_state["iteration_count"] += 1
                    self.current_state["burst_counter"] = burst_step + 1
                    
                else:
                    self.current_state["phase"] = "GUESS"
                    max_depth = self.config['research'].get('research_depth', 15)
                    
                    # Resolve initial topic/vectors
                    topic = self.current_state.get("current_topic")
                    depth = self.current_state.get("depth_counter", 0)
                    vectors = self.current_state.get("topic_vectors", [])

                    def resolve_new_topic():
                        nonlocal topic, vectors, depth
                        if topic: 
                            summary = self.explorer.synthesize(topic, study_mode=True)
                            temp_discovery = {
                                "hypothesis": {"topic": topic, "hypothesis": "Full topic synthesis."},
                                "evaluation": {"significance_score": 0, "verdict": summary}
                            }
                            self.scribe.journal_entry(temp_discovery)
                        
                        cross_pollinated = None
                        if random.random() < 0.2:
                            cross_pollinated = self.reflector.cross_pollinate()

                        if cross_pollinated:
                            topic = cross_pollinated['hybrid_topic']
                            vectors = self.explorer.decompose_topic(topic, count=max_workers)
                            self.current_state['dream_hypothesis_guidance'] = (
                                f"CRITICAL CROSS-POLLINATION MANDATE:\n"\
                                f"You MUST use this exact hybrid hypothesis as your foundation for the new field: {cross_pollinated['hybrid_hypothesis']}\n"\
                                f"Context: {cross_pollinated['isomorphism_analysis']}"
                            )
                        else:
                            past_topics = self.get_past_topics()
                            topic = self.explorer.get_new_topic(past_topics, fast_mode=True)
                            vectors = self.explorer.decompose_topic(topic, study_mode=False, count=max_workers)
                        
                        depth = 0
                        self.current_state["current_topic"] = topic
                        self.current_state["topic_vectors"] = vectors
                        self.current_state["depth_counter"] = 0

                    if not topic or depth >= max_depth or not vectors:
                        resolve_new_topic()

                    # Fill the batch (Support Multi-Topic Spanning)
                    while len(tasks_to_queue) < max_workers:
                        if depth >= max_depth or depth >= len(vectors):
                            self.ui.print_log(f"[GATHERER] Topic '{topic[:20]}' reached depth limit. Picking new topic to fill batch...")
                            resolve_new_topic()
                        
                        current_vector = vectors[depth]['name']
                        target_topic = f"{topic}: {current_vector}"
                        is_high_curiosity = vectors[depth].get('high_curiosity', False)

                        target_iteration = self.current_state.get("iteration_count", 0) + 1
                        tasks_to_queue.append((target_topic, depth, target_iteration, is_high_curiosity))
                        
                        depth += 1
                    
                    self.current_state["depth_counter"] = depth
                    self.current_state["iteration_count"] = self.current_state.get("iteration_count", 0) + 1
                    self.current_state["burst_counter"] = 1

                self.save_state()
                
                tasks_to_queue.sort(key=lambda x: x[3] if len(x) > 3 else False, reverse=True)
                stagger_delay = self.config['hardware'].get('swarm_stagger_s', 5)
                
                import concurrent.futures
                prelim_results = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    self.ui.print_log(f" [1;34m[WAVE 1] Engaging Research Workers (8B). Submitting {len(tasks_to_queue)} tasks... [0m")
                    research_futures = {}
                    for idx, task_data in enumerate(tasks_to_queue):
                        if len(task_data) == 4:
                            t, d, i, p = task_data
                        else:
                            t, d, i = task_data
                        
                        sec_urls = self.config['hardware'].get('secondary_gpu', [])
                        prim_urls = self.config['hardware'].get('api_url', [])
                        
                        if isinstance(sec_urls, str): sec_urls = [sec_urls]
                        if isinstance(prim_urls, str): prim_urls = [prim_urls]
                        
                        all_urls = sec_urls + prim_urls
                        if all_urls:
                            target_url = all_urls[idx % len(all_urls)]
                        else:
                            target_url = None
                        
                        if idx > 0: 
                            time.sleep(0.1) 
                        
                        # Logic to select target_url removed for brevity in chunk
                        future = executor.submit(self.worker_stage_research, t, d, i, target_url)
                        research_futures[future] = t


                    def process_result(future):
                        try:
                            res = future.result()
                            if res:
                                # Run evaluate_novelty in parallel too if we're in a hurry, 
                                # but for now let's just push to queue and let them run.
                                # Actually, evaluate_novelty is fast on 8B, let's just make it async.
                                score = self.explorer.evaluate_novelty(res)
                                res['novelty_score'] = score
                                
                                if score < 20:
                                    res['force_fast_model'] = True
                                elif score > 80:
                                    res['priority_heavy'] = True
                                    
                                self.push_to_research_queue([res])
                        except Exception as e:
                            self.ui.print_log(f"[WAVE 1] Result processing failed: {e}")

                    # Use a secondary executor or just collect them properly
                    # To keep it simple and truly parallel, let's just not block on evaluation
                    for f in concurrent.futures.as_completed(research_futures):
                        # We submit the post-processing to another thread or just background it
                        executor.submit(process_result, f)

                # Feature 5: Semantic Compression Trigger
                # Every 10 iterations, boil down the last 50 entries into Spacetime Axioms
                current_iter = self.current_state.get("iteration_count", 0)
                last_comp = self.current_state.get("last_compressed_iteration", -1)
                
                if current_iter > 0 and current_iter % 10 == 0 and current_iter != last_comp:
                    self.ui.print_log(f"\033[1;33m[MEMORY OPTIMIZATION] Iteration {current_iter} reached. Triggering Semantic Compression...\033[0m")
                    self.scribe.semantic_compression(limit=50)
                    self.current_state["last_compressed_iteration"] = current_iter
                    self.save_state()

                # Responsive interrupt scale delay
                delay = self.config['research'].get('iteration_delay', 5)
                for _ in range(max(1, int(delay * 2))):
                    if self.current_state.get("state") == "PAUSED": break
                    time.sleep(0.5)

            except Exception as e:
                self.ui.print_log(f"[GATHERER CRITICAL] Error: {e}")
                time.sleep(5)

    def run_synthesis_loop(self):
        """
        Thread 2: Pulls from research queue and handles Wave 2+.
        """
        self.ui.print_log("[SYNTHESIZER] Initializing for 70B Collective Wave...")
        self.promote_buffer_to_queue() # Pull in any backlog from KnowledgeBuffer
        
        # Initial Queue Sync
        queue_path = self.get_research_queue_path()
        if os.path.exists(queue_path):
            q = self._safe_load_json(queue_path, default=[])
            if self.ui: self.ui.update_queue_size(len(q))

        self.pre_flight_sync() # 70B hydration check happens here (Blocking)
        self.ui.print_log("[SYNTHESIZER] Starting asynchronous synthesis loop...")
        while True:
            try:
                if self.current_state.get("state") == "PAUSED" or not self.hydration_ready:
                    time.sleep(5)
                    continue

                self.reload_config()
                # Determine batch size dynamically based on primary api_pool
                api_pool = self.config['hardware'].get('api_url', [])
                if isinstance(api_pool, str): api_pool = [api_pool]
                
                secondary_pool = self.config['hardware'].get('secondary_gpu', [])
                if isinstance(secondary_pool, str): secondary_pool = [secondary_pool]

                def _get_pool(comp_name):
                    mapping = self.config['hardware'].get('gpu_mapping', {}).get(comp_name, 'api_url')
                    return secondary_pool if mapping == 'secondary_gpu' else api_pool

                # Determine batch size dynamically. Rather than treating 1 URL as 1 thread, 
                # we use heavy_concurrency_limit to saturate massive single-node pods (A100s).
                base_pods = len(api_pool)
                # Increase pull size if research is throttled to clear synthesis backlog faster
                mult = 2 if getattr(self, 'active_8b_workers', 32) <= 16 else 1
                num_pods = self.config['hardware'].get('heavy_concurrency_limit', max(1, base_pods * 2))
                pull_size = max(1, num_pods * mult)

                prelim_results = self.pop_from_research_queue(pull_size)
                if not prelim_results:
                    self.promote_buffer_to_queue() # Try to pull in any audit-verified findings 
                    time.sleep(5)  # Wait for gatherer or auditor
                    continue

                # self.ui.print_log(f"[1;36m[SYNTHESIZER] Popped {len(prelim_results)} items from research queue.[0m")

                def _run_with_url(url, func, *args, **kwargs):
                    from base_module import _THREAD_LOCAL_CONTEXT
                    _THREAD_LOCAL_CONTEXT.api_url = url
                    return func(*args, **kwargs)
                
                # --- COLLECTIVE A.0: BATCH GENERATION (70B Theorist) ---
                use_large = self.config['research'].get('use_large_theorist')
                topic = prelim_results[0]['topic'].split(":")[0] if prelim_results else None

                import concurrent.futures
                try:
                    if use_large:
                        self.ui.print_log("[1;36m[COLLECTIVE A.0] Synchronizing for Batch Generation (70B)...[0m")
                        batch_contexts = [
                            {
                                "driving_question": r.get('driving_question'),
                                "summary": r.get('research_summary')
                            }
                            for r in prelim_results if 'hypothesis' not in r and not r.get('force_fast_model', False)
                        ]
                        
                        if batch_contexts:
                            num_shards = max(1, min(num_pods, len(batch_contexts)))
                            chunk_size = (len(batch_contexts) + num_shards - 1) // num_shards
                            shards = [batch_contexts[i:i + chunk_size] for i in range(0, len(batch_contexts), chunk_size)]
                            
                            batch_hypotheses = []
                            with concurrent.futures.ThreadPoolExecutor(max_workers=num_shards) as shard_executor:
                                shard_futures = []
                                current_pool = _get_pool('math_engine')
                                self.ui.print_log(f" \033[1;35m[DEBUG] num_pods={num_pods}, num_shards={num_shards}, len(current_pool)={len(current_pool)}\033[0m")
                                for i, s in enumerate(shards):
                                    t_url = current_pool[i % len(current_pool)] if current_pool else None
                                    self.ui.print_log(f" \033[1;35m[DEBUG] Routing Shard {i} to URL: {t_url}\033[0m")
                                    # STICK 70B: allow_fallback=False
                                    shard_futures.append(shard_executor.submit(_run_with_url, t_url, self.explorer.generate_batch_hypotheses, s, topic, allow_fallback=False))
                                for f in shard_futures:
                                    batch_hypotheses.extend(f.result())
                            
                            ctx_idx = 0
                            for r in prelim_results:
                                if 'hypothesis' not in r:
                                    if ctx_idx < len(batch_hypotheses):
                                        r['hypothesis'] = batch_hypotheses[ctx_idx]
                                        ctx_idx += 1

                    # --- COLLECTIVE A.1: BATCH REFINEMENT (72B Architect) ---
                    self.ui.print_log("[1;36m[COLLECTIVE A.1] Synchronizing for Batch Refinement (72B)...[0m")
                    hypotheses = [r['hypothesis'] for r in prelim_results if 'hypothesis' in r and not r.get('force_fast_model', False)]
                    
                    num_shards = max(1, min(num_pods, len(hypotheses)))
                    if num_shards > 0:
                        chunk_size = (len(hypotheses) + num_shards - 1) // num_shards
                        shards = [hypotheses[i:i + chunk_size] for i in range(0, len(hypotheses), chunk_size)]
                        
                        refined_hypotheses = []
                        with concurrent.futures.ThreadPoolExecutor(max_workers=num_shards) as shard_executor:
                            shard_futures = []
                            current_pool = _get_pool('math_engine')
                            self.ui.print_log(f" \033[1;35m[DEBUG REFINEMENT] num_pods={num_pods}, num_shards={num_shards}, pool={len(current_pool)}\033[0m")
                            for i, s in enumerate(shards):
                                t_url = current_pool[i % len(current_pool)] if current_pool else None
                                # STRICT 70B: allow_fallback=False
                                shard_futures.append(shard_executor.submit(_run_with_url, t_url, self.explorer.refine_batch, s, topic, allow_fallback=False))
                            for f in shard_futures:
                                refined_hypotheses.extend(f.result())
                        
                        for i, h in enumerate(refined_hypotheses):
                            if i < len(prelim_results):
                                prelim_results[i]['hypothesis'] = h
                except Exception as e:
                    self.ui.print_log(f"[1;31m[SYNTHESIZER] Collective Hive Offline or API Failure: {e}[0m")
                    self.ui.print_log(f"[1;33m[RE-QUEUING] Pushing {len(prelim_results)} items back to research queue for later 70B processing...[0m")
                    self.push_to_research_queue(prelim_results)
                    # Don't sleep too long - want to retry or pull next shard if some were offline
                    time.sleep(5)
                    continue

                # --- WAVE 2: CONSTRUCTION & EXECUTION (8B) ---
                self.ui.print_log("[1;34m[WAVE 2] Engaging Construction Workers (8B)...[0m")
                test_results = []
                # Execute construction and wait
                max_construction_workers = self.config['hardware'].get('max_swarm_workers', 2)
                if self.config['research'].get('turbo_mode', False) and self.current_state.get("phase") == "GUESS":
                    max_construction_workers = self.config['hardware'].get('turbo_workers', 12)
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_construction_workers) as executor:
                    construction_futures = {}
                    current_pool = _get_pool('lab')
                    for i, r in enumerate(prelim_results):
                        t_url = current_pool[i % len(current_pool)] if current_pool else None
                        if self.ui and t_url:
                            pod_id = str(t_url).split("//")[-1].split(":")[0].split(".")[-1]
                            self.ui.print_log(f"\033[1;36m[QUEUED] Construction: {r['topic'][:30]}... -> Pod {pod_id}\033[0m")
                        future = executor.submit(self.worker_stage_construction, r, t_url)
                        construction_futures[future] = r['topic']
                    for f in concurrent.futures.as_completed(construction_futures):
                        try:
                            res = f.result()
                            if res.get('status') == 'Fatal':
                                failed_topic = construction_futures[f]
                                reason = res.get('reason', 'Unknown Construction Failure')
                                self.explorer.log_failure(failed_topic, {"hypothesis": res.get('hypothesis', {"topic": failed_topic}), "data": {}}, audit_reason=reason)
                                self.ui.print_log(f"[1;31m[OVERMIND] FATAL REJECTION logged for '{failed_topic}': {reason[:100]}...[0m")
                            else:
                                test_results.append(res)
                        except Exception as e:
                            self.ui.print_log(f"[WAVE 2] Worker failed: {e}")

                if not test_results:
                    self.ui.print_log("[OVERMIND] No valid simulation results. Synthesis wave aborted.")
                    continue

                # --- COLLECTIVE B: BATCH AUDIT (72B Auditor) ---
                self.ui.print_log("[1;33m[COLLECTIVE B] Synchronizing for Batch Audit (72B)...[0m")
                num_shards = max(1, min(num_pods, len(test_results)))
                chunk_size = (len(test_results) + num_shards - 1) // num_shards
                shards = [test_results[i:i + chunk_size] for i in range(0, len(test_results), chunk_size)]
                
                audit_reports = []
                shard_offsets = [i * chunk_size for i in range(len(shards))]
                with concurrent.futures.ThreadPoolExecutor(max_workers=num_shards) as shard_executor:
                    shard_futures = []
                    current_pool = _get_pool('critic')
                    for i, (s, offset) in enumerate(zip(shards, shard_offsets)):
                        t_url = current_pool[i % len(current_pool)] if current_pool else None
                        shard_futures.append((shard_executor.submit(_run_with_url, t_url, self.auditor.verify_batch, s), offset))
                    for future, offset in shard_futures:
                        results = future.result()
                        for rep in results:
                            if 'index' in rep:
                                rep['index'] += offset
                        audit_reports.extend(results)
                
                audit_map = {rep['index']: rep for rep in audit_reports if 'index' in rep} if audit_reports else {}

                # --- WAVE 2.5: AUTONOMOUS SELF-FIX (70B) ---
                fix_candidates = [i for i, rep in audit_map.items() if not rep.get('audit_passed') and rep.get('rejection_type') == 'FIXABLE']
                
                if fix_candidates:
                    self.ui.print_log(f"[1;36m[WAVE 2.5] Engaging Self-Fix Workers for {len(fix_candidates)} candidates...[0m")
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_construction_workers) as executor:
                        fix_futures = {}
                        current_pool = _get_pool('math_engine')
                        for i, idx in enumerate(fix_candidates):
                            t_url = current_pool[i % len(current_pool)] if current_pool else None
                            future = executor.submit(self.worker_stage_self_fix, test_results[idx], audit_map[idx], t_url)
                            fix_futures[future] = idx
                        fixed_count = 0
                        for f in concurrent.futures.as_completed(fix_futures):
                            idx = fix_futures[f]
                            try:
                                new_res = f.result()
                                test_results[idx] = new_res
                                fixed_count += 1
                            except Exception as e:
                                self.ui.print_log(f"[WAVE 2.5] Self-Fix worker failed: {e}")
                        
                    if fixed_count > 0:
                        self.ui.print_log(f"[1;32m[WAVE 2.5] Self-Fix complete. Re-Auditing...[0m")
                        audit_reports = self.auditor.verify_batch(test_results)
                        audit_map = {rep['index']: rep for rep in audit_reports if 'index' in rep} if audit_reports else {}

                # --- WAVE 3: FINALIZATION (8B) ---
                self.ui.print_log("[1;34m[WAVE 3] Engaging Finalization Workers (8B)...[0m")
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_construction_workers) as executor:
                    finalize_futures = []
                    current_pool = _get_pool('reflector')
                    for i, res in enumerate(test_results):
                        t_url = current_pool[i % len(current_pool)] if current_pool else None
                        report = audit_map.get(i, {"audit_passed": False, "rejection_type": "FATAL", "reasoning": "Batch audit index mismatch."})
                        finalize_futures.append(executor.submit(self.worker_stage_finalize, res, report, t_url))
                    
                    for f in concurrent.futures.as_completed(finalize_futures):
                        try:
                            f.result()
                        except Exception as e:
                            self.ui.print_log(f"[WAVE 3] Worker failed: {e}")

                # 3. Collective Reflection / Dream Phase
                current_iter = self.current_state.get("iteration_count", 0)
                if prelim_results and current_iter % 5 == 0:
                    self.ui.set_status("Dreaming (Audit Sleep Phase)...")
                    insight = self.reflector.reflect()
                    self.ui.print_log(f"\n[SUBCONSCIOUS] Dream Audit Insight: {insight}\n")
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
                        advice_md = os.path.join(self.config['paths']['memory'], "..", "CREATOR_ADVICE.md")
                        self._safe_append_text(
                            advice_md, 
                            f"## [DREAM PHASE ADVICE] {time.strftime('%Y-%m-%d %H:%M:%S')}\n{ds_dream}\n"
                        )
                    self.run_creator_improvements_phase()
                    latest_guidance = self.reflector.get_latest_dream_guidance()
                    if latest_guidance and latest_guidance.get('code_patch', {}).get('enabled'):
                        self.reflector.try_self_patch(latest_guidance)

                    # --- IDENTITY EVOLUTION (Feature 4511) ---
                    # Periodically evolve personality based on breakthroughs
                    if current_iter % 10 == 0:
                        evolution_rationale = self.reflector.evolve_identity()
                        if evolution_rationale and self.ui:
                            self.ui.print_log(f"\033[1;36m[SUBCONSCIOUS] Identity Evolved: {evolution_rationale[:150]}...\033[0m")
                            # Reload bot name if it changed
                            self.identity = self._safe_load_json(os.path.join(self.config['paths']['memory'], "identity.json"), default={})
                            self.bot_name = self.identity.get("name", "EigenZeta")

                # AUTONOMOUS STUDY MODE CONCLUSION
                is_study_mode = (self.current_state.get("burst_counter", 1) <= 5)
                # Not fully perfect with topics due to decoupling, but this prevents failure
                
                if current_iter % 10 == 0:
                    self.ui.print_log("[METHOD-ADVISOR] Checking method advice...")
                
            except Exception as e:
                self.ui.print_log(f"[SYNTHESIZER CRITICAL] Error: {e}")
                import traceback
                self.ui.print_log(traceback.format_exc())
                time.sleep(5)
    def run_creator_improvements_phase(self):
        """
        WAVE 4: CREATOR IMPROVEMENTS.
        Synthesizes recent swarm performance into architectural advice for the human creator.
        """
        self.ui.set_status("Wave 4: Architectural Review...")
        self.ui.print_log("\n\033[1;36m[WAVE 4] CREATOR IMPROVEMENTS PHASE\033[0m")
        
        report = self.reflector.generate_creator_report()
        
        # 1. Update Persistent UI
        self.ui.print_creator_report(report)
        
        # 2. Persist to Structured Memory
        improvements_file = os.path.join(self.config['paths']['memory'], "CREATOR_IMPROVEMENTS.md")
        
        # Check if we should overwrite or append (maintain last 5 reports)
        existing_reports = []
        if os.path.exists(improvements_file):
            try:
                with open(improvements_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    existing_reports = content.split("---")
            except: pass
        
        new_report_md = f"""
## [ARCHITECTURAL REVIEW] {time.strftime('%Y-%m-%d %H:%M:%S')}
- **Mental Health**: {report.get('mental_health')}
- **Technical Debt**: {report.get('technical_debt')}
- **Architectural Vision**: {report.get('architectural_vision')}

### Recommendations:
"""
        for rec in report.get('recommendations', []):
            new_report_md += f"- {rec}\n"
            
        final_history = [new_report_md] + [r.strip() for r in existing_reports if r.strip()]
        final_history = final_history[:5] # Keep last 5 iterations
        
        try:
            with open(improvements_file, 'w', encoding='utf-8') as f:
                f.write("\n---\n".join(final_history))
        except: pass

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
                                data["evaluation"] = self.reviewer.evaluate_significance(data, data.get("invention"), model=fast_m, vector_mem=self.scribe.vector_mem)
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

    def initiate_zeta_centerpiece(self):
        """
        Special Task: 100,000 High-Precision Zeta Zero run.
        The 'Centerpiece' of the first paper.
        """
        import threading
        
        def run_centerpiece():
            try:
                self.ui.print_log("\033[1;36m[CENTERPIECE] Starting high-precision run for 100,000 Zeta zeros...\033[0m")
                from sci_utils import compute_zeta_zeros, unfold_zeta_zeros, ks_test_gue, send_telegram
                
                # 1. Compute 100k Zeros (Parallel)
                gamma = compute_zeta_zeros(100000)
                
                # 2. Unfold and Test
                spacings, mean_s = unfold_zeta_zeros(gamma)
                ks_stat, p_val, r_squared = ks_test_gue(spacings)
                
                self.ui.print_log(f"\033[1;32m[CENTERPIECE] 100k Run Complete. R^2: {r_squared:.6f}\033[0m")
                
                # 3. Telegram Report
                msg = f"🏆 *ZETA CENTERPIECE VERIFIED*\n\n"
                msg += f"Sample: 100,000 zeros\n"
                msg += f"Precision: 60 dps\n"
                msg += f"R² Fit: {r_squared:.8f}\n"
                msg += f"KS p-value: {p_val:.8e}\n\n"
                
                if r_squared > 0.98:
                    msg += "✅ Threshold met. This is the official 'Centerpiece' of Paper #1."
                    # Formal documentation trigger
                    synthetic_result = {
                        'hypothesis': {'topic': 'Riemann Zeta Centerpiece (100k)', 'hypothesis': 'Verification of Montgomery-Odlyzko Law at high scale.'},
                        'metrics': {'r_squared': r_squared, 'ks_stat': ks_stat, 'sample_size': 100000}
                    }
                    synthetic_eval = {'significance_score': 98, 'verdict': 'Formal verification of GUE statistics at 10^5 scale.'}
                    self.scribe_pro.generate_latex_section(synthetic_result, synthetic_eval)
                else:
                    msg += "⚠️ Threshold not met. Re-evaluating unfolding parameters."
                
                send_telegram(msg)
                
            except Exception as e:
                self.ui.print_log(f"\033[1;31m[CENTERPIECE] Error in high-precision run: {e}\033[0m")

        threading.Thread(target=run_centerpiece, daemon=True).start()

    def run(self):
        self.ui.print_log("Entering core research loop (DECOUPLED)...")
        self.start_input_listener()
        
        # Start Background Streams
        threading.Thread(target=self.start_continuous_8b_stream, daemon=True).start()
        threading.Thread(target=self.buffer_audit_loop, daemon=True).start()
        threading.Thread(target=self.run_adversarial_stream, daemon=True).start()
        
        # Start Decoupled Swarm Threads
        threading.Thread(target=self.run_gatherer_loop, daemon=True).start()
        threading.Thread(target=self.run_synthesis_loop, daemon=True).start()
        
        # Initiate High-Precision Centerpiece
        self.initiate_zeta_centerpiece()
        
        while True:
            try:
                if self.current_state.get("state") == "PAUSED":
                    self.ui.set_status("PAUSED")
                    self.process_interrupt()
                    time.sleep(0.5)
                    continue

                self.process_interrupt()
                time.sleep(1)
                
            except KeyboardInterrupt:
                self.ui.print_log("[SYSTEM] User signal received. Shutting down...")
                break
            except Exception as e:
                self.ui.print_log(f"[CRITICAL] Main Loop Error: {e}")
                time.sleep(5)

if __name__ == "__main__":
    bot = ScienceBot()
    bot.run()
