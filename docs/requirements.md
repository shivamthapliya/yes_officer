# QUIZ & LIVE POLLING PLATFORM

## System Architecture and Technical Design

> Corrected architecture: one pre-provisioned room per teacher

```{=html}
<!-- Page 1 -->
```
QUIZ & LIVE POLLING PLATFORM \| SYSTEM DESIGN QUIZ & LIVE POLLING
PLATFORM System Architecture and Technical Design Corrected
architecture: one pre-provisioned room per teacher

```{=html}
<!-- Page 2 -->
```
QUIZ & LIVE POLLING PLATFORM \| SYSTEM DESIGN 1. Overview The
application is a real-time quiz and polling platform with two user
roles: Teacher and Student. Teachers manage polls in a single room that
is automatically associated with their account. Students can discover
teacher rooms, join a room, participate in polls, chat, and review
completed quizzes. The design separates three responsibilities: -
Official MCQ answer collection and scoring. - Live chat collection,
asynchronous AI analysis, and teacher-facing insights. - Durable storage
of users, rooms, polls, answers, chat history, results, and analytics.
2. Technology Stack Component Technology Responsibility Frontend React +
JavaScript Teacher and student interfaces. Backend FastAPI REST APIs,
authentication, authorization, and business logic. Real-time
communication WebSockets Room chat, poll events, and live analytics
updates. Primary database PostgreSQL Durable application data and
historical records. In-memory / buffer store Redis Live poll state,
accepted answers, and pending chat-message buffers. Background
processing Celery Asynchronous batch processing and AI analysis. Task
broker Redis Queues Celery tasks for workers. Redis serves both as the
application's live-state/buffer store and as the Celery task broker.
These are logically separate responsibilities and should use separate
key namespaces and appropriate operational configuration. The frontend
is implemented with React and JavaScript. 3. User Registration and
Authentication 3.1 User roles - Teacher: manages their assigned room,
creates MCQ polls, monitors participation, and views results and
analytics. - Student: discovers and joins teacher rooms, participates in
polls, chats, and reviews completed polls. 3.2 Registration Teachers and
students can register without email or phone verification in the agreed
flow. 1. The user submits registration details. 2. FastAPI validates the
submitted information. 3. The user account is created in PostgreSQL. 4.
If the new account is a teacher, the system provisions exactly one room
associated with that teacher's ID as part of the registration
transaction or a reliably retried provisioning workflow. 5. Registration
completes successfully.

```{=html}
<!-- Page 3 -->
```
QUIZ & LIVE POLLING PLATFORM \| SYSTEM DESIGN 3.3 Login 6. The user
submits login credentials. 7. FastAPI validates the credentials against
PostgreSQL. 8. The backend identifies the user's role/persona. 9. The
backend issues access and refresh tokens. 10. For a teacher, the backend
retrieves the already-provisioned room associated with the teacher ID
and returns its details. Login must not create another room. 11. The
frontend routes the user to the teacher dashboard/room or student
dashboard. Authorization must be enforced by the backend. A student must
not be able to invoke teacher-only APIs, and a teacher must only manage
the room associated with their own teacher ID. 4. Room Model: Exactly
One Room per Teacher Teachers do not create rooms manually. Each teacher
has one pre-provisioned room associated with their unique teacher ID.
The room is created when the teacher account is registered (or by an
idempotent provisioning process immediately associated with account
creation). - One teacher has exactly one room. - Each room belongs to
exactly one teacher. - A teacher cannot create additional rooms. - When
a teacher logs in, the existing room is retrieved; login does not create
a new room. - Students can browse available teacher rooms and join the
room belonging to the teacher they want to attend. - A teacher's room
can host multiple poll sessions over time. Database enforcement:
rooms.teacher_id should have a UNIQUE constraint and a foreign key to
the teacher account. Room provisioning should be idempotent so retries
or concurrent requests cannot create duplicates. 4.1 Room and poll
relationship Relationship Cardinality Meaning Teacher Room → One-to-one
Each teacher has one pre-provisioned room. Room Poll → One-to-many The
teacher can run multiple polls over time in the same room. Poll
PollQuestion → One-to-many Each poll contains its own MCQ questions.
Poll StudentAnswer → One-to-many Students submit answers to questions in
a poll. Room / Poll ChatMessage → One-to-many Chat messages are
associated with the room and, where relevant, the active poll. 5.
Teacher Workflow - Log in and open the existing room associated with the
teacher account. - Add MCQ questions to a poll and configure answer
options and the correct answer. - Start a poll session. - Monitor
participating students and room chat.

