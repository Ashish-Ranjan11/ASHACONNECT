import hashlib
import time


PENDING_TTL_SECONDS = 300

_pending_actions = {}


def _session_key(authorization: str) -> str:
    return hashlib.sha256(
        authorization.encode("utf-8")
    ).hexdigest()


def set_pending_action(
    authorization: str,
    action: str,
    payload: dict,
):
    key = _session_key(authorization)

    _pending_actions[key] = {
        "action": action,
        "payload": payload,
        "created_at": time.time(),
    }

    return _pending_actions[key]


def get_pending_action(
    authorization: str,
):
    key = _session_key(authorization)

    pending = _pending_actions.get(key)

    if not pending:
        return None

    age = time.time() - pending["created_at"]

    if age > PENDING_TTL_SECONDS:
        _pending_actions.pop(key, None)
        return None

    return pending


def clear_pending_action(
    authorization: str,
):
    key = _session_key(authorization)
    return _pending_actions.pop(key, None)
