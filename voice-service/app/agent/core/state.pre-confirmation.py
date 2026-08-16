from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:

    user_id: str | None = None
    language: str = "hi"

    original_text: str = ""
    normalized_text: str = ""

    intent: str | None = None
    confidence: float = 0.0

    entities: dict[str, Any] = field(
        default_factory=dict
    )

    requires_confirmation: bool = False

    pending_action: dict[str, Any] | None = None

    response_text: str | None = None

    data: Any = None
