"""用户反馈路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.entities import Feedback, User
from app.schemas.schemas import FeedbackCreate, FeedbackOut

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackOut)
def submit_feedback(
    data: FeedbackCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fb = Feedback(
        user_id=user.user_id, analysis_id=data.analysis_id,
        rating=data.rating, comment=data.comment, correct=data.correct,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return FeedbackOut(feedback_id=fb.feedback_id)