```{=html}
<!-- Page 4 -->
```
## QUIZ & LIVE POLLING PLATFORM \| SYSTEM DESIGN

## View live AI-generated insights while the poll is active.

## End the poll normally or cancel it; cancellation follows the separate cleanup workflow in Section 12.1.

## View official results, overall analytics, and individual student analytics.

## Review questions asked by students and the associated chat context.

Access historical polls and reports. 6. Student Workflow - Register and
log in. - Browse available teacher rooms. - Join the room associated
with the relevant teacher. - Participate in room discussions through
chat. - View MCQ questions when a poll is active. - Submit answers. -
View results after the poll is completed, subject to the product's
result-release rules. - Revisit completed polls and review each
question, the answer they submitted, and the correct answer. 7. Poll
Session Lifecycle When the teacher starts a poll, the backend marks the
poll session as active and enables the relevant live workflows. Three
processes operate concurrently: - Official MCQ answer collection. - Chat
collection and buffering. - Asynchronous AI analysis and teacher-facing
analytics. 7.1 Starting a poll 12. The backend verifies that the teacher
owns the room and the poll is eligible to start. 13. The poll status is
changed to active. 14. The system initializes or identifies the Redis
structures for live answer state and pending chat messages. 15. The
server begins associating incoming room chat messages with the active
poll/session. 16. Students in the room receive a poll-start event
through WebSockets. 8. Official MCQ Answer Submission The
answer-submission pipeline is independent of AI processing. A student
answer must be accepted and acknowledged without waiting for chat
batching or AI analysis. 17. The student submits an MCQ answer to
FastAPI. 18. The backend validates the poll state, deadline, student
eligibility, question ID, and submitted option. 19. Redis atomically
checks whether an answer has already been accepted for that student and
question in the poll. 20. The first valid answer is accepted and stored
with a server-generated receipt timestamp. 21. The backend acknowledges
the accepted submission to the frontend. 8.1 Agreed answer rules - First
valid answer wins for a student/question/poll combination.

```{=html}
<!-- Page 5 -->
```
## QUIZ & LIVE POLLING PLATFORM \| SYSTEM DESIGN

## The frontend does not determine the official submission timestamp.

## The official timestamp is the server receipt time recorded when the backend accepts the submission.

Duplicate or subsequent submissions are rejected or treated as already
submitted according to the API contract. - AI analysis and chat messages
never create or modify official MCQ submissions. The server receipt
timestamp is not a claim about the exact physical click time. A request
that reaches the server later can have a later official timestamp, even
if the student clicked earlier. This trade-off was accepted because the
MCQs are not intended to be highly timing-sensitive. 9. Live Chat
Monitoring and AI Analytics Chat monitoring is activated when the
teacher starts a poll and runs concurrently with MCQ answer collection.
The backend receives room chat messages, associates them with the room
and active poll where applicable, and places them into a Redis buffer
for asynchronous analysis. 9.1 Chat message context Each message should
retain sufficient source context for traceability: - Message ID and
poll/session ID. - Room ID and student ID. - Original message content. -
Server receipt timestamp. - Optional question/topic association when it
can be identified. 9.2 AI analytics categories Analytics category
Description Common doubts Identify questions or doubts repeatedly raised
by students, including recurring requests for clarification about the
same concept. Confusion detection Identify topics or questions that
students appear to misunderstand. Engagement Summarize general
participation and discussion activity, using transparent and relevant
indicators. Misconceptions Identify incorrect concepts or explanations
repeatedly expressed in chat. Uncounted responses Identify students who
appear to indicate an MCQ option in chat rather than submitting it
through the official answer interface. Example: several students may
write that they think the answer is option B in chat without submitting
an official MCQ answer. AI may flag this as an uncounted response for
teacher attention. It must not be added to the official answer records
or scoring. 9.3 Live teacher analytics As asynchronous batches are
analyzed, the system stores the resulting insights and makes updated
analytics available to the teacher through WebSockets or an equivalent
refresh mechanism. AI processing must not block chat delivery or MCQ
answer submission. - Frequently asked questions and common doubts.

