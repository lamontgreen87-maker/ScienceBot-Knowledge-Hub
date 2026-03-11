import requests
import json
import time
import os
import threading
from typing import Dict, Any, List
from colorama import Fore

# --- GLOBAL LOAD BALANCER STATE ---
_RR_INDICES = {} # type: Dict[str, int]
_RR_LOCK = threading.Lock()

class _Context(threading.local):
    def __init__(self):
        self.api_url = None

_THREAD_LOCAL_CONTEXT = _Context()

_GLOBAL_FILE_LOCK = threading.RLock()
_HEAVY_SEMAPHORE = None 
_HEAVY_LIMIT = 0
_HEAVY_WAITING_COUNT = 0
_HEAVY_ACTIVE_COUNT = 0
_SEMAPHORE_LOCK = threading.Lock()

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
        
        global _HEAVY_SEMAPHORE, _HEAVY_LIMIT
        with _SEMAPHORE_LOCK:
            new_limit = self.config['hardware'].get('heavy_concurrency_limit', 1)
            _HEAVY_LIMIT = new_limit
            # Use class-level storage for the semaphore itself to ensure it survives re-instantiation
            if not hasattr(BaseModule, '_shared_heavy_semaphore'):
                BaseModule._shared_heavy_semaphore = threading.Semaphore(new_limit)
                BaseModule._current_limit = new_limit
                _HEAVY_SEMAPHORE = BaseModule._shared_heavy_semaphore
            elif BaseModule._current_limit != new_limit:
                # Only update if the limit actually changed
                BaseModule._shared_heavy_semaphore = threading.Semaphore(new_limit)
                BaseModule._current_limit = new_limit
                _HEAVY_SEMAPHORE = BaseModule._shared_heavy_semaphore
            else:
                _HEAVY_SEMAPHORE = BaseModule._shared_heavy_semaphore
            
            if self.ui:
                self.ui.update_heavy_queue(0, new_limit)

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

    def get_vram_headroom(self, gpu_index=0, url=None, reservation_gb=0):
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
                    free_gb = float(lines[gpu_index]) / 1024.0 # Convert MB to GB
                    return max(0.0, free_gb - reservation_gb)
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
                    # But we only want to do this if the url is localhost.
                    is_local = url and ('localhost' in url or '127.0.0.1' in url)
                    
                    if is_local:
                        try:
                            import psutil
                            # Total RAM in GB
                            total_capacity_gb = psutil.virtual_memory().total / (1024**3)
                        except:
                            total_capacity_gb = self.config['hardware'].get('vram_capacity_gb', 16)
                    else:
                        # For remote pods, use the configured VRAM capacity
                        total_capacity_gb = self.config['hardware'].get('vram_capacity_gb', 90)

                    headroom = total_capacity_gb - (total_loaded_mb / 1024.0)
                    return max(0.0, headroom - reservation_gb)
            except Exception as e:
                pass

        # Default fallback: return a "safe" high value if detection fails entirely
        return float(self.config['hardware'].get('vram_capacity_gb', 90))

    def _resolve_pod_priority(self, model_name):
        """
        New v4.0 Pod Resolution:
        1. Checks if model_name explicitly lives in a pod family (alpha, beta, gamma).
        2. Returns (url_pool, reservation_gb) for the best matching pod.
        """
        m_lower = model_name.lower()
        pods = self.config['hardware'].get('pods', {})
        
        all_candidate_urls = []
        max_reservation = 0
        
        # 1st Priority: Exact Family Match (via config.json pods)
        for pod_name, pod_info in pods.items():
            allowed_models = [m.lower() for m in pod_info.get('models', [])]
            # Check for substring match (e.g. "deepseek-r1:70b" in "deepseek-r1:70b" or vice versa)
            if any(m_lower in am or am in m_lower for am in allowed_models):
                urls = pod_info.get('urls', [])
                if isinstance(urls, str): urls = [urls]
                all_candidate_urls.extend(urls)
                max_reservation = max(max_reservation, pod_info.get('reservation_gb', 0))
        
        if all_candidate_urls:
            # Remove duplicates while preserving order
            seen = set()
            unique_urls = [x for x in all_candidate_urls if not (x in seen or seen.add(x))]
            return unique_urls, max_reservation
        
        # 2nd Priority: Legacy Heuristics
        is_8b = "8b" in m_lower or "llama3.1" in m_lower
        is_32b = "32b" in m_lower
        is_heavy = any(x in m_lower for x in [":70b", ":72b", "math", "llama3.3", "latest"])
        
        primary_url = self.config['hardware'].get('api_url')
        secondary_gpu = self.config['hardware'].get('secondary_gpu')
        
        if is_8b:
            return primary_url, 0
        if is_32b:
            return secondary_gpu or primary_url, 20 # 20GB reservation for 32B
        if is_heavy:
            return secondary_gpu or primary_url, 45 # Default high reservation for heavy
            
        return primary_url, 0

    _residency_cache = {}      # {url: (timestamp, residency_dict)}
    _residency_cache_ttl = 60  # seconds

    def get_model_residency(self, url=None):
        """
        Detects if models on a specific node are partially offloaded to system RAM.
        Returns a dict: {model_name: "VRAM" | "RAM" | "PARTIAL"}
        Cached per-URL for 60 seconds to avoid blocking every LLM call.
        """
        if not url: return {}
        now = time.time()
        cached = BaseModule._residency_cache.get(url)
        if cached and (now - cached[0]) < BaseModule._residency_cache_ttl:
            return cached[1]
        try:
            target = url.replace("/api/generate", "/api/ps")
            response = requests.get(target, timeout=2)
            if response.status_code == 200:
                data = response.json()
                residency = {}
                for m in data.get('models', []):
                    name = m.get('name')
                    size = m.get('size', 0)
                    vram_size = m.get('size_vram', 0)
                    if vram_size >= size:
                        status = "VRAM"
                    elif vram_size == 0:
                        status = "RAM"
                    else:
                        status = f"PARTIAL ({(vram_size/size)*100:.0f}%)"
                    residency[name] = status
                BaseModule._residency_cache[url] = (now, residency)
                return residency
        except:
            pass
        return {}

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
        Falls back to the local heavy model if the API key is missing or fails.
        """
        api_key = self.config['hardware'].get('teacher_api_key')
        model = self.config['hardware'].get('teacher_model', "gemini-2.0-flash-thinking-exp-01-21")
        
        fallback_model = self.config['hardware'].get('theorist_model', 'deepseek-r1:70b')

        if not api_key or api_key == "YOUR_GEMINI_API_KEY":
            if self.ui: self.ui.print_log(f"\033[1;33m[TEACHER] API key missing. Falling back to local heavy model: {fallback_model}\033[0m")
            return self._query_llm(prompt, model=fallback_model, timeout=timeout)

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
                    return self._query_llm(prompt, model=fallback_model, timeout=timeout)
            else:
                if self.ui: self.ui.print_log(f"\033[1;33m[TEACHER] API Error {response.status_code}. Falling back to {fallback_model}...\033[0m")
                return self._query_llm(prompt, model=fallback_model, timeout=timeout)
        except Exception as e:
            if self.ui: self.ui.print_log(f"\033[1;33m[TEACHER] Network Exception. Falling back to {fallback_model}...\033[0m")
            return self._query_llm(prompt, model=fallback_model, timeout=timeout)

    def _is_model_available(self, model_name, target_url):
        """Checks if a specific model is present on the SPECIFIC target server (Cached per-URL for 60s)."""
        if not target_url: return False
        
        # Normalize target_url to a single string
        check_url = target_url[0] if isinstance(target_url, list) else target_url
        if not check_url: return False

        cache_key = f"{check_url}_{model_name}"
        
        with self._cache_lock:
            # We'll use a per-pod cache now
            if not hasattr(self, '_pod_model_cache'):
                self._pod_model_cache = {}
            
            cached_val, expiry = self._pod_model_cache.get(check_url, (set(), 0))
            if time.time() < expiry:
                return model_name in cached_val
        
        # Refresh Cache by polling ONLY the specific URL
        found_models = set()
        try:
            tags_url = check_url.replace("/api/generate", "/api/tags")
            response = requests.get(tags_url, timeout=3) # Faster timeout for availability
            if response.status_code == 200:
                for m in response.json().get('models', []):
                    found_models.add(m['name'])
        except:
            pass
        
        with self._cache_lock:
            self._pod_model_cache[check_url] = (found_models, time.time() + 60)
        
        return model_name in found_models

    def _perform_idle_tasks(self):
        """Hook for child classes to perform work while waiting for a heavy model."""
        pass

    def _query_llm(self, prompt, model=None, temperature=0.7, max_tokens=4000, 
                  is_8b=False, is_sleeper=False, allow_fallback=True, api_url=None, timeout=1800):
        """
        Base query method with retry logic and sleeper mode handoff.
        - allow_fallback: If False, will not engage Sleeper Mode on connection failure.
        """
        if model is None:
            model = self.config['hardware'].get('local_model', 'deepseek-r1:8b')
            
        # --- RIGOROUS MODEL REDIRECTION (Suggestion 3510) ---
        is_deep_mode = self.config['research'].get('deep_research_mode', False)
        
        # Normalize model name for checking
        m_check = str(model).lower()
        
        # Determine if heavy (70B/72B/etc.)
        is_8b = "8b" in m_check or "llama3.1" in m_check
        is_32b = "32b" in m_check
        is_heavy = any(x in m_check for x in [":70b", ":72b", "math", "llama3.3", "latest"]) 
        if "r1" in m_check and not is_8b and not is_32b:
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

        # --- HARVEST MODE GUARD (v3.3 - Absolute 70B Isolation) ---
        wave_mode = self.config['hardware'].get('wave_mode', 'MAGISTRATE')
        if wave_mode == "HARVEST" and is_heavy:
             fast_fallback = self.config['hardware'].get('fast_model', 'deepseek-r1:32b')
             if self.ui: self.ui.print_log(f"\033[1;31m[HARVEST-GUARD] Terminating 70B access. Rerouting {model} -> {fast_fallback}\033[0m")
             model = fast_fallback
             is_heavy = False
             m_check = str(model).lower()
             is_8b = "8b" in m_check or "llama3.1" in m_check
             is_32b = "32b" in m_check

        # 0. RESOLVE API URL (Priority: Argument > Thread-Local Override > Instance Default)
        url_arg = api_url
        url_context = getattr(_THREAD_LOCAL_CONTEXT, 'api_url', None)
        is_pinned = (url_arg is not None) or (url_context is not None)
        
        # --- NEW v4.0 SWARM ROUTING (Pod Family Isolation) ---
        url_pool, reservation_gb = self._resolve_pod_priority(model)
        
        # Override pool if specific mapping is defined for this component
        mapping = self.config['hardware'].get('gpu_mapping', {})
        component_key = getattr(self, 'COMPONENT_NAME', self.__class__.__name__.lower())
        gpu_key = mapping.get(component_key)
        if gpu_key and not is_pinned:
             # If mapping exists, it takes precedence unless we are explicitly pinned
             url_pool = self.config['hardware'].get(gpu_key, url_pool)

        def resolve_url_from_pool(pool):
            if not pool: return None
            if isinstance(pool, list) and pool:
                with _RR_LOCK:
                    key = str(pool)
                    idx = _RR_INDICES.get(key, 0)
                    url = pool[idx % len(pool)]
                    _RR_INDICES[key] = (idx + 1) % len(pool)
                    return url
            return pool

        target_url = url_arg or url_context or resolve_url_from_pool(url_pool)

        # 4. Sleeper Mode Reroute (Initial Phase)
        is_sleeper_now = is_sleeper or self.config['hardware'].get('sleeper_mode', False)
        if is_sleeper_now:
            target_url = self.config['hardware'].get('local_url')
            model = self.config['hardware'].get('fallback_model', 'deepseek-r1:8b')
            reservation_gb = 0

        # 5. Default Fallback
        if not target_url:
            target_url = self.config['hardware'].get('local_url') or 'http://localhost:11434/api/generate'
        
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
                "temperature": temperature if temperature is not None else 0.5,
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
        
        # --- DYNAMIC HEAVY DETECTION (For UI and Fallback) ---
        model_name = str(model).lower()
        is_8b = "8b" in model_name or "llama3.1" in model_name
        is_32b = "32b" in model_name
        is_heavy_now = is_heavy or any(x in model_name for x in [":70b", ":72b", ":32b", "math", "llama3.3", "latest"])
        if "r1" in model_name and not (is_8b or is_32b):
            is_heavy_now = True

        if self.ui:
            # 3-tier color: MAGENTA=70B/heavy, GREEN=32B/pod, YELLOW=local
            is_local = "localhost" in target_url or "127.0.0.1" in target_url
            if is_local:
                hw_color = Fore.YELLOW
            elif is_heavy_now:
                hw_color = Fore.MAGENTA
            else:
                hw_color = Fore.GREEN
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
                # --- DYNAMIC URL RESOLUTION (Fix for [API EXCEPTION] List-URL bug) ---
                if isinstance(target_url, list) or target_url is None:
                    target_url = resolve_url_from_pool(url_pool)
                # Final safety: if it's still a list, just take the first one
                if isinstance(target_url, list): target_url = target_url[0]
                if not target_url: target_url = local_url

                # DISPATCH LOGGING & RESIDENCY CHECK (Inside loop for rotation accuracy)
                if self.ui and attempt == 0:
                    residency = self.get_model_residency(target_url)
                    model_status = residency.get(model, "VRAM")
                    if model_status == "RAM" or "PARTIAL" in model_status:
                        self.ui.print_log(f"\033[1;33m[PERF-ALERT] {model} on {target_url} is on {model_status}. Expect slow inference.\033[0m")
                    if is_heavy: self.ui.clear_thought_buffer()

                # --- CONCURRENCY CONTROL & DISPATCH ---
                # Re-evaluate heaviness if model changed (e.g. from fallback)
                model_name_now = str(model).lower()
                is_8b_check = "8b" in model_name_now or "llama3.1" in model_name_now
                is_32b_check = "32b" in model_name_now
                is_heavy_now = is_heavy or any(x in model_name_now for x in [":70b", ":72b", ":32b", "math", "llama3.3", "latest"])
                if "r1" in model_name_now and not (is_8b_check or is_32b_check):
                    is_heavy_now = True

                if is_heavy_now:
                    global _HEAVY_WAITING_COUNT, _HEAVY_ACTIVE_COUNT
                    with _SEMAPHORE_LOCK:
                        _HEAVY_WAITING_COUNT += 1
                    
                    if self.ui:
                        self.ui.update_heavy_queue(_HEAVY_ACTIVE_COUNT, _HEAVY_LIMIT, _HEAVY_WAITING_COUNT)

                    try:
                        # Non-blocking wait loop for "Waiting Room" actions
                        q_start = time.time()
                        acquired = False
                        while time.time() - q_start < 1800: # 30-minute hard timeout for queuing
                            if _HEAVY_SEMAPHORE.acquire(blocking=False):
                                acquired = True
                                break
                            self._perform_idle_tasks()
                            time.sleep(5) 
                        
                        if not acquired:
                            if self.ui: self.ui.print_log(f"\033[1;31m[TIMEOUT] Aborting request for {model} (Queued > 15m)\033[0m")
                            stop_heartbeat.set()
                            if self.ui: self.ui.finish_task(task_id)
                            return None

                        try:
                            # Update task registration with potentially new model/color if we've rotated
                            if self.ui and attempt > 0:
                                is_local = "localhost" in str(target_url) or "127.0.0.1" in str(target_url)
                                hw_color = Fore.YELLOW if is_local else Fore.MAGENTA
                                # Use update_task instead of register_task to avoid resetting the timer to 0
                                self.ui.update_task(task_id, f"Retry: {model}", elapsed=int(time.time() - h_start))
                                if task_id in self.ui.active_tasks:
                                    self.ui.active_tasks[task_id]["color"] = hw_color 
                            else:
                                pod_id = str(target_url).split("//")[-1].split(":")[0].split(".")[-1]
                                if self.ui: self.ui.print_log(f"\033[1;30m[SEM-ACQUIRE] {model} -> Pod {pod_id}\033[0m")
                            
                            is_actually_processing.set()
                            
                            # Increment active count after acquiring slot
                            with _SEMAPHORE_LOCK:
                                _HEAVY_WAITING_COUNT = max(0, _HEAVY_WAITING_COUNT - 1)
                                _HEAVY_ACTIVE_COUNT += 1
                            if self.ui: self.ui.update_heavy_queue(_HEAVY_ACTIVE_COUNT, _HEAVY_LIMIT, _HEAVY_WAITING_COUNT)

                            response = requests.post(target_url, json=payload, headers=headers, timeout=(15, timeout), stream=use_streaming)
                            
                            if response.status_code == 200:
                                if use_streaming:
                                    full_response = ""
                                    full_reasoning = ""
                                    for line in response.iter_lines():
                                        if line:
                                            if not is_actually_processing.is_set():
                                                is_actually_processing.set()
                                            chunk = json.loads(line)
                                            reasoning = chunk.get("reasoning_content", "")
                                            token = chunk.get("response", "")
                                            
                                            if self.ui:
                                                if reasoning: self.ui.append_thought(reasoning)
                                                elif token and not full_response.strip().startswith("{"):
                                                    self.ui.append_thought(token)
                                            
                                            full_response += token
                                            full_reasoning += reasoning
                                            if chunk.get("done"): break
                                    
                                    if self.ui: self.ui.clear_thought_buffer()
                                    stop_heartbeat.set()
                                    
                                    # PRESERVE REASONING: Prepend <think> tags for Scientist Model training
                                    final_out = full_response.strip()
                                    if full_reasoning.strip():
                                        final_out = f"<think>\n{full_reasoning.strip()}\n</think>\n\n{final_out}"
                                    return final_out
                                else:
                                    stop_heartbeat.set()
                                    raw_data = response.json()
                                    resp = raw_data.get('response', '').strip()
                                    reas = raw_data.get('reasoning_content', '').strip()
                                    if reas:
                                        resp = f"<think>\n{reas}\n</think>\n\n{resp}"
                                    return resp
                        finally:
                            is_actually_processing.clear()
                            _HEAVY_SEMAPHORE.release()
                            with _SEMAPHORE_LOCK:
                                _HEAVY_ACTIVE_COUNT = max(0, _HEAVY_ACTIVE_COUNT - 1)
                            if self.ui: 
                                self.ui.update_heavy_queue(_HEAVY_ACTIVE_COUNT, _HEAVY_LIMIT, _HEAVY_WAITING_COUNT)
                                self.ui.finish_task(task_id)
                                self.ui.print_log(f"\033[1;30m[SEM-RELEASE] {model} freed slot\033[0m")
                    finally:
                        # Ensure waiting count is decremented even if we timed out before acquisition
                        if not acquired:
                            with _SEMAPHORE_LOCK:
                                _HEAVY_WAITING_COUNT = max(0, _HEAVY_WAITING_COUNT - 1)
                            if self.ui:
                                self.ui.update_heavy_queue(_HEAVY_ACTIVE_COUNT, _HEAVY_LIMIT, _HEAVY_WAITING_COUNT)
                else:
                    # FAST-LANE DISPATCH
                    try:
                        if self.ui and attempt > 0:
                            is_local = "localhost" in str(target_url) or "127.0.0.1" in str(target_url)
                            hw_color = Fore.YELLOW if is_local else Fore.GREEN
                            self.ui.register_task(task_id, model, color=hw_color)

                        is_actually_processing.set()
                        response = requests.post(target_url, json=payload, headers=headers, timeout=(15, timeout), stream=use_streaming)
                        
                        if response.status_code == 200:
                            if use_streaming:
                                full_response = ""
                                full_reasoning = ""
                                for line in response.iter_lines():
                                    if line:
                                        if not is_actually_processing.is_set():
                                            is_actually_processing.set()
                                        chunk = json.loads(line)
                                        reasoning = chunk.get("reasoning_content", "")
                                        token = chunk.get("response", "")
                                        full_response += token
                                        full_reasoning += reasoning
                                        if chunk.get("done"): break
                                stop_heartbeat.set()
                                
                                final_out = full_response.strip()
                                if full_reasoning.strip():
                                    final_out = f"<think>\n{full_reasoning.strip()}\n</think>\n\n{final_out}"
                                return final_out
                            else:
                                stop_heartbeat.set()
                                raw_data = response.json()
                                resp = raw_data.get('response', '').strip()
                                reas = raw_data.get('reasoning_content', '').strip()
                                if reas:
                                    resp = f"<think>\n{reas}\n</think>\n\n{resp}"
                                return resp
                    finally:
                        if self.ui: self.ui.finish_task(task_id)

                # Handle loading error (Ollama returns 503 or 500 while loading)
                if response.status_code in [500, 503]:
                    if self.ui: self.ui.update_task(task_id, "Hydrating", attempt*30)
                    # Exponential backoff with jitter: 30s, 60s, 90s... capped at 120s
                    wait_time = min(120, (attempt + 1) * 30) + random.uniform(0, 5)
                    masked_url = target_url.replace('http://', '').split(':')[0] if target_url else "Local"
                    if self.ui: self.ui.print_log(f"\033[1;33m[RETRY] GPU ({masked_url}) is busy/loading. Waiting {int(wait_time)}s... (Attempt {attempt+1})\033[0m")
                    time.sleep(wait_time)
                else:
                    if self.ui: 
                        self.ui.print_log(f"[API ERROR] HTTP {response.status_code}: {response.text}")
                    
                    # 404 = Model Not Found — auto-reroute to alpha_url with fast_model
                    if response.status_code == 404 and "not found" in response.text.lower():
                        alpha_pool = self.config['hardware'].get('alpha_url')
                        fast_fallback = self.config['hardware'].get('fast_model', 'deepseek-r1:32b')
                        if alpha_pool and url_pool != alpha_pool:
                            if self.ui: self.ui.print_log(f"\033[1;33m[404-RESCUE] '{model}' not found. Switching to Alpha Pool with {fast_fallback}.\033[0m")
                            url_pool = alpha_pool
                            target_url = alpha_pool # Will be resolved to string in next loop iteration
                            model = fast_fallback
                            continue  # Retry with new target
                    
                    stop_heartbeat.set()
                    return None
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.InvalidSchema, requests.exceptions.MissingSchema) as e:
                # Pool Rotation Logic (New in v3.0) - Skip if strictly pinned
                if not is_pinned and isinstance(url_pool, list) and len(url_pool) > 1:
                    target_url = resolve_url_from_pool(url_pool)
                    if self.ui: 
                        pod_id = str(target_url).split("//")[-1].split(":")[0].split(".")[-1]
                        self.ui.print_log(f"\033[1;36m[ROTATION] Connection failed. Rotating to next pod in pool: Pod {pod_id}\033[0m")
                
                # Delayed Sleeper Handoff - Only after trying a few things or exhausting the pool once
                pool_size = len(url_pool) if isinstance(url_pool, list) else 1
                # Threshold: Try at least two full rotations of the pool before giving up
                sleeper_threshold = max(5, pool_size * 2) 
                if not is_sleeper and attempt >= sleeper_threshold:
                    is_sleeper_enabled = self.config.get("research", {}).get("deep_research_mode", False) or self.config.get("hardware", {}).get("sleeper_mode", False)
                    if is_sleeper_enabled:
                        if self.ui: self.ui.print_log(f"\n\033[1;31m[WARNING] Primary API Offline ({type(e).__name__}). Engaging SLEEPER MODE (Local Fallback).\033[0m")
                        stop_heartbeat.set()
                        if self.ui: self.ui.finish_task(task_id)
                        
                        # Recursive Fallback: Try again using the local sleeper model
                        fallback_model = self.config['hardware'].get('fallback_model', 'deepseek-r1:8b')
                        if self.ui: self.ui.print_log(f"\033[1;33m[SLEEPER] Handoff activated. Resubmitting task to Local {fallback_model}...\033[0m")
                        return self._query_llm(prompt, model=fallback_model, temperature=temperature, timeout=timeout, is_sleeper=True)

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
        import re
        
        # Capture reasoning trace if present
        reasoning_trace = None
        think_match = re.search(r'<think>(.*?)</think>', response, re.DOTALL | re.IGNORECASE)
        if think_match:
            reasoning_trace = think_match.group(1).strip()

        # First attempt: standard parsing
        result = extract_json(response)
        if result is not None:
            if reasoning_trace and isinstance(result, dict):
                result['reasoning_trace'] = reasoning_trace
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
