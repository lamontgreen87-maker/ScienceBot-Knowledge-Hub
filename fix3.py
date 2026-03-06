run_method = """
    def run(self):
        self.ui.print_log("Entering core research loop (DECOUPLED)...")
        self.pre_flight_sync()
        self.start_input_listener()
        
        # Start Background Streams
        threading.Thread(target=self.start_continuous_8b_stream, daemon=True).start()
        threading.Thread(target=self.buffer_audit_loop, daemon=True).start()
        
        # Start Decoupled Swarm Threads
        threading.Thread(target=self.run_gatherer_loop, daemon=True).start()
        threading.Thread(target=self.run_synthesis_loop, daemon=True).start()
        
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
"""

with open("c:\\continuous\\agent.py", "r", encoding="utf-8") as f:
    text = f.read()

# remove the broken run method from the bottom
if "def run(self):" in text.split("if __name__ == \\\"__main__\\\":")[-1]:
    parts = text.split("if __name__ == \\\"__main__\\\":")
    top_part = parts[0]
    bottom_part = parts[1]
    
    # We want to put run_method right before if __name__ == "__main__":
    new_text = top_part + run_method + "\n\nif __name__ == \"__main__\":\n    bot = ScienceBot()\n    bot.run()\n"
    
    with open("c:\\continuous\\agent.py", "w", encoding="utf-8") as f:
        f.write(new_text)
    print("Fixed.")
else:
    print("Not found.")
