"""Single source of truth for Redis key names. Every poll key is namespaced
`poll:{poll_id}:…` so cleanup can never touch another poll."""

FLUSH_INDEX = "chat:flush_index"
INFLIGHT_SCAN_PATTERN = "poll:*:chat:inflight"


def active_poll(room_id) -> str:
    return f"room:{room_id}:active_poll"


def meta(poll_id) -> str:
    return f"poll:{poll_id}:meta"


def questions(poll_id) -> str:
    return f"poll:{poll_id}:questions"


def answers(poll_id) -> str:
    return f"poll:{poll_id}:answers"


def answer_counts(poll_id) -> str:
    return f"poll:{poll_id}:answer_counts"


def seq(poll_id) -> str:
    return f"poll:{poll_id}:seq"


def participants(poll_id) -> str:
    return f"poll:{poll_id}:participants"


def chat_pending(poll_id) -> str:
    return f"poll:{poll_id}:chat:pending"


def chat_batch_prefix(poll_id) -> str:
    return f"poll:{poll_id}:chat:batch:"


def chat_batch(poll_id, batch_id) -> str:
    return f"{chat_batch_prefix(poll_id)}{batch_id}"


def chat_inflight(poll_id) -> str:
    return f"poll:{poll_id}:chat:inflight"


def results(poll_id) -> str:
    return f"poll:{poll_id}:results"


def poll_id_from_inflight_key(key: str) -> str:
    return key.split(":")[1]
