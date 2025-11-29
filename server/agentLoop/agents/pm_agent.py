import json
from typing import List, Dict
from agents.base_agent import BaseAgent

class PMAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are a Pragmatic Project Manager.
Your goal is to read a Product Requirement Document (PRD) and break it down into actionable tasks for developers.

You will work in multiple steps:
1. First, identify Epics (major feature areas). DO NOT create a "Project Setup" epic - project initialization is handled automatically.
2. Then, for each Epic, create Stories (specific tasks) with detailed plans
3. Finally, determine dependencies between Stories

Be logical and avoid circular dependencies.
Each story should be a small, logical step that's easy for AI to execute.
"""
        super().__init__(
            name="Project Manager",
            role="Task Orchestrator",
            system_prompt=system_prompt
        )
        self.project_structure = None  # Will be set before generating tickets

    def generate_epics(self, prd_content: str) -> List[Dict]:
        """Step 1: Generate Epics only"""
        structure_context = ""
        if self.project_structure:
            structure_context = f"\n\nPROJECT STRUCTURE (already initialized - DO NOT create setup tasks):\n{self.project_structure}"
        
        prompt = f"""Here is the PRD. Identify the major feature areas (Epics).
DO NOT create a "Project Setup" epic - the project structure is already initialized automatically.

PRD CONTENT:
{prd_content}{structure_context}

Provide ONLY a JSON list of Epic objects. Each Epic should have:
- "id": A temporary ID as a string (e.g. "1", "2")
- "type": "epic"
- "title": Short summary
- "description": What this epic covers
- "assigned_to": Role (e.g., "Frontend Dev", "Backend Dev", "Designer")

Example:
[
  {{"id": "1", "type": "epic", "title": "User Authentication", "description": "Login, Signup flows...", "assigned_to": "Backend Dev"}},
  {{"id": "2", "type": "epic", "title": "Dashboard UI", "description": "Main dashboard interface...", "assigned_to": "Frontend Dev"}}
]
"""
        response_text = self.get_response(prompt)
        
        try:
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            epics = json.loads(cleaned_text)
            return epics
        except json.JSONDecodeError:
            print(f"Error parsing Epics JSON. Raw response:\n{response_text}")
            return []

    def generate_stories_for_epic(self, epic: Dict, prd_content: str) -> List[Dict]:
        """Step 2: Generate Stories for a specific Epic"""
        epic_id = epic.get("id")
        epic_title = epic.get("title", "")
        
        structure_info = ""
        if self.project_structure:
            structure_info = f"\n\nPROJECT STRUCTURE (use this to know what files/folders already exist):\n{self.project_structure}"
        
        prompt = f"""For the Epic "{epic_title}", create the Stories (specific tasks) needed to complete it.
Each story should be a SMALL, LOGICAL STEP that's easy for AI to execute (one ticket = one logical step).

EPIC DETAILS:
{json.dumps(epic, indent=2)}

PRD CONTENT (for context):
{prd_content}{structure_info}

REQUIREMENTS FOR STORIES:
1. Break down into SMALL, ATOMIC tasks. Each story should be one logical step.
2. Each story description MUST include these sections:
   - **Context**: Explain what's happening and why this task is needed
   - **Goal**: What we aim to achieve with this specific task
   - **Development Plan**: Step-by-step approach (numbered list)
   - **Files Needed**: List of files to create/modify (use project structure to know what exists)
   - **Implementation Details**: Specific code changes, patterns to follow, examples
3. Be VERY detailed and specific. The AI coder needs clear instructions.
4. DO NOT create deployment, hosting, or CI/CD tasks - those are automated.
5. Use TypeScript for all code (frontend: React+TS, backend: Express+TS).

**CRITICAL SIMPLICITY RULES:**
- If there is NO BACKEND, DO NOT suggest databases, SQL, or any data storage systems.
- For simple data (lists, arrays, mappings, static content), create a JSON file in a `data/` or `src/data/` folder.
- Examples: fun facts → `src/data/funFacts.json`, color palettes → `src/data/colors.json`, shape definitions → `src/data/shapes.json`
- Keep it simple: JSON files for data, components for UI, utilities for helpers.
- Only use databases/backend storage if the project explicitly requires a backend (user data, authentication, real-time updates, etc.).

**CRITICAL INTEGRATION RULES:**
- When creating components, ALWAYS specify WHERE they should be used (root page, specific route, nested component, etc.).
- When integrating components, specify EXACTLY where in the file they should be placed (e.g., "Replace the existing content in App.tsx's return statement", "Add as a new section after the header", "Create a new page component in src/pages/ and update routing").
- Specify the PAGE STRUCTURE: Is this the root page (/)? A new route? A section of an existing page?
- After creating a component, the NEXT story should explain how to integrate it (where to import, where to render, what props to pass).
- Be explicit about component hierarchy: "This component will be used in App.tsx" or "This will be a page-level component accessible at /shapes".

