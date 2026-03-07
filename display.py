import sys
import time
import threading
import os
from colorama import init, Fore, Style, Cursor

# Initialize colorama
init(autoreset=True)

def enable_windows_vt100():
    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            # Force UTF-8 encoding for stdout
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass

class Display:
    def __init__(self):
        enable_windows_vt100()
        self.status = "Initializing..."
        self.stop_spinner = False
        self.lock = threading.Lock()
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.input_buffer = ""
        self.thought_buffer = "" # NEW: Real-time model tokens
        self.active_tasks = {}    # NEW: {task_id: {"name": str, "status": str, "time": int}}
        self.queue_size = 0       # NEW: Track 70B Pending Queue
        self.log_file = "bot_output.log"
        
        # Clear log file on startup
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(f"--- Session Started {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        
        self.last_footer_height = 0 # Track lines used by thoughts
        self.spinner_thread = threading.Thread(target=self._animate_spinner, daemon=True)
        self.spinner_thread.start()

    def _get_width(self):
        try:
            return os.get_terminal_size().columns
        except:
            return 80

    def _animate_spinner(self):
        idx = 0
        from colorama import Fore, Style
        while not self.stop_spinner:
            with self.lock:
                width = self._get_width()
                char = self.spinner_chars[idx % len(self.spinner_chars)]
                
                # --- DYNAMIC MULTI-TASK DASHBOARD (Suggestion 3523) ---
                import textwrap
                
                # 1. Prepare Queue Lines
                q_lines = []
                
                # Count totals for hardware summary (Suggestion 3512 / User Request)
                local_count = sum(1 for t in self.active_tasks.values() if t.get('color') == Fore.YELLOW)
                pod_count = sum(1 for t in self.active_tasks.values() if t.get('color') == Fore.GREEN)
                total_active = len(self.active_tasks)
                
                summary = f"{Style.BRIGHT}{Fore.CYAN}[SWARM] {total_active} WORKERS ACTIVE | {Fore.YELLOW}{local_count} LOCAL {Fore.GREEN}{pod_count} POD | {Fore.MAGENTA}70B QUEUE: {self.queue_size}{Style.RESET_ALL}"
                q_lines.append(summary)

                # Intelligent Sort: Thinking tasks first, then by duration (longest first)
                # Limit increased from 6 to 14 for "Full Boar" visibility
                sorted_tasks = sorted(
                    self.active_tasks.items(), 
                    key=lambda x: (x[1]['status'] == "Thinking", x[1]['time']), 
                    reverse=True
                )[:14]

                for tid, tdata in sorted_tasks:
                    s_color = tdata.get('color', Fore.WHITE) if tdata['status'] != "Queued" else Fore.CYAN
                    q_lines.append(f"{s_color}[{tdata['status'].upper():<8}] {Fore.WHITE}{tdata['name'][:30]:<30} {Style.DIM}... {tdata['time']}s{Style.RESET_ALL}")

                # 2. Prepare Thought Lines (Rolling window of 3)
                content = self.thought_buffer.strip()
                if content:
                    thought_limit = max(10, width - 12)
                    wrapped = textwrap.wrap(content, thought_limit)
                    t_lines = wrapped[-3:]
                else:
                    t_lines = []
                
                # Move cursor UP by the total height of the last footer
                if self.last_footer_height > 0:
                    sys.stdout.write(f"\r\033[{self.last_footer_height}A")
                else:
                    sys.stdout.write("\r")
                
                # Clear all old dashboard lines below
                sys.stdout.write("\033[J")
                
                # Draw Queue Section
                for line in q_lines:
                    sys.stdout.write(line + "\n")
                
                # Draw Thought Section
                if content:
                    sys.stdout.write(Fore.YELLOW + "THOUGHTS: " + Style.RESET_ALL + "\n")
                    for line in t_lines:
                        sys.stdout.write(Fore.GREEN + f"  {line}" + Style.RESET_ALL + "\n")
                
                # Draw Spinner + Status + Input (Bottom Line)
                prefix = f"{Fore.CYAN}{char} [{self.status[:15]}] {Style.RESET_ALL}> "
                prefix_visible_len = 1 + 1 + len(self.status[:15]) + 2 + 2
                
                max_input_len = width - prefix_visible_len - 5
                display_input = self.input_buffer
                if len(display_input) > max_input_len:
                    display_input = "..." + display_input[-(max_input_len-3):]
                
                sys.stdout.write(prefix + display_input)
                sys.stdout.flush()
                
                self.last_footer_height = len(q_lines) + (len(t_lines) + 1 if content else 0)
            
            idx += 1
            time.sleep(0.12)

    def update_input_buffer(self, buffer):
        with self.lock:
            self.input_buffer = buffer

    def set_status(self, text):
        with self.lock:
            self.status = text

    def update_queue_size(self, size):
        with self.lock:
            self.queue_size = size

    def append_thought(self, text):
        with self.lock:
            # Only strip specific harmful ANSI, let color pass if needed 
            # (though we strip all for the dashboard to keep it clean)
            import re
            clean_text = re.sub(r'\x1b\[[0-9;]*[mGJK]', '', text)
            self.thought_buffer += clean_text
            # Limit buffer size to prevent memory creep
            if len(self.thought_buffer) > 1000:
                self.thought_buffer = self.thought_buffer[-1000:]

    def clear_thought_buffer(self):
        with self.lock:
            self.thought_buffer = ""

    def register_task(self, task_id, model_name, color=None):
        with self.lock:
            self.active_tasks[task_id] = {"name": model_name, "status": "Queued", "time": 0, "color": color or Fore.WHITE}

    def update_task(self, task_id, status, elapsed):
        with self.lock:
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["status"] = status
                self.active_tasks[task_id]["time"] = elapsed

    def finish_task(self, task_id):
        with self.lock:
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

    def print_log(self, message, continuous=False):
        with self.lock:
            # Get current thread name (e.g., Thread-1, MainThread)
            t_name = threading.current_thread().name
            if t_name == "MainThread":
                t_prefix = ""
            else:
                # Shorten "ThreadPoolExecutor-0_1" to "T-1"
                t_prefix = f"\033[1;30m[{t_name.split('_')[-1]}]\033[0m " if '_' in t_name else f"\033[1;30m[{t_name}]\033[0m "

            if not continuous:
                # Move cursor UP by the number of reasoning lines currently shown
                if self.last_footer_height > 0:
                    sys.stdout.write(f"\r\033[{self.last_footer_height}A")
                else:
                    sys.stdout.write("\r")
                
                # Clear everything from that point to the bottom (wipes thoughts + spinner)
                sys.stdout.write("\033[J")
                
                # Print the persistent log line
                sys.stdout.write(f"{t_prefix}{message.strip()}\n")
                
                # Reset footer height so the spinner thread starts fresh at the new bottom
                self.last_footer_height = 0
            else:
                # Typewriter effect: handled by append_thought in the new dashboard
                pass
            
            sys.stdout.flush()
            
            # Persistent Logging
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    content = message if continuous else f"[{time.strftime('%H:%M:%S')}] {message.strip()}\n"
                    f.write(content)
            except: pass

    def print_discovery(self, test_result):
        topic = test_result['hypothesis']['topic']
        hyp = test_result['hypothesis']['hypothesis']
        
        width = min(self._get_width(), 65)
        border = "═" * (width - 2)
        
        card = f"\n\033[1;32m╔{border}╗\n"
        card += f"║ \033[1;37mDISCOVERY: {topic.upper():<{width-14}}\033[1;32m ║\n"
        card += f"╠{"═" * (width - 2)}╣\n"
        card += f"║ \033[0;37mHypothesis: {hyp[:width-16] + '...' if len(hyp) > width-16 else hyp:<{width-15}}\033[1;32m ║\n"
        card += f"║ \033[0;32mStatus: VERIFIED\033[1;32m {" " * (width-20)} ║\n"
        card += f"╚{border}╝\033[0m"
        
        self.print_log(card)

    def print_breakthrough(self, verdict):
        width = min(self._get_width(), 65)
        border = "★" * width
        
        alert = f"\n\033[1;33m{border}\n"
        alert += f" ★ MAJOR BREAKTHROUGH: {verdict[:width-22]:<{width-21}} ★\n"
        alert += f"{border}\033[0m"
        
        self.print_log(alert)

    def print_study_conclusion(self, topic, summary):
        width = min(self._get_width(), 70)
        border = "≡" * (width - 2)
        
        card = f"\n\033[1;35m╔{border}╗\n"
        card += f"║ \033[1;37mSTUDY CONCLUSION: {topic.upper():<{width-20}}\033[1;35m ║\n"
        card += f"╠{"═" * (width - 2)}╣\033[0;35m\n"
        
        # Word wrap the summary
        import textwrap
        wrapped = textwrap.wrap(summary, width - 4)
        for line in wrapped:
            card += f"║ \033[0;37m{line:<{width-4}}\033[1;35m ║\n"
            
        card += f"╚{border}╝\033[0m"
        self.print_log(card)

    def print_creator_report(self, report):
        """Renders the WAVE 4: ARCHITECTURAL REVIEW block."""
        width = min(self._get_width(), 75)
        border = "═" * (width - 2)
        
        health_colors = {
            "Healthy": Fore.GREEN,
            "Stagnant": Fore.YELLOW,
            "Fragmented": Fore.RED
        }
        h_color = health_colors.get(report.get('mental_health'), Fore.WHITE)

        card = f"\n{Fore.CYAN}╔{border}╗\n"
        card += f"║ {Fore.WHITE}WAVE 4: ARCHITECTURAL REVIEW{' ':<{width-32}}{Fore.CYAN} ║\n"
        card += f"╠{'═' * (width - 2)}╣\n"
        card += f"║ {Fore.WHITE}System Health: {h_color}{report.get('mental_health', 'Unknown'):<{width-17}}{Fore.CYAN} ║\n"
        card += f"║ {Fore.WHITE}Technical Debt: {Fore.YELLOW}{report.get('technical_debt', 'N/A')[:width-19]:<{width-18}}{Fore.CYAN} ║\n"
        card += f"╠{'─' * (width - 2)}╣\n"
        card += f"║ {Fore.WHITE}CREATOR RECOMMENDATIONS:{' ':<{width-26}}{Fore.CYAN} ║\n"
        
        for rec in report.get('recommendations', []):
            card += f"║ {Fore.GREEN}● {Fore.WHITE}{rec[:width-6]:<{width-5}}{Fore.CYAN} ║\n"
            
        card += f"╠{'─' * (width - 2)}╣\n"
        card += f"║ {Fore.WHITE}Vision: {Style.DIM}{report.get('architectural_vision', 'N/A')[:width-11]:<{width-10}}{Style.NORMAL}{Fore.CYAN} ║\n"
        card += f"╚{border}╝{Style.RESET_ALL}\n"
        
        self.print_log(card)

    def print_chat(self, sender, message):
        color = "\033[1;35m" if sender == "USER" else "\033[1;34m"
        formatted = f"{color}[{sender}] \033[0m{message}"
        self.print_log(formatted)

    def shutdown(self):
        self.stop_spinner = True
        with self.lock:
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
