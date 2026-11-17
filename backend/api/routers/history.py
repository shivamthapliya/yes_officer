import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.common.pagination import Page, PaginationParams
from api.db.session import get_db
from api.dependencies import get_live_state, require_student
from api.models import User
from api.realtime.live_state import LiveStateStore
from api.schemas.results import MyPollItem, PollReview
from api.services import results_service

router = APIRouter(prefix="/me", tags=["History"])


@router.get("/polls", response_model=Page[MyPollItem], summary="Polls I took part in")
def my_polls(
    params: PaginationParams = Depends(),
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
    live: LiveStateStore = Depends(get_live_state),
):
    return results_service.list_my_polls(db, live, user, params)


@router.get("/polls/{poll_id}/review", response_model=PollReview, summary="Review my answers vs. correct answers")
def review(
    poll_id: uuid.UUID,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
    live: LiveStateStore = Depends(get_live_state),
):
    return results_service.get_review(db, live, poll_id, user)
