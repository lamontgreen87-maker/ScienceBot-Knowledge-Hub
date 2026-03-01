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
        self.log_file = "bot_output.log"
        
        # Clear log file on startup
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(f"--- Session Started {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        
        # Simple start
        sys.stdout.write("\n")
        sys.stdout.flush()
        
        self.spinner_thread = threading.Thread(target=self._animate_spinner, daemon=True)
        self.spinner_thread.start()

    def _get_width(self):
        try:
            return os.get_terminal_size().columns
        except:
            return 80

    def _animate_spinner(self):
        idx = 0
        while not self.stop_spinner:
            with self.lock:
                width = self._get_width()
                char = self.spinner_chars[idx % len(self.spinner_chars)]
                
                # Format: [⠋ STATUS] > INPUT
                # We must ensure prefix + input_buffer < width
                prefix = f"{Fore.CYAN}{char} [{self.status[:15]}] {Style.RESET_ALL}> "
                
                # ANSI-aware length calculation for the prefix
                # Fore.CYAN is 5 chars, Style.RESET_ALL is 4 chars. Total 9 hidden chars.
                prefix_visible_len = 1 + 2 + len(self.status[:15]) + 2 + 2 # char + space + [status] + space + > space
                
                max_input_len = width - prefix_visible_len - 5
                display_input = self.input_buffer
                if len(display_input) > max_input_len:
                    display_input = "..." + display_input[-(max_input_len-3):]
                
                line = f"\r{prefix}{display_input}"
                
                # Clear to end and flush
                sys.stdout.write(line + "\033[K")
                sys.stdout.flush()
            
            idx += 1
            time.sleep(0.12)

    def update_input_buffer(self, buffer):
        with self.lock:
            self.input_buffer = buffer

    def set_status(self, text):
        with self.lock:
            self.status = text

    def print_log(self, message):
        with self.lock:
            # Get current thread name (e.g., Thread-1, MainThread)
            t_name = threading.current_thread().name
            if t_name == "MainThread":
                t_prefix = ""
            else:
                # Shorten "ThreadPoolExecutor-0_1" to "T-1"
                t_prefix = f"\033[1;30m[{t_name.split('_')[-1]}]\033[0m " if '_' in t_name else f"\033[1;30m[{t_name}]\033[0m "

            # Clear current line and print log above
            sys.stdout.write("\r\033[K")
            sys.stdout.write(f"{t_prefix}{message.strip()}\n")
            sys.stdout.flush()
            
            # Persistent Logging
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%H:%M:%S')}] {message.strip()}\n")
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

    def print_chat(self, sender, message):
        color = "\033[1;35m" if sender == "USER" else "\033[1;34m"
        formatted = f"{color}[{sender}] \033[0m{message}"
        self.print_log(formatted)

    def shutdown(self):
        self.stop_spinner = True
        with self.lock:
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
