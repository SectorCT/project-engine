import json
from typing import List, Dict
from agents.base_agent import BaseAgent

class PMAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are a Pragmatic Project Manager.
Your goal is to read a Product Requirement Document (PRD) and break it down into actionable tasks for developers.

You will work in multiple steps:
1. First, identify Epics (major feature areas). One of these MUST be a "Project Setup" epic.
2. Then, for each Epic, create Stories (specific tasks)
3. Finally, determine dependencies between Stories

Be logical and avoid circular dependencies.
"""
        super().__init__(
            name="Project Manager",
            role="Task Orchestrator",
            system_prompt=system_prompt
        )

    def generate_epics(self, prd_content: str) -> List[Dict]:
        """Step 1: Generate Epics only"""
        prompt = f"""Here is the PRD. Identify the major feature areas (Epics).
One of the Epics MUST be "Project Setup" (or similar) which will contain tasks for initializing the project structure.

PRD CONTENT:
{prd_content}

Provide ONLY a JSON list of Epic objects. Each Epic should have:
- "id": A temporary ID as a string (e.g. "1", "2")
- "type": "epic"
- "title": Short summary
- "description": What this epic covers
- "assigned_to": Role (e.g., "Frontend Dev", "Backend Dev", "Designer")

Example:
[
  {{"id": "1", "type": "epic", "title": "Project Setup", "description": "Initialize repo, Docker, CI/CD...", "assigned_to": "DevOps"}},
  {{"id": "2", "type": "epic", "title": "User Authentication", "description": "Login, Signup flows...", "assigned_to": "Backend Dev"}}
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
        
        prompt = f"""For the Epic "{epic_title}", create the Stories (specific tasks) needed to complete it.

EPIC DETAILS:
{json.dumps(epic, indent=2)}

PRD CONTENT (for context):
{prd_content}

REQUIREMENTS FOR STORIES:
1. Each story must be detailed and actionable.
2. The description must explain "what to do", "how to do it", and "success criteria".
3. Do NOT write one-sentence descriptions. Be verbose.
4. **PROJECT SETUP RESTRICTION**: If this is the "Project Setup" epic, tasks must be strictly limited to LOCAL project structure and configuration.
   - ALLOWED: Initialize git repo, create folder structure (src, public, tests), setup package.json/requirements.txt, create Dockerfile, configure linting.
   - FORBIDDEN: Do NOT create tasks for "Deployment", "Hosting", "Creating Accounts", "Cloud Services", or "CI/CD Pipelines" yet. Focus ONLY on the local codebase structure.

Provide ONLY a JSON list of Story objects. Each Story should have:
- "id": A temporary ID as a string (e.g. "10", "11", "12")
- "type": "story"
- "title": Short summary
- "description": DETAILED instructions for the developer. Include context, files to modify (if known), and expected outcome.
- "assigned_to": Role
- "parent_id": "{epic_id}" (MUST be exactly "{epic_id}" - the Epic's ID)

CRITICAL: parent_id MUST be "{epic_id}" for ALL stories. Do NOT use the story's own ID or any other value.

**IMPORTANT JSON FORMATTING RULE:**
You are writing JSON. All strings must be properly escaped.
Do NOT put literal newlines inside the "description" string.
Use `\\n` for newlines.

BAD:
"description": "First line
Second line"

GOOD:
"description": "First line\\nSecond line"

Example Description:
"Implement the User Login API endpoint.\\nContext: We need a secure way for users to log in.\\nTasks:\\n- Create POST /api/login route in `server.js`\\n- Validate email and password\\n- Return JWT token on success\\n- Handle errors (401 for invalid creds)\\n- Write unit test in `tests/auth.test.js`"

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
            
            stories = json.loads(cleaned_text)
            return stories
        except json.JSONDecodeError:
            # Fallback: Try to clean it more aggressively if needed, but usually finding [ ] is enough
            # If the response has unescaped newlines in descriptions (common in "Tasks: ..."), JSON fails.
            # We can try to fix common issues or just log it.
            # For now, let's log it. The prompt asks for JSON, but multi-line strings in JSON must be escaped \n.
            # OpenAI usually handles this well, but if "Tasks:\n- Item" is literal newline, it breaks.
            print(f"Error parsing Stories JSON for Epic {epic_id}. Raw response:\n{response_text}")
            
            # Last ditch effort: use a regex or manual parse if strict JSON fails?
            # Or just ask it to avoid newlines?
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
- **"Project Setup" Epic (and its stories) should generally come FIRST.**
- Epics can depend on other Epics.
- Stories can depend on other Stories.
- Deployment/hosting stories should depend on ALL development stories in the same epic.

Provide ONLY a JSON object with two keys: "epics" and "stories".
Each maps ticket IDs to their dependency lists.

Example:
{{
  "epics": {{
    "1": [],  // Project Setup - First
    "2": ["1"]  // Feature Epic - Depends on Setup
  }},
  "stories": {{
    "10": [],  // Setup Task 1
    "11": ["10"],  // Setup Task 2
    "20": ["10", "11"],  // Feature Task - Depends on Setup Tasks
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

    def generate_tickets(self, prd_content: str) -> List[Dict]:
        """Main method: Multi-step ticket generation"""
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
