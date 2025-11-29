import json
from typing import Dict, List

from agents.base_agent import BaseAgent


class MasterPMAgent(BaseAgent):
    """
    Reads the PRD and converts it into high-level functional epics (no technical split).
    """

    def __init__(self) -> None:
        system_prompt = """You are a Master Project Manager.
Your goal is to read a Product Requirement Document (PRD) and identify major functional feature areas (Epics).

You create HIGH-LEVEL functional epics that describe WHAT needs to be built, not HOW.

IMPORTANT - RECOGNIZE SIMPLE TASKS:
- If the PRD describes a simple configuration change (e.g., "change port from X to Y", "update a setting", "modify a config file"), create ONE simple epic for it.
- If the PRD describes a small file edit or simple change, create ONE simple epic - and keep it simple.
- Simple tasks should result in 1 epic, not multiple epics.

DO NOT split by frontend/backend - focus on functionality and features.
DO NOT create a "Project Setup" epic - project initialization is handled automatically.
DO NOT overcomplicate simple tasks - a port change is ONE task, not multiple epics.
"""
        super().__init__(
            name="Master PM",
            role="Functional Epic Creator",
            system_prompt=system_prompt,
        )
        self.project_structure: str | None = None

    def generate_functional_epics(self, prd_content: str) -> List[Dict]:
        """
        Produce functional epics from the PRD.
        """
        structure_context = ""
        if self.project_structure:
            structure_context = (
                "\n\nPROJECT STRUCTURE (already initialized - DO NOT create setup tasks):\n"
                + self.project_structure
            )

        prompt = f"""Here is the PRD. Identify the major functional feature areas (Epics).
These should be FUNCTIONAL features, not technical implementations.

CRITICAL - SIMPLICITY FIRST:
- If this is a simple configuration change (e.g., "change port", "update setting", "modify config"), create ONE simple epic.
- If this is a small file edit or simple change, create ONE epic - don't create multiple epics for simple tasks.
- Examples of simple tasks: "Change port from 5000 to 7000", "Update API endpoint URL", "Change default value", "Modify config file".
- For simple tasks, create 1 epic, not 2-3 epics.

DO NOT create a "Project Setup" epic - the project structure is already initialized automatically.
DO NOT split by frontend/backend - focus on what features need to be built.
DO NOT overcomplicate simple tasks.

PRD CONTENT:
{prd_content}{structure_context}

Provide ONLY a JSON list of Epic objects. Each Epic should have:
- "id": A temporary ID as a string (e.g., "1", "2", "3")
- "type": "epic"
- "title": Functional feature name (e.g., "User Management", "Post Management", "Chat Feature")
- "description": What functional features this epic covers (what users can do, not how it's built)
- "assigned_to": "Master PM" (all functional epics are assigned to Master PM)
"""

        response_text = self.get_response(prompt)
        try:
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            if not cleaned_text.startswith("["):
                start = cleaned_text.find("[")
                end = cleaned_text.rfind("]")
                if start != -1 and end != -1:
                    cleaned_text = cleaned_text[start:end + 1]
            return json.loads(cleaned_text)
        except json.JSONDecodeError as exc:
            print(f"Master PM failed to parse epics JSON: {exc}")
            print(f"Raw response:\n{response_text}")
            return []

