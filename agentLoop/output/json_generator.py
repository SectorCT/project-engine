import json
import os
from datetime import datetime
from typing import List, Dict

class JSONGenerator:
    def __init__(self):
        self.output_dir = "project_data"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def generate_output(self, requirements: str, history: List[Dict[str, str]], project_name: str = "project"):
        """
        Generate a JSON file with the full discussion history.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_dir}/{project_name}_{timestamp}.json"
        
        data = {
            "project_name": project_name,
            "timestamp": timestamp,
            "requirements_summary": requirements,
            "discussion_history": history,
            "metadata": {
                "agent_count": 3,
                "agents": ["CEO", "CTO", "Secretary"]
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
            
        print(f"\nJSON output saved to: {filename}")
        return filename