```{=html}
<!-- Page 6 -->
```
## QUIZ & LIVE POLLING PLATFORM \| SYSTEM DESIGN

## Confusion areas and recurring misconceptions.

## Engagement and participation summaries.

## Potential uncounted responses, linked to their source messages.

Student-specific observations where there is sufficient supporting
evidence. 9.4 Insight Aggregation and Duplicate Handling AI analysis is
performed in batches of up to 50 messages. Different batches from the
same poll or question may identify overlapping or repetitive
observations. The system should therefore distinguish batch-level AI
output from the consolidated insights displayed to the teacher. For the
current project, use lightweight, deterministic deduplication rather
than semantic search. Normalize insight categories and topic labels, and
merge observations when their normalized category/topic keys match. When
a match is uncertain, retain the observations separately rather than
risking an incorrect merge. Update supporting message references and
counts when observations are merged. A vector database, embeddings, and
semantic-similarity search are explicitly out of scope for this
implementation. Some semantically similar insights may consequently
remain duplicated across batches. This is an accepted prototype
trade-off; more advanced semantic deduplication can be considered in a
future iteration if the need is demonstrated. Every batch and insight
must retain its originating poll/session ID and, where identifiable,
question ID. If an AI response arrives after the teacher has moved to
another question or started another poll, persist and aggregate it under
its original context. Do not display it in the currently active
question's analytics. The dashboard should request or subscribe to
analytics scoped to the active poll/question, and late results should
remain available in the relevant historical view.

**Implementation comment:** messages, and simple deterministic duplicate
reduction. Accept that this will not eliminate all semantically
equivalent insights. Do not introduce a vector database solely to solve
this edge case; revisit only if duplicate insights materially reduce the
usefulness of the teacher dashboard. 9.5 Teacher Dashboard Update
Presentation AI analysis updates should be pushed to the teacher
dashboard in real time through the existing WebSocket notification flow.
However, the frontend should avoid replacing the visible analysis too
frequently when several batch-completion events arrive close together.
Apply a minimum display duration of 6 seconds to the currently displayed
analysis. Frontend presentation rules: - Apply every incoming event to
the latest client-side analysis state immediately; do not delay backend
processing, persistence, or event handling. - Keep the currently
displayed analysis visible for at least 6 seconds before replacing it
with a newer version. - If one or more updates arrive during that
interval, retain only the newest pending consolidated update for
display. When the 6-second minimum has elapsed, show that latest
update. - If further updates arrive while waiting, replace the pending
update with the newest one. Do not queue every intermediate UI state,
because that can make the dashboard display stale analysis. - Do not
discard batch results or insight data when coalescing UI updates. All
results must still be persisted and merged into the backend consolidated
analytics for their originating poll/question.

```{=html}
<!-- Page 7 -->
```
## QUIZ & LIVE POLLING PLATFORM \| SYSTEM DESIGN

Include a monotonically increasing insights_version (or equivalent
revision) in update events. The frontend should ignore stale versions so
out-of-order WebSocket delivery cannot roll the displayed analysis back
to an older state.

