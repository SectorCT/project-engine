import sys
import os
from agents.pm_agent import PMAgent
from systems.ticket_system import TicketSystem
from config.settings import settings

def main():
    if len(sys.argv) < 2:
        print("Usage: python build.py <path_to_prd.md>")
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
    pm_agent = PMAgent()

    print("\nPM Agent is analyzing the PRD and generating tickets...")
    tickets_data = pm_agent.generate_tickets(prd_content)

    if not tickets_data:
        print("No tickets were generated. Please check the logs or try again.")
        return

    print(f"\nGenerated {len(tickets_data)} tickets. Saving to system...")

    # Map temporary PM-generated IDs (e.g. "1", "2") to real DB IDs (e.g. "692a...")
    # so we can resolve dependencies correctly.
    temp_id_to_db_id = {}

    # First pass: Create tickets to get DB IDs
    # We have to do this carefully if dependencies must exist before creation.
    # But usually dependencies are just string references. 
    # We will insert them, then update dependencies? 
    # OR, simpler: Insert them all, collect map, then update the dependencies in the DB?
    # Let's do a 2-pass approach:
    # 1. Create all tickets (without dependencies or with raw temp IDs)
    # 2. Update tickets with real dependency IDs
    
    # Actually, simpler: PM gives us a list. We iterate. 
    # If dependency "1" is needed for "2", we need "1" ID.
    # If the list is sorted by dependencies, we are good. If not, we might need 2 passes.
    
    # Let's blindly create them all first to get IDs.
    
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
    
    for t in final_tickets:
        # 1. Update Dependencies
        # Filter out dependencies that point to the Epic (use parent_id for that relationship)
        ticket_type = t.get("type", "story")
        raw_deps = t.get("dependencies", [])
        real_deps = []
        
        for d in raw_deps:
            d_str = str(d)
            if d_str in temp_id_to_db_id:
                # Check if this dependency is an Epic - if so, skip it (use parent_id instead)
                dep_ticket = next((t2 for t2 in final_tickets if str(t2.get("id")) == d_str), None)
                if dep_ticket and dep_ticket.get("type") == "epic":
                    # Skip Epic dependencies - parent_id handles that relationship
                    continue
                real_deps.append(temp_id_to_db_id[d_str])
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

if __name__ == "__main__":
    main()


