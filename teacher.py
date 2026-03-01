import json
import os
import time
from base_module import BaseModule

class Teacher(BaseModule):
    COMPONENT_NAME = "teacher"
    
    def __init__(self, config, ui=None):
        super().__init__(config, ui)
        self.lecture_dir = os.path.join(self.config['paths']['memory'], "knowledge", "teacher_lectures")
        if not os.path.exists(self.lecture_dir):
            os.makedirs(self.lecture_dir)

    def curate_lecture(self, inquiry, research_context):
        """
        Consults the Teacher (Multi-Model Pipeline) for a deep-dive lecture on a specific bottleneck.
        """
        if self.ui:
            self.ui.print_log(f"\033[1;36m[TEACHER] Preparing deep-dive lecture on: {inquiry[:60]}...\033[0m")

        # 1. Draft Outline (8B Fast Model)
        if self.ui: self.ui.print_log("[TEACHER] 1/3: Drafting lecture outline with Fast Model...")
        outline_prompt = f"""You are drafting an outline for a Teacher.
Topic: {inquiry}
Context: {research_context}
Provide a brief 3-point outline for a lesson explaining this."""
        outline = self._query_llm(outline_prompt, model=self.config['hardware'].get('fast_model'))

        # 2. Reasoning Model (DeepSeek) - Algebra 2 Level
        if self.ui: self.ui.print_log("[TEACHER] 2/3: Generating Master Lecture with Reasoning Model...")
        lecture_prompt = f"""You are the Science Bot's Principal Teacher.
Topic: {inquiry}
Outline: {outline}
Context: {research_context}

Your task is to write a "Master Lecture".
CRITICAL CONSTRAINT: You MUST explain this at an "Algebra 2 / High School graduate" reading level. 
Do NOT use doctoral-level esoteric terminology without explaining it simple practical analogies.

Respond in JSON ONLY:
{{
    "topic": "{inquiry}",
    "lecture": "Your master lecture text here (Algebra 2 level)...",
    "foundational_pillars": [
        {{"pillar": "Concept Name", "description": "Simple description..."}}
    ],
    "symbolic_rhs_suggestion": "ALPHA * y + BETA * dL/dx",
    "physicist_advice": "A short, sharp directive for the implementation phase."
}}
JSON:"""
        lecture_res = self._query_llm(lecture_prompt, model=self.config['hardware'].get('reasoning_model'))
        lecture_data = self._extract_json(lecture_res)
        
        if not lecture_data:
            if self.ui: self.ui.print_log("[TEACHER] Failed to extract JSON lecture.")
            return None

        # 3. Visuals (Gemini Teacher)
        if self.ui: self.ui.print_log("[TEACHER] 3/3: Requesting pure ASCII visual graphs from Gemini...")
        visual_prompt = f"""You are a visual aid assistant. 
Topic: {inquiry}
Lecture: {lecture_data.get('lecture', '')}

Provide a pure ASCII graph, diagram, or flow chart that visually explains this concept for a high schooler.
Do NOT use Mermaid.js, only use raw ASCII characters (e.g. -, |, +, *, etc). 
Limit the diagram to 30 lines. Explain the visual briefly at the bottom.
Respond ONLY with the raw ASCII text, no markdown code blocks formatting."""
        visuals = self._query_teacher(visual_prompt)
        lecture_data['visuals'] = visuals

        self.save_lesson_to_knowledge(lecture_data)
        return lecture_data

    def save_lesson_to_knowledge(self, lesson_data):
        """Saves the lecture to JSON and compiles a localized PDF."""
        topic_slug = self._sanitize_slug(lesson_data.get('topic', 'unknown_lesson'))
        timestamp = int(time.time())
        json_path = os.path.join(self.lecture_dir, f"lecture_{topic_slug}_{timestamp}.json")
        pdf_path = os.path.join(self.lecture_dir, f"lecture_{topic_slug}_{timestamp}.pdf")
        
        self._safe_save_json(json_path, lesson_data)
        
        # Compile PDF
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            
            def utf8_to_latin(text):
                return str(text).encode('latin-1', 'replace').decode('latin-1')
            
            # Title
            pdf.set_font("Courier", 'B', 16)
            pdf.multi_cell(0, 10, utf8_to_latin(lesson_data.get('topic', 'Master Lesson')), align='C')
            pdf.ln(10)
            
            # Lecture
            pdf.set_font("Courier", '', 11)
            pdf.multi_cell(0, 6, "--- MASTER LECTURE ---")
            pdf.multi_cell(0, 6, utf8_to_latin(lesson_data.get('lecture', '')))
            pdf.ln(5)
            
            # Advice
            pdf.set_font("Courier", 'B', 11)
            pdf.multi_cell(0, 6, "--- ADVICE ---")
            pdf.set_font("Courier", '', 11)
            pdf.multi_cell(0, 6, utf8_to_latin(lesson_data.get('physicist_advice', '')))
            pdf.ln(5)

            # Pillars
            pdf.set_font("Courier", 'B', 11)
            pdf.multi_cell(0, 6, "--- PILLARS ---")
            pdf.set_font("Courier", '', 11)
            for p in lesson_data.get('foundational_pillars', []):
                p_text = f"* {p.get('pillar')}: {p.get('description')}"
                pdf.multi_cell(0, 6, utf8_to_latin(p_text))
            pdf.ln(5)

            # Visuals
            pdf.set_font("Courier", 'B', 11)
            pdf.multi_cell(0, 6, "--- VISUAL DIAGRAM (GEMINI) ---")
            pdf.set_font("Courier", '', 9)
            
            # Clean gemini markdown blocks if they exist
            visuals = lesson_data.get('visuals', '')
            if visuals.startswith("```"):
                visuals = visuals.split("\n", 1)[-1]
                if visuals.endswith("```"):
                    visuals = visuals.rsplit("\n", 1)[0]
                    
            pdf.multi_cell(0, 4, utf8_to_latin(visuals))
            
            pdf.output(pdf_path)
            
            if self.ui:
                self.ui.print_log(f"[TEACHER] PDF Lecture compiled: {os.path.basename(pdf_path)}")
                
            # Launch PDF
            if os.name == 'nt':
                os.startfile(pdf_path)
        except Exception as e:
            if self.ui:
                self.ui.print_log(f"[TEACHER] PDF Generation failed: {e}")

        if self.ui:
            self.ui.print_log(f"[TEACHER] JSON Lecture archived to: {os.path.basename(json_path)}")

    def get_relevant_lectures(self, topic, n=1):
        """Retrieves scientific lectures relevant to the current topic."""
        lectures = []
        if not os.path.exists(self.lecture_dir):
            return ""
            
        # Very simple keyword match for now
        topic_words = set(topic.lower().split())
        
        for f in os.listdir(self.lecture_dir):
            if f.endswith(".json"):
                data = self._safe_load_json(os.path.join(self.lecture_dir, f), default=None)
                if data:
                    lecture_topic = data.get('topic', '').lower()
                    if any(word in lecture_topic for word in topic_words):
                        lectures.append(data)
                        
        if not lectures:
            return ""
            
        # Return the most recent n lectures
        lectures.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        output = "\n=== TEACHER LECTURES (FOUNDATIONAL KNOWLEDGE) ===\n"
        for l in lectures[:n]:
            output += f"Topic: {l.get('topic')}\n"
            output += f"Advice: {l.get('physicist_advice')}\n"
            output += f"Symbols: {l.get('symbolic_rhs_suggestion')}\n"
            output += "---\n"
        return output
