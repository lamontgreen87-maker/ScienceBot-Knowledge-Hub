import os
import json
import time
from sync import GitHubSync
from base_module import BaseModule

class Scribe(BaseModule):
    def __init__(self, config, ui=None):
        super().__init__(config, ui)
        self.memory_dir = self.config['paths']['memory']
        self.sync = GitHubSync(self.config, ui)
        self.sync.initialize_repo()
        
        from vector_memory import VectorMemory
        self.vector_mem = VectorMemory(self.config)

    def _append_past_topic(self, topic):
        """Maintains a lightweight O(1) cache of past topics to avoid os.walk bottlenecks."""
        if not topic or topic == 'general': return
        cache_path = os.path.join(self.memory_dir, "past_topics.json")
        past_topics = self._safe_load_json(cache_path, default=[])
        if topic not in past_topics:
            past_topics.append(topic)
            self._safe_save_json(cache_path, past_topics)

    def archive_discovery(self, test_result):
        topic = test_result['hypothesis'].get('topic', 'general')
        clean_topic = self._sanitize_slug(topic)
        filename = f"discovery_{clean_topic}.json"

        field = test_result['hypothesis'].get('field', 'general')
        clean_field = self._sanitize_slug(field)
        field_dir = os.path.join(self.config['paths']['discoveries'], clean_field)
        if not os.path.exists(field_dir):
            os.makedirs(field_dir)

        save_path = os.path.join(field_dir, filename)
        self._safe_save_json(save_path, test_result)
        self._append_past_topic(topic)

        # Vector Reflection
        self.vector_mem.embed_research(
            topic=topic,
            text=f"Hypothesis: {test_result['hypothesis']['hypothesis']}\nBlueprint: {test_result['hypothesis']['mathematical_blueprint']}",
            metadata={"field": field, "score": test_result.get('evaluation', {}).get('significance_score', 0)},
            is_failure=False
        )

        # Add to Review Queue immediately (Peer-Review Protocol 4002)
        queue_path = os.path.join(self.memory_dir, "review_queue.json")
        queue = self._safe_load_json(queue_path, default=[])
        
        # Calculate relative path from project root
        project_root = os.path.dirname(os.path.abspath(__file__))
        rel_path = os.path.relpath(save_path, project_root).replace("\\", "/")
        
        if not any(q['file_path'] == rel_path for q in queue):
            queue.append({
                "file_path": rel_path,
                "review_count": 0,
                "cumulative_score": 0,
                "status": "pending_review",
                "submission_ready": False,
                "added_timestamp": time.time()
            })
            self._safe_save_json(queue_path, queue)

        if self.ui:
            self.ui.print_log(f"[SCRIBE] TRUE DISCOVERY archived and queued for Peer-Review: {save_path}")
        return save_path

    def archive_knowledge(self, test_result):
        """Archives verified but low-significance results to memory/knowledge."""
        topic = test_result['hypothesis'].get('topic', 'general')
        clean_topic = self._sanitize_slug(topic)
        filename = f"verified_{clean_topic}.json"

        knowledge_dir = os.path.join(self.memory_dir, "knowledge")
        if not os.path.exists(knowledge_dir):
            os.makedirs(knowledge_dir)

        save_path = os.path.join(knowledge_dir, filename)
        self._safe_save_json(save_path, test_result)
        self._append_past_topic(topic)

        # Vector Reflection
        self.vector_mem.embed_research(
            topic=topic,
            text=f"Hypothesis: {test_result['hypothesis']['hypothesis']}\nBlueprint: {test_result['hypothesis']['mathematical_blueprint']}",
            metadata={"field": "verified_knowledge"},
            is_failure=False
        )

        if self.ui:
            self.ui.print_log(f"[SCRIBE] Verified knowledge archived at {save_path}")
        return save_path

    def journal_entry(self, discovery):
        journal_path = os.path.join(self.memory_dir, "scientific_journal.json")
        
        journal = self._safe_load_json(journal_path, default=[])
                
        from json_utils import extract_json
        
        evaluation = discovery.get('evaluation', {})
        prompt = f"""
Topic: {discovery['hypothesis']['topic']}
Hypothesis: {discovery['hypothesis']['hypothesis']}
Research Brief: {discovery['hypothesis'].get('simulation_context', 'N/A')}
Blueprint: {discovery['hypothesis'].get('mathematical_blueprint', 'N/A')}
Review Score: {evaluation.get('significance_score', 'N/A')}
Verdict: {evaluation.get('verdict', 'N/A')}

Write a RIGOROUS SCIENTIFIC SUMMARY for the permanent journal.
This entry must be a 'Knowledge Anchor' for future research.

Include:
1. THE CORE LAW: The final mathematical equation confirmed by simulation.
2. VERIFIED CONSTANTS: List specific numerical values (e.g. ALPHA=0.729) that passed audit.
3. DISCOVERY INSIGHT: One non-obvious relationship observed between variables.
4. FAILED PATHS: What specific math or assumptions failed during this research.
5. OPEN QUESTIONS: 1-2 falsifiable questions for next-gen models.

Respond in JSON ONLY:
{{"summary": "A 5-8 sentence technical synthesis containing the equations and constants...", "open_questions": "..."}}
"""
        response = self._query_llm(prompt, model=self.config['hardware']['reasoning_model'])
        summary_data = extract_json(response)
        
        summary_text = ""
        if summary_data and 'summary' in summary_data:
            text = summary_data['summary']
            # Validation: Must be technical and long enough (Suggestion 3466)
            if len(text) > 200 and any(kw in text.upper() for kw in ['LAW', 'CONSTANTS', 'CONFIRMED', 'SYMBOLIC', 'RELATIONSHIP']):
                summary_text = text
            else:
                if self.ui:
                    self.ui.print_log(f"[SCRIBE] WARNING: LLM summary failed technical depth check. Content: {text[:50]}...")

        if not summary_text:
            # High-Fidelity Fallback: Construct a technical summary from the discovery dict if LLM fails
            summary_text = f"TECHNICAL MEMORANDUM: Verification of {discovery['hypothesis']['topic']} (Significance: {discovery.get('evaluation', {}).get('significance_score')}). "
            summary_text += f"Blueprint: {discovery['hypothesis'].get('mathematical_blueprint')}. "
            summary_text += f"Constants: {json.dumps(discovery['hypothesis'].get('required_constants'))}. "
            summary_text += "Automatic synthesis triggered due to LLM fidelity failure."

        journal.append({
            "topic": discovery['hypothesis']['topic'],
            "summary": summary_text,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        
        self._safe_save_json(journal_path, journal)

        # Trigger GitHub Sync
        if self.config.get('github', {}).get('sync_on_discovery'):
            self.sync.sync_knowledge(message=f"Archive discovery: {discovery['hypothesis']['topic']}")
