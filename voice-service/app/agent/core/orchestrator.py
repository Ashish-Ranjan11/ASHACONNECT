from app.agent.core.state import AgentState
from app.agent.core.confirmation import (
    requires_confirmation
)
from app.agent.intent import detect_intent


async def run_agent(
    text: str,
    language: str = "hi",
    authorization: str | None = None
):

    state = AgentState(
        original_text=text,
        language=language
    )

    result = detect_intent(text)

    state.intent = result["intent"]
    state.confidence = result["confidence"]
    state.entities = result.get(
        "entities",
        {}
    )
    state.normalized_text = result.get(
        "normalized_text",
        text
    )

    # --------------------------------
    # Confirmation required
    # --------------------------------

    if requires_confirmation(state.intent):

        state.requires_confirmation = True

        state.pending_action = {
            "intent": state.intent,
            "entities": state.entities
        }

        state.response_text = (
            "यह कार्रवाई करने के लिए "
            "आपकी पुष्टि चाहिए। "
            "क्या मैं इसे कर दूँ?"
        )

        return state

    # --------------------------------
    # Read actions
    # --------------------------------

    return state