**Implementation comment:** frontend presentation rules only. They must
not slow down WebSocket event consumption, AI batch processing, or
backend persistence. The backend remains the source of truth; after
reconnecting, the dashboard should fetch the latest consolidated
analytics and version for the active poll/question. 10. Redis Buffering
and Celery Batch Processing The application should not create one Celery
task for every chat message. Instead, it accumulates messages in Redis
and dispatches a batch for asynchronous analysis. 10.1 Agreed batching
decisions Decision Agreed approach Maximum batch size 50 messages.
Primary flush trigger Flush when the pending batch reaches 50. Poll-end
flush Flush all remaining messages when the poll ends. Time-based flush
Optionally flush after a short configurable interval so low- volume
polls are not left waiting. Processing Celery workers process the
claimed batch asynchronously. 10.2 Processing flow 22. FastAPI receives
a chat message and appends it to the pending Redis buffer. 23. A
dispatcher is triggered by the batch threshold and/or a periodic
time-based check. 24. The dispatcher atomically claims up to 50 pending
messages. 25. The claimed batch is published as one Celery task. 26. A
Celery worker analyzes the messages and generates structured insights.
27. The system stores the analysis output and its source/batch
references. 28. The teacher dashboard receives an update. 10.3
Concurrency and atomic claiming A simple RPUSH followed by LLEN and
dispatch_batch.delay() is not sufficient: concurrent API requests can
observe the threshold and trigger multiple dispatchers. A Redis
distributed lock can coordinate dispatch decisions, but a mutex alone
does not guarantee safe message claiming. Preferred approach: use an
atomic Redis batch-claim operation, such as a Lua script that moves
messages from a pending queue into a processing queue. The script
executes atomically, preventing concurrent dispatchers from claiming the
same messages. Redis Streams with consumer groups is also a valid design
option if pending-entry tracking, acknowledgement, and recovery are
preferred over implementing these mechanics with lists. 10.4 Reliability
requirements - Keep claimed messages recoverable until processing
succeeds. - Acknowledge or remove messages only after successful
processing and durable storage of the result.

```{=html}
<!-- Page 8 -->
```
## QUIZ & LIVE POLLING PLATFORM \| SYSTEM DESIGN

## Retry transient failures and provide a recovery process for abandoned batches.

## Make processing idempotent using stable message IDs and batch IDs.

Handle the gap between Redis claiming and Celery task publication. A
crash after claiming but before publishing must not silently lose the
batch. - Ensure poll-end flushing does not race with an in-progress
dispatcher or worker. 11. Teacher Analytics and Student-Specific
Insights Teachers need both overall poll analytics and student-level
information. AI insights should be traceable to the messages that
support them. 11.1 Overall poll analytics - Total participating
students. - Question-wise accuracy. - Correct and incorrect answer
distribution. - Option-wise response distribution. - Frequently asked
questions and common doubts. - Confusion areas and misconceptions. -
Engagement and discussion activity. - Potential uncounted responses.
11.2 Individual student analytics - The student's submitted answers and
correctness. - Overall score and performance. - Questions and doubts
raised by the student in chat. - AI-identified misconceptions or
confusion, with supporting source messages. - Relevant participation and
engagement information. 11.3 Student questions and source traceability
The teacher should be able to inspect questions raised by students, not
only an AI-generated summary. Each displayed item should include, where
available: - Student name or identifier. - Original chat message. -
Timestamp. - Associated poll and question/topic, if identifiable. -
AI-generated classification or summary. - A link or reference to the
original message. AI inferences should be clearly distinguished from
observed facts. The system should not present uncertain interpretations
as confirmed student attributes or diagnoses. 12. Poll Completion and
Final Results When the teacher ends a poll, the backend closes the
submission window and coordinates final answer and chat processing. 29.
Mark the poll as ended and reject new answer submissions.

