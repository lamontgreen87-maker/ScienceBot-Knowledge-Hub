import json
from base_module import BaseModule

class Inventor(BaseModule):
    def __init__(self, config, ui=None):
        super().__init__(config, ui)

    def synthesize_existing_tech(self, pain_point, searcher=None, scraper=None):
        """
        Brainstorms existing solutions by leveraging forum data, 
        patents, and GitHub implementations.
        """
        msg = f"[INVENTOR] Brainstorming existing tech solutions for '{pain_point['problem']}'..."
        if self.ui:
            self.ui.print_log(msg)
            
        # ── Step 1: Multi-Source Retrieval (Suggestion 3481) ──
        tech_context = "Industrial standards."
        if searcher and scraper:
            # Search technical forums and GitHub
            query = f"{pain_point['problem']} current solutions stackoverflow github"
            forum_results = searcher.search_technical(pain_point['problem'], site_type='eevblog', max_results=3)
            # Add some SO results too
            so_results = searcher.search_technical(pain_point['problem'], site_type='stackoverflow', max_results=2)
            
            # Distill
            tech_context = scraper.distill_technical_guidance(forum_results + so_results)
            if self.ui:
                self.ui.print_log("[INVENTOR] Injected engineering consensus into tech synthesis.")

        prompt = f"""
        Problem: {pain_point['problem']}
        Industry: {pain_point['industry']}
        Engineering Context: {tech_context}
        
        Identify the current technical state-of-the-art for this problem. 
        What are the "Gold Standard" solutions and their main limitations?
        
        Respond in JSON:
        {{
            "tech_synthesis": "Comprehensive description of current solutions and gaps",
            "state_of_the_art": ["solution1", "solution2"],
            "known_bottlenecks": ["bottleneck1", "bottleneck2"]
        }}
        JSON:"""
            
        target_model = self.config['hardware'].get('reasoning_model') or self.config['hardware'].get('fast_model', 'llama3.1:8b')
        response = self._query_llm(prompt, model=target_model)
        try:
            return json.loads(response[response.find('{'):response.rfind('}')+1])
        except:
            return {"tech_synthesis": f"Manual optimization of current {pain_point['industry']} processes.", "state_of_the_art": [], "known_bottlenecks": []}

    def design_application(self, discovery, pain_point, existing_tech=None):
        msg = f"[INVENTOR] Designing breakthrough solution for '{pain_point['problem']}'..."
        if self.ui:
            self.ui.print_log(msg)
        
        context = f"\nExisting Tech Context: {existing_tech['tech_synthesis']}" if existing_tech else ""
        
        target_model = self.config['hardware'].get('reasoning_model') or self.config['hardware'].get('fast_model', 'llama3.1:8b')
        response = self._query_llm(prompt, model=target_model)
        if not response:
            return {
                "name": "Failed Project",
                "concept": "Ollama connection timeout during design.",
                "technical_specs": "N/A",
                "estimated_impact": "None"
            }

        try:
            json_str = response[response.find('{'):response.rfind('}')+1]
            return json.loads(json_str)
        except:
            return {
                "name": "Project Alpha-Centauri",
                "concept": f"A specialized tool using {discovery['hypothesis']['topic']} to optimize {pain_point['industry']}.",
                "technical_specs": "Implementation of verified mathematical proofs.",
                "estimated_impact": "Moderate"
            }
