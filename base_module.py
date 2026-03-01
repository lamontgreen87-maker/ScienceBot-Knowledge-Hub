import requests
import json
import time
import threading
import os

_GLOBAL_FILE_LOCK = threading.RLock()
_HEAVY_SEMAPHORE = None 
_SEMAPHORE_LOCK = threading.Lock()

class BaseModule:
    def __init__(self, config, ui=None):
        self.config = config
        self.ui = ui
        self.ollama_url = self.config['hardware'].get('api_url', "http://localhost:11434/api/generate")
        self.api_key = self.config['hardware'].get('api_key')
        
        # Initialize the global heavy model semaphore if not already done
        global _HEAVY_SEMAPHORE
        with _SEMAPHORE_LOCK:
            if _HEAVY_SEMAPHORE is None:
                limit = self.config['hardware'].get('heavy_concurrency_limit', 1)
                _HEAVY_SEMAPHORE = threading.Semaphore(limit)

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

    def get_system_health(self):
        """Returns a 'Complexity Multiplier' based on available local resources."""
        import psutil
        try:
            cpu_usage = psutil.cpu_percent(interval=None)
            mem_usage = psutil.virtual_memory().percent
            
            # Simple heuristic: If usage is > 80%, we should downscale complexity.
            if cpu_usage > 85 or mem_usage > 85:
                return 0.5  # Half complexity
            if cpu_usage > 70 or mem_usage > 70:
                return 0.8  # Partial downscale
            return 1.0     # Full speed
        except:
            return 1.0

    def wait_for_backend(self, url, label="Backend", timeout_mins=20):
        """Patience-based ping to ensure 70B model hydration on RunPod."""
        if not url: return True
        
        start_time = time.time()
        timeout_secs = timeout_mins * 60
        if self.ui:
            self.ui.print_log(f"\n\033[1;36m[HYDRATION] Waiting for {label} to hydrate ({url})...\033[0m")
            self.ui.print_log(f"[HYDRATION] 70B models can take 2-5 minutes to load into VRAM.")
        
        while time.time() - start_time < timeout_secs:
            elapsed = int(time.time() - start_time)
            try:
                # Lightweight check: Ping the tags endpoint
                target = url.replace("/api/generate", "/api/tags")
                response = requests.get(target, timeout=5)
                if response.status_code == 200:
                    if self.ui:
                        self.ui.print_log(f"\033[1;32m[HYDRATION] {label} is ONLINE and Hydrated.\033[0m")
                    return True
                else:
                    if self.ui:
                        self.ui.print_log(f"[HYDRATION] {label} returned {response.status_code}. Still waiting... ({elapsed}s)")
            except requests.exceptions.ConnectionError:
                if self.ui:
                    self.ui.print_log(f"[HYDRATION] {label} Connection Refused at {url}. Is the Pod running? ({elapsed}s)")
            except requests.exceptions.Timeout:
                if self.ui:
                    self.ui.print_log(f"[HYDRATION] {label} Timeout at {url}. Network might be slow. ({elapsed}s)")
            except Exception as e:
                if self.ui: self.ui.print_log(f"[HYDRATION] {label} Error: {str(e)} ({elapsed}s)")
            
            time.sleep(15) # Faster polling for better user feedback
            if self.ui:
                self.ui.set_status(f"Hydrating {label}... ({elapsed}s)")
        
        if self.ui:
            self.ui.print_log(f"\033[1;31m[CRITICAL] {label} failed to hydrate after {timeout_mins} minutes.\033[0m")
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
            response = requests.post(url, json=payload, timeout=timeout)
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

    def _perform_idle_tasks(self):
        """Hook for child classes to perform work while waiting for a heavy model."""
        pass

    def _query_llm(self, prompt, model=None, timeout=300, api_url=None, temperature=None):
        if model is None:
            model = self.config['hardware']['local_model']
        
        target_url = api_url
        if not target_url:
            mapping = self.config['hardware'].get('gpu_mapping', {})
            component_key = getattr(self, 'COMPONENT_NAME', self.__class__.__name__.lower())
            gpu_key = mapping.get(component_key)
            if gpu_key:
                target_url = self.config['hardware'].get(gpu_key)
            if not target_url:
                target_url = self.ollama_url
                
        is_sleeper = self.config['hardware'].get('sleeper_mode', False)
        if is_sleeper:
            # Reroute to local fallback immediately
            target_url = self.config['hardware'].get('local_url', 'http://localhost:11434').rstrip('/') + '/api/generate'
            model = self.config['hardware'].get('fallback_model', 'llama3.1:8b')
        
        if self.ui:
            self.ui.print_log(f"\033[1;30m[NETWORK] Requesting {model} from: {target_url}\033[0m")
        
        # Determine temperature
        temp_val = temperature if temperature is not None else 0.5

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": -1,
            "options": {
                "num_predict": 4096, 
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
        
        def heartbeat():
            h_start = time.time()
            while not stop_heartbeat.is_set():
                time.sleep(15) # Faster update interval for status
                if stop_heartbeat.is_set(): break
                elapsed = int(time.time() - h_start)
                
                status_label = "Thinking" if is_actually_processing.is_set() else "Queued"
                msg = f"\t... {status_label} ({model}) ... ({elapsed}s)"
                
                if self.ui:
                    self.ui.set_status(f"{status_label}... ({elapsed}s)")
                    if elapsed % 30 == 0: # Reduce print spam
                        self.ui.print_log(msg)
                else:
                    if elapsed % 30 == 0: print(f"    {msg}")
        
        h_thread = threading.Thread(target=heartbeat, daemon=True)
        h_thread.start()

        retries = 10 # High retry count for hydration periods
        import random
        for attempt in range(retries):
            try:
                # --- CONCURRENCY CONTROL ---
                # Check if model is "heavy" (70B/72B)
                is_heavy = any(x in model.lower() for x in [":70b", ":72b", "r1", "math"])
                
                if is_heavy:
                    if self.ui: self.ui.print_log(f"\033[1;30m[CONCURRENCY] Queuing for heavy model {model}...\033[0m")
                    # Non-blocking wait loop for "Waiting Room" actions
                    while not _HEAVY_SEMAPHORE.acquire(blocking=False):
                        self._perform_idle_tasks()
                        time.sleep(5) 
                    
                    try:
                        is_actually_processing.set()
                        response = requests.post(target_url, json=payload, headers=headers, timeout=timeout)
                    finally:
                        is_actually_processing.clear()
                        _HEAVY_SEMAPHORE.release()
                else:
                    is_actually_processing.set()
                    response = requests.post(target_url, json=payload, headers=headers, timeout=timeout)
                
                stop_heartbeat.set()
                if response.status_code == 200:
                    return response.json().get('response', '').strip()
                
                # Handle loading error (Ollama returns 503 or 500 while loading)
                if response.status_code in [500, 503]:
                    # Exponential backoff with jitter: 30s, 60s, 90s... capped at 120s
                    wait_time = min(120, (attempt + 1) * 30) + random.uniform(0, 5)
                    if self.ui: self.ui.print_log(f"\033[1;33m[RETRY] GPU is busy/loading. Waiting {int(wait_time)}s... (Attempt {attempt+1})\033[0m")
                    time.sleep(wait_time)
                else:
                    if self.ui: self.ui.print_log(f"[API ERROR] HTTP {response.status_code}: {response.text}")
                    return None
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                if attempt < retries - 1:
                    # Exponential backoff with jitter for connection issues
                    wait_time = min(120, (attempt + 1) * 30) + random.uniform(0, 5)
                    if self.ui: self.ui.print_log(f"\033[1;33m[RETRY] Connection Refused/Timeout. GPU likely hydrating. Waiting {int(wait_time)}s... (Attempt {attempt+1})\033[0m")
                    time.sleep(wait_time)
                else:
                    stop_heartbeat.set()
                    if not is_sleeper and "127.0.0.1" not in target_url and "localhost" not in target_url:
                        if self.ui: self.ui.print_log(f"\n\033[1;31m[WARNING] Primary API Offline. Engaging SLEEPER MODE (Local Fallback).\033[0m")
                        self.config['hardware']['sleeper_mode'] = True
                        self.config['hardware']['max_swarm_workers'] = 2
                        
                        # Recursive Fallback: Try again using the sleeper model so the active task doesn't crash
                        fallback_model = self.config['hardware'].get('fallback_model', 'llama3.1:8b')
                        if self.ui: self.ui.print_log(f"\033[1;33m[SLEEPER] Handoff activated. Resubmitting task to Local {fallback_model}...\033[0m")
                        return self._query_llm(prompt, model=fallback_model, timeout=timeout, temperature=temperature)
                        
                    if self.ui: self.ui.print_log(f"[CRITICAL] Max retries reached for {target_url}.")
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

        response = self._query_llm(prompt, model=reasoning_model, timeout=600)

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

        response = self._query_llm(prompt, model=math_model, timeout=600)
        
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
