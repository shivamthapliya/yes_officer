import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response
from sqlalchemy.orm import Session

from api.common.pagination import Page, PaginationParams
from api.db.session import get_db
from api.dependencies import (
    get_connection_manager,
    get_current_user,
    get_live_state,
    require_student,
    require_teacher,
)
from api.enums import PollStatus
from api.models import User
from api.realtime.connection_manager import ConnectionManager
from api.realtime.live_state import LiveStateStore
from api.routers.delivery import schedule_events, schedule_outcome
from api.schemas.insights import InsightsResponse
from api.schemas.poll import (
    LivePollState,
    PollCreateRequest,
    PollDetail,
    PollSummary,
    PollUpdateRequest,
    QuestionInput,
    QuestionOrderRequest,
    QuestionUpdateRequest,
)
from api.schemas.results import AnswerReceipt, AnswerSubmitRequest, PollResults
from api.services import (
    answer_service,
    insight_service,
    poll_lifecycle_service,
    poll_service,
    results_service,
)

router = APIRouter(tags=["Polls"])


# ---------- drafts ----------
@router.get("/rooms/{room_id}/polls", response_model=Page[PollSummary], summary="List the room's polls")
def list_polls(
    room_id: uuid.UUID,
    status: PollStatus | None = Query(None),
    params: PaginationParams = Depends(),
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return poll_service.list_polls(db, room_id, user, status, params)


@router.post("/rooms/{room_id}/polls", response_model=PollDetail, status_code=201, summary="Create a draft poll")
def create_poll(room_id: uuid.UUID, body: PollCreateRequest, user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return poll_service.create_poll(db, room_id, user, body)


@router.get("/polls/{poll_id}", response_model=PollDetail, summary="Poll with questions (owner)")
def get_poll(poll_id: uuid.UUID, user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return poll_service.get_poll(db, poll_id, user)


@router.patch("/polls/{poll_id}", response_model=PollDetail, summary="Edit a draft poll")
def update_poll(poll_id: uuid.UUID, body: PollUpdateRequest, user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return poll_service.update_poll(db, poll_id, user, body)


@router.delete("/polls/{poll_id}", status_code=204, summary="Delete a draft poll")
def delete_poll(poll_id: uuid.UUID, user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    poll_service.delete_poll(db, poll_id, user)
    return Response(status_code=204)


@router.post("/polls/{poll_id}/questions", response_model=PollDetail, status_code=201, summary="Add a question")
def add_question(poll_id: uuid.UUID, body: QuestionInput, user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return poll_service.add_question(db, poll_id, user, body)


@router.patch("/questions/{question_id}", response_model=PollDetail, summary="Edit a question and/or replace its options")
def update_question(
    question_id: uuid.UUID, body: QuestionUpdateRequest, user: User = Depends(require_teacher), db: Session = Depends(get_db)
):
    return poll_service.update_question(db, question_id, user, body)


@router.delete("/questions/{question_id}", response_model=PollDetail, summary="Delete a question")
def delete_question(question_id: uuid.UUID, user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return poll_service.delete_question(db, question_id, user)


@router.put("/polls/{poll_id}/questions/order", response_model=PollDetail, summary="Reorder questions")
def reorder_questions(
    poll_id: uuid.UUID, body: QuestionOrderRequest, user: User = Depends(require_teacher), db: Session = Depends(get_db)
):
    return poll_service.reorder_questions(db, poll_id, user, body)


# ---------- lifecycle ----------
@router.post("/polls/{poll_id}/start", response_model=LivePollState, summary="Start the poll")
def start_poll(
    poll_id: uuid.UUID,
    background: BackgroundTasks,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
    live: LiveStateStore = Depends(get_live_state),
    manager: ConnectionManager = Depends(get_connection_manager),
):
    poll = poll_service.get_owned_poll(db, poll_id, user)
    outcome = poll_lifecycle_service.start_poll(
        db, live, poll_id, user, manager.connected_student_ids(str(poll.room_id))
    )
    schedule_outcome(background, manager, outcome)
    return poll_lifecycle_service.get_live_state(db, live, poll_id, user)


@router.post("/polls/{poll_id}/next-question", response_model=LivePollState, summary="Open the next question")
def next_question(
    poll_id: uuid.UUID,
    background: BackgroundTasks,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
    live: LiveStateStore = Depends(get_live_state),
    manager: ConnectionManager = Depends(get_connection_manager),
):
    schedule_outcome(background, manager, poll_lifecycle_service.next_question(db, live, poll_id, user))
    return poll_lifecycle_service.get_live_state(db, live, poll_id, user)


@router.post("/polls/{poll_id}/end", response_model=PollResults, summary="End the poll and get results")
def end_poll(
    poll_id: uuid.UUID,
    background: BackgroundTasks,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
    live: LiveStateStore = Depends(get_live_state),
    manager: ConnectionManager = Depends(get_connection_manager),
):
    results, outcome = poll_lifecycle_service.end_poll(db, live, poll_id, user)
    schedule_outcome(background, manager, outcome)
    return results


@router.post("/polls/{poll_id}/cancel", response_model=PollSummary, summary="Cancel the poll (no results kept)")
def cancel_poll(
    poll_id: uuid.UUID,
    background: BackgroundTasks,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
    live: LiveStateStore = Depends(get_live_state),
    manager: ConnectionManager = Depends(get_connection_manager),
):
    schedule_outcome(background, manager, poll_lifecycle_service.cancel_poll(db, live, poll_id, user))
    poll = poll_service.get_owned_poll(db, poll_id, user)
    return poll_service.to_summary(poll, 0)


@router.get("/polls/{poll_id}/live", response_model=LivePollState, summary="Live state of a poll")
def live_state(
    poll_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    live: LiveStateStore = Depends(get_live_state),
):
    return poll_lifecycle_service.get_live_state(db, live, poll_id, user)


# ---------- answers & results ----------
@router.post("/polls/{poll_id}/answers", response_model=AnswerReceipt, summary="Submit an answer to the open question")
def submit_answer(
    poll_id: uuid.UUID,
    body: AnswerSubmitRequest,
    background: BackgroundTasks,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
    live: LiveStateStore = Depends(get_live_state),
    manager: ConnectionManager = Depends(get_connection_manager),
):
    receipt, progress = answer_service.submit_answer(db, live, poll_id, user, body)
    schedule_events(background, manager, progress)
    return receipt


@router.get("/polls/{poll_id}/results", response_model=PollResults, summary="Per-question results")
def get_results(
    poll_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    live: LiveStateStore = Depends(get_live_state),
):
    return results_service.get_results(db, live, poll_id, user)


# ---------- insights ----------
@router.get("/polls/{poll_id}/insights", response_model=InsightsResponse, summary="AI insights for the poll")
def get_insights(
    poll_id: uuid.UUID,
    question_id: uuid.UUID | None = Query(None),
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return insight_service.get_insights(db, poll_id, user, question_id)


@router.get("/polls/{poll_id}/students/{student_id}/insights", response_model=InsightsResponse, summary="AI insights about one student")
def get_student_insights(
    poll_id: uuid.UUID, student_id: uuid.UUID, user: User = Depends(require_teacher), db: Session = Depends(get_db)
):
    return insight_service.get_student_insights(db, poll_id, student_id, user)
