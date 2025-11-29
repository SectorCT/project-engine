import sys
import os
import time
from typing import Any, Dict, List, Optional
from agents.pm_agent import PMAgent
from agents.coder_agent import CoderAgent
from systems.ticket_system import TicketSystem
from systems.docker_env import DockerEnv
from systems.project_initializer import ProjectInitializer
from config.settings import settings


class BuildCallbackAdapter:
    """Lightweight adapter that forwards events to the provided delegate if present."""

    def __init__(self, delegate: Optional[Any] = None):
        self.delegate = delegate

    def stage(self, stage: str, message: str):
        if self.delegate and hasattr(self.delegate, 'on_stage'):
            try:
                self.delegate.on_stage(stage=stage, message=message)
            except Exception:
                pass

    def ticket(self, ticket: Dict, status: str, message: str = '', extra: Optional[Dict[str, Any]] = None):
        if not self.delegate or not hasattr(self.delegate, 'on_ticket_progress'):
            return
        ticket_id = str(ticket.get('id') or ticket.get('_id') or '')
        payload = extra or {}
        try:
            self.delegate.on_ticket_progress(
                ticket_id=ticket_id,
                status=status,
                message=message,
                extra=payload,
            )
        except Exception:
            pass

    def log(self, message: str):
        if self.delegate and hasattr(self.delegate, 'on_log'):
            try:
                self.delegate.on_log(message)
            except Exception:
                pass

    def error(self, message: str):
        if self.delegate and hasattr(self.delegate, 'on_error'):
            try:
                self.delegate.on_error(message)
            except Exception:
                pass

    def complete(self, message: str):
        if self.delegate and hasattr(self.delegate, 'on_complete'):
            try:
                self.delegate.on_complete(message)
            except Exception:
                pass

