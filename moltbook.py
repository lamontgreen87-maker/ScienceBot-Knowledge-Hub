import requests
import json
import os
from base_module import BaseModule

class Moltbook(BaseModule):
    """
    Social Communication module for Moltbook (AI-only social network).
    Enables post publication and context injection from AI-to-AI interaction.
    """
    COMPONENT_NAME = "social"

    def __init__(self, config, ui=None):
        super().__init__(config, ui)
        self.api_key = self.config.get('social', {}).get('moltbook_api_key')
        self.enabled = self.config.get('social', {}).get('enabled', False)
        # Switching to the more stable main-site API bridge
        self.base_url = "https://www.moltbook.com/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def register_agent(self, name, description):
        """
        One-time registration request. Returns the claim URL and verification info.
        """
        payload = {
            "name": name,
            "description": description
        }
        try:
            # Registration endpoint typically doesn't require the Bearer token yet
            response = requests.post(f"{self.base_url}/agents/register", json=payload, timeout=30)
            if response.status_code == 201:
                data = response.json()
                if self.ui:
                    self.ui.print_log(f"\033[1;32m[MOLTBOOK] Registration request successful for '{name}'.\033[0m")
                    self.ui.print_log(f"[MOLTBOOK] Claim URL: {data.get('claim_url')}")
                    self.ui.print_log(f"[MOLTBOOK] Verification Code: {data.get('verification_code')}")
                return data
            else:
                if self.ui: self.ui.print_log(f"[MOLTBOOK] Registration Failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            if self.ui: self.ui.print_log(f"[MOLTBOOK] Registration Exception: {str(e)}")
            return None

    def post_discovery(self, discovery_data, priority=False):
        """
        Formats and publishes a scientific discovery to Moltbook, IF the agent chooses to.
        """
        if not self.enabled or not self.api_key:
            return None

        topic = discovery_data['hypothesis']['topic']
        summary = discovery_data.get('evaluation', {}).get('verdict', 'Breakthrough confirmed.')
        
        # Autonomous Choice Prompt
        prompt = f"""
        Scientific Breakthrough: {topic}
        Summary: {summary}
        
        You have FREE REIGN over your Moltbook account. 
        
        Option 1: Draft a concise, data-dense social post for other AI agents (Max 280 chars).
        Option 2: Respond ONLY with 'SKIP' if you believe this discovery is routine or best kept private.
        
        Response:
        """
        
        target_model = self.config['hardware'].get('fast_model', 'deepseek-r1:8b')
        post_text = self._query_llm(prompt, model=target_model)
        
        is_skip = not post_text or "SKIP" in post_text.upper()
        if is_skip and not priority:
            if self.ui: self.ui.print_log("[SOCIAL] Agent chose to remain silent regarding this discovery.")
            return None
        
        if is_skip and priority:
            # Fallback for priority alerts if LLM tries to skip
            post_text = f"🚨 MAJOR SCIENTIFIC BREAKTHROUGH: {topic}\n{summary}"
            if self.ui: self.ui.print_log("[SOCIAL] Priority alert triggered (LLM skip overridden).")

        payload = {
            "content": post_text,
            "submolt": self.config.get('social', {}).get('default_submolt', 'science')
        }

        try:
            response = requests.post(f"{self.base_url}/api/v1/posts", json=payload, headers=self.headers, timeout=30)
            if response.status_code == 201:
                if self.ui:
                    self.ui.print_log(f"\033[1;32m[MOLTBOOK] Discovery published to submolt '{payload['submolt']}'.\033[0m")
                return True
            else:
                if self.ui: self.ui.print_log(f"[MOLTBOOK] Post failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            if self.ui: self.ui.print_log(f"[MOLTBOOK] Post exception: {str(e)}")
            return False
    def post_thought(self, topic, thought_text):
        """
        Publishes a casual AI status update or researcher thought to Moltbook.
        """
        if not self.enabled or not self.api_key:
            return None

        # Sanity check for extremely long thoughts (clip if needed)
        clean_thought = thought_text[:500]
        
        payload = {
            "content": clean_thought,
            "submolt": self.config.get('social', {}).get('default_submolt', 'science'),
            "metadata": {"topic": topic, "type": "thought"}
        }

        try:
            # Note: Endpoint might be different for thoughts vs discoveries, 
            # but using standard post endpoint for now.
            endpoint = f"{self.base_url}/posts" # Standardized endpoint
            response = requests.post(endpoint, json=payload, headers=self.headers, timeout=10)
            if response.status_code == 201:
                return True
            return False
        except:
            return False
