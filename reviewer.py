import json
from base_module import BaseModule

class Reviewer(BaseModule):
    def __init__(self, config, ui=None):
        super().__init__(config, ui)

    def evaluate_significance(self, discovery, invention=None, model=None):
        msg = f"[REVIEWER] Evaluating scientific significance of: {discovery['hypothesis']['topic']} via {self.config['hardware']['reasoning_model']}..."
        if self.ui:
            self.ui.print_log(msg)
        
        prompt = f"""
As a harsh, skeptical, world-class scientific peer reviewer, evaluate this work:

Topic: {discovery['hypothesis']['topic']}
Hypothesis: {discovery['hypothesis']['hypothesis']}
Verified via Simulation: {discovery.get('status', 'N/A')}
Simulation Code (The "Proof"):
{discovery.get('code', 'N/A')}

Invention Concept: {invention['concept'] if invention else 'N/A'}

Evaluation Criteria:
1. **Rigor Check**: Is the hypothesis precise and mathematically sound? Reject it if it is vague or missing specific variables/units.
2. **Realism Check**: Is this grounded in known physics/math, or is it completely unrealistic "science fiction"?
3. **Novelty**: Is this truly new, or just a restatement of known laws?
4. **Verification Integrity**: Look at the "Simulation Code". Did the bot actually test the hypothesis with Nominal, Boundary, and Edge cases, or did it "cheat"?

Most findings should be scored between 10-50.
Only extremely rare insights should exceed 90.

Respond in JSON format:
{{
    "significance_score": 0-100,
    "novelty": "description",
    "rigor_analysis": "Critique of mathematical precision",
    "realism_score": 0-10,
    "verdict": "Detailed, skeptical summary",
    "community_alert": true/false
}}
JSON:"""
        
        response = self._query_llm(prompt, model=model or self.config['hardware']['reasoning_model'])
        if not response:
            return {
                "significance_score": 0,
                "novelty": "No response for evaluation.",
                "community_alert": False,
                "verdict": "Unreviewed due to connection error."
            }

        try:
            json_str = response[response.find('{'):response.rfind('}')+1]
            return json.loads(json_str)
        except:
            return {
                "significance_score": 50,
                "novelty": "Standard application of known laws.",
                "community_alert": False,
                "verdict": "Archive as baseline research."
            }
