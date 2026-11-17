"""Typed wrapper over the Redis live-state store (answers, chat buffer, batches).

All multi-step mutations go through Lua scripts, so single-threaded Redis gives
them a total order. Used from the API (threadpool) and Celery workers alike.
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from redis import Redis

from api.config.settings import settings
from api.realtime import redis_keys as K

_LUA_DIR = Path(__file__).parent / "lua"


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True)
class AcceptResult:
    outcome: str  # accepted | duplicate | closed | not_current | expired | invalid_option
    option_id: str | None = None
    ts_ms: int | None = None
    seq: int | None = None
    answered_count: int | None = None


@dataclass
class AnswerRecord:
    question_id: str
    student_id: str
    option_id: str
    ts_ms: int
    seq: int


@dataclass
class PollSnapshot:
    previous_status: str
    answers: list[AnswerRecord] = field(default_factory=list)
    participant_ids: set[str] = field(default_factory=set)


class LiveStateStore:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.ttl = settings.REDIS_POLL_TTL_SECONDS
        self._scripts = {
            name: redis.register_script((_LUA_DIR / f"{name}.lua").read_text(encoding="utf-8"))
            for name in (
                "accept_answer",
                "buffer_chat",
                "claim_batch",
                "close_and_snapshot",
                "cancel_cleanup",
                "open_question",
            )
        }

    # ---------- lifecycle ----------
    def init_poll(
        self,
        *,
        poll_id: str,
        room_id: str,
        deadline_ms: int,
        question_map: dict[str, dict[str, Any]],
        first_question_id: str,
        participant_ids: list[str],
    ) -> None:
        pointer_ttl = max(1, (deadline_ms - now_ms()) // 1000) + settings.ACTIVE_POINTER_GRACE_SECONDS
        stale = [
            K.answers(poll_id), K.answer_counts(poll_id), K.seq(poll_id), K.participants(poll_id),
            K.chat_pending(poll_id), K.chat_inflight(poll_id), K.results(poll_id), K.questions(poll_id),
        ]
        pipe = self.redis.pipeline(transaction=True)
        pipe.delete(*stale)
        pipe.hset(
            K.meta(poll_id),
            mapping={
                "status": "ACTIVE",
                "room_id": room_id,
                "current_question_id": first_question_id,
                "current_index": 0,
                "opened_ms": now_ms(),
                "deadline_ms": deadline_ms,
            },
        )
        pipe.expire(K.meta(poll_id), self.ttl)
        pipe.hset(K.questions(poll_id), mapping={q: json.dumps(v) for q, v in question_map.items()})
        pipe.expire(K.questions(poll_id), self.ttl)
        if participant_ids:
            pipe.sadd(K.participants(poll_id), *participant_ids)
            pipe.expire(K.participants(poll_id), self.ttl)
        pipe.set(K.active_poll(room_id), poll_id, ex=pointer_ttl)
        pipe.execute()

    def discard_poll(self, poll_id: str, room_id: str) -> None:
        """Compensating cleanup when a start fails after Redis was initialized."""
        self.cancel_cleanup(poll_id, room_id)
        self.redis.delete(K.meta(poll_id))

    def open_question(self, poll_id: str, expected_qid: str | None, next_qid: str, index: int) -> str:
        result = self._scripts["open_question"](
            keys=[K.meta(poll_id)], args=[expected_qid or "", next_qid, index, now_ms()]
        )
        return _s(result)

    def get_meta(self, poll_id: str) -> dict[str, str]:
        raw = self.redis.hgetall(K.meta(poll_id))
        return {_s(k): _s(v) for k, v in raw.items()}

    def get_active_poll_id(self, room_id: str) -> str | None:
        value = self.redis.get(K.active_poll(room_id))
        return _s(value) if value else None

    # ---------- answers ----------
    def accept_answer(self, poll_id: str, question_id: str, student_id: str, option_id: str) -> AcceptResult:
        res = self._scripts["accept_answer"](
            keys=[
                K.meta(poll_id), K.questions(poll_id), K.answers(poll_id),
                K.seq(poll_id), K.participants(poll_id), K.answer_counts(poll_id),
            ],
            args=[question_id, student_id, option_id, now_ms(), self.ttl],
        )
        outcome = _s(res[0])
        if outcome in ("accepted", "duplicate"):
            record = json.loads(_s(res[1]))
            count = int(_s(res[2])) if outcome == "accepted" else None
            return AcceptResult(outcome, record["option_id"], int(record["ts_ms"]), int(record["seq"]), count)
        return AcceptResult(outcome)

    def get_student_answer(self, poll_id: str, question_id: str, student_id: str) -> dict | None:
        raw = self.redis.hget(K.answers(poll_id), f"{question_id}:{student_id}")
        return json.loads(_s(raw)) if raw else None

    def answer_count(self, poll_id: str, question_id: str) -> int:
        return int(self.redis.hget(K.answer_counts(poll_id), question_id) or 0)

    def option_counts(self, poll_id: str, question_id: str) -> dict[str, int]:
        prefix = f"{question_id}:"
        return {
            _s(k)[len(prefix):]: int(v)
            for k, v in self.redis.hgetall(K.answer_counts(poll_id)).items()
            if _s(k).startswith(prefix)
        }

    def add_participant(self, poll_id: str, student_id: str) -> None:
        pipe = self.redis.pipeline()
        pipe.sadd(K.participants(poll_id), student_id)
        pipe.expire(K.participants(poll_id), self.ttl)
        pipe.execute()

    def participant_count(self, poll_id: str) -> int:
        return int(self.redis.scard(K.participants(poll_id)))

    # ---------- chat buffer & batches ----------
    def buffer_chat(self, poll_id: str, payload: dict[str, Any]) -> int:
        return int(
            self._scripts["buffer_chat"](
                keys=[K.meta(poll_id), K.chat_pending(poll_id), K.FLUSH_INDEX],
                args=[poll_id, json.dumps(payload), payload["received_ms"], self.ttl],
            )
        )

    def claim_batch(self, poll_id: str, min_count: int) -> tuple[str, list[dict[str, Any]]] | None:
        batch_id = str(uuid.uuid4())
        msgs = self._scripts["claim_batch"](
            keys=[K.chat_pending(poll_id), K.chat_inflight(poll_id), K.FLUSH_INDEX],
            args=[
                poll_id, K.chat_batch_prefix(poll_id), settings.CHAT_BATCH_SIZE,
                min_count, now_ms(), self.ttl, batch_id,
            ],
        )
        if not msgs:
            return None
        return batch_id, [json.loads(_s(m)) for m in msgs]

    def get_batch(self, poll_id: str, batch_id: str) -> list[dict[str, Any]]:
        return [json.loads(_s(m)) for m in self.redis.lrange(K.chat_batch(poll_id, batch_id), 0, -1)]

    def ack_batch(self, poll_id: str, batch_id: str) -> None:
        pipe = self.redis.pipeline(transaction=True)
        pipe.delete(K.chat_batch(poll_id, batch_id))
        pipe.zrem(K.chat_inflight(poll_id), batch_id)
        pipe.execute()

    def inflight_count(self, poll_id: str) -> int:
        return int(self.redis.zcard(K.chat_inflight(poll_id)))

    def pending_count(self, poll_id: str) -> int:
        return int(self.redis.llen(K.chat_pending(poll_id)))

    def due_flush_polls(self, older_than_ms: int) -> list[str]:
        return [_s(p) for p in self.redis.zrangebyscore(K.FLUSH_INDEX, "-inf", older_than_ms)]

    def iter_inflight(self, claimed_before_ms: int):
        """Yield (poll_id, batch_id) for in-flight batches claimed before the cutoff."""
        for key in self.redis.scan_iter(match=K.INFLIGHT_SCAN_PATTERN, count=200):
            key_s = _s(key)
            poll_id = K.poll_id_from_inflight_key(key_s)
            for batch_id in self.redis.zrangebyscore(key_s, "-inf", claimed_before_ms):
                yield poll_id, _s(batch_id)

    # ---------- finalization ----------
    def close_and_snapshot(self, poll_id: str, room_id: str) -> PollSnapshot:
        prev, flat, members = self._scripts["close_and_snapshot"](
            keys=[K.meta(poll_id), K.active_poll(room_id), K.answers(poll_id), K.participants(poll_id)],
            args=[poll_id],
        )
        answers: list[AnswerRecord] = []
        for i in range(0, len(flat), 2):
            qid, sid = _s(flat[i]).split(":", 1)
            rec = json.loads(_s(flat[i + 1]))
            answers.append(AnswerRecord(qid, sid, rec["option_id"], int(rec["ts_ms"]), int(rec["seq"])))
        return PollSnapshot(_s(prev), answers, {_s(m) for m in members})

    def cancel_cleanup(self, poll_id: str, room_id: str) -> int:
        return int(
            self._scripts["cancel_cleanup"](
                keys=[
                    K.meta(poll_id), K.active_poll(room_id), K.chat_pending(poll_id),
                    K.chat_inflight(poll_id), K.answers(poll_id), K.seq(poll_id),
                    K.participants(poll_id), K.questions(poll_id), K.results(poll_id),
                    K.FLUSH_INDEX, K.answer_counts(poll_id),
                ],
                args=[poll_id, K.chat_batch_prefix(poll_id)],
            )
        )

    def store_results(self, poll_id: str, snapshot: dict[str, Any]) -> None:
        self.redis.set(K.results(poll_id), json.dumps(snapshot), ex=self.ttl)

    def get_results(self, poll_id: str) -> dict[str, Any] | None:
        raw = self.redis.get(K.results(poll_id))
        return json.loads(_s(raw)) if raw else None

    def clear_after_persist(self, poll_id: str) -> None:
        self.redis.delete(
            K.results(poll_id), K.answers(poll_id), K.answer_counts(poll_id),
            K.seq(poll_id), K.participants(poll_id), K.questions(poll_id),
        )


def _s(value: Any) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)
