from agents.client_relations_agent import ClientRelationsAgent
from config.settings import settings

class RequirementsGatherer:
    def __init__(self):
        self.agent = ClientRelationsAgent()
        self.round_count = 0

    def gather_requirements(self, initial_idea: str) -> str:
        """
        Interact with the user to clarify requirements.
        Returns the final summarized requirements.
        """
        print(f"\n--- Client Relations Phase ---\n")
        
        # Initial probe
        response = self.agent.get_response(f"The user has this idea: '{initial_idea}'. Review it. If it's vague, ask clarifying questions. If it's detailed enough, summarize it starting with 'REQUIREMENTS_SUMMARY:'.")
        print(f"{self.agent.name}: {response}\n")

        while self.round_count < settings.MAX_REQUIREMENTS_ROUNDS:
            # Check if requirements are finalized
            if "REQUIREMENTS_SUMMARY:" in response:
                return response.split("REQUIREMENTS_SUMMARY:")[1].strip()

            # Get user input
            user_input = input("User (You): ")
            self.round_count += 1

            # Get agent response
            response = self.agent.get_response(user_input)
            print(f"\n{self.agent.name}: {response}\n")

        # Force summary if max rounds reached
        print("\n(Max rounds reached, summarizing...)\n")
        final_response = self.agent.get_response("We are out of time. Please summarize the requirements as they stand now, starting with 'REQUIREMENTS_SUMMARY:'.")
        if "REQUIREMENTS_SUMMARY:" in final_response:
            return final_response.split("REQUIREMENTS_SUMMARY:")[1].strip()
        return final_response

