import os
import re

agent_path = "c:\\continuous\\agent.py"
with open(agent_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add queue methods
queue_methods = r"""
    def get_research_queue_path(self):
        return os.path.join(self.config['paths']['memory'], "research_queue.json")

    def push_to_research_queue(self, items):
        if not items: return
        queue_path = self.get_research_queue_path()
        queue = self._safe_load_json(queue_path, default=[])
        queue.extend(items)
        self._safe_save_json(queue_path, queue)
        self.ui.print_log(f"\033[1;32m[GATHERER] Pushed {len(items)} items to queue. Total pending: {len(queue)}\033[0m")

    def pop_from_research_queue(self, batch_size):
        queue_path = self.get_research_queue_path()
        queue = self._safe_load_json(queue_path, default=[])
        if not queue: return []
        batch = queue[:batch_size]
        self._safe_save_json(queue_path, queue[batch_size:])
        return batch

    def run_gatherer_loop(self):
        \"\"\"
        Thread 1: Generates topics, runs Wave 1, and pushes to research queue.
        \"\"\"
        self.ui.print_log("[GATHERER] Starting asynchronous gatherer loop...")
        while True:
            try:
                if self.current_state.get("state") == "PAUSED":
                    time.sleep(2)
                    continue

                self.reload_config()
                is_turbo = self.config['research'].get('turbo_mode', False)
                if is_turbo and self.current_state.get("phase") == "GUESS":
                    max_workers = self.config['hardware'].get('turbo_workers', 12)
                else:
                    max_workers = self.config['hardware'].get('max_swarm_workers', 2)

                tasks_to_queue = []
                # SAME LOGIC as before for STUDY/GUESS
                burst_step = self.current_state.get("burst_counter", 1)
                is_study_mode = (burst_step <= 5)
                
                study_topic = None
                if is_study_mode:
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
                    for _ in range(max_workers):
                        topic = self.current_state.get("current_topic")
                        depth = self.current_state.get("depth_counter", 0)
                        max_depth = self.config['research'].get('research_depth', 3)

                        if not topic or depth >= max_depth:
                            if topic: 
                                summary = self.explorer.synthesize(topic, study_mode=True)
                                temp_discovery = {
                                    "hypothesis": {"topic": topic, "hypothesis": "Full topic synthesis."},
                                    "evaluation": {"significance_score": 0, "verdict": summary}
                                }
                                self.scribe.journal_entry(temp_discovery)
                            
                            cross_pollinated = None
                            import random
                            if random.random() < 0.2:
                                cross_pollinated = self.reflector.cross_pollinate()

                            if cross_pollinated:
                                broad_topic = cross_pollinated['hybrid_topic']
                                vectors = self.explorer.decompose_topic(broad_topic)
                                self.current_state['dream_hypothesis_guidance'] = (
                                    f"CRITICAL CROSS-POLLINATION MANDATE:\n"
                                    f"You MUST use this exact hybrid hypothesis as your foundation for the new field: {cross_pollinated['hybrid_hypothesis']}\n"
                                    f"Context: {cross_pollinated['isomorphism_analysis']}"
                                )
                            else:
                                past_topics = self.get_past_topics()
                                broad_topic = self.explorer.get_new_topic(past_topics, fast_mode=True)
                                vectors = self.explorer.decompose_topic(broad_topic, study_mode=False, count=max_workers)
                            
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

                        self.current_state["depth_counter"] += 1
                        self.current_state["iteration_count"] = self.current_state.get("iteration_count", 0) + 1
                        target_iteration = self.current_state["iteration_count"]
                        tasks_to_queue.append((target_topic, depth, target_iteration))
                    
                    self.current_state["burst_counter"] = 1

                self.save_state()
                
                tasks_to_queue.sort(key=lambda x: x[3] if len(x) > 3 else False, reverse=True)
                stagger_delay = self.config['hardware'].get('swarm_stagger_s', 5)
                
                import concurrent.futures
                prelim_results = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    self.ui.print_log(f"\033[1;34m[WAVE 1] Engaging Research Workers (8B). Submitting {len(tasks_to_queue)} tasks...\033[0m")
                    research_futures = {}
                    for idx, task_data in enumerate(tasks_to_queue):
                        if len(task_data) == 4:
                            t, d, i, p = task_data
                        else:
                            t, d, i = task_data
                        
                        sec_urls = self.config['hardware'].get('secondary_gpu', [])
                        check_url = sec_urls[0] if isinstance(sec_urls, list) and sec_urls else (sec_urls if isinstance(sec_urls, str) else None)
                        
                        while self.get_vram_headroom(url=check_url) < 12.0:
                            self.ui.set_status(f"THROTTLED: Waiting for VRAM")
                            time.sleep(10)
                        
                        if idx > 0: time.sleep(stagger_delay)
                        future = executor.submit(self.worker_stage_research, t, d, i, None)
                        research_futures[future] = t

                    for f in concurrent.futures.as_completed(research_futures):
                        try:
                            prelim_results.append(f.result())
                        except Exception as e:
                            self.ui.print_log(f"[WAVE 1] Worker failed: {e}")

                if prelim_results:
                    self.push_to_research_queue(prelim_results)

                # Responsive interrupt scale delay
                delay = self.config['research'].get('iteration_delay', 5)
                for _ in range(max(1, int(delay * 2))):
                    if self.current_state.get("state") == "PAUSED": break
                    time.sleep(0.5)

            except Exception as e:
                self.ui.print_log(f"[GATHERER CRITICAL] Error: {e}")
                time.sleep(5)

    def run_synthesis_loop(self):
        \"\"\"
        Thread 2: Pulls from research queue and handles Wave 2+.
        \"\"\"
        self.ui.print_log("[SYNTHESIZER] Starting asynchronous synthesis loop...")
        while True:
            try:
                if self.current_state.get("state") == "PAUSED":
                    time.sleep(2)
                    continue

                self.reload_config()
                # Determine batch size dynamically based on api_pool
                api_pool = self.config['hardware'].get('api_url', [])
                num_pods = len(api_pool) if isinstance(api_pool, list) else 1
                pull_size = max(1, num_pods * 2) # Pull up to 2 tasks per pod

                prelim_results = self.pop_from_research_queue(pull_size)
                if not prelim_results:
                    time.sleep(2)  # Wait for gatherer
                    continue

                self.ui.print_log(f"\033[1;36m[SYNTHESIZER] Popped {len(prelim_results)} items from research queue.\033[0m")
                
                # --- COLLECTIVE A.0: BATCH GENERATION (70B Theorist) ---
                use_large = self.config['research'].get('use_large_theorist')
                topic = prelim_results[0]['topic'].split(":")[0] if prelim_results else None

                import concurrent.futures
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
                        num_shards = max(1, min(num_pods, len(batch_contexts)))
                        chunk_size = (len(batch_contexts) + num_shards - 1) // num_shards
                        shards = [batch_contexts[i:i + chunk_size] for i in range(0, len(batch_contexts), chunk_size)]
                        
                        batch_hypotheses = []
                        with concurrent.futures.ThreadPoolExecutor(max_workers=num_shards) as shard_executor:
                            shard_futures = [shard_executor.submit(self.explorer.generate_batch_hypotheses, s, topic) for s in shards]
                            for f in shard_futures:
                                batch_hypotheses.extend(f.result())
                        
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
                
                num_shards = max(1, min(num_pods, len(hypotheses)))
                if num_shards > 0:
                    chunk_size = (len(hypotheses) + num_shards - 1) // num_shards
                    shards = [hypotheses[i:i + chunk_size] for i in range(0, len(hypotheses), chunk_size)]
                    
                    refined_hypotheses = []
                    with concurrent.futures.ThreadPoolExecutor(max_workers=num_shards) as shard_executor:
                        shard_futures = [shard_executor.submit(self.explorer.refine_batch, s, topic) for s in shards]
                        for f in shard_futures:
                            refined_hypotheses.extend(f.result())
                    
                    for i, h in enumerate(refined_hypotheses):
                        if i < len(prelim_results):
                            prelim_results[i]['hypothesis'] = h

                # --- WAVE 2: CONSTRUCTION & EXECUTION (8B) ---
                self.ui.print_log("\033[1;34m[WAVE 2] Engaging Construction Workers (8B)...\033[0m")
                test_results = []
                # Execute construction and wait
                max_construction_workers = self.config['hardware'].get('max_swarm_workers', 2)
                if self.config['research'].get('turbo_mode', False) and self.current_state.get("phase") == "GUESS":
                    max_construction_workers = self.config['hardware'].get('turbo_workers', 12)
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_construction_workers) as executor:
                    construction_futures = {executor.submit(self.worker_stage_construction, r, None): r['topic'] for r in prelim_results}
                    for f in concurrent.futures.as_completed(construction_futures):
                        try:
                            res = f.result()
                            if res.get('status') == 'Fatal':
                                failed_topic = construction_futures[f]
                                reason = res.get('reason', 'Unknown Construction Failure')
                                self.explorer.log_failure(failed_topic, {"hypothesis": res.get('hypothesis', {"topic": failed_topic}), "data": {}}, audit_reason=reason)
                                self.ui.print_log(f"\033[1;31m[OVERMIND] FATAL REJECTION logged for '{failed_topic}': {reason[:100]}...\033[0m")
                            else:
                                test_results.append(res)
                        except Exception as e:
                            self.ui.print_log(f"[WAVE 2] Worker failed: {e}")

                if not test_results:
                    self.ui.print_log("[OVERMIND] No valid simulation results. Synthesis wave aborted.")
                    continue

                # --- COLLECTIVE B: BATCH AUDIT (72B Auditor) ---
                self.ui.print_log("\033[1;33m[COLLECTIVE B] Synchronizing for Batch Audit (72B)...\033[0m")
                num_shards = max(1, min(num_pods, len(test_results)))
                chunk_size = (len(test_results) + num_shards - 1) // num_shards
                shards = [test_results[i:i + chunk_size] for i in range(0, len(test_results), chunk_size)]
                
                audit_reports = []
                shard_offsets = [i * chunk_size for i in range(len(shards))]
                with concurrent.futures.ThreadPoolExecutor(max_workers=num_shards) as shard_executor:
                    shard_futures = [(shard_executor.submit(self.auditor.verify_batch, s), offset)
                                     for s, offset in zip(shards, shard_offsets)]
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
                    self.ui.print_log(f"\033[1;36m[WAVE 2.5] Engaging Self-Fix Workers for {len(fix_candidates)} candidates...\033[0m")
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_construction_workers) as executor:
                        fix_futures = {executor.submit(self.worker_stage_self_fix, test_results[i], audit_map[i], None): i for i in fix_candidates}
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
                        self.ui.print_log(f"\033[1;32m[WAVE 2.5] Self-Fix complete. Re-Auditing...\033[0m")
                        audit_reports = self.auditor.verify_batch(test_results)
                        audit_map = {rep['index']: rep for rep in audit_reports if 'index' in rep} if audit_reports else {}

                # --- WAVE 3: FINALIZATION (8B) ---
                self.ui.print_log("\033[1;34m[WAVE 3] Engaging Finalization Workers (8B)...\033[0m")
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_construction_workers) as executor:
                    finalize_futures = []
                    for i, res in enumerate(test_results):
                        report = audit_map.get(i, {"audit_passed": False, "rejection_type": "FATAL", "reasoning": "Batch audit index mismatch."})
                        finalize_futures.append(executor.submit(self.worker_stage_finalize, res, report, None))
                    
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
                    if latest_guidance and latest_guidance.get('hypothesis_generation_guidance'):
                        self.current_state['dream_hypothesis_guidance'] = latest_guidance['hypothesis_generation_guidance']
                    if latest_guidance and latest_guidance.get('code_patch', {}).get('enabled'):
                        self.reflector.try_self_patch(latest_guidance)

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
"""

# Replace run_swarm function declaration with our new methods
pattern = re.compile(r'    def run_swarm\(self.*?(?=    def run_creator_improvements_phase)', re.DOTALL)

run_mod = r"""
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

agent_tmp = content.replace("def run(self):", "def _old_run_deprecated(self):")
agent_tmp = pattern.sub(queue_methods, agent_tmp)
with open("agent_mod.py", "w", encoding="utf-8") as f:
    f.write(agent_tmp + "\n" + run_mod)

print("Script generated successfully.")