def build_phase(job_id: Optional[str] = None, callbacks: Optional[Any] = None):
    """
    The Build Phase:
    1. Get project structure info from tickets or determine has_backend/has_frontend
    2. Spin up Docker Environment
    3. Initialize project structure in Docker
    4. Iterate through tickets
    5. Coder Agent resolves them using Cursor CLI
    """
    print("\n--- Starting Build Phase ---")
    cb = BuildCallbackAdapter(callbacks)
    cb.stage("Build Preparation", "Starting build phase")
    
    # Initialize Systems
    ticket_system = TicketSystem(job_id=job_id)
    
    # 1. Get all "todo" tickets
    all_tickets = ticket_system.get_tickets()
    
    # Filter out Epics - we only build Stories/Tasks
    todo_tickets = [
        t for t in all_tickets 
        if t.get('type') != 'epic' and str(t.get('status', 'todo')).lower() in ('todo', 'pending', 'in_progress')
    ]
    
    if not todo_tickets:
        print("No 'todo' tickets found (excluding Epics). Nothing to build.")
        cb.stage("Build Preparation", "No tickets to execute.")
        cb.complete("No tickets required execution.")
        return

    print(f"Found {len(todo_tickets)} tickets to resolve.")

    # 2. Determine has_backend and has_frontend from tickets or use defaults
    # For now, we'll check if there are backend/frontend related tickets
    # In the future, this should come from the discussion/PRD
    has_backend = any('backend' in str(t.get('title', '')).lower() or 'api' in str(t.get('title', '')).lower() or 'server' in str(t.get('title', '')).lower() for t in all_tickets)
    has_frontend = any('frontend' in str(t.get('title', '')).lower() or 'ui' in str(t.get('title', '')).lower() or 'component' in str(t.get('title', '')).lower() for t in all_tickets)
    
    # Default to both if we can't determine
    if not has_backend and not has_frontend:
        has_backend = True
        has_frontend = True
    
    project_structure = ProjectInitializer.get_project_structure(has_backend, has_frontend)
    cb.stage("Environment", f"Project structure resolved. backend={has_backend}, frontend={has_frontend}")
    
    # 3. Get project structure
    # 4. Initialize Docker Env
    workspace_path = os.getcwd()  # Not used for copying, but kept for compatibility
    docker_env = DockerEnv(workspace_path, project_id=job_id)
    
    try:
        cb.stage("Environment", "Building Docker image")
        docker_env.build_image()
        cb.stage("Environment", "Starting Docker container")
        docker_env.start_container(has_backend=has_backend)
        
        # 5. Initialize project structure in Docker
        cb.stage("Environment", "Initializing project structure")
        ProjectInitializer.init_project(project_structure, docker_env)
        
        # 5.5. Install npm dependencies
        print("\nInstalling npm dependencies...")
        cb.stage("Environment", "Installing npm dependencies")
        exit_code, output = docker_env.exec_run("npm install", workdir="/app")
        if exit_code == 0:
            print("✅ npm install completed successfully!")
        else:
            print(f"⚠️  npm install had issues (exit code: {exit_code})")
            print(f"Output: {output[:500]}")
        
        # 6. Initialize Coder Agent
        coder_agent = CoderAgent()
        
        # 7. Loop through tickets and execute cursor commands
        for ticket in todo_tickets:
            ticket_id = str(ticket.get('id') or ticket.get('_id') or '')
            cb.ticket(
                ticket,
                'in_progress',
                message=f"Starting ticket {ticket.get('title')}",
                extra={'title': ticket.get('title')},
            )
            # Look up parent context if available
            parent_context = ""
            parent_id = ticket.get("parent_id")
            if parent_id:
                parent_epic = next(
                    (
                        t
                        for t in all_tickets
                        if str(t.get('_id') or t.get('id')) == str(parent_id)
                    ),
                    None,
                )
                if parent_epic:
                     parent_context = f"Title: {parent_epic.get('title')}\nDescription: {parent_epic.get('description')}"

            # Pass full context to the coder agent
            success = coder_agent.resolve_ticket(
                ticket, 
                docker_env, 
                parent_context=parent_context,
                project_structure=project_structure,
                all_tickets=all_tickets
            )
            
            if success:
                ticket['status'] = 'done'
                if ticket_id:
                    try:
                        ticket_system.update_ticket_status(str(ticket_id), 'done')
                    except Exception as exc:
                        print(f"⚠️  Failed to update ticket status in TicketSystem: {exc}")
                cb.ticket(
                    ticket,
                    'done',
                    message=f"Ticket {ticket.get('title')} completed",
                    extra={'title': ticket.get('title')},
                )
                print(f"Ticket {ticket.get('title')} marked as DONE.")
            else:
                ticket['status'] = 'failed'
                if ticket_id:
                    try:
                        ticket_system.update_ticket_status(str(ticket_id), 'failed', check_epic_completion=False)
                    except Exception as exc:
                        print(f"⚠️  Failed to update ticket status in TicketSystem: {exc}")
                cb.ticket(
                    ticket,
                    'failed',
                    message=f"Ticket {ticket.get('title')} failed",
                    extra={'title': ticket.get('title')},
                )
                print(f"Ticket {ticket.get('title')} FAILED. Skipping.")
                
        cb.complete("Ticket execution finished")
    except Exception as exc:
        cb.error(str(exc))
        raise
    finally:
        # Cleanup
        # We explicitly do NOT stop the container as requested
        print("\nKeeping container running as requested.")
        print("Container port 3000 is exposed - frontend accessible at http://localhost:3000")
        print(f"You can inspect the container with: docker exec {docker_env.container_name} ls -la /app")
        # docker_env.stop_container()


