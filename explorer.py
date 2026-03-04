import random
import json
import os
from base_module import BaseModule

class CuriosityEngine(BaseModule):
    COMPONENT_NAME = "explorer"
    def __init__(self, config, ui=None):
        super().__init__(config, ui)
        self.failure_log = os.path.join(self.config['paths']['memory'], "failures.json")
        from vector_memory import VectorMemory
        self.vector_mem = VectorMemory(self.config)

    def get_new_topic(self, past_topics=None, fast_mode=False):
        """Delegates to strategic_topic_selection() with DeepSeek reasoning."""
        return self.strategic_topic_selection(past_topics, fast_mode=fast_mode)

    def strategic_topic_selection(self, past_topics=None, fast_mode=False):
        """
        Feature 4: Topic Strategist — DeepSeek R1 picks the next research topic.

        Reads past discoveries and failures to find the most fertile direction
        rather than cycling topics randomly.
        """
        if past_topics is None:
            past_topics = []

        import random
        focus_areas = self.config['research'].get('focus_areas', ['Science', 'Math'])
        shuffled_focus = list(focus_areas)
        random.shuffle(shuffled_focus)

        physics_types = ["Fractional ODEs", "Ricci curvature", "Nonlinear ODEs", "Stochastic SDEs", "Power-law scaling"]
        random.shuffle(physics_types)
        physics_str = ", ".join(physics_types)

        # ── Gather context ──────────────────────────────────────────────────────
        # Use Vector memory for more relevant strategic context
        recent_successes = self.vector_mem.query_past_research("General Scientific Discoveries", n_results=10, filter_type="success")
        recent_failures = self.vector_mem.query_past_research("Scientific Failures and Audit Rejections", n_results=10, filter_type="failure")

        discoveries_ctx = [f"- {r['topic']}: {r['content'][:120]}" for r in recent_successes]
        failure_ctx = [f"- {r['topic']}: {r['content'][:120]} [FAIL]" for r in recent_failures]

        # Journal fallback for open questions
        journal_path = os.path.join(self.config['paths']['memory'], "scientific_journal.json")
        journal = self._safe_load_json(journal_path, default=[])
        open_questions = [e.get('open_questions', '') for e in journal[-3:] if e.get('open_questions')]

        context = (
            f"Recent Verified Discoveries (Vector Memory):\n" + "\n".join(discoveries_ctx or ["None yet."]) +
            f"\n\nRecent Failures (Vector Memory):\n" + "\n".join(failure_ctx or ["None."]) +
            f"\n\nOpen Questions from Journal:\n" + "\n".join(open_questions or ["None."])
        )

        question = (
            f"Given the research results above, which NEW topic from this list would be most "
            f"likely to yield novel, mathematically verifiable discoveries? "
            f"Focus areas available: {', '.join(shuffled_focus[:7])}. "
            f"Avoid these past topics: {', '.join(past_topics[-10:])}. "
            f"CRITICAL: Choose a topic that maps clearly to one of these frameworks: {physics_str} — NOT abstract theory. "
            f"MANDATORY: Prioritize 'PARADOX-LEVEL' topics that involve extreme singularities, non-Euclidean manifolds, or quantum entanglement at scale. "
            f"Respond with ONLY the topic name (max 8 words)."
        )


        if self.ui:
            self.ui.print_log(f"[STRATEGIST] Selecting optimal next topic (FastMode: {fast_mode})...")
            self.ui.set_status("Topic Strategy...")

        if not fast_mode:
            topic = self.consult_reasoner(question, context=context, label="[STRATEGIST]")
        else:
            topic = None # Force fallback to fast model

        # Clean up — DeepSeek may reason at length before answering
        if topic:
            # Take the last short line as the topic
            lines = [l.strip() for l in topic.strip().splitlines() if l.strip()]
            # Find first line that looks like a topic (short, no "I think" etc.)
            for line in reversed(lines):
                if 3 < len(line) < 80 and not line.startswith(('I ', 'The ', 'Based')):
                    topic = line.strip('*•-').strip()
                    break
            if self.ui:
                self.ui.print_log(f"[STRATEGIST] DeepSeek selected topic: {topic}")
            return topic

        # Fallback to fast model
        if self.ui:
            self.ui.print_log("[STRATEGIST] DeepSeek unavailable, using fast model for topic.")
        prompt = f"""You are a Scientific Methodology Engine.
Focus areas: {", ".join(shuffled_focus[:7])}
Avoid: {", ".join(past_topics[-5:])}
Pick one specific, implementable topic ({physics_str}).
Respond with ONLY the topic name.
Topic:"""
        fallback = self._query_llm(prompt)
        
        if fallback:
            return fallback.strip('*•-').strip()
        import random
        return f"{random.choice(focus_areas)} Theoretical Research"


    def decompose_topic(self, topic, study_mode=False, count=16):
        """Breaks a broad topic into specific research vectors."""
        if self.ui:
            self.ui.print_log(f"[EXPLORER] Decomposing broad topic: {topic} (StudyMode: {study_mode}, Vectors: {count})")
            
        target_model = "deepseek-r1:70b"
        
        # Build just enough example lines to show format without biasing count
        example_lines = "\n".join(
            f'        {{"name": "Specific Vector {i+1}", "area": "Focus"}}' + ("," if i < count - 1 else "")
            for i in range(min(count, 3))
        )
        if count > 3:
            example_lines += f'\n        ... (total of {count} vectors)'

        # ── Semantic Recall (Top 3 Successes, Top 3 Failures) ────────────────────
        past_successes = self.vector_mem.query_past_research(topic, n_results=3, filter_type="success")
        past_failures = self.vector_mem.query_past_research(topic, n_results=3, filter_type="failure")

        success_ctx = "\n".join([f"- {r['topic']}: SUCCESS. Results: {r['content'][:150]}..." for r in past_successes])
        failure_ctx = "\n".join([f"- {r['topic']}: FAILURE. Pitfall: {r['content'][:150]}..." for r in past_failures])

        past_context = ""
        if success_ctx or failure_ctx:
            past_context = "\n### SEMANTIC RECALL (PAST ATTEMPTS):\n"
            if success_ctx: past_context += f"**Validated Successes**:\n{success_ctx}\n"
            if failure_ctx: past_context += f"**Critical Failures to Avoid**:\n{failure_ctx}\n"

        prompt = f"""Topic: {topic}
{past_context}

As a Lead Scientist, perform a **LOGIC HOLE AUDIT** based on PEER-REVIEWED PHYSICS (arXiv, OpenAlex).
MANDATORY: Do NOT invent new framework names or acronyms (e.g., USGD-H). Use established concepts.
1. Identify exactly {count} specific "Logic Holes" or missing mathematical links in this topic that are documented in the literature.
2. Formulate exactly {count} "Synthesis Bridges" (research vectors) designed to resolve these holes.
3. Each bridge must be "Atomic" (solvable in 3 minutes) but "Structural" (contributes to the larger theory).
4. **PRIORITIZATION**: Mark vectors that involve direct paradoxes, singularity math, or "High Curiosity" anomalies with a `"high_curiosity": true` flag. 

MANDATORY: Do NOT invent new framework names, acronyms, or non-standard physical constants (e.g., alpha=0.729). Use ONLY established physics from peer-reviewed literature.
MANDATORY: Forbid "Event Horizon" unless it includes specific Kerr/Schwarzschild metric requirements.
MANDATORY: You MUST return exactly {count} vectors. No more, no fewer.

You MUST think carefully about this before answering. 
Start your response with a <think>...</think> block to reason through the physics.
After thinking, respond in strict JSON format:
{{
    "vectors": [
        {{
            "name": "Specific Vector Name",
            "area": "Focus Area",
            "high_curiosity": true/false
        }},
        ...
    ]
}}
"""
        response = self._query_llm(prompt, model=target_model, temperature=0.2)
        try:
            json_str = response[response.find('{'):response.rfind('}')+1]
            return json.loads(json_str).get('vectors', [])
        except:
            return [{"name": topic, "area": "General"}]


    def synthesize(self, topic, study_mode=False):
        discoveries_dir = self.config['paths']['discoveries']
        learnings = []
        
        # High-Fidelity Synthesis requires a larger context window and better reasoning
        target_model = self.config['hardware'].get('theorist_model') or self.config['hardware'].get('reasoning_model')
        
        if study_mode:
            target_model = self.config['hardware'].get('reasoning_model')
        
        if os.path.exists(discoveries_dir):
            for root, dirs, files in os.walk(discoveries_dir):
                for file in files:
                    if file.endswith(".json"):
                        try:
                            with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                                data = json.load(f)
                                discovery_topic = data.get('hypothesis', {}).get('topic', '')
                                if discovery_topic.lower() == topic.lower():
                                    learnings.append(f"VERIFIED: {data['hypothesis'].get('hypothesis', '')}")
                        except Exception:
                            continue
        
        prompt = f"""Topic: {topic}
Verified Findings:
{chr(10).join(learnings)}

Provide a HIGH-FIDELITY TECHNICAL SYNTHESIS of our research on this topic.
Your goal is to ensure NO CRITICAL DATA (constants, scaling laws, or validated equations) is lost during the topic transition.

Structure your response as follows:
1. **Consolidated Theory**: The most accurate mathematical equation(s) verified so far.
2. **Foundational Constants**: List ALL specific numerical values (ALPHA, BETA, etc.) that passed audit.
3. **Audit Hardening**: What failure patterns were observed and how to avoid them (e.g. .subs() issues).
4. **Knowledge Threads**: 1-2 unanswered questions that serve as the next logical steps for exploration.

You MUST think carefully about the physics before answering. 
Start your response with a <think>...</think> block to reason through the verified findings and how they form a foundation for future work.
After thinking, respond with the synthesis structured exactly as requested above.

Synthesis:"""
        return self._query_llm(prompt, model=target_model) or "Synthesis failed."

    def form_questions(self, topic, research_brief):
        """
        Scientific Method Step 2: Question Formation.

        Reads the contemplation brief and past discoveries, then generates
        3-5 specific, falsifiable questions that identify genuine knowledge gaps.
        Returns a list of question dicts and selects the best one to pursue.
        """
        if self.ui:
            self.ui.print_log(f"[EXPLORER] Forming scientific questions from research brief...")

        # Pull any prior verified findings on this topic to avoid re-asking answered questions
        discoveries_dir = self.config['paths']['discoveries']
        prior_findings = []
        if os.path.exists(discoveries_dir):
            for file in os.listdir(discoveries_dir):
                if file.endswith(".json"):
                    try:
                        with open(os.path.join(discoveries_dir, file), 'r', encoding='utf-8', errors='ignore') as f:
                            data = json.load(f)
                        if topic.lower() in data.get('hypothesis', {}).get('topic', '').lower():
                            prior_findings.append(data['hypothesis'].get('hypothesis', ''))
                    except Exception:
                        pass
                        
        # Also include summarized Study Mode knowledge
        journal_path = os.path.join(self.config['paths'].get('memory', ''), "scientific_journal.json")
        if os.path.exists(journal_path):
            try:
                journal_data = self._safe_load_json(journal_path, default=[])
                for entry in journal_data[-30:]:
                    if any(word in entry.get('topic', '').lower() for word in topic.lower().split() if len(word) > 4):
                        prior_findings.append(f"Study Conclusion on {entry.get('topic')}: {entry.get('summary')}")
            except Exception:
                pass

        prior_context = ("Prior verified findings on this topic:\n" +
                         "\n".join(f"- {p}" for p in prior_findings[-5:]))\
                         if prior_findings else "No prior verified findings on this topic yet."

        # ── MODULAR PROMPT INJECTION ──
        from prompt_templates import QUESTION_FORMATION_PROMPT
        
        prompt = QUESTION_FORMATION_PROMPT.format(
            topic=topic,
            context=research_brief[:2500],
            prior_findings=prior_context
        )

        # Tier 1 (Knowledge Gap Analysis Requires Reasoning, but must stay on its assigned pod)
        target_model = self.config['hardware'].get('explorer_model')
        response = self._query_llm(prompt, model=target_model, temperature=0.2)
        result = self._extract_json(response)

        if result and result.get('selected_question'):
            selected = result['selected_question']
            rationale = result.get('selection_rationale', '')
            if self.ui:
                self.ui.print_log(f"[EXPLORER] Driving Question: {selected}")
                if rationale:
                    self.ui.print_log(f"[EXPLORER] Rationale: {rationale[:120]}")
            return result

        # Fallback
        if self.ui:
            self.ui.print_log("[EXPLORER] Question formation fallback — using broad topic question.")
        return {
            "questions": [{"question": f"What governs the scaling behaviour of {topic}?",
                           "rationale": "Default gap question.", "testable_with": "power_law"}],
            "selected_question": f"What governs the scaling behaviour of {topic}?",
            "selection_rationale": "Fallback default."
        }


    def generate_hypothesis(self, topic, search_data=None, dream_hint=None, driving_question=None, study_mode=False):
        research_context = search_data if search_data else "General knowledge."
    
        # --- FEATURE 4: ChromaDB Vector Memory Injection ---
        try:
            from vector_memory import VectorMemory
            v_mem = VectorMemory(self.config['paths'].get('memory', ''))
            similar_discoveries = v_mem.query_similar_physics(topic, n_results=3)
            if similar_discoveries:
                context_string = "\n".join(similar_discoveries)
                research_context += f"\n\n=== CROSS-POLLINATED VECTOR MEMORY ===\n(These are mathematically similar discoveries from our past research that you MUST consider building upon):\n{context_string}\n==================\n"
                if self.ui: self.ui.print_log(f"\033[1;36m[VECTOR-MEM] Injected {len(similar_discoveries)} prior breakthroughs into reasoning context.\033[0m")
        except ImportError:
            pass # Handle if vector_memory fails to load during transition
        except Exception as e:
            if self.ui: self.ui.print_log(f"\033[1;33m[VECTOR-MEM] Warning: Failed to query ChromaDB: {e}\033[0m")
            
        # Pre-emptive Complexity Scaling (Hardware Adaptive)
        multiplier = self.get_system_health()
        base_complexity = self.config['research'].get('min_complexity', 1)
        min_complexity = max(1, int(base_complexity * multiplier))
        
        if multiplier < 1.0 and self.ui:
            self.ui.print_log(f"[EXPLORER] System loaded. Scaling complexity to {min_complexity} (Multiplier: {multiplier})")

        # Dream-phase audit guidance block (injected only when available)
        dream_guidance_section = ""
        if dream_hint:
            dream_guidance_section = f"""
### DREAM-PHASE AUDIT GUIDANCE (learned from past audit failures — comply with ALL points below):
{dream_hint}
### END DREAM GUIDANCE
"""
            if self.ui:
                self.ui.print_log("[EXPLORER] Dream-phase audit guidance injected into hypothesis prompt.")
        
        # Dynamic Rulebook (Strict rolling rules from past failures)
        dynamic_rulebook_section = ""
        import os
        rulebook_path = os.path.join(self.config['paths'].get('memory', ''), "dynamic_rulebook.json")
        if os.path.exists(rulebook_path):
            rules = self._safe_load_json(rulebook_path, default=[])
            if rules:
                formatted_rules = "\n".join([f"  {i+1}. {r}" for i, r in enumerate(rules)])
                dynamic_rulebook_section = f"""
=== DYNAMIC A.I. RULES (Learned from past failures — NON-NEGOTIABLE) ===
{formatted_rules}
=== END DYNAMIC RULES ===
"""
                if self.ui:
                    self.ui.print_log(f"\033[1;36m[EXPLORER] Attached {len(rules)} Dynamic Rules to generation constraint.\033[0m")
        
        # Driving question section
        driving_question_section = ""
        if driving_question:
            driving_question_section = f"""
### YOUR DRIVING QUESTION (answer this with your hypothesis):
"{driving_question}"
Your hypothesis MUST be a direct, falsifiable answer to this question.
### END DRIVING QUESTION
"""
            if self.ui:
                self.ui.print_log(f"[EXPLORER] Hypothesis will answer: {str(driving_question)[:80]}...")

        # ── MODULAR PROMPT INJECTION ──
        from prompt_templates import HYPOTHESIS_GENERATION_PROMPT, FAST_CYCLE_MANDATE, DEEP_RESEARCH_MANDATE
        
        # Select mandate based on Deep Research Mode toggle
        is_deep_mode = self.config['research'].get('deep_research_mode', False)
        rigor_mandate = DEEP_RESEARCH_MANDATE if is_deep_mode else FAST_CYCLE_MANDATE

        # Randomize the physics menu to prevent the LLM from biasing toward the first item (e.g., Fractional Calculus)
        import random
        physics_menu_items = [
            "Fractional Calculus (grunwald_letnikov_diff) - Memory Effects",
            "Nonlinear Dynamics (add_noise, ODE solvers)",
            "Stochastic Systems (SDEs with Brownian noise)",
            "Manifold Geometry (ricci_scalar_symbolic) - Kerr/Schwarzschild Metrics",
            "Black Hole Thermodynamics (Energy extraction kernels)",
            "High-Fidelity Event Horizon Simulations (Requires massive VRAM/Matrices)",
            "Manifold Geometry (ricci_scalar_symbolic) - Kerr/Schwarzschild Metrics (High-VRAM)",
            "Black Hole Thermodynamics (Energy extraction kernels) (High-VRAM)",
            "Black Hole Metrics (Kerr/Schwarzschild) - Requires `ricci_scalar_symbolic` and `einstein_tensor_from_metric` (High-VRAM)"
        ]
        random.shuffle(physics_menu_items)
        physics_menu = "\n".join([f"- {item}" for item in physics_menu_items])

        prompt = HYPOTHESIS_GENERATION_PROMPT.format(
            topic=topic,
            research_context=research_context,
            dream_guidance=dream_guidance_section,
            dynamic_rules=dynamic_rulebook_section,
            driving_question=driving_question_section,
            implementable_physics_menu=physics_menu,
            rigor_mandate=rigor_mandate
        )
        
        # Inject High-VRAM Mandate for Black Hole research
        if "Black Hole" in topic:
            prompt += "\n**VRAM MANDATE**: This is a high-fidelity simulation. Use 4x4 or larger SymPy matrices. Allocate large numerical grids (e.g. 500x500 steps) to utilize the cluster's 288GB VRAM pool. Placeholder physics will be REJECTED.\n"

        # specialized Math Engine is now the primary THEORIST for Study phase.
        # If in Guess mode (Phase 1), use fast_model (8B).
        if study_mode:
            target_model = self.config['hardware'].get('math_model') or self.config['hardware'].get('reasoning_model')
            label = "[THEORIST]" if "math" in str(target_model).lower() else "[REASONER]"
        else:
            if self.config['research'].get('use_large_theorist'):
                target_model = self.config['hardware'].get('theorist_model') or self.config['hardware'].get('reasoning_model')
                label = "[LARGE THEORIST]"
            else:
                target_model = self.config['hardware'].get('fast_model', 'deepseek-r1:8b')
                label = "[GUESSER]"

        if self.ui:
            self.ui.print_log(f"{label} Generating hypothesis (StudyMode: {study_mode}) using {target_model}...")

        response = self._query_llm(prompt, model=target_model, temperature=0.2)
        if not response:
            if self.ui:
                self.ui.print_log("[EXPLORER] Reasoning model returned NO response.")
            return self._fallback_hypothesis(topic)

        from json_utils import extract_and_validate
        data, error = extract_and_validate(response, "hypothesis")
        
        # ── RETRY LOOP (Creator Suggestion 3456) ──
        if error:
            if self.ui:
                self.ui.print_log(f"\033[1;33m[EXPLORER] Validation FAILED: {error}. Retrying Turn 2...\033[0m")
            
            retry_prompt = prompt + f"\n\nCRITICAL JSON ERROR: {error}. Respond ONLY with a valid JSON object matching the required schema."
            response = self._query_llm(retry_prompt, temperature=0.2)
            data, error = extract_and_validate(response, "hypothesis")

        if data:
            return data
        
        if self.ui:
            self.ui.print_log(f"[EXPLORER] Failed to extract valid JSON from hypothesis response.")
        return self._fallback_hypothesis(topic)

    def _fallback_hypothesis(self, topic):
        return {
            "topic": topic,
            "hypothesis": f"The recursive complexity of {topic} is self-similar.",
            "field": "general",
            "atomic_specification": {
                "independent_variable": {"name": "t", "symbol": "t"},
                "dependent_variable": {"name": "y", "symbol": "y"},
                "symbolic_parameters": ["t", "y"]
            },
            "mathematical_blueprint": "dy/dt = y/t",
            "test_params": {"complexity_level": 1}
        }

    def generate_batch_hypotheses(self, research_contexts, topic):
        """
        [COLLECTIVE THEORIST]
        Generates N hypotheses in a single 70B call based on parallel research contexts.
        research_contexts: List of dicts { 'driving_question': ..., 'summary': ... }
        """
        if not research_contexts:
            return []

        if self.ui:
            self.ui.print_log(f"\033[1;36m[COLLECTIVE THEORIST] Generating batch of {len(research_contexts)} hypotheses for: {topic}\033[0m")

        target_model = self.config['hardware'].get('theorist_model') or self.config['hardware'].get('reasoning_model')
        
        # Format contexts for the model
        contexts_str = ""
        for i, ctx in enumerate(research_contexts):
            contexts_str += f"--- RESEARCH CONTEXT {i+1} ---\n"
            contexts_str += f"QUESTION: {ctx.get('driving_question')}\n"
            contexts_str += f"SUMMARY: {str(ctx.get('summary'))[:1500]}...\n\n"

        prompt = f"""
You are the Lead Scientific Theorist. You have been given research data from {len(research_contexts)} parallel investigation vectors.
MANDATORY: Do NOT invent or name new theoretical frameworks (no USGD-H, etc.). Use established terminology.
Your task is to generate one high-fidelity hypothesis for EACH context.

Topic: {topic}

CONEXTS:
{contexts_str}

MANDATORY RULES:
1. Every hypothesis MUST be a unique, falsifiable answer to its specific driving question.
2. Use sophisticated mathematical frameworks (Fractional ODEs, Ricci Curvature, Non-linear Dynamics).
3. Ensure 'mathematical_blueprint' is an explicit symbolic expression.
4. Respond in strict JSON format.

Respond exactly like this:
{{
    "hypotheses": [
        {{ "topic": "...", "hypothesis": "...", "mathematical_blueprint": "...", ... }},
        ...
    ]
}}
"""
        response = self._query_llm(prompt, model=target_model, temperature=0.2)
        
        from json_utils import extract_and_validate
        data, error = extract_and_validate(response, "batch_hypotheses")
        
        if data and "hypotheses" in data:
            return data["hypotheses"]
        
        if self.ui:
            self.ui.print_log(f"\033[1;31m[COLLECTIVE THEORIST] Batch generation failed: {error or 'Malformed JSON'}. Returning fallbacks.\033[0m")
        
        return [self._fallback_hypothesis(topic) for _ in research_contexts]

    def refine_batch(self, hypotheses, topic):
        """
        [COLLECTIVE ARCHITECT] 
        Takes a list of 8B preliminary hypotheses and uses the 72B model
        to refine all of them into rigorous mathematical blueprints in a single pass.
        """
        if not hypotheses:
            return []

        if self.ui:
            self.ui.print_log(f"\033[1;36m[COLLECTIVE ARCHITECT] Refining batch of {len(hypotheses)} hypotheses for: {topic}\033[0m")

        target_model = self.config['hardware'].get('math_model') or self.config['hardware'].get('reasoning_model')
        
        # Format the hypotheses into a clear list for the LLM
        hypotheses_str = ""
        for i, h in enumerate(hypotheses):
            hypotheses_str += f"--- HYPOTHESIS {i+1} ---\n{json.dumps(h, indent=2)}\n\n"

        prompt = f"""
You are the Lead Scientific Architect. You have been given a set of preliminary research 'guesses' generated by junior models.
Your task is to refine EXACTLY these {len(hypotheses)} hypotheses into high-fidelity scientific blueprints.

Topic: {topic}

PRELIMINARY GUESSES:
{hypotheses_str}

MANDATORY REFINEMENT RULES:
1. Maintain the "personality" of each guess but fix the math.
2. Every refined hypothesis MUST have a unique 'mathematical_blueprint'.
3. Ensure 'mathematical_implementation_guide' provides literal, step-by-step instructions for a Python programmer.
4. 'atomic_specification' MUST identify the specific independent/dependent variables.
5. All constants MUST be explicitly listed.

Respond in strict JSON format:
{{
    "refined_hypotheses": [
        {{ ... hypothesis 1 ... }},
        {{ ... hypothesis 2 ... }},
        ...
    ]
}}
"""
        response = self._query_llm(prompt, model=target_model, temperature=0.2)
        
        from json_utils import extract_and_validate
        data, error = extract_and_validate(response, "batch_hypotheses") 
        
        if data and "refined_hypotheses" in data:
            return data["refined_hypotheses"]
        
        if self.ui:
            self.ui.print_log(f"\033[1;31m[COLLECTIVE ARCHITECT] Batch refinement failed: {error or 'Malformed JSON'}. Falling back to individual processing.\033[0m")
        return hypotheses

    def log_failure(self, topic, data, context=None, audit_reason=None):
        log = self._safe_load_json(self.failure_log, default=[])
        
        import time
        log_entry = {
            "topic": topic, 
            "data": data, 
            "research_context_peek": str(context)[:500] if context else "None",
            "audit_reason": audit_reason,
            "timestamp": time.time()
        }
        log.append(log_entry)
        self._safe_save_json(self.failure_log, log)

        # Vector Reflection
        self.vector_mem.embed_research(
            topic=topic,
            text=f"Reason: {audit_reason}\nHypothesis: {data.get('hypothesis', {}).get('hypothesis', 'N/A')}",
            metadata={"audit_reason": audit_reason},
            is_failure=True
        )

    def synthesize(self, topic, study_mode=False):
        """
        Gonzo Synthesis (Feature 3520): Builds larger hypotheses from atomic findings.
        Ingests the journal and generates a unified theory.
        """
        journal_path = os.path.join(self.config['paths']['memory'], "scientific_journal.json")
        journal = self._safe_load_json(journal_path, default=[])
        
        # Extract recent verified findings
        findings = []
        for entry in journal[-15:]:
            findings.append(f"Result: {entry.get('summary', 'N/A')}\nOpen Questions: {entry.get('open_questions', 'None')}")
        
        findings_ctx = "\n\n".join(findings) if findings else "No verified findings yet."
        
        prompt = f"""
As the Lead Scientific Architect, perform an **INTEGRAL SYNTHESIS** of our recent findings.

TOPIC: {topic}
RECENT VERIFIED FINDINGS:
{findings_ctx}

YOUR TASK:
1. **The Building Blocks**: Connect these atomic findings into a coherent technical summary.
2. **The Logic Hole**: Identify the most critical "Hole" or contradiction that we need to bridge next.
3. **The Next Foundation**: Propose the next specific, implementable research phase.

Maintain high physical rigor. Your synthesis should feel like a peer-reviewed summary of a long-term study.
"""
        target_model = self.config['hardware'].get('reasoning_model') or "llama3.3:latest"
        
        if self.ui:
            self.ui.print_log(f"[EXPLORER] Performing Synthesis on '{topic}'...")
            
        summary = self.consult_reasoner(prompt, context="Incremental Synthesis Phase", label="[SYNTHESIS]")
        return summary or "Synthesis failed to generate viable theory."
