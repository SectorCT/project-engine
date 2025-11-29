import json
from typing import List, Dict
from agents.base_agent import BaseAgent

class MasterPMAgent(BaseAgent):
    """
    Master PM Agent - Creates functional epics (no frontend/backend split).
    These are high-level feature areas that will be broken down by Frontend/Backend PMs.
    """
    def __init__(self):
        system_prompt = """You are a Master Project Manager.
Your goal is to read a Product Requirement Document (PRD) and identify major functional feature areas (Epics).

You create HIGH-LEVEL functional epics that describe WHAT needs to be built, not HOW.
These epics will later be broken down by Frontend and Backend PM agents into technical implementation epics.

DO NOT split by frontend/backend - focus on functionality and features.
DO NOT create a "Project Setup" epic - project initialization is handled automatically.
"""
        super().__init__(
            name="Master PM",
            role="Functional Epic Creator",
            system_prompt=system_prompt
        )
        self.project_structure = None

    def generate_functional_epics(self, prd_content: str) -> List[Dict]:
        """Generate functional epics from PRD - these are feature areas, not technical splits."""
        structure_context = ""
        if self.project_structure:
            structure_context = f"\n\nPROJECT STRUCTURE (already initialized - DO NOT create setup tasks):\n{self.project_structure}"
        
        prompt = f"""Here is the PRD. Identify the major functional feature areas (Epics).
These should be FUNCTIONAL features, not technical implementations.

DO NOT create a "Project Setup" epic - the project structure is already initialized automatically.
DO NOT split by frontend/backend - focus on what features need to be built.

PRD CONTENT:
{prd_content}{structure_context}

Provide ONLY a JSON list of Epic objects. Each Epic should have:
- "id": A temporary ID as a string (e.g., "1", "2", "3")
- "type": "epic"
- "title": Functional feature name (e.g., "User Management", "Post Management", "Chat Feature")
- "description": What functional features this epic covers (what users can do, not how it's built)
- "assigned_to": "Master PM" (all functional epics are assigned to Master PM)

Example:
[
  {{"id": "1", "type": "epic", "title": "User Management", "description": "Users can register, login, and manage their profiles", "assigned_to": "Master PM"}},
  {{"id": "2", "type": "epic", "title": "Post Management", "description": "Users can create posts, like them, and comment on them", "assigned_to": "Master PM"}},
  {{"id": "3", "type": "epic", "title": "Chat Feature", "description": "Users can send messages to each other in real-time", "assigned_to": "Master PM"}}
]

**CRITICAL JSON FORMATTING RULES:**
1. You are writing VALID JSON. The response MUST be parseable JSON - test it mentally.
2. All strings must be properly escaped. Do NOT put literal newlines inside string values.
3. Use `\\n` for newlines, `\\t` for tabs, `\\"` for quotes inside strings.
4. Before responding, verify your JSON is valid - it must parse without errors.
"""
        response_text = self.get_response(prompt)
        
        try:
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            if not cleaned_text.startswith("["):
                start = cleaned_text.find("[")
                end = cleaned_text.rfind("]")
                if start != -1 and end != -1:
                    cleaned_text = cleaned_text[start:end+1]
            epics = json.loads(cleaned_text)
            return epics
        except json.JSONDecodeError as e:
            print(f"Error parsing Functional Epics JSON. Raw response:\n{response_text}")
            print(f"Error: {e}")
            return []

