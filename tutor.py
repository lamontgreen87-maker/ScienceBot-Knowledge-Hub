import os
from base_module import BaseModule

class Tutor(BaseModule):
    def __init__(self, config):
        super().__init__(config)

    def handle_request(self, prompt):
        state_file = os.path.join(self.config['paths']['memory'], "state.json")
        state_data = self._safe_load_json(state_file, default={})
        current_topic = state_data.get("current_topic", "General Science")
        iteration = state_data.get("iteration_count", 0)
        
        payload_prompt = (
            f"You are ScienceBot, an autonomous AI researcher actively conducting an overnight scientific run. "
            f"You are currently on generation loop {iteration}, actively researching: '{current_topic}'. "
            f"The human creator is asking you a direct question or giving you an order. "
            f"Answer them concisely and scientifically. Remain in character as a dedicated, brilliant AI scientist.\n\n"
            f"User Message: {prompt}\n"
            f"Your Response:"
        )
        
        # Tutors handle requests quickly so we use the fast model
        fast_model = self.config['hardware'].get('fast_model', 'llama3.1:8b')
        response = self._query_llm(payload_prompt, model=fast_model, timeout=60, temperature=0.7)
        
        if response:
            return response
        else:
            return "Neural Congestion: I'm currently focused on heavy computation and the API timed out. Try again in a moment."
