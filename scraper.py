import json
from base_module import BaseModule

class Scraper(BaseModule):
    def __init__(self, config, ui=None):
        super().__init__(config, ui)

    def find_pain_point(self, discovery_topic, search_data=None):
        if self.ui:
            self.ui.print_log(f"[SCRAPER] Searching for real-world pain points for: {discovery_topic}...")
        
        research_context = search_data if search_data else "Industry standards."
        
        prompt = f"""
Discovery: {discovery_topic}
Research Context: {research_context}

Identify a major real-world "pain point" or industry problem (e.g., energy efficiency, high latency, safety) that could be solved by this scientific area.
Respond in JSON format:
{{
    "problem": "a specific, detailed description of the problem",
    "industry": "e.g., Aerospace",
    "urgency": "High/Medium/Low"
}}
JSON:"""
        
        target_model = self.config['hardware'].get('fast_model', 'deepseek-r1:8b')
        response = self._query_llm(prompt, model=target_model)
        try:
            json_str = response[response.find('{'):response.rfind('}')+1]
            data = json.loads(json_str)
            return {
                "problem": data['problem'],
                "source": "LLM_Simulated_Industry_Research",
                "industry": data['industry']
            }
        except:
            return {
                "problem": "High energy consumption in decentralized computing networks.",
                "source": "Fallback_Industry_Data",
                "industry": "Computing"
            }
    def distill_academic_papers(self, search_results):
        """
        Parses search results (from arXiv/OpenAlex) and extracts structured 
        citations and theoretical foundations.
        """
        if not search_results:
            return "No academic papers found."
            
        prompt = f"""You are a Scientific Librarian. Analyze these academic search results:
        {json.dumps(search_results[:10])}
        
        Synthesize a Research Statement (3 sentences) that identifies:
        1. The primary mathematical framework cited.
        2. Known scaling laws or constants mentioned.
        3. Literature gaps that our hypothesis could address.
        
        Research Statement:"""
        
        target_model = self.config['hardware'].get('fast_model', 'deepseek-r1:8b')
        return self._query_llm(prompt, model=target_model)

    def distill_technical_guidance(self, search_results):
        """
        Extracts "Engineering Consensus" from forum data (StackOverflow, EEVblog, etc.)
        (Suggestion 3481)
        """
        if not search_results:
            return "No technical guidance found."

        prompt = f"""You are a Hardware/Software Engineering Lead. Review these forum discussions:
        {json.dumps(search_results[:5])}
        
        Extract the 'Engineering Consensus':
        1. Recommended libraries or implementation patterns.
        2. Known pitfalls (e.g., race conditions, noise coupling).
        3. Most upvoted solution or prevailing technical opinion.
        
        Engineering Consensus:"""

        target_model = self.config['hardware'].get('fast_model', 'deepseek-r1:8b')
        return self._query_llm(prompt, model=target_model)
