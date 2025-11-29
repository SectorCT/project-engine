from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List


class PRDGenerator:
    """
    Renders a PRD markdown string for the Django backend while preserving the
    original CLI-friendly file export behaviour for standalone runs.
    """

    def __init__(self) -> None:
        self.output_dir = "project_docs"
        os.makedirs(self.output_dir, exist_ok=True)

    def render_prd(self, requirements: str, history: List[Dict[str, str]], project_name: str = "project") -> str:
        """Return the PRD markdown content without touching the filesystem."""
        summary_content = self._extract_summary(history)
        content = [
            f"# Master PRD: {project_name}",
            "",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d')}",
            "",
            "## Client Requirements",
            requirements.strip(),
            "",
            "## Executive Discussion Summary",
            summary_content.strip() or "Summary not available.",
        ]
        return "\n".join(content).strip() + "\n"

    def generate_prd(self, requirements: str, history: List[Dict[str, str]], project_name: str = "project") -> str:
        """
        Generate a PRD file on disk for CLI usage.
        Returns the path to the written file.
        """
        content = self.render_prd(requirements, history, project_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_dir, f"{project_name}_PRD_{timestamp}.md")
        with open(filename, 'w', encoding='utf-8') as fh:
            fh.write(content)
        print(f"PRD output saved to: {filename}")
        return filename

    @staticmethod
    def _extract_summary(history: List[Dict[str, str]]) -> str:
        for entry in reversed(history):
            if entry.get('agent') == 'Secretary':
                return entry.get('content', '')
        return ""

