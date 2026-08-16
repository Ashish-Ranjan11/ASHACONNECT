from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:
    pending_action: str | None = None
    pending_payload: dict[str, Any] = field(default_factory=dict)
    awaiting_confirmation: bool = False


_states: dict[str, AgentState] = {}


def get_state(user_id: str) -> AgentState:
    if user_id not in _states:
        _states[user_id] = AgentState()

    return _states[user_id]


def clear_state(user_id: str):
    _states.pop(user_id, None)
