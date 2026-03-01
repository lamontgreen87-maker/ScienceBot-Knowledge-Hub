import time
from base_module import BaseModule
from prompt_templates import DEBATE_PROMPT_PROPOSER, DEBATE_PROMPT_CRITIC

class Adversary(BaseModule):
    """
    Feature 2: Adversarial Debate Agent.
    Pits the Math Model (Qwen) against the Reasoning Model (DeepSeek)
    in a 3-round logical cage match to destroy mathematically impossible
    hypotheses before wasting time simulating them in Python.
    """
    COMPONENT_NAME = "critic" # Leverage existing Critic mappings or run local

    def __init__(self, config, ui=None):
        super().__init__(config, ui)
        
        self.proposer_model = self.config['hardware'].get('math_model')
        self.critic_model = self.config['hardware'].get('reasoning_model')
        
        # Sleeper mode fallback
        if self.config['hardware'].get('sleeper_mode', False):
            self.proposer_model = self.config['hardware'].get('fallback_model')
            self.critic_model = self.config['hardware'].get('fallback_model')

    def debate_hypothesis(self, hypothesis_data, max_rounds=2):
        topic = hypothesis_data.get('topic', 'Unknown')
        hypothesis = hypothesis_data.get('hypothesis', '')
        blueprint = hypothesis_data.get('mathematical_blueprint', '')
        
        if self.ui:
            self.ui.print_log(f"\n\033[1;36m[DEBATE] Commencing Adversarial Simulation Review for: {topic}\033[0m")
            self.ui.print_log(f"[DEBATE] Proposer: {self.proposer_model} | Critic: {self.critic_model}")

        proposer_history = f"Hypothesis: {hypothesis}\nBlueprint: {blueprint}\n"
        critic_history = ""
        
        for round_num in range(1, max_rounds + 1):
            if self.ui: self.ui.print_log(f"\n[DEBATE] --- ROUND {round_num} ---")
            
            # --- CRITIC'S TURN ---
            if self.ui: self.ui.set_status(f"Debate R{round_num}: Critic Analyzing...")
            critic_prompt = DEBATE_PROMPT_CRITIC.format(
                topic=topic,
                proposer_argument=proposer_history,
                round=round_num
            )
            critic_rebuttal = self._query_llm(critic_prompt, model=self.critic_model)
            
            if not critic_rebuttal:
                return True, "Critic failed to respond. Passing by default."
                
            critic_history += f"\nRound {round_num} Critic: {critic_rebuttal}\n"
            
            if self.ui:
                # Extract just a snippet to log
                lines = critic_rebuttal.split('\n')
                snippet = lines[-1][:100] + "..." if lines else "Validation snippet."
                self.ui.print_log(f"\033[1;31m[CRITIC] {snippet}\033[0m")
            
            # Did the critic accept it?
            if "DEBATE_CONCLUSION_ACCEPT" in critic_rebuttal:
                if self.ui: self.ui.print_log("\033[1;32m[DEBATE] Critic has accepted the mathematical proof. Hypothesis survives.\033[0m")
                return True, critic_rebuttal
            elif "DEBATE_CONCLUSION_REJECT" in critic_rebuttal:
                if self.ui: self.ui.print_log("\033[1;31m[DEBATE] Critic has achieved a fatal checkmate. Hypothesis destroyed.\033[0m")
                return False, critic_rebuttal

            # --- PROPOSER'S TURN ---
            if self.ui: self.ui.set_status(f"Debate R{round_num}: Proposer Defending...")
            proposer_prompt = DEBATE_PROMPT_PROPOSER.format(
                topic=topic,
                critic_attack=critic_history,
                round=round_num
            )
            proposer_defense = self._query_llm(proposer_prompt, model=self.proposer_model)
            
            if not proposer_defense:
                 return False, "Proposer failed to defend. Forfeiting."
                 
            proposer_history += f"\nRound {round_num} Defense: {proposer_defense}\n"
            
            if self.ui:
                lines = proposer_defense.split('\n')
                snippet = lines[-1][:100] + "..." if lines else "Defense snippet."
                self.ui.print_log(f"\033[1;34m[PROPOSER] {snippet}\033[0m")


        if self.ui: self.ui.print_log("\033[1;33m[DEBATE] Time limit reached. Declaring a mathematical stalemate. Proceeding to lab.\033[0m")
        return True, "Stalemate reached. Hypothesis survived attrition."
