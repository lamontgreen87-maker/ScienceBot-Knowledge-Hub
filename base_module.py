import requests
import json
import time
import threading
import os
from colorama import Fore

_GLOBAL_FILE_LOCK = threading.RLock()
_HEAVY_SEMAPHORE = None 
_SEMAPHORE_LOCK = threading.Lock()
_THREAD_LOCAL_CONTEXT = threading.local()

class BaseModule:
    def __init__(self, config, ui=None):
        self.config = config
        self.ui = ui
        self.ollama_url = self.config['hardware'].get('api_url', "http://localhost:11434/api/generate")
        self.api_key = self.config['hardware'].get('api_key')
        
        # Model Availability Cache (New)
        self._model_cache = set()
        self._cache_expiry = 0
        self._cache_lock = threading.Lock()
        
        # Initialize/Update the global heavy model semaphore
        global _HEAVY_SEMAPHORE
        with _SEMAPHORE_LOCK:
            new_limit = self.config['hardware'].get('heavy_concurrency_limit', 1)
            if _HEAVY_SEMAPHORE is None:
                _HEAVY_SEMAPHORE = threading.Semaphore(new_limit)
                BaseModule._current_limit = new_limit
            elif getattr(BaseModule, '_current_limit', 1) != new_limit:
                # If the limit changed, we need to create a new one. 
                # Note: This won't affect already-waiting threads but will affect new ones.
                _HEAVY_SEMAPHORE = threading.Semaphore(new_limit)
                BaseModule._current_limit = new_limit

    def _safe_load_json(self, file_path, default=[]):
        """Standardized, BOM-aware, and corruption-resilient thread-safe JSON loader."""
        with _GLOBAL_FILE_LOCK:
            if not os.path.exists(file_path):
                return default
                
            try:
                # Try 1: Standard UTF-8 with BOM skipping
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if not content.strip(): return default
                    return json.loads(content.lstrip('\ufeff').lstrip('\ufffe'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                try:
                    # Try 2: UTF-16 (sometimes PowerShell/Windows writes this)
                    with open(file_path, 'r', encoding='utf-16', errors='ignore') as f:
                        content = f.read()
                        if not content.strip(): return default
                        return json.loads(content)
                except:
                    if self.ui: self.ui.print_log(f"[WARNING] JSON Corruption in {os.path.basename(file_path)}. Resetting to default.")
                    return default
            except Exception:
                return default

    def _safe_save_json(self, file_path, data):
        """Thread-safe JSON writer to prevent concurrent corruption during swarm execution."""
        with _GLOBAL_FILE_LOCK:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)

    def _safe_append_text(self, file_path, text):
        """Thread-safe text appendage."""
        with _GLOBAL_FILE_LOCK:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(text + "\n")

    def get_vram_headroom(self, gpu_index=0, url=None):
        """
        Robustly detects available VRAM (in GB) on a specific GPU.
        Uses nvidia-smi with a fallback to Ollama /api/ps telemetry.
        """
        import subprocess
        import re
        
        # Method 1: nvidia-smi (Local)
        try:
            # Common paths for nvidia-smi on Windows
            paths = [
                "nvidia-smi",
                r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"
            ]
            output = None
            for p in paths:
                try:
                    output = subprocess.check_output(
                        [p, "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                        encoding='utf-8', stderr=subprocess.DEVNULL
                    )
                    break
                except: continue
                
            if output:
                lines = output.strip().split('\n')
                if gpu_index < len(lines):
                    return float(lines[gpu_index]) / 1024.0 # Convert MB to GB
        except:
            pass

        # Method 2: Ollama Telemetry (Remote/Local Fallback)
        if url:
            try:
                target = url.replace("/api/generate", "/api/ps")
                if "/api/ps" not in target:
                    target = url.rstrip('/') + "/api/ps"
                
                response = requests.get(target, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    # Calculate total loaded VRAM from /api/ps
                    total_loaded_mb = sum(m.get('size_vram', 0) for m in data.get('models', [])) / 1e6
                    
                    # For integrated graphics (APUs like SER5), system RAM is acting as VRAM
                    # Fallback to config value if psutil isn't available
                    try:
                        import psutil
                        # Total RAM in GB
                        total_capacity_gb = psutil.virtual_memory().total / (1024**3)
                    except:
                        total_capacity_gb = self.config['hardware'].get('vram_capacity_gb', 16)
                        
                    return total_capacity_gb - (total_loaded_mb / 1024.0)
            except:
                pass

        # Default fallback: return a "safe" high value if detection fails entirely
        return 16.0

    def get_system_health(self):
        """Returns a 'Complexity Multiplier' based on available local resources."""
        import psutil
        try:
            cpu_usage = psutil.cpu_percent(interval=None)
            mem_usage = psutil.virtual_memory().percent
            
            # Relaxed heuristics for high-capacity hardware (User Request: "Fast enough")
            if cpu_usage > 95 or mem_usage > 95:
                return 0.7  # Minor downscale at extreme load
            if cpu_usage > 85 or mem_usage > 85:
                return 0.9  # Barely noticeable downscale
            return 1.0     # Full speed
        except:
            return 1.0

    def wait_for_backend(self, url, label="Backend", timeout_mins=20):
        """Patience-based ping to ensure 70B model hydration on RunPod."""
        if not url: return True
        
        start_time = time.time()
        timeout_secs = timeout_mins * 60
        urls_to_check = url if isinstance(url, list) else [url]
        
        if self.ui:
            self.ui.print_log(f"\n\033[1;36m[HYDRATION] Waiting for {label} to hydrate ({len(urls_to_check)} node(s))...\033[0m")
            self.ui.print_log(f"[HYDRATION] 70B models can take 2-5 minutes to load into VRAM.")
        
        while time.time() - start_time < timeout_secs:
            elapsed = int(time.time() - start_time)
            any_up = False

            for check_url in urls_to_check:
                try:
                    target = check_url.replace("/api/generate", "/api/tags")
                    response = requests.get(target, timeout=5)
                    if response.status_code == 200:
                        any_up = True
                    else:
                        if self.ui:
                            self.ui.print_log(f"\033[1;33m[HYDRATION] {label} node {check_url} returned {response.status_code}. ({elapsed}s)\033[0m")
                except Exception as e:
                    if self.ui:
                        self.ui.print_log(f"[HYDRATION] {label} node {check_url} Error: {e} ({elapsed}s)")

            if any_up:
                if self.ui:
                    self.ui.print_log(f"\033[1;32m[HYDRATION] {label} is ONLINE — at least one node ready. Proceeding.\033[0m")
                return True
            
            time.sleep(15) 
            if self.ui:
                self.ui.set_status(f"Hydrating {label}... ({elapsed}s)")
        
        if self.ui:
            self.ui.print_log(f"\033[1;31m[CRITICAL] {label} — no nodes responded after {timeout_mins} minutes.\033[0m")
        return False

    def _query_teacher(self, prompt, timeout=600):
        """
        Queries the external Teacher oracle (Google Gemini / DeepThink).
        Requires 'teacher_api_key' and 'teacher_model' in config.
        """
        api_key = self.config['hardware'].get('teacher_api_key')
        model = self.config['hardware'].get('teacher_model', "gemini-2.0-flash-thinking-exp-01-21")
        
        if not api_key:
            if self.ui: self.ui.print_log("[TEACHER] No API key found. Teaching phase skipped.")
            return None

        # Google Generative Language API endpoint
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 8192,
            }
        }

        if self.ui:
            self.ui.print_log(f"\033[1;36m[TEACHER] Consulted Gemini ({model})...\033[0m")
            self.ui.set_status("Teacher is reflecting...")

        try:
            # Tight 10s connection timeout, long 600s read timeout
            response = requests.post(url, json=payload, timeout=(10, timeout))
            if response.status_code == 200:
                res_json = response.json()
                # Extract text from Gemini response structure
                try:
                    return res_json['candidates'][0]['content']['parts'][0]['text'].strip()
                except (KeyError, IndexError):
                    if self.ui: self.ui.print_log(f"[TEACHER] Unexpected response format: {json.dumps(res_json)[:200]}")
                    return None
            else:
                if self.ui: self.ui.print_log(f"[TEACHER] API Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            if self.ui: self.ui.print_log(f"[TEACHER] Exception: {str(e)}")
            return None

    def _is_model_available(self, model_name, target_url):
        """Checks if a specific model is present on ANY server in the pool (Cached for 60s)."""
        with self._cache_lock:
            if time.time() < self._cache_expiry:
                return model_name in self._model_cache
        
        # Build full list of URLs to check — always check the whole pool for heavy models
        api_pool = self.config['hardware'].get('api_url', [])
        if isinstance(api_pool, str):
            api_pool = [api_pool]
        
        # Include the specific target_url in case it's not in the pool
        check_url = target_url[0] if isinstance(target_url, list) else target_url
        urls_to_check = list({check_url} | set(api_pool)) if check_url else list(api_pool)
        
        # Refresh Cache by polling all URLs
        found_models = set()
        for url in urls_to_check:
            try:
                tags_url = url.replace("/api/generate", "/api/tags")
                response = requests.get(tags_url, timeout=5)
                if response.status_code == 200:
                    for m in response.json().get('models', []):
                        found_models.add(m['name'])
            except:
                pass  # Pod unreachable, try next
        
        with self._cache_lock:
            self._model_cache = found_models
            self._cache_expiry = time.time() + 60
        
        return model_name in found_models

    def _perform_idle_tasks(self):
        """Hook for child classes to perform work while waiting for a heavy model."""
        pass

    def _query_llm(self, prompt, model=None, timeout=600, api_url=None, temperature=None):
        if model is None:
            model = self.config['hardware'].get('local_model', 'deepseek-r1:8b')
            
        # --- RIGOROUS MODEL REDIRECTION (Suggestion 3510) ---
        is_deep_mode = self.config['research'].get('deep_research_mode', False)
        
        # Normalize model name for checking
        m_check = str(model).lower()
        
        # Determine if heavy (70B/72B/etc.)
        is_8b = "8b" in m_check or "llama3.1" in m_check
        is_heavy = any(x in m_check for x in [":70b", ":72b", "math", "llama3.3", "latest"]) 
        if "r1" in m_check and not is_8b:
            is_heavy = True
            
        if not is_deep_mode:
            # If the user wants speed, swap the "Thinking" R1 for a "Fast" standard 70B
            if "70b" in m_check and "r1" in m_check:
                if self.ui: self.ui.print_log(f"\033[1;36m[FAST-70B] SWAP: {model} -> llama3.3:latest for speed!\033[0m")
                model = "llama3.3:latest"
            
            # Universal fallback for other heavy models (scaling down to 8B if deep mode is OFF)
            heavy_keys = ['large_model', 'math_model', 'theorist_model']
            heavy_val_checks = [str(self.config['hardware'].get(k, "")).lower() for k in heavy_keys]
            
            if m_check in heavy_val_checks and "llama3.3" not in m_check:
                fast_fallback = self.config['hardware'].get('fast_model', 'deepseek-r1:8b')
                if self.ui: self.ui.print_log(f"\033[1;33m[FAST-MODE] SWAP: {model} -> {fast_fallback} (Standard Duty Cycle)\033[0m")
                model = fast_fallback
        # 0. RESOLVE API URL (Priority: Argument > Thread-Local Override > Instance Default)
        target_url = api_url
        if not target_url:
            target_url = getattr(_THREAD_LOCAL_CONTEXT, 'api_url', None)
        
        # --- DUAL-CLUSTER ROUTING & MULTI-URL LOAD BALANCING ---
        if not target_url:
            # 1. Instance-level override (set by Agent load balancer)
            if self.ollama_url:
                target_url = self.ollama_url
            else:
                # 2. Hardware mapping from config
                mapping = self.config['hardware'].get('gpu_mapping', {})
                component_key = getattr(self, 'COMPONENT_NAME', self.__class__.__name__.lower())
                gpu_key = mapping.get(component_key)
                if gpu_key:
                    target_url = self.config['hardware'].get(gpu_key)
        
        # 2.1 Handle URL Lists (Load Balancing)
        if isinstance(target_url, list) and target_url:
            import random
            target_url = random.choice(target_url)

        # 3. Default to local for 8B if still no target
        if not target_url and is_8b:
            target_url = self.config['hardware'].get('local_url', 'http://localhost:11434/api/generate')

        # --- MANDATORY CLAMPING FOR 8B (v1.1) ---
        # 8B models MUST stay on local or secondary_gpu (Speed Hub) to avoid 404s on 70B pool
        secondary_gpu = self.config['hardware'].get('secondary_gpu')
        local_url = self.config['hardware'].get('local_url')
        
        flat_allowed = []
        for u in [local_url, secondary_gpu]:
            if isinstance(u, list): flat_allowed.extend(u)
            elif u: flat_allowed.append(u)
            
        if is_8b and (not target_url or target_url not in flat_allowed):
            target_url = secondary_gpu or local_url

        # --- FINAL SAFETY NORMALIZATION ---
        if isinstance(target_url, list) and target_url:
            import random
            target_url = random.choice(target_url)
        elif not target_url:
            target_url = self.config['hardware'].get('local_url', 'http://localhost:11434/api/generate')
            
        # Ensure it's a string, not a list of one string (double safety)
        if isinstance(target_url, list): target_url = target_url[0]
            
        is_sleeper = self.config['hardware'].get('sleeper_mode', False)
        
        # Adaptive Availability Handover (New)
        # If the user wants a heavy model but it's not on the server yet, use fallback
        if not is_sleeper and is_heavy:
            if not self._is_model_available(model, target_url):
                fallback = self.config['hardware'].get('local_model', 'deepseek-r1:8b')
                if self.ui:
                    self.ui.print_log(f"\033[1;33m[ADAPTIVE] {model} not found on pod yet. Using {fallback} temporarily...\033[0m")
                model = fallback
                is_heavy = False
                is_8b = True  # Re-flag so clamping below sends it to local/secondary
                # Immediately reroute away from the remote 70B pod
                target_url = self.config['hardware'].get('secondary_gpu') or self.config['hardware'].get('local_url', 'http://localhost:11434/api/generate')
                if isinstance(target_url, list) and target_url:
                    target_url = target_url[0]
            else:
                if self.ui:
                    # Optional: Subtle log to show we successfully graduated
                    pass

        if is_sleeper:
            # Reroute to local fallback immediately
            target_url = self.config['hardware'].get('local_url', 'http://localhost:11434').rstrip('/') + '/api/generate'
            model = self.config['hardware'].get('fallback_model', 'deepseek-r1:8b')
        
        if self.ui:
            # self.ui.print_log(f"\033[1;30m[NETWORK] Requesting {model} from: {target_url}\033[0m")
            self.ui.clear_thought_buffer()
        
        # Determine temperature
        temp_val = temperature if temperature is not None else 0.5

        # ALWAYS use streaming for heavy models to prevent proxy/network idle timeouts
        use_streaming = is_heavy or "r1" in model.lower()

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": use_streaming,
            "keep_alive": -1,
            "options": {
                "num_predict": 8192, 
                "temperature": temp_val,
                "num_ctx": 4096 if is_sleeper else self.config['hardware'].get('num_ctx', 32768)
            }
        }
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        # Heartbeat and Processing status
        stop_heartbeat = threading.Event()
        is_actually_processing = threading.Event()
        from queue import Queue
        token_buffer = Queue()
        
        h_start = time.time()
        # Use a more specific 'llm_' prefix to avoid colliding with parent 'worker_' tasks on the display
        task_id = f"llm_{id(threading.current_thread())}_{int(time.time()*1000)}"
        if self.ui:
            # Determine color based on hardware location (Suggestion 3512 / User Request)
            # Yellow for local, Green for Pod Server
            is_local = "localhost" in target_url or "127.0.0.1" in target_url
            hw_color = Fore.YELLOW if is_local else Fore.GREEN
            self.ui.register_task(task_id, model, color=hw_color)

        def heartbeat():
            last_log_check = -1
            while not stop_heartbeat.is_set():
                time.sleep(0.5)
                if stop_heartbeat.is_set(): break
                elapsed = int(time.time() - h_start)
                status_label = "Thinking" if is_actually_processing.is_set() else "Queued"
                
                if self.ui:
                    self.ui.set_status(f"{status_label}... ({elapsed}s)")
                    self.ui.update_task(task_id, status_label, elapsed)
                    # heartbeat log removed to silence "timer spam"
        
        h_thread = threading.Thread(target=heartbeat, daemon=True)
        h_thread.start()

        retries = 10 # High retry count for hydration periods
        import random
        for attempt in range(retries):
            try:
                # --- CONCURRENCY CONTROL ---
                # Check if model is "heavy" (70B/72B)
                is_8b_now = "8b" in model.lower() or "llama3.1" in model.lower()
                is_heavy_now = any(x in model.lower() for x in [":70b", ":72b", "math", "llama3.3", "latest"])
                if "r1" in model.lower() and not is_8b_now:
                    is_heavy_now = True
                
                if is_heavy_now:
                    # self.ui.print_log(f"\033[1;30m[CONCURRENCY] Queuing for heavy model {model}...\033[0m")
                    # Non-blocking wait loop for "Waiting Room" actions
                    while not _HEAVY_SEMAPHORE.acquire(blocking=False):
                        self._perform_idle_tasks()
                        time.sleep(5) 
                    
                    try:
                        is_actually_processing.set()
                        # Tight 15s connection timeout, 600s (default) read timeout
                        # Using a tuple (connect_timeout, read_timeout)
                        response = requests.post(target_url, json=payload, headers=headers, timeout=(15, timeout), stream=use_streaming)
                        
                        if response.status_code == 200:
                            if use_streaming:
                                full_response = ""
                                streaming_text = ""
                                for line in response.iter_lines():
                                    if line:
                                        if not is_actually_processing.is_set():
                                            is_actually_processing.set()
                                        chunk = json.loads(line)
                                        # Prefer reasoning_content for the dashboard (Transparency)
                                        reasoning = chunk.get("reasoning_content", "")
                                        token = chunk.get("response", "")
                                        
                                        if self.ui:
                                            # Prioritize R1 "Thinking" tokens
                                            if reasoning:
                                                self.ui.append_thought(reasoning)
                                            elif token and not full_response.strip().startswith("{"):
                                                # Regular tokens from 8B or Non-R1 70B
                                                self.ui.append_thought(token)
                                        
                                        full_response += token
                                        if chunk.get("done"): break
                                
                                if self.ui: 
                                    self.ui.clear_thought_buffer()
                                    self.ui.finish_task(task_id)
                                stop_heartbeat.set()
                                return full_response.strip()
                            else:
                                if self.ui: self.ui.finish_task(task_id)
                                stop_heartbeat.set()
                                return response.json().get('response', '').strip()
                        
                        else:
                            if self.ui: self.ui.finish_task(task_id)
                        
                    finally:
                        is_actually_processing.clear()
                        _HEAVY_SEMAPHORE.release()
                else:
                    # self.ui.print_log(f"\033[1;32m[FAST-LANE] Bypassing queue for {model}...\033[0m")
                    is_actually_processing.set()
                    response = requests.post(target_url, json=payload, headers=headers, timeout=(15, timeout), stream=use_streaming)
                    
                    if response.status_code == 200:
                        if use_streaming:
                            full_response = ""
                            for line in response.iter_lines():
                                if line:
                                    if not is_actually_processing.is_set():
                                        is_actually_processing.set()
                                    chunk = json.loads(line)
                                    reasoning = chunk.get("reasoning_content", "")
                                    token = chunk.get("response", "")
                                    
                                    full_response += token
                                    if self.ui:
                                        if reasoning:
                                            self.ui.append_thought(reasoning)
                                        elif token and not full_response.strip().startswith("{"):
                                            self.ui.append_thought(token)
                                            
                                    if chunk.get("done"): break
                                    
                            if self.ui: 
                                self.ui.clear_thought_buffer()
                                self.ui.finish_task(task_id)
                            stop_heartbeat.set()
                            return full_response.strip()
                        else:
                            if self.ui: self.ui.finish_task(task_id)
                            stop_heartbeat.set()
                            return response.json().get('response', '').strip()
                
                # Handle loading error (Ollama returns 503 or 500 while loading)
                if response.status_code in [500, 503]:
                    if self.ui: self.ui.update_task(task_id, "Hydrating", attempt*30)
                    # Exponential backoff with jitter: 30s, 60s, 90s... capped at 120s
                    wait_time = min(120, (attempt + 1) * 30) + random.uniform(0, 5)
                    if self.ui: self.ui.print_log(f"\033[1;33m[RETRY] GPU is busy/loading. Waiting {int(wait_time)}s... (Attempt {attempt+1})\033[0m")
                    time.sleep(wait_time)
                else:
                    if self.ui: 
                        self.ui.print_log(f"[API ERROR] HTTP {response.status_code}: {response.text}")
                        self.ui.finish_task(task_id)
                    stop_heartbeat.set()
                    return None
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                # Immediate Sleeper Handoff
                if not is_sleeper and "127.0.0.1" not in target_url and "localhost" not in target_url:
                    is_sleeper_enabled = self.config.get("research", {}).get("deep_research_mode", False) or self.config.get("hardware", {}).get("sleeper_mode", False)
                    if is_sleeper_enabled:
                        if self.ui: self.ui.print_log(f"\n\033[1;31m[WARNING] Primary API Offline ({type(e).__name__}). Engaging SLEEPER MODE (Local Fallback).\033[0m")
                        stop_heartbeat.set()
                        if self.ui: self.ui.finish_task(task_id)
                        
                        # Recursive Fallback: Try again using the local sleeper model
                        fallback_model = self.config['hardware'].get('fallback_model', 'deepseek-r1:8b')
                        if self.ui: self.ui.print_log(f"\033[1;33m[SLEEPER] Handoff activated. Resubmitting task to Local {fallback_model}...\033[0m")
                        return self._query_llm(prompt, model, temperature, timeout, max_retries, is_sleeper=True)

                # Default retry logic for hydration or temporary flakes
                if attempt < retries - 1:
                    if self.ui: self.ui.update_task(task_id, "Reconn-Wait", attempt*30)
                    wait_time = min(120, (attempt + 1) * 30) + random.uniform(0, 5)
                    log_msg = f"\033[1;33m[RETRY] Connection issue ({type(e).__name__}). GPU likely hydrating or network flaked. Waiting {int(wait_time)}s... (Attempt {attempt+1})\033[0m"
                    if self.ui: self.ui.print_log(log_msg)
                    time.sleep(wait_time)
                else:
                    if self.ui: self.ui.finish_task(task_id)
                    stop_heartbeat.set()
                    return None
            except Exception as e:
                stop_heartbeat.set()
                if self.ui: self.ui.print_log(f"[API EXCEPTION] {str(e)}")
                return None
        return None

    def consult_reasoner(self, question, context="", label="[DEEPSEEK]"):
        """
        Consults DeepSeek R1 (reasoning_model) for strategic advice.
        
        Unlike _query_llm() which executes tasks, this is for reasoning:
        - Analyzing failure patterns
        - Validating a scientific approach before committing to it
        - Getting a second opinion when the fast model keeps failing
        
        Returns plain-text reasoning response, or None on failure.
        """
        reasoning_model = self.config['hardware'].get('reasoning_model')
        if not reasoning_model:
            return None

        if self.ui:
            self.ui.print_log(f"{label} Consulting DeepSeek R1 for strategic advice...")
            self.ui.set_status(f"Consulting DeepSeek R1...")

        prompt = f"""You are DeepSeek R1, a reasoning expert consulting on a scientific research pipeline.

{f'Context: {context}' if context else ''}

Question: {question}

Think step by step. Be specific and actionable. Focus on what is most likely to cause the observed problem and the single most impactful fix.

Answer:"""

        response = self._query_llm(prompt, model=reasoning_model)

        if response and self.ui:
            # Extract the actual <think> block to show the user it is reasoning
            import re
            think_match = re.search(r'<think>(.*?)</think>', response, re.DOTALL)
            if think_match:
                think_block = think_match.group(1).strip()
                self.ui.print_log(f"\n\033[1;35m[DEEPSEEK REASONING]\n{think_block[:1000]}" + ("...\n[Truncated]" if len(think_block) > 1000 else "") + "\033[0m\n")
            
            # Print the final concise answer
            clean_response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
            self.ui.print_log(f"{label} DeepSeek advice: {clean_response[:200]}...")

        return response


    def consult_math_engine(self, problem, context="", label="[MATH-AI]"):
        """
        Consults the specialized Qwen2.5-Math model for symbolic/numerical rigidity.
        
        Specifically used for:
        - Generating SymPy code from natural language theory
        - Verifying symbolic truths and derivations
        - Calculating precise physical constants or coefficients
        """
        math_model = self.config['hardware'].get('math_model')
        if not math_model:
            # Fallback to general reasoning if math engine isn't defined
            return self.consult_reasoner(problem, context, label="[FALLBACK-MATH]")

        if self.ui:
            self.ui.print_log(f"{label} Consulting specialized Math Engine...")
            self.ui.set_status(f"Consulting Math Engine...")

        prompt = f"""You are a specialized Mathematical & Physics AI (Qwen2.5-Math).
Your goal is to provide rigorous symbolic logic, derivation steps, or SymPy code.

{f'Context: {context}' if context else ''}

Mathematical Problem: {problem}

Provide a precise, step-by-step derivation or implementation. If generating code, ensure it uses standard scientific libraries (numpy, scipy, sympy).

Response:"""

        response = self._query_llm(prompt, model=math_model)
        
        if response and self.ui:
            self.ui.print_log(f"{label} Engine response received ({len(response)} chars).")

        return response


    def _sanitize_slug(self, text, max_length=100):
        """Sanitizes a string for use as a Windows-safe filename."""
        import re
        if not text: return "unknown"
        # Remove invalid Windows characters: \ / : * ? " < > |
        sanitized = re.sub(r'[\\/:*?"<>|]', '', text)
        # Replace spaces and non-alphanumeric with underscores (keep dots/hyphens if safe)
        sanitized = re.sub(r'[^a-zA-Z0-9\.\-_]', '_', sanitized)
        # Collapse multiple underscores
        sanitized = re.sub(r'_{2,}', '_', sanitized)
        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip('_')
        return sanitized.strip('_').lower()

    def _extract_json(self, response, model=None, allow_llm_retry=True):
        """
        Standardized JSON extraction via json_utils, with an LLM retry fallback.
        If the initial parse fails (garbled/truncated response), asks the LLM
        to clean up its own output and tries once more.
        """
        from json_utils import extract_json
        
        # First attempt: standard parsing
        result = extract_json(response)
        if result is not None:
            return result
        
        # Second attempt: ask the LLM to fix its own output
        if allow_llm_retry and response:
            if self.ui:
                self.ui.print_log("\033[1;33m[JSON-RETRY] Initial extraction failed. Asking LLM to clean up response...\033[0m")
            cleanup_prompt = (
                f"The following text is supposed to be valid JSON but is malformed or contains extra text. "
                f"Extract and return ONLY the JSON object with no markdown, no explanation, no code blocks. "
                f"Raw text:\n\n{response[:3000]}"
            )
            retry_response = self._query_llm(cleanup_prompt, model=model)
            if retry_response:
                result = extract_json(retry_response)
                if result is not None:
                    if self.ui:
                        self.ui.print_log("\033[1;32m[JSON-RETRY] Successfully recovered JSON on retry.\033[0m")
                    return result
            if self.ui:
                self.ui.print_log("\033[1;31m[JSON-RETRY] Retry also failed. Dropping response.\033[0m")
        
        return None
