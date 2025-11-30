import json
from typing import Dict, List

from agents.base_agent import BaseAgent


class FrontendPMAgent(BaseAgent):
    """
    Converts functional epics into frontend-specific epics/stories (UI, UX, components).
    Keeps things simple for configuration-only changes.
    """

    def __init__(self) -> None:
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
"""
        super().__init__(
            name="Frontend PM",
            role="Frontend Epic and Story Creator",
            system_prompt=system_prompt,
        )
        self.project_structure: str | None = None

    def generate_frontend_epic_and_stories(self, functional_epic: Dict, prd_content: str) -> Dict:
        structure_info = (
            f"\n\nPROJECT STRUCTURE (use this to know what files/folders already exist):\n{self.project_structure}"
            if self.project_structure
            else ""
        )

        prompt = f"""For the functional epic "{functional_epic.get('title', '')}", create:
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

**CRITICAL AUTHENTICATION RULES:**
- **MANDATORY PAIRING**: If you create ANY login/authentication functionality, you MUST also create signup/registration functionality.
- Login and Signup are ALWAYS created together - never create one without the other.
- **If this functional epic is about authentication/login, you MUST create BOTH:**
  1. "Create Login Page UI" OR "Create Login Form Component" story
  2. "Create Signup Page UI" OR "Create Registration Page UI" story
  3. "Integrate Login API" story
  4. "Integrate Signup API" OR "Integrate Registration API" story
- **NEVER create only login stories without signup stories** - this is a critical error.
- **Example**: If creating "Create Login Form Component", you MUST also create "Create Signup Form Component" and both API integration stories (4 stories minimum for authentication epics).

Each story should include context, goal, steps, files, and implementation hints.
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

        def fix_missing_commas(text: str) -> str:
            """Fix missing commas in JSON - adds commas after closing quotes when followed by a key."""
            result: List[str] = []
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
        
        try:
            cleaned_text = fix_string_newlines(cleaned_text)
            cleaned_text = fix_missing_commas(cleaned_text)
            result = json.loads(cleaned_text)
            # Validate and add missing signup stories
            result = self._validate_and_add_signup_stories(result, functional_epic)
            return result
        except json.JSONDecodeError as e:
            print(f"Frontend PM failed to parse JSON for epic {functional_epic.get('title')}")
            print(f"JSON Error: {str(e)}")
            print(response_text[:600])
            
            # Try one more time with array extraction
            try:
                array_start = cleaned_text.find('[')
                array_end = cleaned_text.rfind(']')
                if array_start != -1 and array_end != -1:
                    array_text = cleaned_text[array_start:array_end+1]
                    fixed_text = fix_string_newlines(array_text)
                    fixed_text = fix_missing_commas(fixed_text)
                    result = json.loads(fixed_text)
                    print(f"Successfully parsed after extracting array and fixing.")
                    # Validate and add missing signup stories
                    result = self._validate_and_add_signup_stories(result, functional_epic)
                    return result
            except (json.JSONDecodeError, Exception) as e2:
                print(f"Still failed after fix attempts. Error: {e2}")
            
            return {"epic": None, "stories": []}

    def _validate_and_add_signup_stories(self, result: Dict, functional_epic: Dict) -> Dict:
        """Validate that login stories have corresponding signup stories, and add missing ones."""
        if not result or "stories" not in result:
            return result
        
        stories = result.get("stories", [])
        if not stories:
            return result
        
        # Check if this functional epic is about authentication/login
        epic_title = functional_epic.get('title', '').lower()
        is_auth_epic = any(keyword in epic_title for keyword in ['login', 'authentication', 'auth', 'user authentication'])
        
        if not is_auth_epic:
            return result
        
        # Find login-related stories
        login_stories = []
        signup_stories = []
        
        for story in stories:
            title_lower = story.get('title', '').lower()
            if any(keyword in title_lower for keyword in ['login', 'log in']):
                login_stories.append(story)
            elif any(keyword in title_lower for keyword in ['signup', 'sign up', 'registration', 'register']):
                signup_stories.append(story)
        
        # If we have login stories but no signup stories, add them
        if login_stories and not signup_stories:
            print(f"⚠️  WARNING: Found login stories without signup stories in epic '{functional_epic.get('title')}'. Adding missing signup stories...")
            
            # Get the highest story ID to continue numbering
            max_id = 0
            for story in stories:
                try:
                    story_id = int(story.get('id', '0'))
                    max_id = max(max_id, story_id)
                except:
                    pass
            
            # Get epic ID from result
            epic_id = result.get('epic', {}).get('id', '1')
            
            new_stories = []
            
            # Add frontend signup page and API integration stories
            max_id += 1
            new_stories.append({
                "id": str(max_id),
                "type": "story",
                "title": "Create Signup Page UI",
                "description": "Context: Users need to be able to create new accounts. We have a login page but no signup page.\\n\\nGoal: Create a signup/registration page component that allows users to register with email and password.\\n\\nDevelopment Plan:\\n1. Create src/pages/Signup.tsx or src/components/SignupForm.tsx\\n2. Add form fields: email, password, confirm password\\n3. Add form validation (email format, password strength, password match)\\n4. Add form state management with React useState\\n5. Style the form to match the login page design\\n6. Add error handling and display error messages\\n\\nFiles Needed:\\n- src/pages/Signup.tsx (create) OR src/components/SignupForm.tsx (create)\\n- src/App.tsx (modify - add route for signup page)\\n\\nImplementation: Create a React functional component with form fields for email, password, and confirm password. Use useState for form state. Add validation for email format and password match. Style consistently with the login page. This will be accessible at /signup route.",
                "assigned_to": "Frontend Dev",
                "parent_id": epic_id
            })
            
            max_id += 1
            new_stories.append({
                "id": str(max_id),
                "type": "story",
                "title": "Integrate Signup API",
                "description": "Context: We have created a signup page UI and a backend registration endpoint. Now we need to connect them.\\n\\nGoal: Integrate the signup form with the backend registration API endpoint.\\n\\nDevelopment Plan:\\n1. Add signup API function to src/utils/api.ts\\n2. Import and use the signup API function in the signup page/component\\n3. Call the API on form submission\\n4. Handle success (redirect to login or auto-login)\\n5. Handle errors (display error messages)\\n6. Add loading state during API call\\n\\nFiles Needed:\\n- src/utils/api.ts (modify - add signup/register function)\\n- src/pages/Signup.tsx or src/components/SignupForm.tsx (modify - add API integration)\\n\\nImplementation: In the signup component, add an onSubmit handler that calls the signup API function with form data. Use fetch() to POST to /api/register. On success, either redirect to login page or automatically log the user in. On error, display the error message to the user.",
                "assigned_to": "Frontend Dev",
                "parent_id": epic_id
            })
            
            stories.extend(new_stories)
            result["stories"] = stories
            print(f"✅ Added {len(new_stories)} missing signup/registration story(ies)")
        
        return result

