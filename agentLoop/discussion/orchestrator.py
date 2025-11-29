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
        initial_context = f"""Here are the project requirements from the client:
{self.requirements}

CEO, start the meeting. Define the complete vision with:
1. All features broken down into complete feature sets (e.g., Authentication includes signup, login, logout)
2. For EVERY data entity, explicitly list ALL CRUD operations (Create, Read, Update, Delete) and how users perform them
3. For EVERY screen/page, explicitly list ALL UI elements (buttons, forms, links) - e.g., "Password list page has: 'Add New Password' button, 'Edit' button for each item, 'Delete' button for each item"
4. Complete user flows for each feature (step-by-step what users do, including every button click)
5. All related components for each feature

CRITICAL: Think through the entire user journey. If users can view passwords, they MUST be able to add new ones. If users can see a list, there MUST be a button to create new items. Don't assume - explicitly state every button, form, and action.

Be thorough - ensure nothing is missing that would prevent a developer from implementing the feature."""
        
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
            response = self.ceo.get_response(f"""CTO just said: '{last_cto}'. 

CEO, review the CTO's technical plan. Ensure:
1. All features have complete user flows defined (including every button click and form submission)
2. All related features are included (e.g., if signup exists, login and logout must exist)
3. For EVERY data entity, ALL CRUD operations are explicitly defined (Create, Read, Update, Delete)
4. For EVERY screen/page, ALL UI elements are explicitly listed (buttons, forms, links)
5. Users can complete the full workflow from start to finish
6. Nothing is missing that would prevent implementation

CRITICAL CHECK: If users can view a list of items, is there a button to create new items? If users can see data, can they edit it? Can they delete it? Walk through the entire user journey and verify every action is possible.

Do you want to add missing features/flows, push back, or accept?""")
            self._log_response(self.ceo, response)

            # CTO responds to CEO
            last_ceo = self.history[-1]['content']
            response = self.cto.get_response(f"""CEO said: '{last_ceo}'. 

CTO, review the CEO's feature definitions. Ensure:
1. All technical requirements are specified (endpoints, models, security, etc.)
2. All technical components are included (e.g., authentication needs tokens, validation, etc.)
3. Complete technical flows are defined

What's your technical assessment? Are all technical requirements covered?""")
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

