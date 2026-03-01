import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
from duckduckgo_search import DDGS
import json
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
from base_module import BaseModule

class Searcher(BaseModule):
    def __init__(self, config, ui=None):
        super().__init__(config, ui)

    def search(self, query, max_results=5):
        msg = f"[SEARCHER] Searching the web for: {query}..."
        if self.ui:
            self.ui.print_log(msg)
        else:
            print(msg)
        results = []
        try:
            import contextlib
            import io
            f = io.StringIO()
            with contextlib.redirect_stderr(f):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    with DDGS() as ddgs:
                        for r in ddgs.text(query, max_results=max_results):
                            results.append({
                                "title": r['title'],
                                "body": r['body'],
                                "href": r['href']
                            })
            return results
        except Exception as e:
            msg = f"[ERROR] Search failed: {e}"
            if self.ui:
                self.ui.print_log(msg)
            else:
                print(msg)
            return []

    def search_academic(self, query, max_results=5):
        """
        Retrieves papers from arXiv and OpenAlex.
        Grounds theories in peer-reviewed literature.
        """
        if self.ui:
            self.ui.print_log(f"[ACADEMIC] Retrieving papers for: {query}...")
        
        results = []
        
        # 1. arXiv (via Atom API)
        try:
            arxiv_url = f"http://export.arxiv.org/api/query?search_query=all:{quote(query)}&start=0&max_results={max_results}"
            r = requests.get(arxiv_url, timeout=10)
            if r.status_code == 200:
                root = ET.fromstring(r.text)
                # arXiv namespace
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                for entry in root.findall('atom:entry', ns):
                    title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
                    summary = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
                    link = entry.find('atom:id', ns).text
                    results.append({
                        "title": f"[arXiv] {title}",
                        "body": summary,
                        "href": link,
                        "source": "arXiv"
                    })
        except Exception as e:
            if self.ui: self.ui.print_log(f"[ACADEMIC] arXiv error: {e}")

        # 2. OpenAlex (via Polite Pool if email provided)
        try:
            user_email = self.config['research'].get('user_email', '')
            oa_url = f"https://api.openalex.org/works?search={quote(query)}&per_page={max_results}"
            headers = {}
            if user_email and "@" in user_email:
                headers['User-Agent'] = f"ScienceBot/1.0 (mailto:{user_email})"
            
            r = requests.get(oa_url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                for work in data.get('results', []):
                    title = work.get('title', 'No Title')
                    # OpenAlex doesn't always have a full abstract in the main search return, 
                    # but it has 'abstract_inverted_index'. We'll simplify for now.
                    abstract = "Abstract not available in brief."
                    if work.get('abstract_inverted_index'):
                        abstract = "Abstract available (Inverted Index format)."
                    
                    results.append({
                        "title": f"[OpenAlex] {title}",
                        "body": abstract,
                        "href": work.get('doi') or work.get('id'),
                        "source": "OpenAlex"
                    })
        except Exception as e:
            if self.ui: self.ui.print_log(f"[ACADEMIC] OpenAlex error: {e}")

        return results

    def search_technical(self, query, site_type='stackoverflow', max_results=3):
        """
        Site-wrapped technical search (Suggestion 3466, 3481).
        Options: stackoverflow, eevblog, hackaday, reddit_hardware.
        """
        domains = {
            'stackoverflow': 'stackoverflow.com',
            'eevblog': 'eevblog.com',
            'hackaday': 'hackaday.io',
            'reddit_hardware': 'reddit.com/r/hardware'
        }
        
        domain = domains.get(site_type, 'stackoverflow.com')
        wrapped_query = f"site:{domain} {query}"
        
        if self.ui:
            self.ui.print_log(f"[TECHNICAL] Searching {domain} for: {query}...")
            
        return self.search(wrapped_query, max_results=max_results)

    def search_github(self, query, max_results=3):
        """
        Retrieves code implementations and repository descriptions from GitHub.
        """
        wrapped_query = f"site:github.com {query} filetype:py OR filetype:ipynb"
        if self.ui:
            self.ui.print_log(f"[GITHUB] Searching for code in: {query}...")
        return self.search(wrapped_query, max_results=max_results)

    def summarize_results(self, results):
        if not results:
            return "No recent data found."
        
        summary = ""
        for i, res in enumerate(results):
            summary += f"Source {i+1}: {res['title']}\nSnippet: {res['body']}\n\n"
        return summary

    def contemplate(self, topic):
        """
        Multi-round research loop — Contemplation Phase.

        Round 1: Broad search for current state of the topic.
        Round 2: LLM generates 3 targeted follow-up queries from Round 1 findings.
        Round 3: Each follow-up is searched and the results are cross-referenced.
        Final:   LLM synthesizes everything into a unified research brief.

        Returns a rich research brief string to inform hypothesis generation.
        """
        if self.ui:
            self.ui.print_log(f"[CONTEMPLATION] Beginning multi-round research on: {topic}")

        # ── Step 0: Internal Knowledge Retrieval ────────────────────────────────
        internal_knowledge = ""
        import os
        for db_dir in ['discoveries', 'memory']:
            path = self.config['paths'].get(db_dir)
            if path and os.path.exists(path):
                # Search JSONs, but specifically look in memory/knowledge if it's the memory dir
                search_dir = os.path.join(path, "knowledge") if db_dir == 'memory' else path
                if not os.path.exists(search_dir): continue
                
                for file in os.listdir(search_dir):
                    if file.endswith('.json'):
                        data = self._safe_load_json(os.path.join(search_dir, file))
                        # Simple heuristic: if the topic words overlap with the archived topic
                        if data and 'topic' in data.get('hypothesis', {}):
                            archived_topic = data['hypothesis']['topic'].lower()
                            if any(word in archived_topic for word in topic.lower().split() if len(word) > 4):
                                internal_knowledge += f"- Past finding on '{archived_topic}': {data['hypothesis'].get('hypothesis', '')}\n"

        # Also pull from the scientific journal (Study Mode syntheses)
        journal_path = os.path.join(self.config['paths'].get('memory', ''), "scientific_journal.json")
        if os.path.exists(journal_path):
            journal_data = self._safe_load_json(journal_path, default=[])
            search_keywords = [w.lower() for w in topic.split() if len(w) > 4]
            for entry in journal_data[-100:]:  # Scan more history
                entry_topic = entry.get('topic', '').lower()
                # Check for significant overlap or exact phrasing
                if any(word in entry_topic for word in search_keywords) or topic.lower() in entry_topic:
                    internal_knowledge += f"- Study Synthesis ({entry.get('timestamp')}) on '{entry.get('topic')}': {entry.get('summary', '')}\n"

        if internal_knowledge and self.ui:
            self.ui.print_log("[CONTEMPLATION] Found prior internal knowledge to build upon.")

        # ── Round 1: Broad sweep (Web + Academic) ────────────────────────────────
        broad_results = self.search(f"current research frontiers {topic} 2024 2025", max_results=5)
        
        # Mandatory Scientific Sweep (Suggestion 3466)
        academic_results = self.search_academic(topic, max_results=5)
        
        broad_summary = self.summarize_results(broad_results)
        academic_summary = self.summarize_results(academic_results)

        if not broad_summary or broad_summary == "No recent data found.":
            if not academic_summary or academic_summary == "No recent data found.":
                return "No recent data found."

        # ── Round 2: LLM generates targeted follow-up queries ───────────────────
        if self.ui:
            self.ui.print_log("[CONTEMPLATION] Generating targeted follow-up queries...")

        query_prompt = f"""You are a research strategist. A broad web search on the topic '{topic}' returned:

{broad_summary[:2000]}

Based on this, generate exactly 3 targeted follow-up search queries to fill knowledge gaps.
Focus on: (1) mathematical models or equations used, (2) recent experimental anomalies or open problems, (3) competing theories or alternative mechanisms.

Respond ONLY with a JSON array of 3 strings:
["query one", "query two", "query three"]
JSON:"""

        query_response = self._query_llm(query_prompt)
        from json_utils import extract_json
        follow_up_queries = extract_json(query_response)
        if not isinstance(follow_up_queries, list):
            follow_up_queries = []
            follow_up_queries = [
                f"{topic} mathematical models equations",
                f"{topic} unsolved problems anomalies",
                f"{topic} experimental evidence 2024",
            ]

        # ── Round 3: Execute follow-up searches ─────────────────────────────────
        all_follow_up = ""
        for i, raw_query in enumerate(follow_up_queries[:3]):
            query_str = ""
            if isinstance(raw_query, str):
                query_str = raw_query
            elif isinstance(raw_query, dict):
                # Try to extract from common keys or just take the first value
                query_str = raw_query.get('query', list(raw_query.values())[0] if raw_query else str(raw_query))
            else:
                query_str = str(raw_query)
                
            if self.ui:
                self.ui.print_log(f"[CONTEMPLATION] Follow-up {i+1}/3: {query_str[:60]}...")
            results = self.search(query_str, max_results=4)
            summary = self.summarize_results(results)
            all_follow_up += f"\n--- Follow-up {i+1}: {query_str} ---\n{summary}"

        # ── Final synthesis ──────────────────────────────────────────────────────
        if self.ui:
            self.ui.print_log("[CONTEMPLATION] Synthesizing research brief...")

        synthesize_prompt = f"""You are a Lead Research Scientist. Synthesize this multi-source research into a concise brief.

Topic: {topic}

=== BROAD RESEARCH ===
{broad_summary[:1200]}

=== ACADEMIC/PEER-REVIEWED FINDINGS ===
{academic_summary[:1500]}

=== TARGETED FOLLOW-UPS ===
{all_follow_up[:2000]}

=== PRIOR INTERNAL KNOWLEDGE ===
{internal_knowledge[:1500] if internal_knowledge else "No immediate prior findings on this exact vector."}

Write a research brief (4-6 sentences) covering:
1. The current state of the field and dominant theories.
2. The key open problems or anomalies that need explaining.
3. The mathematical frameworks currently in use.
4. Where the most promising research opportunities lie.

Research Brief:"""

        brief = self._query_llm(synthesize_prompt)
        if not brief:
            # Fallback: just concatenate the raw results
            brief = broad_summary + all_follow_up

        if self.ui:
            self.ui.print_log(f"[CONTEMPLATION] Brief complete ({len(brief)} chars).")
        return brief

    def deepen_research(self, topic, question, previous_brief, probe_results=None):
        """
        Deep-dive round of research focused on a specific question.
        """
        if self.ui:
            self.ui.print_log(f"[CONTEMPLATION] Deepening research on: {question[:80]}")

        # 1. Generate more aggressive search queries
        query_prompt = f"""You are a research scientist. You have a broad brief but need to dive deeper.
Topic: {topic}
Current Question: {question}
Current Knowledge: {previous_brief[:1000]}

Generate 2-3 extremely specific search queries to answer the question.
Include technical terms, specific experiments, or mathematical frameworks.
JSON ONLY: ["query1", "query2"]
"""
        response = self._query_llm(query_prompt)
        queries = []
        try:
            start = response.find('[')
            end = response.rfind(']') + 1
            queries = json.loads(response[start:end])
        except:
            queries = [f"{topic} {question} details", f"{topic} mathematical derivation"]

        # 2. Search (Web + Technical/Academic where relevant)
        new_findings = ""
        for q in queries[:2]:
            if any(term in q.lower() for term in ['proof', 'derivation', 'theory', 'paper', 'formal']):
                res = self.search_academic(q, max_results=3)
            elif any(term in q.lower() for term in ['error', 'fix', 'bug', 'circuit', 'implementation']):
                res = self.search_technical(q, site_type='stackoverflow', max_results=2)
            elif any(term in q.lower() for term in ['code', 'repo', 'library', 'algorithm']):
                res = self.search_github(q, max_results=2)
            else:
                res = self.search(q, max_results=3)
            new_findings += self.summarize_results(res)

        # 3. Augment brief with new findings and probe results
        from prompt_templates import RESEARCH_AUGMENTATION_PROMPT
        
        aug_prompt = RESEARCH_AUGMENTATION_PROMPT.format(
            topic=topic,
            initial_brief=previous_brief,
            web_findings=new_findings,
            probe_results=probe_results if probe_results else "No probe performed this round."
        )

        if self.ui:
            self.ui.print_log("[CONTEMPLATION] Augmenting research brief with deep-dive findings.")

        augmented_brief = self._query_llm(aug_prompt)
        return augmented_brief if augmented_brief else previous_brief + "\n" + new_findings
