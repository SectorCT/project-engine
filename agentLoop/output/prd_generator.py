import os
from datetime import datetime
from typing import List, Dict

class PRDGenerator:
    def __init__(self):
        self.output_dir = "project_docs"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def generate_prd(self, requirements: str, history: List[Dict[str, str]], project_name: str = "project"):
        """
        Generate a Master PRD Markdown file from the discussion.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_dir}/{project_name}_PRD_{timestamp}.md"
        
        # Find the Secretary's summary
        summary_content = "Summary not available."
        for entry in reversed(history):
            if entry['agent'] == 'Secretary':
                summary_content = entry['content']
                break

        content = f"# Master PRD: {project_name}\n\n"
        content += f"**Date:** {datetime.now().strftime('%Y-%m-%d')}\n\n"
        
        # Use the Secretary's structured output as the main content
        content += f"{summary_content}\n\n"
        
        # Appendix removed as requested
        
        with open(filename, 'w') as f:
            f.write(content)
            
        print(f"PRD output saved to: {filename}")
        return filename

