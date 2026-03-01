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

        if self.ui:
            self.ui.print_log(f"[SCRIBE] Verified knowledge archived at {save_path}")
        return save_path

    def journal_entry(self, discovery):
        journal_path = os.path.join(self.memory_dir, "scientific_journal.json")
        
        journal = self._safe_load_json(journal_path, default=[])
                
        evaluation = discovery.get('evaluation', {})
        prompt = f"""
Topic: {discovery['hypothesis']['topic']}
Hypothesis: {discovery['hypothesis']['hypothesis']}
Review Score: {evaluation.get('significance_score', 'N/A')}
Verdict: {evaluation.get('verdict', 'N/A')}

Write a DETAILED SCIENTIFIC SUMMARY for the permanent journal. 
Include the exact mathematical laws confirmed and one 'lesson learned' for future researchers.
JSON: {{"summary": "..."}}
"""
        response = self._query_llm(prompt, model=self.config['hardware']['reasoning_model'])
        try:
            summary_data = json.loads(response[response.find('{'):response.rfind('}')+1])
            summary_text = summary_data.get('summary', f"Exploration of {discovery['hypothesis']['topic']} complete.")
        except:
            summary_text = f"Scientific verification of {discovery['hypothesis']['topic']} concluded."

        journal.append({
            "topic": discovery['hypothesis']['topic'],
            "summary": summary_text,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        
        self._safe_save_json(journal_path, journal)

        # Trigger GitHub Sync
        if self.config.get('github', {}).get('sync_on_discovery'):
            self.sync.sync_knowledge(message=f"Archive discovery: {discovery['hypothesis']['topic']}")
