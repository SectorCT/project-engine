import json
from typing import List, Dict
from agents.base_agent import BaseAgent

class FrontendPMAgent(BaseAgent):
    """
    Frontend PM Agent - Takes functional epics and creates frontend epics + stories.
    Creates UI components, pages, API integration, and user interactions.
    """
    def __init__(self):
        system_prompt = """You are a Frontend Project Manager.
Your goal is to take functional epics and break them down into frontend-specific epics and stories.

You create:
1. Frontend Epics - UI/UX feature areas (one per functional epic)
2. Frontend Stories - Specific tasks for UI components, pages, API integration, user interactions

CRITICAL - RECOGNIZE SIMPLE TASKS:
- If the functional epic is a simple configuration change (e.g., "change port", "update config"), create ONE simple story, not multiple stories.
- Simple config changes don't need components, pages, or API integration - just file edits.
- Examples: "Change port from 5000 to 7000" = ONE story to edit vite.config.ts
- Don't create components, pages, or API integration for simple config changes.

Focus on: React components, pages, forms, API calls, user interactions, displays, routing.
But ONLY when needed - simple config changes are just file edits.
"""
        super().__init__(
            name="Frontend PM",
            role="Frontend Epic and Story Creator",
            system_prompt=system_prompt
        )
        self.project_structure = None

    def generate_frontend_epic_and_stories(self, functional_epic: Dict, prd_content: str) -> Dict:
        """
        Generate a frontend epic and its stories for a given functional epic.
        Returns: {"epic": {...}, "stories": [...]}
        """
        functional_epic_id = functional_epic.get("id")
        functional_epic_title = functional_epic.get("title", "")
        
        structure_info = ""
        if self.project_structure:
            structure_info = f"\n\nPROJECT STRUCTURE (use this to know what files/folders already exist):\n{self.project_structure}"
        
        prompt = f"""For the functional epic "{functional_epic_title}", create:
1. ONE Frontend Epic (UI/UX implementation of this feature)
2. Frontend Stories (specific tasks - but keep it SIMPLE for simple changes)

FUNCTIONAL EPIC DETAILS:
{json.dumps(functional_epic, indent=2)}

PRD CONTENT (for context):
{prd_content}{structure_info}

**CRITICAL - SIMPLICITY FIRST:**
- If this is a SIMPLE configuration change (e.g., "change port", "update config value", "modify setting"), create ONLY ONE story that directly edits the file.
- Simple config changes do NOT need: components, pages, API integration, user interactions, state management, or routing.
- Example: "Change port from 5000 to 7000" = ONE story: "Update port in vite.config.ts from 5000 to 7000"
- Don't create multiple stories for a simple file edit.

**FRONTEND EPIC:**
- Title: "{functional_epic_title} (Frontend)"
- Description: Frontend UI/UX implementation of {functional_epic_title}
- assigned_to: "Frontend Dev"
- This epic will be a child of the functional epic (parent_id will be set separately)

**FRONTEND STORIES:**
For COMPLEX features, create stories for:
- UI components (forms, displays, buttons, modals, etc.)
- Pages/routes (ALWAYS include integration details: routing, navigation)
- API integration (calling backend endpoints)
- User interactions (click handlers, form submissions, etc.)
- State management
- Routing and navigation

CRITICAL FOR PAGES/ROUTES:
When creating a page/route story, ALWAYS specify in the description:
1. How the page is accessed (URL route, navigation link, button click, etc.)
2. Where navigation to this page exists (navbar, menu, button, etc.)
3. How it integrates with the app structure (routing setup)
4. If it's a home/landing page, specify it should be the default route (/)
Example: "Create HomePage component at / route, accessible as default route and via navbar 'Home' link. Add route to router configuration and ensure it's the default route."

For SIMPLE config changes, create ONE story that directly edits the file.

Each story should be SMALL and ATOMIC. Include:
- Context: Why this task is needed
- Goal: What we aim to achieve
- Development Plan: Step-by-step approach (for pages, include routing and navigation steps)
- Files Needed: List of files to create/modify (in src/ directory)
- Implementation: Specific code changes (for pages, include routing setup)

Provide ONLY a JSON object with this structure:
{{
  "epic": {{
    "id": "F1",  // Temporary ID for frontend epic
    "type": "epic",
    "title": "{functional_epic_title} (Frontend)",
    "description": "Frontend UI/UX implementation of {functional_epic_title}",
    "assigned_to": "Frontend Dev",
    "functional_epic_id": "{functional_epic_id}"  // Reference to functional epic
  }},
  "stories": [
    {{
      "id": "FS1",
      "type": "story",
      "title": "Create [Component Name] Component",
      "description": "Context: [why]\\n\\nGoal: [what]\\n\\nDevelopment Plan:\\n1. [step]\\n2. [step]\\n\\nFiles Needed:\\n- src/components/[name].tsx (create)\\n\\nImplementation: [details]",
      "assigned_to": "Frontend Dev"
    }}
  ]
}}

**CRITICAL JSON FORMATTING RULES:**
1. You are writing VALID JSON. The response MUST be parseable JSON.
2. All strings must be properly escaped. Use `\\n` for newlines, NOT literal newlines.
3. Description strings must be on ONE LINE in the JSON with `\\n` for line breaks.
4. Before responding, verify your JSON is valid.
"""
        response_text = self.get_response(prompt)
        
        # Fix literal newlines in JSON strings
        def fix_string_newlines(text):
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
                    if char == '\n':
                        result.append('\\n')
                    elif char == '\r':
                        result.append('\\r')
                    elif char == '\t':
                        result.append('\\t')
                    else:
                        result.append(char)
                else:
                    result.append(char)
                
                i += 1
            
            return ''.join(result)
        
        try:
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            if not cleaned_text.startswith("{"):
                start = cleaned_text.find("{")
                end = cleaned_text.rfind("}")
                if start != -1 and end != -1:
                    cleaned_text = cleaned_text[start:end+1]
            
            # Always apply fix_string_newlines before parsing
            cleaned_text = fix_string_newlines(cleaned_text)
            result = json.loads(cleaned_text)
            return result
        except json.JSONDecodeError as e:
            print(f"Error parsing Frontend Epic/Stories JSON for {functional_epic_title}.")
            print(f"JSON Error: {str(e)}")
            if hasattr(e, 'pos'):
                print(f"Error at position: {e.pos}")
                start = max(0, e.pos - 100)
                end = min(len(cleaned_text), e.pos + 100)
                print(f"Context: ...{cleaned_text[start:end]}...")
            
            # Try one more time with the fix (sometimes it needs multiple passes)
            try:
                fixed_text = fix_string_newlines(cleaned_text)
                # Try parsing again
                result = json.loads(fixed_text)
                print(f"Successfully parsed after second fix attempt.")
                return result
            except (json.JSONDecodeError, Exception) as e3:
                print(f"Still failed after second fix attempt. Error: {e3}")
                # Try fixing missing commas after string fields
                try:
                    import re
                    # Fix missing commas: look for "field": "value" followed by "field" (missing comma)
                    # Pattern: "value"\n\s*"field" -> "value",\n\s*"field"
                    fixed_text = re.sub(r'"\s*\n\s*"([a-zA-Z_][a-zA-Z0-9_]*)"\s*:', r'",\n    "\1":', cleaned_text)
                    # Also fix: "value"\s+"field" (same line, missing comma)
                    fixed_text = re.sub(r'"\s+"([a-zA-Z_][a-zA-Z0-9_]*)"\s*:', r'", "\1":', fixed_text)
                    # Apply newline fix again
                    fixed_text = fix_string_newlines(fixed_text)
                    result = json.loads(fixed_text)
                    print(f"Successfully parsed after comma fix.")
                    return result
                except Exception as e4:
                    print(f"Comma fix failed. Error: {e4}")
                    # Last resort: try to manually extract and fix just the description fields
                    try:
                        import re
                        # Find all description fields and fix them
                        def replace_newlines_in_quotes(match):
                            full_match = match.group(0)
                            # Replace literal newlines with \n in the matched string
                            fixed = full_match.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                            return fixed
                        
                        # Match: "description": "..." handling escaped quotes
                        # This is a simple approach: find strings that span multiple lines
                        pattern = r'"description"\s*:\s*"[^"]*(?:\n[^"]*)*"'
                        fixed_text = re.sub(pattern, replace_newlines_in_quotes, cleaned_text, flags=re.MULTILINE)
                        # Also try to fix missing commas after description
                        fixed_text = re.sub(r'(description"\s*:\s*"[^"]*")\s*\n\s*"([a-zA-Z_])', r'\1,\n    "\2', fixed_text)
                        result = json.loads(fixed_text)
                        print(f"Successfully parsed after manual description fix.")
                        return result
                    except Exception as e5:
                        print(f"All fix attempts failed. Error: {e5}")
                        print(f"Raw response (first 1000 chars):\n{response_text[:1000]}")
                        return {"epic": None, "stories": []}