Provide ONLY a JSON list of Story objects. Each Story should have:
- "id": A temporary ID as a string (e.g. "10", "11", "12")
- "type": "story"
- "title": Short summary (one specific action)
- "description": MUST follow this format:
  Context: [explain what's happening and why]\\n\\nGoal: [what we aim to achieve]\\n\\nDevelopment Plan:\\n1. [step one]\\n2. [step two]\\n3. [step three]\\n\\nFiles Needed:\\n- path/to/file.ts (create|modify)\\n- another/file.ts (create|modify)\\n\\nImplementation: [specific code changes, patterns, examples]
- "assigned_to": Role
- "parent_id": "{epic_id}" (MUST be exactly "{epic_id}")

CRITICAL: parent_id MUST be "{epic_id}" for ALL stories.

**IMPORTANT JSON FORMATTING RULE:**
You are writing JSON. All strings must be properly escaped.
Do NOT put literal newlines inside the "description" string.
Use `\\n` for newlines.

Example Descriptions:

For BACKEND tasks (only if backend exists):
"Context: We need user authentication for the app. Users must be able to log in securely.\\n\\nGoal: Create a secure login endpoint that validates credentials and returns JWT tokens.\\n\\nDevelopment Plan:\\n1. Create POST /api/login route in server/routes/auth.ts\\n2. Add validation middleware for email/password format\\n3. Implement JWT token generation utility\\n4. Add error handling for invalid credentials\\n\\nFiles Needed:\\n- server/routes/auth.ts (create)\\n- server/middleware/validation.ts (create)\\n- server/utils/jwt.ts (create)\\n\\nImplementation: Create POST endpoint that accepts {{email, password}}, validates format, checks against user store, generates JWT on success, returns 401 on failure. Use Express Request/Response types."

For FRONTEND component creation:
"Context: We need to display basic shapes on the website. Each shape should be rendered as a visual element.\\n\\nGoal: Create a reusable Shape component that can render different shapes (circle, square, triangle, rectangle).\\n\\nDevelopment Plan:\\n1. Create src/components/Shape.tsx file\\n2. Define a functional component that accepts shape type and size as props\\n3. Use SVG or CSS to render the shape based on the type prop\\n4. Export the component for use in other files\\n\\nFiles Needed:\\n- src/components/Shape.tsx (create)\\n\\nImplementation: Create a React functional component with props: {{shapeType: 'circle' | 'square' | 'triangle' | 'rectangle', size?: number}}. Use SVG paths or CSS border-radius/transform to render shapes. This component will be used in the main App.tsx page to display all shapes."

For FRONTEND data tasks (NO backend):
"Context: We need to display fun facts about shapes on the website.\\n\\nGoal: Create a simple JSON file containing fun facts for each shape.\\n\\nDevelopment Plan:\\n1. Create src/data/funFacts.json file\\n2. Define JSON structure with shape names and arrays of facts\\n3. Add fun facts for each shape (circle, square, triangle, rectangle)\\n\\nFiles Needed:\\n- src/data/funFacts.json (create)\\n\\nImplementation: Create a JSON file with structure like: [{{shape: 'circle', facts: ['fact1', 'fact2']}}, ...]. Keep it simple - just a static JSON file, no database needed."

For FRONTEND integration tasks:
"Context: We have created Shape components and fun facts data. Now we need to display them on the main page.\\n\\nGoal: Integrate the Shape component and fun facts data into the root App.tsx page to display all shapes with their facts.\\n\\nDevelopment Plan:\\n1. Import Shape component from src/components/Shape.tsx into src/App.tsx\\n2. Import funFacts data from src/data/funFacts.json\\n3. Replace the existing placeholder content in App.tsx's return statement\\n4. Map over the funFacts array to render each shape with its facts\\n5. Pass shape type and facts as props to the Shape component\\n\\nFiles Needed:\\n- src/App.tsx (modify - replace the existing return statement)\\n- src/components/Shape.tsx (already created, will be imported)\\n- src/data/funFacts.json (already created, will be imported)\\n\\nImplementation: In App.tsx, replace the current return statement with a layout that maps over funFacts. For each item, render a Shape component with shapeType={{item.shape}} and display the facts array below it. This will be the root page (/) of the website."

DO NOT include dependencies yet - that will be determined in the next step.
"""
        response_text = self.get_response(prompt)
        
        # The model sometimes puts extra text or comments that break JSON parsing.
        # We need to be robust.
        try:
            # Basic cleanup
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            
            # Sometimes the model returns just the array, sometimes it wraps it.
            # If it fails, we can try to find the first [ and last ]
            if not cleaned_text.startswith("["):
                start = cleaned_text.find("[")
                end = cleaned_text.rfind("]")
                if start != -1 and end != -1:
                    cleaned_text = cleaned_text[start:end+1]
            
            # Fix literal newlines in JSON strings (common issue)
            # The model sometimes includes literal newlines instead of escaped ones
            import re
            # Simple approach: replace literal newlines/tabs/carriage returns that appear
            # between quotes (but not escaped ones)
            # This regex matches: " then any chars (including newlines) until the next unescaped "
            def fix_string_newlines(text):
                # Replace literal control characters within string values
                # We'll do this by finding string patterns and fixing them
                result = []
                i = 0
                in_string = False
                escape_next = False
                
                while i < len(text):
                    char = text[i]
                    
                    if escape_next:
                        result.append(char)
                        escape_next = False
                    elif char == '\\':
                        result.append(char)
                        escape_next = True
                    elif char == '"' and not escape_next:
                        in_string = not in_string
                        result.append(char)
                    elif in_string:
                        # Inside a string - escape control characters
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
            
            # Try parsing first
            stories = json.loads(cleaned_text)
            return stories
        except json.JSONDecodeError as e:
            # Log the actual parsing error for debugging
            print(f"Error parsing Stories JSON for Epic {epic_id}.")
            print(f"JSON Error: {str(e)}")
            if hasattr(e, 'pos'):
                print(f"Error at position: {e.pos}")
                # Show context around error
                start = max(0, e.pos - 50)
                end = min(len(cleaned_text), e.pos + 50)
                print(f"Context: ...{cleaned_text[start:end]}...")
            
            # Try to fix literal newlines in string values
            try:
                fixed_text = fix_string_newlines(cleaned_text)
                stories = json.loads(fixed_text)
                print(f"Successfully parsed after fixing newlines.")
                return stories
            except json.JSONDecodeError as e2:
                print(f"Still failed after fix attempt. Error: {e2}")
                print(f"Raw response (first 500 chars):\n{response_text[:500]}")
                return []

    def generate_dependencies(self, all_epics: List[Dict], all_stories: List[Dict], prd_content: str) -> Dict[str, Dict[str, List[str]]]:
        """Step 3: Generate dependencies between Epics and Stories"""
        epics_json = json.dumps(all_epics, indent=2)
        stories_json = json.dumps(all_stories, indent=2)
        
        prompt = f"""Given these Epics and Stories, determine the dependencies.

EPICS:
{epics_json}

STORIES:
{stories_json}

PRD CONTENT (for context):
{prd_content}

Think logically about the order:
- Epics can depend on other Epics.
- Stories can depend on other Stories.
- Base features should come before dependent features.

Provide ONLY a JSON object with two keys: "epics" and "stories".
Each maps ticket IDs to their dependency lists.

Example:
{{
  "epics": {{
    "1": [],  // Base Epic - No dependencies
    "2": ["1"]  // Feature Epic - Depends on Base
  }},
  "stories": {{
    "10": [],  // Base Task 1
    "11": ["10"],  // Base Task 2 - Depends on Task 1
    "20": ["11"],  // Feature Task - Depends on Base Tasks
    "21": ["20"]
  }}
}}

IMPORTANT: 
- Avoid circular dependencies
- Epic dependencies: Epics can depend on other Epics
- Story dependencies: Stories can depend on other Stories (not Epics - use parent_id for that)
"""
        response_text = self.get_response(prompt)
        
        try:
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            if not cleaned_text.startswith("{"):
                start = cleaned_text.find("{")
                end = cleaned_text.rfind("}")
                if start != -1 and end != -1:
                    cleaned_text = cleaned_text[start:end+1]
            dependencies = json.loads(cleaned_text)
            return dependencies
        except json.JSONDecodeError:
            print(f"Error parsing Dependencies JSON. Raw response:\n{response_text}")
            return {}

    def generate_tickets(self, prd_content: str, project_structure: Dict = None) -> List[Dict]:
        """Main method: Multi-step ticket generation"""
        # Store project structure for context
        if project_structure:
            from systems.project_initializer import ProjectInitializer
            self.project_structure = ProjectInitializer.get_structure_summary(project_structure)
        
        print("  Step 1: Generating Epics...")
        epics = self.generate_epics(prd_content)
        
        if not epics:
            print("No Epics generated.")
            return []
        
        print(f"  Generated {len(epics)} Epics")
        
        all_tickets = []
        all_stories = []
        
        # Add epics to tickets
        for epic in epics:
            all_tickets.append(epic)
        
        # Generate stories for each epic
        for epic in epics:
            print(f"  Step 2: Generating Stories for Epic '{epic.get('title')}'...")
            stories = self.generate_stories_for_epic(epic, prd_content)
            all_tickets.extend(stories)
            all_stories.extend(stories)
            print(f"    Generated {len(stories)} Stories")
        
        # Generate dependencies
        print("  Step 3: Generating dependencies...")
        dependencies_map = self.generate_dependencies(epics, all_stories, prd_content)
        
        # Apply Epic dependencies
        epic_deps = dependencies_map.get("epics", {})
        for epic in epics:
            epic_id = str(epic.get("id", ""))
            if epic_id in epic_deps:
                epic["dependencies"] = epic_deps[epic_id]
            else:
                epic["dependencies"] = []
        
        # Apply Story dependencies
        story_deps = dependencies_map.get("stories", {})
        for story in all_stories:
            story_id = str(story.get("id", ""))
            if story_id in story_deps:
                story["dependencies"] = story_deps[story_id]
            else:
                story["dependencies"] = []
        
        print(f"    Resolved dependencies for {len(epic_deps)} Epics and {len(story_deps)} Stories")
        
        return all_tickets
