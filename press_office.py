import json
import os
from base_module import BaseModule

class PressOffice(BaseModule):
    def __init__(self, config, ui=None):
        super().__init__(config, ui)
        # Use absolute path to avoid directory confusion during recovery scans
        self.press_dir = os.path.abspath(os.path.join(self.config['paths']['memory'], "press_releases"))

    def create_press_release(self, discovery):
        topic = discovery['hypothesis']['topic']
        if self.ui:
            self.ui.print_log(f"[PRESS OFFICE] Drafting press release for: {topic}...")
        
        prompt = f"""
Scientific Discovery: {topic}
Hypothesis: {discovery['hypothesis']['hypothesis']}
Invention: {json.dumps(discovery.get('invention', 'N/A'), indent=2)}
Evaluation: {json.dumps(discovery.get('evaluation', 'N/A'), indent=2)}

Write a compelling, high-level Scientific Press Release for this discovery.
The tone should be professional yet exciting.
Include:
- A catchy HEADLINE.
- THE DISCOVERY: What was found?
- THE SIGNIFICANCE: Why does it matter to humanity?
- THE APPLICATION: What can we build with it?
- A FINAL VERDICT: Is this world-changing?

Respond in Markdown format.
"""

        # Tier 3 (Fast Tier) for creative writing
        target_model = self.config['hardware'].get('fast_model', 'deepseek-r1:8b')
        release_text = self._query_llm(prompt, model=target_model)
        if not release_text:
            return None

        # Ensure directory exists
        if not os.path.exists(self.press_dir):
            os.makedirs(self.press_dir)

        # Save release
        clean_name = self._sanitize_slug(topic, max_length=50).upper()
        filename = f"BREAKTHROUGH_{clean_name}.md"
        save_path = os.path.join(self.press_dir, filename)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(release_text)
            
        if self.ui:
            self.ui.print_log(f"[PRESS OFFICE] Press Release published at: {save_path}")
        return save_path
