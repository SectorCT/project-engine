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
    
    for t in tickets_data:
        temp_id = t.get("id") # e.g. "1"
        
        # Create the ticket (initially with empty dependencies to avoid broken links)
        real_id = ticket_system.create_ticket(
            type=t.get("type", "story"),
            title=t.get("title", "Untitled"),
            description=t.get("description", ""),
            assigned_to=t.get("assigned_to", "Unassigned"),
            dependencies=[] # We will fill this in pass 2
        )
        
        if temp_id:
            temp_id_to_db_id[temp_id] = real_id
        
        # Store for pass 2
        t['real_db_id'] = real_id
        final_tickets.append(t)
        print(f"  [+] Created {t.get('type').upper()}: {t.get('title')} (ID: {real_id})")

    # Second pass: Update dependencies
    print("Resolving dependencies...")
    # Note: This requires ticket_system to support 'update_ticket'.
    # If it doesn't, we might have to just accept that dependencies are text or do a hack.
    # Let's add update support or just do it in one pass if we assume order?
    # No, order isn't guaranteed.
    
    # Let's add a quick update method to ticket_system if we can, or re-save.
    # Since we are using MongoDB or local file, we can update.
    
    # If we don't want to edit ticket_system right now, we can rely on the fact that
    # the User said "dependencies array has the wrong id".
    # So we MUST fix it.
    
    # Let's just use a simple helper in build.py to update the dependencies
    # But we can't easily update if we don't have an update method.
    # Okay, let's ADD an update method to ticket_system.py first.
    pass 

    # Wait, I can't edit ticket_system.py in this block.
    # I will edit ticket_system.py in a separate step to add `update_dependencies`.
    
    # For now, let's assume we have `update_dependencies`.
    for t in final_tickets:
        raw_deps = t.get("dependencies", [])
        real_deps = []
        for d in raw_deps:
            # d might be "1" or "2"
            if str(d) in temp_id_to_db_id:
                real_deps.append(temp_id_to_db_id[str(d)])
            else:
                real_deps.append(d) # Keep as is if not found (maybe external dep?)
        
        if real_deps:
             ticket_system.update_ticket_dependencies(t['real_db_id'], real_deps)

    print("\nBuild Planning Complete.")
    print(f"Tickets saved to {ticket_system.local_file} (or MongoDB if configured).")

if __name__ == "__main__":
    main()


