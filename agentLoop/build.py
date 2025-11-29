import sys
import os
import time
from typing import List, Dict
from agents.master_pm_agent import MasterPMAgent
from agents.frontend_pm_agent import FrontendPMAgent
from agents.backend_pm_agent import BackendPMAgent
from agents.coder_agent import CoderAgent
from systems.ticket_system import TicketSystem
from systems.docker_env import DockerEnv
from systems.project_initializer import ProjectInitializer
from config.settings import settings

def build_phase(prd_path: str = None):
    """
    The Build Phase:
    1. Get project structure info from PRD (if provided) or determine from tickets
    2. Spin up Docker Environment
    3. Initialize project structure in Docker
    4. Iterate through tickets
    5. Coder Agent resolves them using Cursor CLI
    
    Args:
        prd_path: Optional path to PRD file to determine project structure (backend/frontend)
    """
    print("\n--- Starting Build Phase ---")
    
    # Initialize Systems
    ticket_system = TicketSystem()
    
    # 1. Get all "todo" tickets
    all_tickets = ticket_system.get_tickets()
    
    # Filter out Epics - we only build Stories/Tasks
    todo_tickets = [
        t for t in all_tickets 
        if t.get('status') == 'todo' and t.get('type') != 'epic'
    ]
    
    if not todo_tickets:
        print("No 'todo' tickets found (excluding Epics). Nothing to build.")
        return

    print(f"Found {len(todo_tickets)} tickets to resolve.")

    # 2. Determine has_backend and has_frontend
    # If PRD is provided, read it to determine structure
    # Otherwise, infer from tickets
    if prd_path and os.path.exists(prd_path):
        print(f"Reading PRD from: {prd_path} to determine project structure...")
        with open(prd_path, 'r') as f:
            prd_content = f.read()
        
        # Simple heuristic: check PRD content for backend/frontend keywords
        prd_lower = prd_content.lower()
        has_backend = any(keyword in prd_lower for keyword in ['backend', 'api', 'server', 'database', 'mongodb', 'express'])
        has_frontend = any(keyword in prd_lower for keyword in ['frontend', 'ui', 'component', 'react', 'vite', 'interface'])
        
        # Default to both if we can't determine from PRD
        if not has_backend and not has_frontend:
            has_backend = True
            has_frontend = True
    else:
        # Fallback: determine from tickets
        has_backend = any('backend' in str(t.get('title', '')).lower() or 'api' in str(t.get('title', '')).lower() or 'server' in str(t.get('title', '')).lower() for t in all_tickets)
        has_frontend = any('frontend' in str(t.get('title', '')).lower() or 'ui' in str(t.get('title', '')).lower() or 'component' in str(t.get('title', '')).lower() for t in all_tickets)
        
        # Default to both if we can't determine
        if not has_backend and not has_frontend:
            has_backend = True
            has_frontend = True
    
    print(f"Project structure: backend={has_backend}, frontend={has_frontend}")
    
    # 3. Get project structure
    project_structure = ProjectInitializer.get_project_structure(has_backend, has_frontend)
    
    # 4. Initialize Docker Env
    workspace_path = os.getcwd() # Not used for copying, but kept for compatibility
    docker_env = DockerEnv(workspace_path)
    
    try:
        docker_env.build_image()
        docker_env.start_container(has_backend=has_backend)
        
        # 5. Initialize project structure in Docker
        ProjectInitializer.init_project(project_structure, docker_env)
        
        # 5.5. Start MongoDB service if backend exists
        if has_backend:
            print("\nStarting MongoDB service...")
            # MongoDB will be started by _setup_mongodb() in init_project()
            # But we verify it's running here
            time.sleep(2)  # Give MongoDB time to start
            exit_code, output = docker_env.exec_run(
                "mongosh --eval 'db.adminCommand(\"ping\")' --quiet",
                workdir="/app"
            )
            if exit_code == 0:
                print("✅ MongoDB is running and accessible.")
            else:
                print(f"⚠️  MongoDB verification failed (exit code: {exit_code})")
                print(f"Output: {output[:500]}")
        
        # 5.5. Install npm dependencies
        print("\nInstalling npm dependencies...")
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
            # Look up parent context if available
            parent_context = ""
            parent_id = ticket.get("parent_id")
            if parent_id:
                # Find the epic in all_tickets
                # Check both mongo string ID and original ID formats just in case
                parent_epic = next((t for t in all_tickets if str(t.get('_id')) == str(parent_id) or str(t.get('id')) == str(parent_id)), None)
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
            
            # Update ticket status based on success
            # Get the ticket ID (MongoDB uses '_id', local JSON uses 'id')
            ticket_id = ticket.get('_id') or ticket.get('id')
            
            if success:
                if ticket_id:
                    try:
                        ticket_system.update_ticket_status(str(ticket_id), "done")
                        print(f"✅ Ticket '{ticket.get('title')}' marked as DONE.")
                    except Exception as e:
                        print(f"⚠️  Failed to update ticket status: {e}")
                        print(f"   Ticket ID was: {ticket_id}")
                else:
                    print(f"⚠️  Could not find ticket ID for '{ticket.get('title')}'")
            else:
                # Mark as failed
                if ticket_id:
                    try:
                        ticket_system.update_ticket_status(str(ticket_id), "failed")
                        print(f"❌ Ticket '{ticket.get('title')}' marked as FAILED.")
                    except Exception as e:
                        print(f"⚠️  Failed to update ticket status: {e}")
                        print(f"   Ticket ID was: {ticket_id}")
                else:
                    print(f"⚠️  Could not find ticket ID for '{ticket.get('title')}'")
                
    finally:
        # Cleanup
        # We explicitly do NOT stop the container as requested
        print("\nKeeping container running as requested.")
        print("Container port 3000 is exposed - frontend accessible at http://localhost:3000")
        if has_backend:
            print("Container port 27017 is exposed on host port 6666 - MongoDB accessible at mongodb://localhost:6666")
        print("You can inspect the container with: docker exec project_engine_builder_container ls -la /app")
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
        
        # Verify MongoDB if backend exists
        if has_backend:
            print("\nVerifying MongoDB service...")
            time.sleep(2)  # Give MongoDB time to start
            exit_code, output = docker_env.exec_run(
                "mongosh --eval 'db.adminCommand(\"ping\")' --quiet",
                workdir="/app"
            )
            if exit_code == 0:
                print("✅ MongoDB is running and accessible.")
            else:
                print(f"⚠️  MongoDB verification failed (exit code: {exit_code})")
                print(f"Output: {output[:500]}")
        
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
        if has_backend:
            print("MongoDB is running with port 27017 exposed on host port 6666.")
            print("MongoDB URI: mongodb://localhost:6666/project_db")
            print("MongoDB config file: server/mongodb.config.ts")
        print("\nYou can inspect the container with:")
        print("  docker exec project_engine_builder_container ls -la /app")
        print("  docker exec project_engine_builder_container find /app -type f")
        print("\nTo run npm commands inside the container:")
        print("  docker exec project_engine_builder_container npm <command>")
        print("  Example: docker exec project_engine_builder_container npm run dev")
        print("  (Then access http://localhost:3000 in your browser)")
        if has_backend:
            print("\nTo connect to MongoDB from host:")
            print("  mongosh mongodb://localhost:6666/project_db")
        print("\nTo stop the container:")
        print("  docker stop project_engine_builder_container")
        print("  docker rm project_engine_builder_container")
        
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        raise


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--build":
        # Check if PRD path is provided as second argument
        prd_path = sys.argv[2] if len(sys.argv) > 2 else None
        build_phase(prd_path=prd_path)
        return
    
    if len(sys.argv) > 1 and sys.argv[1] == "--init":
        init_structure_only()
        return

    if len(sys.argv) < 2:
        print("Usage: python build.py <path_to_prd.md> [--no-build]")
        print("       python build.py --build [<path_to_prd.md>]  # Build from existing tickets (optionally use PRD for structure)")
        print("       python build.py --init       # Initialize structure only (for testing)")
        print("")
        print("By default, running with a PRD will generate tickets AND run the build phase.")
        print("Use --no-build to skip the build phase after ticket generation.")
        print("Use --build <prd_path> to build from existing tickets but use PRD to determine project structure.")
        return

    # Check for --no-build flag
    skip_build = "--no-build" in sys.argv
    
    # Get PRD path (first non-flag argument)
    prd_path = None
    for arg in sys.argv[1:]:
        if arg not in ["--no-build"]:
            prd_path = arg
            break
    
    if not prd_path:
        print("Error: PRD file path is required.")
        return
        
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
    
    # Get project structure before PM agents
    project_structure_dict = ProjectInitializer.get_project_structure(has_backend, has_frontend)
    project_structure = ProjectInitializer.get_structure_summary(project_structure_dict)
    print(f"Project structure: backend={has_backend}, frontend={has_frontend}")
    
    # Step 1: Master PM creates functional epics
    master_pm = MasterPMAgent()
    master_pm.project_structure = project_structure
    
    print("\n=== Step 1: Master PM creating functional epics ===")
    functional_epics = master_pm.generate_functional_epics(prd_content)
    
    if not functional_epics:
        print("No functional epics were generated. Please check the logs or try again.")
        return
    
    print(f"Generated {len(functional_epics)} functional epics.")
    
    # Step 2: Create functional epics first (to get their DB IDs)
    print("\n=== Creating functional epics ===")
    functional_epic_db_ids = {}  # Map functional epic temp_id to DB ID
    
    for epic in functional_epics:
        func_epic_temp_id = str(epic.get("id")) if epic.get("id") else None
        func_epic_db_id = ticket_system.create_ticket(
            type="epic",
            title=epic.get("title", "Untitled"),
            description=epic.get("description", ""),
            assigned_to=epic.get("assigned_to", "Master PM"),
            dependencies=[],
            parent_id=None
        )
        if func_epic_temp_id:
            functional_epic_db_ids[func_epic_temp_id] = func_epic_db_id
        print(f"  [+] Created FUNCTIONAL EPIC: {epic.get('title')} (ID: {func_epic_db_id})")
    
    # Step 3: Generate frontend and backend epics/stories for each functional epic
    # Create them immediately as we generate them
    frontend_pm = FrontendPMAgent()
    frontend_pm.project_structure = project_structure
    
    backend_pm = BackendPMAgent()
    backend_pm.project_structure = project_structure
    
    backend_epic_db_ids = {}  # Track backend epic DB IDs for frontend dependencies
    
    for functional_epic in functional_epics:
        func_epic_title = functional_epic.get("title", "")
        func_epic_temp_id = str(functional_epic.get("id")) if functional_epic.get("id") else None
        func_epic_db_id = functional_epic_db_ids.get(func_epic_temp_id) if func_epic_temp_id else None
        
        print(f"\n=== Processing functional epic: {func_epic_title} ===")
        
        backend_epic_db_id = None
        
        # Generate backend epic and stories
        if has_backend:
            print(f"  Backend PM creating epic and stories...")
            backend_result = backend_pm.generate_backend_epic_and_stories(functional_epic, prd_content)
            if backend_result.get("epic"):
                backend_epic = backend_result["epic"]
                
                # Create backend epic immediately
                backend_epic_db_id = ticket_system.create_ticket(
                    type="epic",
                    title=backend_epic.get("title", "Untitled"),
                    description=backend_epic.get("description", ""),
                    assigned_to=backend_epic.get("assigned_to", "Backend Dev"),
                    dependencies=[],
                    parent_id=func_epic_db_id
                )
                print(f"    [+] Created BACKEND EPIC: {backend_epic.get('title')} (ID: {backend_epic_db_id})")
                
                # Create backend stories immediately with the epic as parent
                for story in backend_result.get("stories", []):
                    story_db_id = ticket_system.create_ticket(
                        type="story",
                        title=story.get("title", "Untitled"),
                        description=story.get("description", ""),
                        assigned_to=story.get("assigned_to", "Backend Dev"),
                        dependencies=[],
                        parent_id=backend_epic_db_id
                    )
                    print(f"      [+] Created BACKEND STORY: {story.get('title')} (ID: {story_db_id})")
                
                print(f"    Created backend epic with {len(backend_result.get('stories', []))} stories")
        
        # Generate frontend epic and stories
        if has_frontend:
            print(f"  Frontend PM creating epic and stories...")
            frontend_result = frontend_pm.generate_frontend_epic_and_stories(functional_epic, prd_content)
            if frontend_result.get("epic"):
                frontend_epic = frontend_result["epic"]
                
                # Create frontend epic immediately (depends on backend epic if it exists)
                frontend_epic_db_id = ticket_system.create_ticket(
                    type="epic",
                    title=frontend_epic.get("title", "Untitled"),
                    description=frontend_epic.get("description", ""),
                    assigned_to=frontend_epic.get("assigned_to", "Frontend Dev"),
                    dependencies=[backend_epic_db_id] if backend_epic_db_id else [],
                    parent_id=func_epic_db_id
                )
                if backend_epic_db_id:
                    print(f"    [+] Created FRONTEND EPIC: {frontend_epic.get('title')} (ID: {frontend_epic_db_id}, depends on backend)")
                else:
                    print(f"    [+] Created FRONTEND EPIC: {frontend_epic.get('title')} (ID: {frontend_epic_db_id})")
                
                # Create frontend stories immediately with the epic as parent
                for story in frontend_result.get("stories", []):
                    story_db_id = ticket_system.create_ticket(
                        type="story",
                        title=story.get("title", "Untitled"),
                        description=story.get("description", ""),
                        assigned_to=story.get("assigned_to", "Frontend Dev"),
                        dependencies=[],
                        parent_id=frontend_epic_db_id
                    )
                    print(f"      [+] Created FRONTEND STORY: {story.get('title')} (ID: {story_db_id})")
                
                print(f"    Created frontend epic with {len(frontend_result.get('stories', []))} stories")
    
    # Cleanup: Delete epics with no stories
    print(f"\n=== Cleaning up epics with no stories ===")
    all_tickets = ticket_system.get_tickets()
    epics = [t for t in all_tickets if t.get("type") == "epic"]
    stories = [t for t in all_tickets if t.get("type") == "story"]
    
    # Build a map of epic IDs to story counts
    epic_id_to_story_count = {}
    for story in stories:
        parent_id = story.get("parent_id")
        if parent_id:
            # Normalize parent_id (could be ObjectId or string)
            parent_id_str = str(parent_id)
            epic_id_to_story_count[parent_id_str] = epic_id_to_story_count.get(parent_id_str, 0) + 1
    
    # Find and delete epics with no stories
    deleted_count = 0
    for epic in epics:
        epic_id = str(epic.get("_id") or epic.get("id"))
        story_count = epic_id_to_story_count.get(epic_id, 0)
        
        if story_count == 0:
            print(f"  Deleting epic '{epic.get('title')}' (ID: {epic_id}) - no stories")
            if ticket_system.delete_ticket(epic_id):
                deleted_count += 1
    
    if deleted_count > 0:
        print(f"  Deleted {deleted_count} epics with no stories")
    else:
        print(f"  No epics to delete - all epics have stories")
    
    print(f"\n✅ Ticket generation complete!")
    print(f"   - {len(functional_epics)} functional epics created")
    print(f"   - All epics and stories created with correct parent relationships")
    
    return  # Ticket generation complete

    print("\nBuild Planning Complete.")
    print(f"Tickets saved to {ticket_system.local_file} (or MongoDB if configured).")
    
    # Automatically run build phase unless --no-build flag is set
    if not skip_build:
        print("\n" + "=" * 80)
        print("Starting Build Phase automatically...")
        print("=" * 80)
        build_phase()
    else:
        print("\nSkipping build phase (--no-build flag set).")
        print("Run 'python build.py --build' to execute the build phase later.")

if __name__ == "__main__":
    main()
