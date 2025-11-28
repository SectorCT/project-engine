import os
from requirements.gatherer import RequirementsGatherer
from discussion.orchestrator import Orchestrator
from output.json_generator import JSONGenerator
from output.prd_generator import PRDGenerator
from config.settings import settings

def main():
    print("==========================================")
    print("   Welcome to Project Engine: Executive   ")
    print("==========================================")
    
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
    gatherer = RequirementsGatherer()
    requirements = gatherer.gather_requirements(initial_idea)
    
    print("\n------------------------------------------")
    print("Finalized Requirements Summary:")
    print(requirements)
    print("------------------------------------------\n")
    
    # Step 3: Executive Discussion (CEO, CTO, Legal)
    print("Initializing Executive Team...")
    orchestrator = Orchestrator(requirements)
    history = orchestrator.start_discussion()
    
    # Step 4: Generate Outputs
    print("\nGenerating Project Documentation...")
    
    project_name = "project_idea" # In a real app, we'd extract this dynamically
    
    json_gen = JSONGenerator()
    json_gen.generate_output(requirements, history, project_name)
    
    prd_gen = PRDGenerator()
    prd_gen.generate_prd(requirements, history, project_name)
    
    print("\nProcess Complete. Thank you for choosing Project Engine.")

if __name__ == "__main__":
    main()