```{=html}
<!-- Page 9 -->
```
QUIZ & LIVE POLLING PLATFORM \| SYSTEM DESIGN 30. Ensure all accepted
answers are included in the final answer snapshot. 31. Flush remaining
chat messages into the AI processing pipeline. 32. Calculate official
results using accepted MCQ answers and teacher-defined correct answers.
33. Persist answers and results to PostgreSQL using reliable bulk
operations. 34. Complete final AI analysis for the remaining chat
messages. 35. Make final analytics available to the teacher. Official
scores are calculated exclusively from accepted MCQ submissions.
AI-generated observations are supplementary and must never modify
official scores. The system should track result-persistence and
final-analysis status separately. It should not claim that all final
analytics are complete while the last chat batch is still processing.
12.1 Poll Cancellation and Cleanup The teacher can cancel an active poll
instead of ending it normally. Cancellation is different from
completion: a cancelled poll does not produce official results or a
historical quiz record. The cancellation workflow must prevent any
remaining answer, chat, or AI-analysis work associated with that poll
from being persisted as completed poll data. Cancellation workflow: -
The teacher sends a cancel request. The backend verifies ownership and
atomically transitions the poll from ACTIVE to CANCELLED. This state
transition is the cancellation boundary; subsequent answer submissions
and poll-scoped chat/AI work must be rejected or ignored. - The backend
marks the poll as cancelled before performing cleanup, so concurrent
requests and workers can see the cancellation state. Cancellation must
be idempotent; repeated cancel requests must not create additional
cleanup work or change the outcome. - Remove the cancelled poll's
question records and any poll-scoped official answer/result data from
PostgreSQL. Do not create or retain a completed poll result, answer
history, or AI insight records for the cancelled poll. Any poll-scoped
chat messages intended only for that cancelled poll must also not be
persisted; unrelated room-level chat history is unaffected. - Clear
Redis data belonging to the cancelled poll, including live poll
metadata, accepted-answer structures, temporary answer snapshots,
pending AI message buffers, batch payloads, pending-dispatch entries,
and other poll-scoped keys. Use a poll-specific key namespace so cleanup
cannot affect another poll in the same room. - Mark all AI batches
associated with the poll as CANCELLED and prevent queued batches from
starting. Workers must check the poll cancellation state before invoking
the LLM and again before writing any results. If a task is already
executing an external LLM request and cannot be stopped safely, allow
the request to finish but discard its response and do not persist or
publish insights. - Best-effort Celery task revocation may be used to
reduce unnecessary queued work, but correctness must not depend on
force-terminating a running worker. The cancellation marker/state check
is the authoritative safeguard against late AI results. - Notify
connected students and the teacher through WebSockets that the poll was
cancelled. The teacher dashboard should clear the cancelled poll's live
results and AI analysis and return to the appropriate room state.

**Implementation comment:** run the normal finalization pipeline,
calculate official scores, bulk-persist answers, or flush remaining chat
for

```{=html}
<!-- Page 10 -->
```
QUIZ & LIVE POLLING PLATFORM \| SYSTEM DESIGN AI evaluation. Use
poll-scoped cleanup and cancellation checks to ensure delayed Celery
tasks cannot recreate data after cleanup. 13. Student Historical Results
and Answer Review After a poll is completed and results are released,
students should be able to revisit their completed polls. This is a core
product requirement. 13.1 Student review screen For every question,
display: - Question statement. - All available answer options. - The
option submitted by the student, or an explicit indication that no
answer was submitted. - The correct answer. - Whether the submitted
answer was correct or incorrect. The student should also be able to view
their total score, correct and incorrect answer counts, overall
percentage, and poll completion information. Historical review data must
be retrieved from PostgreSQL, not from temporary Redis state. The
backend must authorize access so students can only view their own
submissions and permitted poll results. 14. Data Persistence and
Suggested Data Model Redis supports live state and temporary processing.
PostgreSQL is the durable source of truth for accounts, room ownership,
polls, official submissions, chat history, results, and stored
analytics. Entity Purpose / key relationships User Teacher and student
accounts; includes role/persona. Room One room per teacher; teacher_id
is unique. RoomParticipant Tracks students associated with a room, if
membership is persisted. Poll Poll session belonging to a room; multiple
polls can exist over time. PollQuestion MCQ questions belonging to a
poll. QuestionOption Options belonging to a question, including the
correct-answer configuration. StudentAnswer Official accepted answer,
student, question, poll, and server receipt timestamp. PollResult
Persisted official results or result snapshots. ChatMessage Original
chat message, author, room, timestamp, and relevant poll association.
AIAnalysisBatch Batch ID, poll ID, processing status, retry metadata,
and message references. AIInsight Generated insight, category, poll,
optional student association, and source-message references. 14.1
Important constraints - UNIQUE constraint on Room.teacher_id to enforce
one room per teacher. - Foreign keys to enforce room ownership and
poll/question relationships.