def init_structure_only():
    """
    Initialize project structure in Docker and stop.
    Useful for testing the file structure creation.
    """
    print("\n--- Initializing Project Structure Only ---")
    
    # Initialize Systems
    ticket_system = TicketSystem()
    
    # Get all tickets to determine structure
    all_tickets = ticket_system.get_tickets()
    
    # Determine has_backend and has_frontend from tickets or use defaults
    has_backend = any('backend' in str(t.get('title', '')).lower() or 'api' in str(t.get('title', '')).lower() or 'server' in str(t.get('title', '')).lower() for t in all_tickets)
    has_frontend = any('frontend' in str(t.get('title', '')).lower() or 'ui' in str(t.get('title', '')).lower() or 'component' in str(t.get('title', '')).lower() for t in all_tickets)
    
    # Default to both if we can't determine
    if not has_backend and not has_frontend:
        has_backend = True
        has_frontend = True
    
    print(f"Project structure: backend={has_backend}, frontend={has_frontend}")
    
    # Get project structure
    project_structure = ProjectInitializer.get_project_structure(has_backend, has_frontend)
    
    # Initialize Docker Env
    workspace_path = os.getcwd()
    docker_env = DockerEnv(workspace_path)
    
    try:
        print("Building Docker image...")
        docker_env.build_image()
        
        print("Starting Docker container...")
        docker_env.start_container(has_backend=has_backend)
        
        print("Initializing project structure in Docker...")
        ProjectInitializer.init_project(project_structure, docker_env)
        
        print("\nInstalling npm dependencies...")
        exit_code, output = docker_env.exec_run("npm install", workdir="/app")
        if exit_code == 0:
            print("✅ npm install completed successfully!")
        else:
            print(f"⚠️  npm install had issues (exit code: {exit_code})")
            print(f"Output: {output[:500]}")
        
        print("\n✅ Project structure initialized successfully!")
        print("Container is running with port 3000 exposed.")
        print("Frontend will be accessible at: http://localhost:3000")
        print("\nYou can inspect the container with:")
        print(f"  docker exec {docker_env.container_name} ls -la /app")
        print(f"  docker exec {docker_env.container_name} find /app -type f")
        print("\nTo run npm commands inside the container:")
        print(f"  docker exec {docker_env.container_name} npm <command>")
        print(f"  Example: docker exec {docker_env.container_name} npm run dev")
        print("  (Then access http://localhost:3000 in your browser)")
        print("\nTo stop the container:")
        print(f"  docker stop {docker_env.container_name}")
        print(f"  docker rm {docker_env.container_name}")
        
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        raise


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--build":
        build_phase()
        return
    
    if len(sys.argv) > 1 and sys.argv[1] == "--init":
        init_structure_only()
        return

    if len(sys.argv) < 2:
        print("Usage: python build.py <path_to_prd.md>")
        print("       python build.py --build      # Full build (tickets + agent)")
        print("       python build.py --init       # Initialize structure only (for testing)")
        return

    prd_path = sys.argv[1]
    if not os.path.exists(prd_path):
        print(f"Error: File '{prd_path}' not found.")
        return

    if not settings.OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not found in environment variables.")
        return

    print(f"--- Initializing Build Flow ---")
    print(f"Reading PRD from: {prd_path}")

    with open(prd_path, 'r') as f:
        prd_content = f.read()

    # Initialize Systems
    ticket_system = TicketSystem()
    
    # Determine has_backend and has_frontend
    # For now, we'll need to parse from PRD or get from user
    # TODO: Extract from CTO/CEO discussion or PRD
    # For now, defaulting to both - this should be determined from discussion
    print("\nDetermining project structure requirements...")
    has_backend = True  # TODO: Extract from discussion/PRD
    has_frontend = True  # TODO: Extract from discussion/PRD
    
    # Get project structure before PM agent
    project_structure = ProjectInitializer.get_project_structure(has_backend, has_frontend)
    print(f"Project structure: backend={has_backend}, frontend={has_frontend}")
    
    pm_agent = PMAgent()

    print("\nPM Agent is analyzing the PRD and generating tickets...")
    tickets_data = pm_agent.generate_tickets(prd_content, project_structure=project_structure)

    if not tickets_data:
        print("No tickets were generated. Please check the logs or try again.")
        return

    print(f"\nGenerated {len(tickets_data)} tickets. Saving to system...")
    
    # Fix parent_id: Stories should point to their Epic, not to other stories
    epics = [t for t in tickets_data if t.get("type") == "epic"]
    stories = [t for t in tickets_data if t.get("type") == "story"]
    
    # Build a map of epic temp IDs to epic objects
    epic_map = {str(epic.get("id")): epic for epic in epics}
    story_map = {str(s.get("id")): s for s in stories}
    
    # Fix stories: if parent_id points to a story or is wrong, find the correct epic
    # Stories are generated in batches after their epic, so we'll use order-based matching
    current_epic = None
    for ticket in tickets_data:
        if ticket.get("type") == "epic":
            current_epic = ticket
        elif ticket.get("type") == "story":
            current_parent = str(ticket.get("parent_id", ""))
            
            # Check if parent_id is valid (points to an epic)
            if current_parent in epic_map:
                # Good, it's already correct
                continue
            
            # Check if parent_id points to a story (wrong) or is empty/wrong
            parent_is_story = current_parent in story_map
            parent_is_self = current_parent == str(ticket.get("id"))
            
            if parent_is_story or parent_is_self or not current_parent or current_parent not in epic_map:
                # Fix: assign to the current epic (last epic we saw)
                if current_epic:
                    correct_epic_id = str(current_epic.get("id"))
                    ticket["parent_id"] = correct_epic_id
                    print(f"  Fixed parent_id for '{ticket.get('title')}': {current_parent} -> {correct_epic_id}")
                else:
                    # No epic found, assign to first epic as fallback
                    if epics:
                        correct_epic_id = str(epics[0].get("id"))
                        ticket["parent_id"] = correct_epic_id
                        print(f"  Fixed parent_id for '{ticket.get('title')}': {current_parent} -> {correct_epic_id} (fallback)")

    # Map temporary PM-generated IDs (e.g. "1", "2") to real DB IDs (e.g. "692a...")
    # so we can resolve dependencies correctly.
    temp_id_to_db_id = {}

    # First pass: Create tickets to get DB IDs
    final_tickets = []
    
    for idx, t in enumerate(tickets_data):
        # If PM agent didn't provide an id, auto-assign one based on position
        if t.get("id") is None:
            t["id"] = str(idx + 1)
        
        temp_id = str(t.get("id")) if t.get("id") is not None else None # Ensure string
        
        # Create the ticket (initially with empty dependencies to avoid broken links)
        real_id = ticket_system.create_ticket(
            type=t.get("type", "story"),
            title=t.get("title", "Untitled"),
            description=t.get("description", ""),
            assigned_to=t.get("assigned_to", "Unassigned"),
            dependencies=[], # We will fill this in pass 2
            parent_id=None   # We will fill this in pass 2
        )
        
        if temp_id:
            temp_id_to_db_id[temp_id] = real_id
        
        # Store for pass 2
        t['real_db_id'] = real_id
        final_tickets.append(t)
        print(f"  [+] Created {t.get('type').upper()}: {t.get('title')} (ID: {real_id})")

    # Second pass: Update dependencies and parent
    print("Resolving dependencies and parents...")
    
    # Check for circular dependencies before applying
    def has_circular_dependency(ticket_id: str, deps: List[str], all_tickets: List[Dict], visited: set = None) -> bool:
        """Check if adding these dependencies would create a cycle"""
        if visited is None:
            visited = set()
        
        ticket_id_str = str(ticket_id)
        if ticket_id_str in visited:
            return True  # Circular!
        
        visited.add(ticket_id_str)
        
        for dep_id in deps:
            dep_ticket = next((t for t in all_tickets if str(t.get("id")) == str(dep_id)), None)
            if dep_ticket:
                dep_deps = dep_ticket.get("dependencies", [])
                if has_circular_dependency(dep_id, dep_deps, all_tickets, visited.copy()):
                    return True
        
        return False
    
    for t in final_tickets:
        # 1. Update Dependencies
        # Filter out dependencies that point to the Epic (use parent_id for that relationship)
        ticket_type = t.get("type", "story")
        raw_deps = t.get("dependencies", [])
        real_deps = []
        
        for d in raw_deps:
            d_str = str(d)
            if d_str in temp_id_to_db_id:
                dep_ticket = next((t2 for t2 in final_tickets if str(t2.get("id")) == d_str), None)
                
                # If this is a Story depending on an Epic, skip it (use parent_id instead)
                if ticket_type == "story" and dep_ticket and dep_ticket.get("type") == "epic":
                    # Stories should not depend on Epics - parent_id handles that relationship
                    continue
                
                # Epics can depend on other Epics, Stories can depend on other Stories
                # Check for circular dependency
                if not has_circular_dependency(t.get("id"), [d_str], final_tickets):
                    real_deps.append(temp_id_to_db_id[d_str])
                else:
                    print(f"  WARNING: Skipping circular dependency for ticket {t.get('title')} -> {dep_ticket.get('title') if dep_ticket else d_str}")
            else:
                # Skip unknown dependencies
                pass
        
        if real_deps:
            # Pass as strings - update_ticket_dependencies will convert to ObjectIds
            real_deps_str = [str(d) for d in real_deps]
            ticket_system.update_ticket_dependencies(t['real_db_id'], real_deps_str)

        # 2. Update Parent
        raw_parent = t.get("parent_id")
        if raw_parent:
            parent_str = str(raw_parent)
            if parent_str in temp_id_to_db_id:
                real_parent = temp_id_to_db_id[parent_str]
                ticket_system.update_ticket_parent(t['real_db_id'], str(real_parent))

    print("\nBuild Planning Complete.")
    print(f"Tickets saved to {ticket_system.local_file} (or MongoDB if configured).")


def run_ticket_builder(job_id: str, callbacks: Optional[Any] = None):
    """Entry point used by Django backend to execute tickets for a specific job."""
    return build_phase(job_id=job_id, callbacks=callbacks)


if __name__ == "__main__":
    main()
