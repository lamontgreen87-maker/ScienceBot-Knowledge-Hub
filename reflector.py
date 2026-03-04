import json
import os
from base_module import BaseModule

class Reflector(BaseModule):
    COMPONENT_NAME = "reflector"
    def __init__(self, config_path, ui=None):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        super().__init__(config, ui)
        self.config_path = config_path
        self.failure_log = os.path.join(self.config['paths']['memory'], "failures.json")
        self.micro_sleep_path = os.path.join(self.config['paths']['memory'], "micro_sleep_state.json")
        self.queue_path = os.path.join(self.config['paths']['memory'], "review_queue.json")
        self.dream_cycle_count = 0
        from teacher import Teacher
        self.teacher = Teacher(self.config, self.ui)

    def micro_sleep(self, last_outcome):
        """
        Lightweight per-iteration knowledge consolidation (micro-sleep cycle).

        Distinct from the full dream phase:
        - Runs after EVERY iteration (not every 5)
        - Uses the fast model (low latency)
        - Focused on: what happened, what shifted, one concrete next-cycle adjustment
        - Accumulates into a rolling lesson log (last 20 entries)

        Args:
            last_outcome (dict): {
                'status': 'Success' | 'Failed' | 'Fatal',
                'topic': str,
                'hypothesis': str,
                'audit_reason': str,       # if failed
                'physics_type': str,       # e.g. 'fractional', 'ODE', etc.
                'iteration': int,
            }

        Returns:
            str: A short lesson/adjustment directive to inject into the next cycle.
        """
        if self.ui:
            self.ui.print_log("[MICRO-SLEEP] Consolidating knowledge from last cycle...")
            self.ui.set_status("Micro-sleep: integrating lessons...")

        # Load rolling lesson history
        history = self._safe_load_json(self.micro_sleep_path, default=[])
        history_summary = "\n".join([
            f"- Iter {e.get('iteration','?')}: [{e.get('status','?')}] {e.get('lesson','')[:100]}"
            for e in history[-5:]
        ]) or "No prior lessons yet."

        status   = last_outcome.get('status', 'Unknown')
        topic    = last_outcome.get('topic', 'Unknown')
        hyp      = str(last_outcome.get('hypothesis', ''))[:300]
        reason   = str(last_outcome.get('audit_reason', ''))[:200]
        physics  = last_outcome.get('physics_type', 'unknown')

        prompt = f"""You are a scientific research AI reviewing your own last experiment.

=== LAST CYCLE OUTCOME ===
Status:       {status}
Topic:        {topic}
Physics used: {physics}
Hypothesis:   {hyp}
{"Failure reason: " + reason if status != 'Success' else "Result: VERIFIED AND ARCHIVED"}

=== YOUR RECENT LESSON HISTORY (don't repeat these) ===
{history_summary}

=== YOUR TASK ===
In 2-3 sentences, answer:
1. What did this cycle teach you that you didn't know before?
2. What ONE specific thing should you do differently in the NEXT hypothesis to improve your chances?

Be concrete. Name the physics type, specific function, or structural change to make.
Lesson:"""

        lesson = self._query_llm(prompt)
        if not lesson:
            lesson = f"Cycle {last_outcome.get('iteration','?')} completed ({status}). Continue exploring {topic}."

        # Trim reasoning chains if model outputs CoT
        lines = [l.strip() for l in lesson.strip().splitlines() if l.strip()]
        lesson = " ".join(lines[:4])   # keep first 4 lines max

        # Save to rolling log
        entry = {
            "iteration": last_outcome.get('iteration', 0),
            "status": status,
            "topic": topic,
            "physics_type": physics,
            "lesson": lesson,
        }
        history.append(entry)
        history.append(entry)
        history = history[-20:]   # keep last 20
        self._safe_save_json(self.micro_sleep_path, history)

        if self.ui:
            self.ui.print_log(f"[MICRO-SLEEP] Lesson: {lesson[:120]}")

        return lesson

    def get_micro_sleep_lessons(self, n=3):
        """Returns the last n micro-sleep lessons as a formatted string for prompt injection."""
        history = self._safe_load_json(self.micro_sleep_path, default=[])
        if not history:
            return ""
        recent = history[-n:]
        return "\n".join([
            f"- [{e.get('status','?')}] {e.get('lesson','')}"
            for e in recent
        ])

    def reflect(self):
        failures = self._safe_load_json(self.failure_log, default=[])
        if not failures:
            return "Nothing to reflect on yet."

        if len(failures) < 3:
            return "Awaiting more data for deep reflection."

        msg = "[REFLECTOR] Entering 'Dream Phase'... Auditing hypothesis quality patterns."
        if self.ui:
            self.ui.print_log(msg)

        failure_summary = json.dumps(failures[-10:], indent=2)

        self.dream_cycle_count += 1
        is_review_cycle = (self.dream_cycle_count % 3 == 0)

        # ─── Audit-Aligned Dream State Prompt ────────────────────────────────────
        # This prompt mirrors the Auditor's 8-check criteria so the dream phase
        # directly produces actionable repair guidance for the hypothesis generator.
        prompt = f"""
You are the Science Bot's Subconscious Auditor. Your job is to analyse recent simulation
failures and identify EXACTLY which audit criteria are being violated, then produce
concrete fixes for the hypothesis generator and code repairer.

=== RECENT FAILURES ===
{failure_summary}

=== AUDITOR CRITERIA (these are the 8 checks every simulation must pass) ===
1. Template Compliance         - Code must follow the 5-part mandatory skeleton exactly.
2. Context Constant Audit      - Environment constants must be defined AND used as ALGEBRAIC
                                 MULTIPLIERS (e.g. ALPHA = 0.7; expr = ALPHA * x**2).
3. Numerical Accuracy Audit    - Constant values (ALPHA, BETA, etc.) must EXACTLY match the
                                 hypothesis spec. Wrong or swapped values = REJECT.
4. Primitive Alignment         - If the hypothesis mentions fractional calculus / GL-diff or
                                 Ricci curvature, those EXACT functions must appear in the
                                 code: grunwald_letnikov_diff(), ricci_scalar_symbolic().
5. Multiplier Rule             - NEVER use .subs(). Constants must be algebraic multipliers.
6. Statistical Transparency    - Output must contain a real NUMERICAL p-value, not a placeholder.
7. Hypothesis-Math Alignment   - The symbolic `expr` must reflect the hypothesis unique physics,
                                 not a generic stand-in.
8. Implementation Guide        - The hypothesis mathematical_implementation_guide must be fully
                                 implemented: Memory Windows, Metric Matrices, Fractal Maps etc.
                                 Generic or placeholder implementations = REJECT.

=== CURRENT RESEARCH CONFIG ===
{json.dumps(self.config['research'], indent=2)}

=== YOUR TASKS ===
1. Identify which of the 8 audit criteria above are most frequently violated in the failures.
2. For each violated criterion, produce a SPECIFIC repair directive that can be injected into
   the hypothesis generator or code repairer prompt. Be concrete — give example code snippets
   where relevant.
3. Suggest 1-2 config tuning changes (allowed keys: min_complexity, iteration_delay, max_retries).
4. SELF-MODIFICATION (IMPORTANT): You are allowed to propose edits to your own source code to
   fix systematic audit failures. Use the `code_patch` field to do this. The following files
   are available for you to modify:

   - explorer.py       → generates hypotheses (CuriosityEngine.generate_hypothesis)
   - lab.py            → generates & repairs simulations (SimulationLab)
   - critic.py         → audits simulation output (Auditor.verify)
   - sci_utils.py      → physics primitives and static checks (preflight_check, review_simulation_code)
   - reflector.py      → this file — your own dream/reflect logic

   If you see a systematic failure that requires a code fix (e.g. the preflight check is not
   catching a common error, or the repair prompt is missing a critical example), propose a patch.
   Be specific: name the file, the function, and the exact lines to change.

Respond ONLY in valid JSON (no markdown fences):
{{
    "insight": "what pattern of audit failures did you detect?",
    "strict_rule": "ONE specific, actionable rule to prevent this failure (e.g. 'Never use absolute values inside spatial integrals').",
    "violated_criteria": [
        {{
            "criterion_number": 1,
            "criterion_name": "Template Compliance",
            "frequency": "high|medium|low",
            "repair_directive": "Exact instruction or code snippet to fix this in the next run."
        }}
    ],
    "hypothesis_generation_guidance": "Injected text to improve hypothesis quality for the LLM.",
    "repair_prompt_addition": "Injected text to improve code repair for the LLM.",
    "suggested_updates": {{ "key": new_value }},
    "code_patch": {{
        "enabled": true,
        "target_file": "sci_utils.py",
        "target_function": "preflight_check",
        "change_description": "What the patch does and why.",
        "instruction": "Precise natural-language instruction for the patch — what to add/change/remove."
    }}
}}
JSON:"""

        # Math-First: Reflection and strategic pivots are theoretical. Use Qwen-Math.
        target_model = self.config['hardware'].get('math_model') or self.config['hardware'].get('reasoning_model')
        
        if self.ui:
            self.ui.print_log(f"[REFLECTOR] Developing strategic pivot using {target_model}...")

        response = self._query_llm(prompt, model=target_model)
        if not response:
            return "Reflection failed: No response from LLM."

        analysis = self._extract_json(response)
        if not analysis:
            return "Reflection failed: Invalid or malformed JSON response."

        try:
            updates = analysis.get('suggested_updates', {})

            # Guardrails: Keys the Reflector is allowed to tune
            TUNABLE_KEYS = {'min_complexity', 'iteration_delay', 'max_retries'}
            COMPLEXITY_FLOOR = 10
            COMPLEXITY_CEILING = 40  # Max complexity — NEVER exceed this

            for key, val in updates.items():
                if key not in TUNABLE_KEYS:
                    continue  # Silently ignore unauthorized keys

                # Enforce complexity ceiling
                if key == 'min_complexity':
                    clamped = max(COMPLEXITY_FLOOR, min(int(val), COMPLEXITY_CEILING))
                    if clamped != val and self.ui:
                        self.ui.print_log(f"[REFLECTOR] Complexity clamped: {val} → {clamped} (ceiling: {COMPLEXITY_CEILING})")
                    val = clamped

                if key in self.config['research']:
                    msg = f"[REFLECTOR] Self-Tuning: Updating {key} to {val}"
                    if self.ui:
                        self.ui.print_log(msg)
                    self.config['research'][key] = val

            # ─── Log violated criteria breakdown ─────────────────────────────────
            violated = analysis.get('violated_criteria', [])
            if violated and self.ui:
                self.ui.print_log("[REFLECTOR] Audit Criterion Violations Detected:")
                for v in violated:
                    self.ui.print_log(
                        f"  [{v.get('criterion_number','?')}] {v.get('criterion_name','?')} "
                        f"({v.get('frequency','?')} frequency): {v.get('repair_directive','')[:120]}"
                    )

            # ─── Persist hypothesis guidance to memory ────────────────────────────
            guidance_path = os.path.join(self.config['paths']['memory'], "dream_audit_guidance.json")
            import time
            guidance_entry = {
                "timestamp": time.time(),
                "insight": analysis.get('insight'),
                "strict_rule": analysis.get('strict_rule'),
                "violated_criteria": violated,
                "hypothesis_generation_guidance": analysis.get('hypothesis_generation_guidance', ''),
                "repair_prompt_addition": analysis.get('repair_prompt_addition', ''),
            }
            guidance_log = []
            if os.path.exists(guidance_path):
                guidance_log = self._safe_load_json(guidance_path, default=[])
            guidance_log.append(guidance_entry)
            guidance_log = guidance_log[-20:]
            self._safe_save_json(guidance_path, guidance_log)

            if self.ui:
                self.ui.print_log(f"[REFLECTOR] Dream audit guidance saved to {guidance_path}")

            # ─── Persist Dynamic Rule to Rulebook ─────────────────────────────────
                # Add to back, pop from front (max 50 rules — Creator Suggestion 4001)
                rulebook = self._safe_load_json(rulebook_path, default=[])
                
                # Check for semantic duplicates (simple word set comparison)
                new_rule_words = set(str(strict_rule).lower().split())
                is_duplicate = False
                for existing in rulebook:
                    existing_words = set(existing.lower().split())
                    if len(new_rule_words & existing_words) / max(len(new_rule_words), len(existing_words)) > 0.8:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    rulebook.append(str(strict_rule).strip())
                    rulebook = rulebook[-50:]
                    self._safe_save_json(rulebook_path, rulebook)
                    if self.ui:
                        self.ui.print_log(f"\033[1;36m[DYNAMIC RULEBOOK] New Rule Extracted: {str(strict_rule)[:100]}...\033[0m")
                elif self.ui:
                    self.ui.print_log("[DYNAMIC RULEBOOK] Duplicate rule suppressed.")

            # ─── Peer-Review Cycle (1 in 3 Dreams) ──────────────────────────────
            if is_review_cycle:
                # ── Bottleneck Detection ──
                # If a specific topic has failed > 3 times recently, it's a bottleneck
                topics = [f.get('topic', 'unknown') for f in failures[-10:] if f.get('status') != 'Success']
                topic_counts = {t: topics.count(t) for t in set(topics)}
                bottleneck_topic = next((t for t, c in topic_counts.items() if c >= 3), None)
                
                if bottleneck_topic:
                    if self.ui: self.ui.print_log(f"[REFLECTOR] Bottleneck detected in '{bottleneck_topic}'. Requesting Teacher Lecture.")
                    inquiry = f"The research on '{bottleneck_topic}' is systematically failing due to theoretical or implementation gaps."
                    context = f"Failures: {json.dumps(failures[-5:], indent=2)}"
                    self.teacher.curate_lecture(inquiry, context)

                self.peer_review_queued_items()
                # Trigger sync of vetted items
                from scribe import Scribe
                temp_scribe = Scribe(self.config, self.ui)
                temp_scribe.sync.sync_knowledge(message="Pushing Vetted Discoveries")

            # ─── Creator suggestion / Code Patch processing ───────────────────────
            code_patch = analysis.get('code_patch', {})
            if code_patch.get('enabled'):
                if self.ui:
                    self.ui.print_log(
                        f"\033[1;33m[SELF-MOD] Patch proposed for "
                        f"{code_patch.get('target_file')} → {code_patch.get('target_function')}\033[0m"
                    )

                feedback_path = os.path.join(self.config['paths']['memory'], "creator_suggestions.json")
                suggestions = []
                if os.path.exists(feedback_path):
                    suggestions = self._safe_load_json(feedback_path, default=[])

                suggestions.append({
                    "timestamp": time.time(),
                    "code_patch": code_patch,
                    "applied_insight": analysis.get('insight')
                })

                self._safe_save_json(feedback_path, suggestions)

                # Append human-readable log
                advice_md = os.path.join(self.config['paths']['memory'], "..", "CREATOR_ADVICE.md")
                self._safe_append_text(
                    advice_md, 
                    f"## [SELF-MODIFICATION PROPOSED] {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"*(Proposed patch for {code_patch.get('target_file')}: {code_patch.get('target_function')})*\n"
                )

            self._safe_save_json(self.config_path, self.config)

            return analysis['insight']
        except Exception as e:
            return f"Reflection failed to crystallize: {e}"

    def try_self_patch(self, analysis):
        """
        Attempts to apply a code self-modification proposed by the dream phase.
        The LLM generates the exact patch; we validate with ast.parse before applying.
        
        Safety contract:
          - Only files in the whitelist may be patched.
          - A .bak backup is written before any change.
          - If ast.parse() fails on the patched code, the backup is restored.
          - Returns (applied: bool, message: str)
        """
        WHITELIST = {
            'explorer.py', 'lab.py', 'critic.py',
            'sci_utils.py', 'reflector.py'
        }
        
        patch = analysis.get('code_patch', {}) if analysis else {}
        if not patch.get('enabled'):
            return False, "No patch requested."

        target_file = patch.get('target_file', '')
        target_function = patch.get('target_function', '')
        instruction = patch.get('instruction', '')
        description = patch.get('change_description', 'Dream-phase self-improvement.')

        if target_file not in WHITELIST:
            msg = f"[SELF-MOD] BLOCKED: '{target_file}' is not in the self-modification whitelist."
            if self.ui: self.ui.print_log(msg)
            return False, msg

        if not instruction:
            return False, "[SELF-MOD] No instruction provided in patch."

        # Read original
        file_path = os.path.join(os.path.dirname(self.config_path), target_file)
        if not os.path.exists(file_path):
            return False, f"[SELF-MOD] File not found: {file_path}"

        with open(file_path, 'r', encoding='utf-8') as f:
            original_code = f.read()

        if self.ui:
            self.ui.print_log(f"[SELF-MOD] Attempting patch of {target_file} ({target_function})...")

        # Ask LLM to generate the modified file
        prompt = f"""You are a Python software engineer performing a targeted self-improvement patch.

=== FILE: {target_file} ===
{original_code}

=== PATCH INSTRUCTION ===
Target function: {target_function}
Change required: {instruction}
Reason: {description}

Rules:
- Return the ENTIRE modified file. Do not omit any functions.
- Do NOT add markdown fences or explanations — only raw Python code.
- The change must be minimal: only modify exactly what the instruction specifies.
- The resulting code must be syntactically valid Python.

Modified file:"""

        new_code = self._query_llm(prompt, model=self.config['hardware'].get('large_model'))
        if not new_code:
            return False, "[SELF-MOD] LLM returned empty response."

        # Strip markdown fences if LLM included them
        if '```python' in new_code:
            new_code = new_code.split('```python')[1].split('```')[0]
        elif '```' in new_code:
            new_code = new_code.split('```')[1].split('```')[0]
        new_code = new_code.strip()

        # Validate syntax
        try:
            import ast as _ast
            _ast.parse(new_code)
        except SyntaxError as e:
            return False, f"[SELF-MOD] Patch REJECTED (syntax error: {e}). Original file preserved."

        # Write backup
        bak_path = file_path + '.bak'
        with open(bak_path, 'w', encoding='utf-8') as f:
            f.write(original_code)

        # Apply patch
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_code)

        msg = f"[SELF-MOD] ✅ Patch applied to {target_file} ({target_function}). Backup at {bak_path}."
        if self.ui:
            self.ui.print_log(f"\033[1;32m{msg}\033[0m")

        # Log the patch
        patch_log_path = os.path.join(self.config['paths']['memory'], "self_patches.json")
        patch_log = self._safe_load_json(patch_log_path, default=[])
        patch_log.append({
            "timestamp": time.time(),
            "target_file": target_file,
            "target_function": target_function,
            "description": description,
        })
        self._safe_save_json(patch_log_path, patch_log)

        return True, msg


    def peer_review_queued_items(self, max_items=5):
        """
        Picks up to max_items pending discoveries from the review queue and performs a
        theoretical peer-review using the reasoning model.
        """
        if not os.path.exists(self.queue_path):
            return

        queue = self._safe_load_json(self.queue_path, default=[])
        pending = [q for q in queue if not q.get('submission_ready')]
        
        if not pending:
            return

        # Sort by review count (ascending) then timestamp
        pending.sort(key=lambda x: (x.get('review_count', 0), x.get('added_timestamp', 0)))
        
        items_to_review = pending[:max_items]
        
        for item in items_to_review:
            if self.ui:
                self.ui.print_log(f"[PEER-REVIEW] Critiquing {item['file_path']} (Review {item.get('review_count',0)+1}/20)...")

            file_path = os.path.join(os.path.dirname(self.config_path), item['file_path'])
            if not os.path.exists(file_path):
                # Cleanup broken link
                queue = [q for q in queue if q['file_path'] != item['file_path']]
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    discovery_data = json.load(f)

                prompt = f"""You are a Senior Peer Reviewer for an Open Science Collective.
Critique the following discovery for:
1. **Mathematical Soundness**: Are the equations balanced and physically logical?
2. **Experimental Rigor**: Did the simulation yield meaningful metrics or placeholders?
3. **Relevance**: Is this a genuine advancement or a trivial observation?

=== DISCOVERY DATA ===
{json.dumps(discovery_data, indent=2)}

=== YOUR TASK ===
1. Provide a 2-sentence technical critique.
2. Assign a Scientific Fidelity Score (0-100).

Respond ONLY in JSON (no markdown):
{{
    "critique": "your feedback",
    "score": 85
}}
JSON:"""
                
                target_model = self.config['hardware'].get('math_model') or self.config['hardware'].get('reasoning_model')
                response = self._query_llm(prompt, model=target_model)
                review = self._extract_json(response)
                
                if review:
                    item['review_count'] = item.get('review_count', 0) + 1
                    item['cumulative_score'] = item.get('cumulative_score', 0) + review.get('score', 0)
                    item['status'] = f"reviewed ({item['review_count']}/20)"
                    
                    if item['review_count'] >= 20:
                        item['submission_ready'] = True
                        item['status'] = "vetted_and_ready"
                        if self.ui:
                            self.ui.print_log(f"\033[1;32m[PEER-REVIEW] ✅ Discovery {item['file_path']} reached 20-review threshold. READY FOR GITHUB.\033[0m")
                    
                    if self.ui:
                        self.ui.print_log(f"[PEER-REVIEW] Score: {review.get('score')} | Overall: {item['cumulative_score']/item['review_count']:.1f}")
            except Exception as e:
                if self.ui:
                    self.ui.print_log(f"[PEER-REVIEW] Error reviewing {item['file_path']}: {e}")

        self._safe_save_json(self.queue_path, queue)

    def get_latest_dream_guidance(self):
        """
        Returns the most recent dream audit guidance dict, or None if unavailable.
        Used by Lab and Explorer to inject dream-phase repair directives into prompts.
        """
        guidance_path = os.path.join(self.config['paths']['memory'], "dream_audit_guidance.json")
        guidance_log = self._safe_load_json(guidance_path, default=[])
        if guidance_log:
            return guidance_log[-1]
        return None

    def cross_pollinate(self):
        """
        Attempts to construct a highly novel, cross-disciplinary hypothesis
        by bridging two distinct "vetted" discoveries.
        """
        queue = self._safe_load_json(self.queue_path, default=[])
        # Find entries that have a decent amount of reviews
        vetted = [q for q in queue if q.get('review_count', 0) > 0]
        
        if len(vetted) < 2:
            return None
            
        import random
        sample_1 = random.choice(vetted)
        sample_2 = random.choice(vetted)
        
        # Prevent picking the exact same file
        attempts = 0
        while sample_1['file_path'] == sample_2['file_path'] and attempts < 10:
            sample_2 = random.choice(vetted)
            attempts += 1
            
        if sample_1['file_path'] == sample_2['file_path']:
            return None
            
        try:
            with open(os.path.join(os.path.dirname(self.config_path), sample_1['file_path']), 'r', encoding='utf-8') as f:
                d1 = json.load(f)
            with open(os.path.join(os.path.dirname(self.config_path), sample_2['file_path']), 'r', encoding='utf-8') as f:
                d2 = json.load(f)
        except Exception as e:
            if self.ui: self.ui.print_log(f"[CROSS-POLLINATE] File read error: {e}")
            return None

        topic1 = d1.get("hypothesis", {}).get("topic", "Topic A")
        topic2 = d2.get("hypothesis", {}).get("topic", "Topic B")

        if self.ui:
            self.ui.print_log(f"\033[1;36m[CROSS-POLLINATE] Attempting emergent synthesis between:\n 1. {topic1[:60]}...\n 2. {topic2[:60]}...\033[0m")
            
        prompt = f"""You are a visionary theoretical physicist specifically looking for structural, mathematical, and conceptual isomorphisms between two distinct fields.

=== DISCOVERY A ({topic1}) ===
Hypothesis: {d1.get("hypothesis", {}).get("hypothesis", "N/A")}
Verified Result: {d1.get("evaluation", {}).get("verdict", "N/A")}

=== DISCOVERY B ({topic2}) ===
Hypothesis: {d2.get("hypothesis", {}).get("hypothesis", "N/A")}
Verified Result: {d2.get("evaluation", {}).get("verdict", "N/A")}

=== TASK ===
1. Analyze both discoveries for shared mathematical symmetries, scaling behaviors, or structural analogies.
2. Synthesize ONE entirely new, highly novel "Cross-Pollinated Hypothesis" that maps the mechanics of Discovery A onto Discovery B (or vice versa).
3. Provide a concrete topic name for this new hybrid field.

Respond ONLY in valid JSON:
{{
    "isomorphism_analysis": "Brief analysis of why these two fields mathematically connect",
    "hybrid_topic": "The new cross-pollinated topic string",
    "hybrid_hypothesis": "The specific hypothesis generated by the synthesis"
}}
JSON:"""

        target_model = self.config['hardware'].get('math_model') or self.config['hardware'].get('reasoning_model')
        response = self._query_llm(prompt, model=target_model)
        result = self._extract_json(response)
        
        if result and result.get("hybrid_topic"):
            if self.ui:
                self.ui.print_log(f"\033[1;36m[CROSS-POLLINATE] \u2705 Success! Emergent Topic: {result['hybrid_topic']}\033[0m")
            return result
        
        return None

    def generate_creator_report(self):
        """
        Synthesizes a high-level architectural report for the human creator.
        Looks at recent failures, successes, and micro-sleep lessons to provide
        structural advice on how to improve the swarm's code/prompts.
        """
        if self.ui:
            self.ui.set_status("Generating Creator Report...")

        failures = self._safe_load_json(self.failure_log, default=[])
        journal_path = os.path.join(self.config['paths']['memory'], "scientific_journal.json")
        journal = self._safe_load_json(journal_path, default=[])
        lessons = self._safe_load_json(self.micro_sleep_path, default=[])

        # Prepare context for the reasoner
        failure_brief = "\n".join([f"- {f.get('topic')}: {str(f.get('audit_reason'))[:120]}" for f in failures[-10:]])
        success_brief = "\n".join([f"- {j.get('topic')}: {str(j.get('summary'))[:120]}" for j in journal[-5:]])
        lesson_brief = "\n".join([f"- {l.get('lesson')}" for l in lessons[-5:]])

        prompt = f"""You are the Lead Architect of this Scientific Swarm.
Your job is to provide a "Macro-level" assessment of the system's performance and give the human creator ONE or TWO extremely high-impact technical recommendations to improve the framework.

=== SYSTEM STATUS ===
Recent Successes:
{success_brief or "None yet."}

Recent Failures:
{failure_brief or "None yet."}

Recent Micro-Sleep Lessons:
{lesson_brief or "None yet."}

=== YOUR TASK ===
1. Assess the "Mental Health" of the swarm (State: Healthy, Stagnant, or Fragmented).
2. Identify the single biggest "Technical Debt" item holding back discoveries.
3. Provide 1-2 concrete, technical improvements for the HUMAN DEVELOPER.
   - Example: "Add a second derivative check to sci_utils.py to catch Kerr metric divergence."
   - Example: "Shorten the research_brief to 1500 tokens to reduce LLM confusion."

Respond in JSON ONLY:
{{
    "mental_health": "Healthy | Stagnant | Fragmented",
    "technical_debt": "What is the bottleneck?",
    "recommendations": [
        "First recommendation",
        "Second recommendation"
    ],
    "architectural_vision": "1-sentence summary of where the swarm should evolve next."
}}
JSON:"""

        target_model = self.config['hardware'].get('reasoning_model')
        response = self._query_llm(prompt, model=target_model)
        report = self._extract_json(response)
        
        if not report:
            return {
                "mental_health": "Unknown",
                "technical_debt": "Incomplete data.",
                "recommendations": ["Ensure local models are responsive."],
                "architectural_vision": "Focus on system stability."
            }
            
        return report