```{=html}
<!-- Page 11 -->
```
## QUIZ & LIVE POLLING PLATFORM \| SYSTEM DESIGN

A uniqueness constraint for one accepted answer per
student/question/poll, matching the first-answer- wins rule. - Stable
unique message IDs and batch IDs for idempotent processing. -
Appropriate indexes for poll ID, room ID, student ID, and timestamps.
15. End-to-End Architecture Summary The system has three concurrent
pipelines during an active poll: Pipeline A --- Official MCQ answer
processing Student submits answer FastAPI validation atomic first-answer
acceptance in Redis live answer state → → → final scoring durable
PostgreSQL persistence. → → Pipeline B --- Chat collection and AI
analytics Student sends chat message FastAPI/WebSocket handling Redis
pending buffer atomic batch → → → dispatcher Celery broker Celery worker
AI analysis stored insights teacher dashboard update → → → → → through
WebSockets. Pipeline C --- Historical review Poll completion durable
PostgreSQL records student reviews their own submitted and correct
answers; → → teacher reviews poll results, student questions, and
overall and individual analytics. 16. Implementation Roadmap 36.
Registration, login, JWT access/refresh tokens, and role-based
authorization. 37. Teacher room provisioning at account creation;
enforce one room per teacher. 38. Teacher dashboard retrieves the
existing room on login; no room-creation workflow. 39. Student room
discovery and joining. 40. MCQ and poll management. 41. WebSocket room
communication and chat. 42. Poll lifecycle and session controls. 43.
Redis-based atomic official answer acceptance. 44. Redis chat buffering
and Celery batch dispatcher. 45. Asynchronous AI chat monitoring and
live teacher analytics. 46. Teacher overall and individual student
analytics views. 47. Poll completion, official result calculation, and
poll-cancellation cleanup. 48. Reliable PostgreSQL persistence. 49.
Student historical poll and answer review. 50. Teacher historical
reports and student-question review. 51. Concurrency, retry, recovery,
idempotency, and end-to-end testing. - AI insight deduplication uses
normalized deterministic keys for this prototype; vector-database-based
semantic search is out of scope, and some duplicate insights are an
accepted trade-off.

```{=html}
<!-- Page 12 -->
```
QUIZ & LIVE POLLING PLATFORM \| SYSTEM DESIGN 17. Final Architectural
Principles - Each teacher has exactly one pre-provisioned room; teachers
cannot create additional rooms. - Teacher login retrieves the existing
room and must not create another one. - A room can host multiple polls
over time. - Official MCQ answer processing and AI chat analysis remain
independent. - The first valid MCQ answer is accepted; the server
receipt timestamp is authoritative. - Redis handles low-latency live
state and temporary buffering. - PostgreSQL stores durable records and
historical results. - Celery handles asynchronous workloads and AI
processing. A cancelled poll is not finalized: remove its question and
poll-scoped data, clear its Redis state, and cancel/discard associated
AI batches without persisting results. - Chat batches contain at most 50
messages and are flushed on threshold, time interval, and poll end. -
Batch claiming, retries, acknowledgement, recovery, and cancellation
must be reliable and idempotent. - AI analytics should be available
during the poll, not only after completion. - Teachers can inspect
overall analytics, individual student analytics, and original student
questions. - Students can revisit completed polls and compare their
submitted answers with correct answers. - AI observations are
supplementary and never become official submissions or alter scores.

### Overall design objective

Build a real-time polling platform in which each teacher operates from
one permanent room, students can participate and review their
performance, and teachers receive conventional quiz analytics together
with AI-powered insights into classroom discussions, doubts,
misconceptions, engagement, and student-specific questions.
