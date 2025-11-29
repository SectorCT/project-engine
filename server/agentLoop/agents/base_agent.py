from typing import List, Dict, Optional
from openai import OpenAI
from config.settings import settings

class BaseAgent:
    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.messages: List[Dict[str, str]] = []
        self.reset()

    def reset(self):
        """Reset the agent's memory to the initial system prompt."""
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def load_state(self, messages: Optional[List[Dict[str, str]]] = None):
        """Hydrate the agent with a previously stored conversation."""
        if messages:
            self.messages = messages

    def dump_state(self) -> List[Dict[str, str]]:
        """Return the current conversation history for persistence."""
        return list(self.messages)

    def add_message(self, role: str, content: str):
        """Add a message to the agent's history."""
        self.messages.append({"role": role, "content": content})

    def get_response(self, context: Optional[str] = None) -> str:
        """Generate a response based on the current history and optional new context."""
        if context:
            self.add_message("user", context)

        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=self.messages,
                temperature=settings.OPENAI_TEMPERATURE
            )
            content = response.choices[0].message.content
            if content:
                self.add_message("assistant", content)
                return content
            return ""
        except Exception as e:
            print(f"Error generating response for {self.name}: {e}")
            return f"Error: {str(e)}"

