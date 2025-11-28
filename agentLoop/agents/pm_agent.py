import json
from typing import List, Dict
from agents.base_agent import BaseAgent

class PMAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are a Pragmatic Project Manager.
Your goal is to read a Product Requirement Document (PRD) and break it down into actionable tasks for developers.

Your Output Format must be a valid JSON list of objects. NO Markdown formatting.
Each object should have:
- "type": "epic" or "story"
- "title": Short summary
- "description": Detailed instructions for the developer.
- "assigned_to": Role (e.g., "Frontend Dev", "Backend Dev", "Designer")
- "dependencies": List of temporary ticket IDs (e.g. ["2"]) that must be completed before this one. Stories can depend on other Stories. Epics should NOT be in dependencies - use parent_id for Epic relationship.
- "parent_id": For "story" types, the temporary ID of the "epic" it belongs to (e.g. "1"). For "epic", leave null.

Guidelines:
1. KEEP IT SIMPLE. Do not create 10 tiny tickets for a simple feature.
2. PROTECT THE TEAM. Assign clear ownership. Don't make two people work on the same exact file if possible.
3. LOGICAL BREAKDOWN.
   - Create an "Epic" for each major feature area (e.g. "User Auth", "Main Dashboard").
   - Create "Stories" under those Epics.
4. If the PRD describes a simple static site, maybe you only need 1-3 tickets total.
5. Do not over-engineer the process.
"""
        super().__init__(
            name="Project Manager",
            role="Task Orchestrator",
            system_prompt=system_prompt
        )

    def generate_tickets(self, prd_content: str) -> List[Dict]:
        prompt = f"""Here is the approved PRD. Break it down into Epics and Stories as JSON.
        
PRD CONTENT:
{prd_content}

Provide ONLY the JSON list. 
IMPORTANT: For "dependencies", use the temporary integer IDs (e.g., "1", "2") that you assign to tickets in this list. 
The system will map them to real database IDs later.
Each ticket MUST have a temporary "id" field (e.g. "1", "2", "3") so dependencies and parent_id can reference it.
Use STRING values for these temporary IDs (e.g. "1" not 1).
"""
        response_text = self.get_response(prompt)
        
        # Attempt to clean and parse JSON
        try:
            # Strip markdown code blocks if present
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            tickets = json.loads(cleaned_text)
            return tickets
        except json.JSONDecodeError:
            print(f"Error parsing PM response as JSON. Raw response:\n{response_text}")
            return []
