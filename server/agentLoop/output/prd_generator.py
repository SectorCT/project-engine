from datetime import datetime
from typing import List, Dict


class PRDGenerator:
    def render_prd(self, requirements: str, history: List[Dict[str, str]], project_name: str = "project") -> str:
        """
        Render a Master PRD Markdown string from the discussion.
        """
        # Find the Secretary's summary
        summary_content = "Summary not available."
        for entry in reversed(history):
            if entry['agent'] == 'Secretary':
                summary_content = entry['content']
                break

        content = f"# Master PRD: {project_name}\n\n"
        content += f"**Date:** {datetime.now().strftime('%Y-%m-%d')}\n\n"
        content += f"{summary_content}\n\n"
        return content

