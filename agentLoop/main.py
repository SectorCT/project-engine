import os
import sys
import subprocess
from requirements.gatherer import RequirementsGatherer
from discussion.orchestrator import Orchestrator
from output.json_generator import JSONGenerator
from output.prd_generator import PRDGenerator
from config.settings import settings

def main():
    # Parse command line arguments
    stop_at = None
    if "--stop-at" in sys.argv:
        stop_at_idx = sys.argv.index("--stop-at")
        if stop_at_idx + 1 < len(sys.argv):
            stop_at = sys.argv[stop_at_idx + 1].lower()
        else:
            print("Error: --stop-at requires a stage name")
            print("Valid stages: requirements, discussion, prd, tickets")
            print("Note: By default (no --stop-at), the process continues through all stages including build.")
            return
    
    valid_stages = ["requirements", "discussion", "prd", "tickets"]
    if stop_at and stop_at not in valid_stages:
        print(f"Error: Invalid stage '{stop_at}'")
        print(f"Valid stages: {', '.join(valid_stages)}")
        print("Note: By default (no --stop-at), the process continues through all stages including build.")
        return
    
    print("==========================================")
    print("   Welcome to Project Engine: Executive   ")
    print("==========================================")
    
    if stop_at:
        print(f"Will stop at stage: {stop_at}")
    
    if not settings.OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not found in environment variables.")
        print("Please check your .env file.")
        return

    # Ensure output directories exist
    for directory in ["project_data", "project_docs"]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")

    # Step 1: Get Project Idea
    initial_idea = input("\nEnter your project idea: ")
    
    # Step 2: Refine Requirements (Client Relations)
    print("\n" + "=" * 50)
    print("STEP 1: Gathering Requirements")
    print("=" * 50)
    gatherer = RequirementsGatherer()
    requirements = gatherer.gather_requirements(initial_idea)
    
    print("\n------------------------------------------")
    print("Finalized Requirements Summary:")
    print(requirements)
    print("------------------------------------------\n")
    
    if stop_at == "requirements":
        print("\nStopped at 'requirements' stage (--stop-at=requirements)")
        return
    
    # Step 3: Executive Discussion (CEO, CTO, Legal)
    print("\n" + "=" * 50)
    print("STEP 2: Executive Discussion")
    print("=" * 50)
    print("Initializing Executive Team...")
    orchestrator = Orchestrator(requirements)
    history = orchestrator.start_discussion()
    
    if stop_at == "discussion":
        print("\nStopped at 'discussion' stage (--stop-at=discussion)")
        return
    
    # Step 4: Generate Outputs
    print("\n" + "=" * 50)
    print("STEP 3: Generating PRD")
    print("=" * 50)
    print("\nGenerating Project Documentation...")
    
    project_name = "project_idea" # In a real app, we'd extract this dynamically
    
    json_gen = JSONGenerator()
    json_gen.generate_output(requirements, history, project_name)
    
    prd_gen = PRDGenerator()
    prd_filename = prd_gen.generate_prd(requirements, history, project_name)
    
    # Ensure we have the full path (PRD generator returns relative path)
    if not os.path.isabs(prd_filename):
        prd_path = os.path.abspath(prd_filename)
    else:
        prd_path = prd_filename
    
    print(f"\nPRD generated: {prd_path}")
    
    if stop_at == "prd":
        print("\nStopped at 'prd' stage (--stop-at=prd)")
        print(f"You can continue later with: python build.py {prd_path}")
        return
    
    # Step 5: Automatically continue to build phase
    print("\n" + "=" * 50)
    print("STEP 4: Generating Tickets and Building")
    print("=" * 50)
    
    # Use subprocess to run build.py to keep it clean
    build_script = os.path.join(os.path.dirname(__file__), "build.py")
    
    if stop_at == "tickets":
        # Generate tickets but don't build
        print(f"\nContinuing to ticket generation (stopping before build)...")
        result = subprocess.run(
            [sys.executable, build_script, prd_path, "--no-build"],
            cwd=os.path.dirname(__file__)
        )
        if result.returncode == 0:
            print("\nStopped at 'tickets' stage (--stop-at=tickets)")
            print("You can continue later with: python build.py --build")
        else:
            print("\nError during ticket generation.")
        return
    
    # Full build (default)
    print(f"\nContinuing to ticket generation and build phase...")
    result = subprocess.run(
        [sys.executable, build_script, prd_path],
        cwd=os.path.dirname(__file__)
    )
    
    if result.returncode == 0:
        print("\n" + "=" * 50)
        print("Process Complete. Thank you for choosing Project Engine.")
        print("=" * 50)
    else:
        print("\nError during build phase.")

if __name__ == "__main__":
    main()

