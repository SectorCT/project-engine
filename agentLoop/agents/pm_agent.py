import json
from typing import List, Dict
from agents.base_agent import BaseAgent

class PMAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are a Pragmatic Project Manager.
Your goal is to read a Product Requirement Document (PRD) and break it down into actionable tasks for developers.

You will work in multiple steps:
1. First, identify Epics (major feature areas)
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
  {{"id": "1", "type": "epic", "title": "User Authentication", "description": "...", "assigned_to": "Backend Dev"}},
  {{"id": "2", "type": "epic", "title": "Dashboard", "description": "...", "assigned_to": "Frontend Dev"}}
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

Provide ONLY a JSON list of Story objects. Each Story should have:
- "id": A temporary ID as a string (e.g. "10", "11", "12")
- "type": "story"
- "title": Short summary
- "description": Detailed instructions for the developer
- "assigned_to": Role
- "parent_id": "{epic_id}" (MUST be exactly "{epic_id}" - the Epic's ID, NOT the story's own ID)

CRITICAL: parent_id MUST be "{epic_id}" for ALL stories. Do NOT use the story's own ID or any other value.

DO NOT include dependencies yet - that will be determined in the next step.

Example:
[
  {{"id": "10", "type": "story", "title": "Create HTML Structure", "description": "...", "assigned_to": "Frontend Dev", "parent_id": "{epic_id}"}},
  {{"id": "11", "type": "story", "title": "Add CSS Styling", "description": "...", "assigned_to": "Frontend Dev", "parent_id": "{epic_id}"}}
]
"""
        response_text = self.get_response(prompt)
        
        try:
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            stories = json.loads(cleaned_text)
            return stories
        except json.JSONDecodeError:
            print(f"Error parsing Stories JSON for Epic {epic_id}. Raw response:\n{response_text}")
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
- Epics can depend on other Epics (e.g., "Deploy" epic depends on "Develop" epic)
- Stories can depend on other Stories (e.g., CSS depends on HTML, JavaScript depends on HTML/CSS)
- Epics do NOT need to depend on their own Stories - that relationship is handled by parent_id
- Deployment/hosting stories should depend on ALL development stories in the same epic

Provide ONLY a JSON object with two keys: "epics" and "stories".
Each maps ticket IDs to their dependency lists.

Example:
{{
  "epics": {{
    "1": [],  // Develop epic has no dependencies
    "2": ["1"]  // Deploy epic depends on Develop epic
  }},
  "stories": {{
    "10": [],  // HTML has no dependencies
    "11": ["10"],  // CSS depends on HTML
    "12": ["10", "11"],  // JavaScript depends on HTML and CSS
    "20": ["10", "11", "12"]  // Deployment story depends on all development stories
  }}
}}

IMPORTANT: 
- Avoid circular dependencies
- Epic dependencies: Epics can depend on other Epics
- Story dependencies: Stories can depend on other Stories (not Epics - use parent_id for that)
- Epics never depend on their own Stories
"""
        response_text = self.get_response(prompt)
        
        try:
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
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
