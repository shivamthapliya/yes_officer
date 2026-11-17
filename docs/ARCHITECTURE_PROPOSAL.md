# Quiz & Live Polling Platform — Schema & Architecture Proposal (rev 2)

Status: **DRAFT rev 2 — awaiting approval**. Nothing is implemented yet; the repo contains only `docs/`.
Sources: `docs/requirements.md`, `docs/CODING_PRACTICES.md`, plus the product decisions below, which **override** the requirements where they conflict.

## Rev 2 decisions (from product owner)

| # | Decision | Effect on design |
|---|---|---|
| D1 | The teacher steps through questions **one at a time** | A live "current question" lives in Redis. Answers are accepted only for the current question. Chat is tagged with the current question. |
| D2 | Time limit adjustable by the teacher, **max 5 min per poll** | `polls.time_limit_seconds` 10–300. Answers after the deadline are rejected, and the poll auto-ends at the deadline. |
| D3 | **No scoring** | No scores, totals, or percentages per student. The results are per-question distributions, correctness, and the first correct student. |
| D4 | Results are visible to teacher and students **as soon as the poll ends** | No release step. Results are computed from Redis at end, returned immediately, and broadcast over WebSocket. |
| D5 | The first student (per question) is shown in a **React toast** | The results payload carries `first_correct_student` per question. |
| D6 | **Ephemeral chat** (YouTube Live style) | **No `chat_messages` table**, no history API. Chat uses in-memory WebSocket broadcast. Redis buffers chat only for AI. |
| D7 | Only AI-generated analytics are persisted | No message content, excerpts, or message references are stored in PostgreSQL. |
| D8 | Finalization: teacher sees results without waiting | PostgreSQL persistence and the final AI flush run asynchronously after the response. |

Requirement sections superseded by D6/D7: §9.1 (message persistence), §11.3 "original chat message / link to original message", §14 `ChatMessage`, and the cancellation step "delete poll-scoped chat rows" (replaced by Redis cleanup).

---

## 0. Terminology

| Generic term | This product |
|---|---|
| Classroom | **Room**: exactly one per teacher, auto-provisioned |
| Assessment | **Poll**: many per room over time, at most one active |
| Question / option | **PollQuestion / QuestionOption**: MCQ, one correct option |
| Submission | **StudentAnswer**: one per student per question, first valid answer wins |
| Attempts | **Not supported** (one attempt per poll) |
| Scheduling | **Not supported** (the teacher starts manually) |
| Score | **Not supported** (D3) |

---

## 1. Requirements analysis

### 1.1 Roles and permissions
| Capability | Teacher | Student |
|---|---|---|
| Register / log in | ✓ (registration provisions their room) | ✓ |
| Browse and join rooms | — | ✓ |
| Manage polls, questions, options (DRAFT only) | Own room only | ✗ |
| Start poll, advance question, end, cancel | Own room only | ✗ |
| Live chat over WebSocket | Own room | Joined rooms |
| Submit answer (current question, before deadline) | ✗ | ✓ |
| See results | Own polls, at end | Polls they participated in, at end |
| AI insights (live and historical) | Own polls | ✗ |
| Review own answers vs. correct answers | — | Own only |

### 1.2 Workflows
1. **Register**: create the user and, for a teacher, provision the room in the same transaction (idempotent).
2. **Login**: return the existing room. Login never creates one.
3. **Draft**: questions, options, correct option, and time limit.
4. **Start**: `DRAFT → ACTIVE`. Redis live state is initialized, question 1 is opened, and the WebSocket sends `poll_started` and `question_opened`.
5. **Advance**: the teacher opens the next question. The WebSocket sends `question_opened`.
6. **Answer**: validate → atomic first-wins in Redis → ack with the server receipt time.
7. **Chat**: WebSocket receive → validate → **broadcast immediately** → *if a poll is active*, append to the Redis AI buffer (fire-and-forget).
8. **AI**: buffer reaches 50 messages or the time-based flush fires → atomic claim → Celery → insights merged → teacher notified.
9. **End** (by the teacher or at the deadline): atomic close and snapshot in Redis → compute results → respond and broadcast → async persist and final AI flush.
10. **Cancel**: `ACTIVE → CANCELLED` → Redis cleanup → batches cancelled → late AI output discarded. Chat keeps working.
11. **History**: the student reviews their own answers. The teacher sees per-question results and stored insights. Both come from PostgreSQL only.

