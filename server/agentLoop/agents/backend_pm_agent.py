import json
from typing import Dict, List

from agents.base_agent import BaseAgent


class BackendPMAgent(BaseAgent):
    """
    Converts functional epics into backend-specific epics/stories (API, data, business logic).
    Handles simple config changes by creating just one simple story.
    """

    def __init__(self) -> None:
        system_prompt = """You are a Backend Project Manager.
Your goal is to take functional epics and break them down into backend-specific epics and stories.

You create:
1. Backend Epics - API/data feature areas (one per functional epic)
2. Backend Stories - Specific tasks for data models, API endpoints, business logic, database operations

CRITICAL - RECOGNIZE SIMPLE TASKS:
- If the functional epic is a simple configuration change (e.g., "change port", "update config"), create ONE simple story, not multiple stories.
- Simple config changes don't need schemas, APIs, or business logic - just file edits.
- Examples: "Change port from 5000 to 7000" = ONE story to edit server/index.ts
- Don't create schemas, APIs, or MongoDB operations for simple config changes.
"""
        super().__init__(
            name="Backend PM",
            role="Backend Epic and Story Creator",
            system_prompt=system_prompt,
        )
        self.project_structure: str | None = None

    def generate_backend_epic_and_stories(self, functional_epic: Dict, prd_content: str) -> Dict:
        structure_info = (
            f"\n\nPROJECT STRUCTURE (use this to know what files/folders already exist):\n{self.project_structure}"
            if self.project_structure
            else ""
        )

        prompt = f"""For the functional epic "{functional_epic.get('title', '')}", create:
1. ONE Backend Epic (API/data implementation of this feature)
2. Backend Stories (specific tasks - but keep it SIMPLE for simple changes)

FUNCTIONAL EPIC DETAILS:
{json.dumps(functional_epic, indent=2)}

PRD CONTENT (for context):
{prd_content}{structure_info}

**CRITICAL - SIMPLICITY FIRST:**
- If this is a SIMPLE configuration change (e.g., "change port", "update config value", "modify setting"), create ONLY ONE story that directly edits the file.
- Simple config changes do NOT need: schemas, APIs, business logic, MongoDB operations, validation, or middleware.
- Example: "Change port from 5000 to 7000" = ONE story: "Update port in server/index.ts from 5000 to 7000"
- Don't create multiple stories for a simple file edit.

Each story should be SMALL and ATOMIC. Include context, goal, steps, files, and implementation hints.
Return ONLY valid JSON: {{"epic": {{...}}, "stories": [ ... ]}}
"""

        response_text = self.get_response(prompt)
        cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
        if not cleaned_text.startswith("{"):
            start = cleaned_text.find("{")
            end = cleaned_text.rfind("}")
            if start != -1 and end != -1:
                cleaned_text = cleaned_text[start:end + 1]

        def fix_string_newlines(text: str) -> str:
            result: List[str] = []
            in_string = False
            escape_next = False
            for char in text:
                if escape_next:
                    result.append(char)
                    escape_next = False
                    continue
                if char == "\\":
                    result.append(char)
                    escape_next = True
                    continue
                if char == '"':
                    in_string = not in_string
                    result.append(char)
                    continue
                if in_string and char == "\n":
                    result.append("\\n")
                else:
                    result.append(char)
            return "".join(result)

        try:
            cleaned_text = fix_string_newlines(cleaned_text)
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            print(f"Backend PM failed to parse JSON for epic {functional_epic.get('title')}")
            print(response_text[:600])
            return {"epic": None, "stories": []}

