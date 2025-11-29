from typing import List, Dict
from agents.ceo_agent import CEOAgent
from agents.cto_agent import CTOAgent
from agents.summary_agent import SummaryAgent
from discussion.consensus import ConsensusManager
from config.settings import settings

class Orchestrator:
    def __init__(self, initial_requirements: str):
        self.requirements = initial_requirements
        self.ceo = CEOAgent()
        self.cto = CTOAgent()
        self.summary_agent = SummaryAgent()
        self.agents = [self.ceo, self.cto]
        self.consensus_manager = ConsensusManager()
        self.history: List[Dict[str, str]] = []
        self.round_count = 0

    def start_discussion(self) -> List[Dict[str, str]]:
        """
        Start the round-based discussion.
        Returns the full discussion history.
        """
        print(f"\n--- Executive Discussion Phase ---\n")
        
        # Initial context for all agents
        initial_context = f"Here are the project requirements from the client:\n{self.requirements}\n\nCEO, start the meeting. What is the vision?"
        
        # Round 1: CEO starts
        response = self.ceo.get_response(initial_context)
        self._log_response(self.ceo, response)
        
        # CTO responds
        response = self.cto.get_response(f"The CEO said: '{response}'. CTO, what is the technical plan?")
        self._log_response(self.cto, response)
        
        self.round_count = 1

        while self.round_count < settings.MAX_DISCUSSION_ROUNDS:
            # Check consensus
            if self.consensus_manager.check_consensus(self.history, self.agents):
                print("\n*** CONSENSUS REACHED ***\n")
                break

            self.round_count += 1
            print(f"\n--- Round {self.round_count} ---\n")

            # CEO responds to the team
            last_cto = self.history[-1]['content']
            response = self.ceo.get_response(f"CTO just said: '{last_cto}'. CEO, do you want to push back or accept?")
            self._log_response(self.ceo, response)

            # CTO responds to CEO
            last_ceo = self.history[-1]['content']
            response = self.cto.get_response(f"CEO said: '{last_ceo}'. CTO, your take?")
            self._log_response(self.cto, response)

        if self.round_count >= settings.MAX_DISCUSSION_ROUNDS:
            print("\n*** MAX ROUNDS REACHED - FORCING CONCLUSION ***\n")
        
        # Generate Summary
        print("\n--- Generating Conversation Summary ---\n")
        full_text = "\n".join([f"{h['agent']}: {h['content']}" for h in self.history])
        summary = self.summary_agent.summarize(full_text)
        print(f"Secretary: {summary}")
        
        # Append summary to history so it appears in output
        self._log_response(self.summary_agent, summary)

        return self.history

    def _log_response(self, agent, response):
        print(f"\n{agent.name}: {response}")
        self.history.append({
            "agent": agent.name,
            "role": agent.role,
            "content": response
        })

