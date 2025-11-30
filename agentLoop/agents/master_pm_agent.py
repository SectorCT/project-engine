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

IMPORTANT - RECOGNIZE SIMPLE TASKS:
- If the PRD describes a simple configuration change (e.g., "change port from X to Y", "update a setting", "modify a config file"), create ONE simple epic for it.
- If the PRD describes a small file edit or simple change, create ONE simple epic - don't overcomplicate it.
- Simple tasks should result in 1 epic, not multiple epics.

DO NOT split by frontend/backend - focus on functionality and features.
DO NOT create a "Project Setup" epic - project initialization is handled automatically.
DO NOT overcomplicate simple tasks - a port change is ONE task, not multiple epics.
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
            print(f"Master PM failed to parse epics JSON: {e}")
            print(f"Raw response:\n{response_text}")
            
            # Try to fix common JSON errors
            def fix_string_newlines(text):
                """Replace literal control characters within JSON string values with escaped versions."""
                result = []
                i = 0
                in_string = False
                escape_next = False
                
                while i < len(text):
                    char = text[i]
                    
                    if escape_next:
                        result.append(char)
                        escape_next = False
                        i += 1
                        continue
                    
                    if char == '\\':
                        result.append(char)
                        escape_next = True
                        i += 1
                        continue
                    
                    if char == '"':
                        in_string = not in_string
                        result.append(char)
                        i += 1
                        continue
                    
                    if in_string:
                        # Inside a string - escape control characters that aren't already escaped
                        if char == '\n':
                            result.append('\\n')
                        elif char == '\r':
                            result.append('\\r')
                        elif char == '\t':
                            result.append('\\t')
                        elif char == '\b':
                            result.append('\\b')
                        elif char == '\f':
                            result.append('\\f')
                        else:
                            result.append(char)
                    else:
                        result.append(char)
                    
                    i += 1
                
                return ''.join(result)
            
            def fix_missing_commas(text):
                """Fix missing commas in JSON - adds commas after closing quotes when followed by a key."""
                result = []
                i = 0
                in_string = False
                escape_next = False
                
                while i < len(text):
                    char = text[i]
                    
                    if escape_next:
                        result.append(char)
                        escape_next = False
                        i += 1
                        continue
                    
                    if char == '\\':
                        result.append(char)
                        escape_next = True
                        i += 1
                        continue
                    
                    if char == '"':
                        was_in_string = in_string
                        in_string = not in_string
                        result.append(char)
                        
                        # If we just closed a string, check if we need a comma
                        if was_in_string and not in_string:
                            # Look ahead past whitespace
                            j = i + 1
                            while j < len(text) and text[j] in ' \t\n\r':
                                j += 1
                            
                            if j < len(text):
                                next_char = text[j]
                                # If next char is a quote (indicating a new key), we likely need a comma
                                if next_char == '"':
                                    # Look backwards to find the last non-whitespace char before the quote we just closed
                                    k = len(result) - 2  # -2 because we just added the closing quote
                                    while k >= 0 and result[k] in ' \t\n\r':
                                        k -= 1
                                    
                                    # Check if there's already a comma, colon, or opening brace/bracket
                                    # We don't want to add a comma if we're right after a colon (key: value)
                                    if k >= 0 and result[k] not in ',{[:\n':
                                        # No comma found, add one after the closing quote
                                        result.append(',')
                        
                        i += 1
                        continue
                    
                    result.append(char)
                    i += 1
                
                return ''.join(result)
            
            # Try to fix and parse again
            try:
                fixed_text = fix_string_newlines(cleaned_text)
                fixed_text = fix_missing_commas(fixed_text)
                epics = json.loads(fixed_text)
                print(f"Successfully parsed after fixing JSON errors.")
                return epics
            except json.JSONDecodeError as e2:
                # Try one more time with array extraction
                try:
                    array_start = cleaned_text.find('[')
                    array_end = cleaned_text.rfind(']')
                    if array_start != -1 and array_end != -1:
                        array_text = cleaned_text[array_start:array_end+1]
                        fixed_text = fix_string_newlines(array_text)
                        fixed_text = fix_missing_commas(fixed_text)
                        epics = json.loads(fixed_text)
                        print(f"Successfully parsed after extracting array and fixing.")
                        return epics
                except (json.JSONDecodeError, Exception) as e3:
                    print(f"Still failed after fix attempts. Error: {e3}")
            
            return []

