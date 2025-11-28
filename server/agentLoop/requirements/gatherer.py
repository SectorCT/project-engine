from typing import Dict, Optional

from agents.client_relations_agent import ClientRelationsAgent
from config.settings import settings


class RequirementsGatherer:
    """Structured wrapper around the client-relations agent for programmable interactions."""

    SUMMARY_PREFIX = "REQUIREMENTS_SUMMARY:"

    def __init__(self, state: Optional[Dict] = None):
        self.agent = ClientRelationsAgent()
        self.round_count = 0
        self.started = False

        if state:
            self.round_count = state.get('round_count', 0)
            self.started = state.get('started', False)
            self.agent.load_state(state.get('messages'))

    def start(self, initial_idea: str) -> Dict:
        """Kick off the clarification phase with the initial idea."""
        if self.started:
            raise RuntimeError('Session already started')

        self.started = True
        context = (
            f"The user has this idea: '{initial_idea}'. Review it. "
            "If it's vague, ask clarifying questions. If it's detailed enough, summarize it "
            f"starting with '{self.SUMMARY_PREFIX}'."
        )
        response = self.agent.get_response(context)
        return self._build_payload(response)

    def handle_user_message(self, message: str) -> Dict:
        """Process a user reply and return the agent's next response."""
        if not self.started:
            raise RuntimeError('Session has not been started')

        self.round_count += 1
        response = self.agent.get_response(message)
        return self._build_payload(response)

    def force_summary(self) -> Dict:
        """Force the agent to summarize when rounds are exhausted."""
        response = self.agent.get_response(
            f"We are out of time. Please summarize the requirements as they stand now, "
            f"starting with '{self.SUMMARY_PREFIX}'."
        )
        return self._build_payload(response)

    def serialize(self) -> Dict:
        return {
            'round_count': self.round_count,
            'started': self.started,
            'messages': self.agent.dump_state(),
        }

    def _build_payload(self, response: str) -> Dict:
        summary = ''
        finished = False

        if self.SUMMARY_PREFIX in response:
            finished = True
            summary = response.split(self.SUMMARY_PREFIX, 1)[1].strip()

        if self.round_count >= settings.MAX_REQUIREMENTS_ROUNDS and not finished:
            finished = True
            summary = summary or response

        return {
            'agent_name': self.agent.name,
            'agent_role': self.agent.role,
            'message': response,
            'finished': finished,
            'summary': summary,
            'state': self.serialize(),
        }

