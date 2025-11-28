from typing import List, Dict
from agents.base_agent import BaseAgent

class ConsensusManager:
    def __init__(self):
        pass

    def check_consensus(self, recent_history: List[Dict[str, str]], agents: List[BaseAgent]) -> bool:
        """
        Check if the agents have reached a consensus.
        Simple heuristic: Check if all agents have expressed agreement in their last turn.
        """
        # This is a simplified consensus check. In a real system, we might use an LLM to judge.
        # For now, we'll check for keywords indicating agreement or if the conversation seems to have settled.
        
        # Actually, a better approach for this system:
        # Let the Orchestrator ask an "Observer" (or just reuse an agent) if consensus is reached?
        # OR, we can check if the last 3 messages (one from each) contain affirmative phrases 
        # AND do not contain "but", "however", "disagree", "wait".
        
        if len(recent_history) < len(agents):
            return False

        last_messages = recent_history[-len(agents):]
        
        agreement_keywords = ["agree", "sounds good", "proceed", "approved", "consensus", "accept", "make it happen"]
        disagreement_keywords = ["disagree", "wait", "concern", "cannot", "issue", "stop", "objection"]
        
        agreements = 0
        for msg in last_messages:
            content = msg['content'].lower()
            if any(word in content for word in disagreement_keywords):
                return False
            if any(word in content for word in agreement_keywords):
                agreements += 1
                
        # If everyone seems to agree and no one disagrees
        return agreements >= len(agents) - 1 # Allow one implicit agreement (e.g. just a nod or silence)

    def get_consensus_status(self, history: List[Dict[str, str]]) -> str:
        return "Checking consensus..."