### 1.3 Where data lives
| PostgreSQL (durable) | Redis (temporary, TTL'd) | Process memory | Browser memory |
|---|---|---|---|
| users, rooms, room_participants, refresh_tokens | room → active poll pointer | WebSocket connections by room | Last N chat messages |
| polls, questions, options | poll live meta, question map, answers, participants | | |
| student_answers, poll_participants | chat AI buffer, claimed batches, in-flight index | | |
| ai_analysis_batches, ai_insights | final results snapshot (until persisted) | | |

---

## 2. Conventions
PostgreSQL ≥ 13, SQLAlchemy 2.x, Alembic. UUID primary keys. `TIMESTAMPTZ` (UTC). Native PostgreSQL enums mirrored in `api/enums/`. Foreign keys default to `RESTRICT`. `CASCADE` is used only inside a poll's own subtree.

---

## 3. Schema (PostgreSQL)

### 3.1 `users`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| email | VARCHAR(255) | NOT NULL. Unique on `lower(email)` |
| password_hash | VARCHAR(255) | NOT NULL |
| full_name | VARCHAR(120) | NOT NULL. The name shown in chat and in the toast |
| role | `user_role` (`TEACHER`,`STUDENT`) | NOT NULL. **Immutable** |
| is_active | BOOLEAN | NOT NULL DEFAULT true. Soft deactivation only |
| created_at, updated_at | TIMESTAMPTZ | NOT NULL |

`UNIQUE (id, role)` is the target for the role-pinned composite FKs.

### 3.2 `rooms`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| teacher_id | UUID | NOT NULL **UNIQUE** |
| teacher_role | `user_role` | NOT NULL DEFAULT `'TEACHER'`, `CHECK = 'TEACHER'` |
| name | VARCHAR(120) | NOT NULL |
| created_at, updated_at | TIMESTAMPTZ | NOT NULL |

`FK (teacher_id, teacher_role) → users(id, role)`. Provisioning uses `INSERT … ON CONFLICT (teacher_id) DO NOTHING` followed by a select.

### 3.3 `room_participants`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| room_id | UUID | NOT NULL FK → rooms |
| student_id | UUID | NOT NULL |
| student_role | `user_role` | NOT NULL DEFAULT `'STUDENT'`, `CHECK = 'STUDENT'` |
| joined_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

`FK (student_id, student_role) → users(id, role)`. `UNIQUE (room_id, student_id)`. Index on `(student_id)`. This is the eligibility check for WebSocket connections, chat, and answers.

### 3.4 `polls`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| room_id | UUID | NOT NULL FK → rooms |
| title | VARCHAR(200) | NOT NULL |
| status | `poll_status` (`DRAFT`,`ACTIVE`,`COMPLETED`,`CANCELLED`) | NOT NULL DEFAULT `DRAFT` |
| time_limit_seconds | SMALLINT | NOT NULL DEFAULT 120, `CHECK BETWEEN 10 AND 300` (D2) |
| started_at | TIMESTAMPTZ | NULL |
| deadline_at | TIMESTAMPTZ | NULL. `started_at + time_limit` |
| ended_at | TIMESTAMPTZ | NULL |
| cancelled_at | TIMESTAMPTZ | NULL |
| results_status | `results_status` (`NOT_STARTED`,`PROCESSING`,`PERSISTED`,`FAILED`) | NOT NULL DEFAULT `NOT_STARTED` |
| analysis_status | `analysis_status` (`IDLE`,`LIVE`,`FINALIZING`,`COMPLETE`,`FAILED`) | NOT NULL DEFAULT `IDLE` |
| insights_version | BIGINT | NOT NULL DEFAULT 0. Monotonic per poll |
| created_at, updated_at | TIMESTAMPTZ | NOT NULL |

- Partial unique index `ON (room_id) WHERE status = 'ACTIVE'` allows **one active poll per room**.
- CHECKs: DRAFT ⇒ `started_at IS NULL`. ACTIVE or COMPLETED ⇒ `started_at` and `deadline_at` NOT NULL. COMPLETED ⇒ `ended_at` NOT NULL. CANCELLED ⇒ `cancelled_at` NOT NULL.
- Indexes: `(room_id, status)` and `(room_id, created_at DESC)`.
- Transitions use a conditional `UPDATE … WHERE status = :expected` under a row lock: `DRAFT → ACTIVE → COMPLETED | CANCELLED`. A draft can be deleted. A cancelled poll keeps its row as a tombstone (the authoritative cancellation flag for workers) and has its subtree deleted.

### 3.5 `poll_questions`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| poll_id | UUID | NOT NULL FK → polls **CASCADE** |
| position | SMALLINT | NOT NULL `>= 0` |
| prompt | TEXT | NOT NULL, 1–1000 chars |
| created_at, updated_at | TIMESTAMPTZ | NOT NULL |

`UNIQUE (poll_id, position) DEFERRABLE INITIALLY DEFERRED` (for reordering). `UNIQUE (id, poll_id)` is the composite FK target. Questions are opened in `position` order (D1).

### 3.6 `question_options`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| question_id | UUID | NOT NULL FK → poll_questions **CASCADE** |
| position | SMALLINT | NOT NULL `>= 0` |
| label | VARCHAR(500) | NOT NULL |
| is_correct | BOOLEAN | NOT NULL DEFAULT false |

- `UNIQUE (question_id, position) DEFERRABLE`, and a partial unique index `ON (question_id) WHERE is_correct`, which allows **at most one correct option**.
- `UNIQUE (id, question_id)` is the composite FK target.
- On start, the service validates that the poll has ≥1 question and each question has 2–6 options with exactly one correct.
- Questions and options are editable **only in DRAFT**, which keeps history correct without snapshots.

### 3.7 `student_answers`
These are written asynchronously after the poll ends, from the Redis snapshot.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| poll_id | UUID | NOT NULL |
| question_id | UUID | NOT NULL |
| student_id | UUID | NOT NULL FK → users |
| selected_option_id | UUID | NOT NULL |
| is_correct | BOOLEAN | NOT NULL. Set at finalization. Used for review, not scoring |
| received_at | TIMESTAMPTZ | NOT NULL. Server receipt time |
| accept_seq | BIGINT | NOT NULL. Redis `INCR` at acceptance, giving a total order of accepted answers |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

- `FK (question_id, poll_id) → poll_questions(id, poll_id)` CASCADE. `FK (selected_option_id, question_id) → question_options(id, question_id)` CASCADE.
- **`UNIQUE (poll_id, question_id, student_id)`** enforces first-wins durably. Inserts use `ON CONFLICT DO NOTHING`, so persistence retries are idempotent.
- `UNIQUE (poll_id, accept_seq)`.
- Indexes: `(poll_id, student_id)` for review, and `(poll_id, question_id, selected_option_id)` for distributions.
- **First correct student** = the lowest `accept_seq` among correct answers for the question. `accept_seq` breaks ties exactly where timestamps could collide.
- Unanswered questions have no row.

### 3.8 `poll_participants`
This replaces `poll_results` (D3). It records who took part in the poll.

| Column | Type | Constraints |
|---|---|---|
| poll_id | UUID | FK → polls CASCADE |
| student_id | UUID | FK → users |
| PK | | `(poll_id, student_id)` |

Rows come from students connected to the room while the poll was active, plus anyone who answered. The table supports "my past polls" (including polls where the student answered nothing) and the participant count, which is the denominator shown next to each question's distribution. Index on `(student_id)`.

**No per-question results table.** Per-question distributions and the first correct student are computed from `student_answers` and `poll_participants`, which are immutable once completed. The live end-of-poll payload is computed from the Redis snapshot using the **same pure function** (`compute_poll_results`), so the live view and historical view can't disagree.

### 3.9 `ai_analysis_batches`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK. Stable batch ID assigned at claim |
| poll_id | UUID | NOT NULL FK → polls CASCADE |
| question_id | UUID | NULL FK → poll_questions SET NULL. Set when all messages in the batch share a question |
| status | `batch_status` (`PENDING`,`PROCESSING`,`SUCCEEDED`,`FAILED`,`CANCELLED`) | NOT NULL DEFAULT `PENDING` |
| trigger | `batch_trigger` (`THRESHOLD`,`INTERVAL`,`POLL_END`) | NOT NULL |
| message_count | SMALLINT | NOT NULL `BETWEEN 1 AND 50` |
| attempt_count | SMALLINT | NOT NULL DEFAULT 0 |
| celery_task_id | VARCHAR(155) | NULL |
| last_error | VARCHAR(1000) | NULL, sanitized |
| raw_output | JSONB | NULL. Validated structured AI output. **The schema contains no message text or quotes** |
| claimed_at | TIMESTAMPTZ | NOT NULL |
| started_at, completed_at | TIMESTAMPTZ | NULL |
| created_at, updated_at | TIMESTAMPTZ | NOT NULL |

Indexes: `(poll_id, status)` and `(status, updated_at)` for the recovery sweeper. **No message link table**, because messages exist only in Redis (D7).

### 3.10 `ai_insights` (consolidated, teacher-facing)
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| poll_id | UUID | NOT NULL FK → polls CASCADE |
| question_id | UUID | NULL FK → poll_questions CASCADE |
| student_id | UUID | NULL FK → users. Only for student-level insights |
| category | `insight_category` (`COMMON_DOUBT`,`CONFUSION`,`ENGAGEMENT`,`MISCONCEPTION`,`UNCOUNTED_RESPONSE`,`STUDENT_QUESTION`) | NOT NULL |
| topic_label | VARCHAR(200) | NOT NULL |
| normalized_topic_key | VARCHAR(200) | NULL. NULL means uncertain and never merged |
| summary | VARCHAR(2000) | NOT NULL. AI-written description, never a quote |
| referenced_option_id | UUID | NULL FK → question_options. For `UNCOUNTED_RESPONSE`. Informational only |
| confidence | NUMERIC(3,2) | NULL, 0–1 |
| support_count | INTEGER | NOT NULL DEFAULT 1. Number of messages that supported it (summed per merged batch) |
| first_observed_at, last_observed_at | TIMESTAMPTZ | NOT NULL |
| updated_in_version | BIGINT | NOT NULL |
| created_at, updated_at | TIMESTAMPTZ | NOT NULL |

- Dedup: unique index on `(poll_id, COALESCE(question_id, nil), COALESCE(student_id, nil), category, normalized_topic_key) WHERE normalized_topic_key IS NOT NULL`, merged with `INSERT … ON CONFLICT DO UPDATE`.
- Indexes: `(poll_id, question_id, category)` and `(poll_id, student_id)`.
- **Idempotent merge without message references:** the worker's write transaction first runs `UPDATE ai_analysis_batches SET status='SUCCEEDED' WHERE id=:b AND status IN ('PENDING','PROCESSING') RETURNING id`. If that returns no row, the batch was already merged or cancelled, and the transaction writes nothing. So a batch's insights are merged exactly once, even if the task runs twice.
- The API marks every insight as `kind: "ai_inference"` with its confidence. Answer statistics are marked `kind: "verified"`. AI tables have no path into `student_answers`.

### 3.11 `refresh_tokens`
`id` PK, `user_id` FK CASCADE, `jti` UUID UNIQUE, `expires_at`, `revoked_at` NULL, `created_at`. Index on `(user_id)`. Used for rotation and logout.

### Relationship summary
```
users(TEACHER) 1──1 rooms                  role-pinned FK, UNIQUE teacher_id
users(STUDENT) *──* rooms                  room_participants
rooms          1──* polls                  ≤1 ACTIVE
polls          1──* poll_questions 1──* question_options (≤1 correct)
polls          1──* student_answers        option ∈ question ∈ poll (composite FKs), UNIQUE poll+question+student
polls          *──* users(STUDENT)         poll_participants
polls          1──* ai_analysis_batches, ai_insights   (no link to answers, no chat rows)
```

---

## 4. Redis design

The live-state store and the Celery broker use **separate logical DBs** (`REDIS_URL` db 0, `CELERY_BROKER_URL` db 1). All poll keys are namespaced `poll:{poll_id}:…` so cleanup can't touch another poll.

| Key | Type | Purpose | TTL |
|---|---|---|---|
| `room:{room_id}:active_poll` | string | poll_id of the active poll | time limit + 10 min |
| `poll:{id}:meta` | hash | `status` (ACTIVE/CLOSED/CANCELLED), `room_id`, `current_question_id`, `deadline_ms` | 24 h |
| `poll:{id}:questions` | hash | qid → JSON `{options:[…], correct}` for O(1) validation | 24 h |
| `poll:{id}:answers` | hash | `{qid}:{sid}` → JSON `{option_id, ts_ms, seq}` | 24 h |
| `poll:{id}:seq` | string | `INCR` counter for `accept_seq` | 24 h |
| `poll:{id}:participants` | set | student ids seen during the poll | 24 h |
| `poll:{id}:chat:pending` | list | JSON `{msg_id, student_id, question_id, received_ms, content}` | 24 h |
| `poll:{id}:chat:batch:{batch_id}` | list | claimed batch payload, removed after success | 24 h |
| `poll:{id}:chat:inflight` | zset | batch_id → claim time (handoff recovery) | 24 h |
| `poll:{id}:results` | string | final results snapshot JSON, removed after the PostgreSQL persist | 24 h |
| `chat:flush_index` | zset | poll_id → time of the oldest pending message (time-based flush) | none (entries removed) |

### Atomic Lua scripts (single-threaded Redis gives a total order)
- **`accept_answer`**: check that `meta.status == ACTIVE`, `qid == current_question_id`, `now < deadline`, and the option is in the question map → `HSETNX` the answer with `INCR seq` → `SADD participants`. Returns `accepted | duplicate(original) | closed | not_current | expired | invalid_option`.
- **`buffer_chat`**: if `meta.status == ACTIVE`, `RPUSH pending` and `ZADD NX chat:flush_index`. Returns the new length, and the API triggers a dispatch at ≥50. If the poll is not active, it does nothing, so no message can enter a closed or cancelled poll's buffer.
- **`claim_batch(max=50, force)`**: `LRANGE`/`LTRIM` up to 50 messages from `pending` into `chat:batch:{new_id}` → `ZADD inflight` → update or clear `flush_index`. With `force=1` (poll end) it loops until `pending` is empty.
- **`close_and_snapshot`**: set `meta.status = CLOSED` and `DEL room active_poll` → return `HGETALL answers`, `SMEMBERS participants`. Answer acceptance and chat buffering stop at exactly this point. Every message buffered before it is included in the final flush.
- **`cancel_cleanup`**: set `meta.status = CANCELLED` → `DEL` the active pointer, pending list, all `chat:batch:*` (enumerated via `inflight`), `inflight`, answers, seq, participants, questions, results, and the `flush_index` entry. Keep `meta` (status CANCELLED) until its TTL expires, as a fast-path cancellation marker.

### Batch handoff without loss
1. `claim_batch` moves the messages into `chat:batch:{id}` and records `id` in `inflight` atomically.
2. Insert the `ai_analysis_batches` row (PENDING) → `analyze_batch.apply_async(task_id=batch_id)`.
3. If the process crashes between 1 and 2, the batch still exists in Redis and in `inflight`. **`recover_batches`** (Celery beat, every 30 s) republishes any in-flight batch older than 60 s whose row is missing or not terminal, creating the row if needed. Because the batch ID is the same, duplicates are harmless.
4. Time-based flush: **`flush_due_buffers`** (Celery beat, every `CHAT_FLUSH_INTERVAL_SECONDS`, default 10 s) claims a batch for every poll in `chat:flush_index` whose oldest pending message is older than the interval, so low-volume polls still get analytics.

### Worker (`analyze_batch`)
1. Load the batch row. If it's terminal, delete the Redis payload and stop. If the poll isn't ACTIVE or COMPLETED, mark the batch CANCELLED and stop (**check 1**).
2. Mark it PROCESSING and `attempt_count += 1`. Read the payload from Redis.
3. Call the LLM with a structured-output schema (no quotes or excerpts).
4. Start the transaction: `SELECT status FROM polls … FOR SHARE` (**check 2**; cancellation holds `FOR UPDATE`, so the two can't interleave) → conditional `SUCCEEDED` transition → merge insights → `insights_version += 1` → commit. If the poll was cancelled, discard the output (step 8 of the cancellation spec).
5. After the commit: `DEL chat:batch:{id}` and `ZREM inflight`, then notify the API (see §5).
6. Transient errors are retried with backoff (max 3 attempts), and the payload stays in Redis. After the last failure the batch is marked FAILED; its payload expires with the TTL.

---

## 5. WebSocket and chat

- **`ConnectionManager`** (in process memory): `dict[room_id, dict[connection_id, Connection]]` guarded by an `asyncio.Lock`. `broadcast(room_id, event)` snapshots the room's connections and sends to all of them concurrently (`asyncio.gather(…, return_exceptions=True)`) with a per-send timeout. Any connection that errors or times out is removed, so one dead client never blocks the others.
- **Handshake** `WS /ws/rooms/{room_id}`: the access token is read from the HTTP-only cookie. The user must be the room's teacher or a `room_participants` row; otherwise the socket is closed with code 4403. If a poll is active, students are added to `poll:{id}:participants` on connect.
- **Inbound** `{type:"chat", content}`: content is 1–500 characters after trimming, with a per-connection rate limit of 5 messages per 5 s. The server builds `{type:"chat", id, author_id, author_name, author_role, content, sent_at}` → **broadcast first** → then `buffer_chat` (student messages only, and only if a poll is active) runs as a background task. Redis or Celery problems are logged and never affect delivery.
- **Server events**: `chat`, `poll_started`, `question_opened`, `poll_ended {results}`, `poll_cancelled`, `insights_updated {poll_id, question_id, version}` (sent to the teacher's connections only).
- **Worker → API notification:** Celery runs in separate processes, which can't reach the in-memory connections. The worker POSTs to an internal endpoint `POST /internal/events/insights-updated`, authenticated with a shared secret in a header and bound to the single server, and the API broadcasts to the teacher. This uses no Redis Pub/Sub, as required.
- **Scale-out note** (to be placed as a comment on `ConnectionManager`): with more than one FastAPI instance, in-memory broadcast only reaches sockets on the receiving instance. The future design is to publish every room event to Redis Pub/Sub (channel `room:{id}`) and have each instance relay to its local sockets. The internal worker callback would become a publish too. This is **out of scope** now.

---

## 6. Poll finalization and cancellation

**End** (teacher request, or the `auto_end_poll` Celery task scheduled with `eta = deadline_at`, which is a no-op if the poll isn't ACTIVE):
1. PostgreSQL: lock the row and conditionally update `ACTIVE → COMPLETED` (`ended_at`, `results_status = PROCESSING`, `analysis_status = FINALIZING`). If the poll isn't active, return `POLL_NOT_ACTIVE` (or the cached results if it already completed).
2. Redis `close_and_snapshot`. Answers stop at this instant.
3. `compute_poll_results(snapshot, question_map)` computes, per question: option counts and percentages, the correct option, answered count, participant count, and the first correct student (lowest seq) with their name.
4. Store the results in `poll:{id}:results`. **Return them to the teacher** and broadcast `poll_ended {results}` to the room (D4/D5).
5. Async: `persist_poll_results` bulk-inserts answers and participants (`ON CONFLICT DO NOTHING`) → `results_status = PERSISTED` → `DEL poll:{id}:results`. `claim_batch(force)` → dispatch POLL_END batches. `analysis_status = COMPLETE` is set when no non-terminal batches remain for the poll; whichever worker finishes last checks this.

Until `PERSISTED`, the history endpoints serve the poll's results from `poll:{id}:results`, so a student who opens history immediately doesn't see an empty view.

**Cancel:** lock the row → conditional `ACTIVE → CANCELLED` → `UPDATE ai_analysis_batches SET status='CANCELLED' WHERE poll_id=… AND status IN ('PENDING','PROCESSING')` → delete the poll's questions (cascading to options and answers) and its `poll_participants` and `ai_insights` → commit → Redis `cancel_cleanup` → best-effort `revoke` of in-flight task ids → broadcast `poll_cancelled`. A repeat cancel is a no-op. Chat keeps broadcasting, and `buffer_chat` refuses messages because `meta.status` is CANCELLED and the active pointer is gone.

---

## 7. API boundaries

| Router | Endpoints | Access |
|---|---|---|
| `auth` | `POST /auth/register`, `/login`, `/refresh`, `/logout`, `GET /auth/me` | public / any user |
| `rooms` | `GET /rooms` (paginated), `GET /rooms/{id}`, `GET /rooms/mine`, `POST /rooms/{id}/join`, `GET /rooms/joined`, `GET /rooms/{id}/participants` | student / owner |
| `polls` | `GET/POST /rooms/{id}/polls`, `GET/PATCH/DELETE /polls/{id}`, question and option CRUD, `PUT /polls/{id}/questions/order`, `POST /polls/{id}/start`, `/next-question`, `/end`, `/cancel` | owner |
| `answers` | `POST /polls/{id}/answers` | student member |
| `results` | `GET /polls/{id}/results` (per-question distributions and first correct student) | owner, or participant once ended |
| `history` | `GET /me/polls`, `GET /me/polls/{id}/review` | student, own only |
| `insights` | `GET /polls/{id}/insights?question_id=` (+ version), `GET /polls/{id}/students/{sid}/insights` | owner |
| `ws` | `WS /ws/rooms/{id}` | member / owner |
| `internal` | `POST /internal/events/insights-updated` | shared secret |

There is **no chat history endpoint**.

---

## 8. Code layout and conventions

```
backend/
  api/  config/ enums/ errors/ exceptions.py dependencies.py db/ models/ repositories/
        schemas/ services/ routers/ realtime/ (connection_manager.py, redis_keys.py, lua/)
        workers/ (celery_app.py, tasks.py, llm_client.py)
  alembic/   tests/
frontend/   (React + Vite; see below)
docker-compose.yml   (postgres, redis, for local dev and tests)
```

Taken from CODING_PRACTICES: router → service → repository/client layers, `ErrorDefinition` + `create_error`, dependency injection via `app.state`, JWT persona claims in HTTP-only cookies, `PaginationParams`/`Page`, slowapi on auth routes, and settings from the environment.

Deliberate deviations:
- Repositories `flush()` and services `commit()`, for atomic multi-step workflows.
- Pydantic v2.
- snake_case fields, because there are no external APIs to mirror.

**Frontend mock data vs. backend models:** mocks live only in `frontend/src/mocks/` behind `VITE_USE_MOCKS` and are shaped like API responses, never like ORM models. The backend never seeds from them.

**Frontend chat:** a `useLiveChat` reducer keeps in-memory state only and stores at most `MAX_CHAT_MESSAGES = 200` (oldest dropped). It makes no fetch on mount or reconnect, so a reload starts empty. AI insights render in a separate teacher panel, which applies the 6 s minimum display time and ignores stale `insights_version` values.

---

## 9. Test plan

Backend tests use pytest, the FastAPI TestClient (WebSocket), fakeredis with Lua, and Celery tasks invoked directly. The LLM client is stubbed. PostgreSQL comes from docker-compose.

| Area | Tests |
|---|---|
| Connection manager | delivery to all sockets in a room; no cross-room delivery; register and unregister; a dead or slow socket is pruned and the others still receive |
| Chat | broadcast with no active poll and nothing buffered; broadcast plus buffering when a poll is active; there is no chat table, and the message count in the DB is unchanged after chatting; chat works after cancellation and is not buffered |
| Batching | dispatch at 50; time-based flush below 50; forced final flush includes every pre-close message; a message after close is not buffered |
| Handoff and retry | a publish failure after claim is recovered by the sweeper; transient LLM failure retries; a duplicate task run merges once |
| Cancellation | Redis poll keys cleared; pending batches CANCELLED; a queued task doesn't call the LLM; a running task's output is discarded |
| Finalization | atomic close stops answers; results computed from the snapshot; the first correct student is decided by seq; async persist is idempotent |
| Frontend (Vitest + RTL) | chat starts empty on mount or reload; the list is capped at 200; no fetch for history |
