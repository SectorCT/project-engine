from __future__ import annotations

from typing import Dict, Optional

from agents.client_relations_agent import ClientRelationsAgent
from agentLoop.config.settings import settings


class RequirementsGatherer:
    """
    Stateful wrapper around the client relations agent so a caller (e.g. the Django backend)
    can drive the requirements conversation turn-by-turn and persist the agent's memory.
    """

    SUMMARY_PREFIX = "REQUIREMENTS_SUMMARY:"

    def __init__(self, state: Optional[Dict] = None):
        self.agent = ClientRelationsAgent()
        self.round_count = 0
        self.started = False

        if state:
            self.round_count = state.get("round_count", 0)
            self.started = state.get("started", False)
            messages = state.get("messages")
            if messages:
                self.agent.load_state(messages)

    def start(self, initial_idea: str) -> Dict[str, object]:
        """Begin the conversation with the user's initial idea."""
        if self.started:
            raise RuntimeError("requirements session already started")

        self.started = True
        context = (
            f"The user has this idea: '{initial_idea}'. "
            f"If it is vague, ask clarifying questions. "
            f"If it is detailed enough, summarize it starting with '{self.SUMMARY_PREFIX}'."
        )
        response = self.agent.get_response(context)
        return self._build_payload(response)

    def handle_user_message(self, message: str) -> Dict[str, object]:
        """Advance the conversation using the provided user message."""
        if not self.started:
            raise RuntimeError("requirements session has not been started")

        self.round_count += 1
        response = self.agent.get_response(message)
        return self._build_payload(response)

    def force_summary(self) -> Dict[str, object]:
        """Force the agent to summarize even if the summary keyword was not hit yet."""
        response = self.agent.get_response(
            f"We are out of time. Please summarize the requirements as they stand now, "
            f"starting with '{self.SUMMARY_PREFIX}'."
        )
        return self._build_payload(response)

    def serialize(self) -> Dict[str, object]:
        """Return the data needed to recreate this gatherer on a future call."""
        return {
            "round_count": self.round_count,
            "started": self.started,
            "messages": self.agent.dump_state(),
        }

    def _build_payload(self, response: str) -> Dict[str, object]:
        summary = ""
        finished = False

        if self.SUMMARY_PREFIX in response:
            finished = True
            summary = response.split(self.SUMMARY_PREFIX, 1)[1].strip()

        if self.round_count >= settings.MAX_REQUIREMENTS_ROUNDS and not finished:
            finished = True
            summary = summary or response

        return {
            "agent_name": self.agent.name,
            "agent_role": self.agent.role,
            "message": response,
            "stage": "requirements",
            "finished": finished,
            "summary": summary,
            "state": self.serialize(),
        }

