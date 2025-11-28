from agents.base_agent import BaseAgent

class SummaryAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are the Project Secretary and Technical Writer.
Your goal is to read the discussion between the CEO and CTO and synthesize a concrete, actionable list of requirements and features.

Your Output Format:
1. **Project Vision**: A one-sentence summary.
2. **Core Features**: A bulleted list of features agreed upon.
3. **Tech Stack**: The agreed-upon technologies.
4. **Next Steps**: Immediate actions.

Do not include "I agree" or conversational filler. Just the facts.
"""
        super().__init__(
            name="Secretary",
            role="Technical Writer",
            system_prompt=system_prompt
        )

    def summarize(self, history_text: str) -> str:
        prompt = f"Review the following discussion and provide the final project summary:\n\n{history_text}"
        return self.get_response(prompt)

