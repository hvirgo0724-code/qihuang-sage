"""知识库浏览与检索路由（公开，需登录）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.schemas import GraphStats, NodeDetail, SearchResponse
from app.services import knowledge_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = "",
    type: str = "all",
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = knowledge_service.search(type, q, page, page_size)
    return SearchResponse(items=items, total=total)


@router.get("/formulas/{name}", response_model=NodeDetail)
def formula(name: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    detail = knowledge_service.get_node_detail("Formula", name)
    if not detail:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="方剂不存在")
    return detail


@router.get("/herbs/{name}", response_model=NodeDetail)
def herb(name: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    detail = knowledge_service.get_node_detail("Herb", name)
    if detail is None:
        raise HTTPException(status_code=404, detail="中药不存在或知识库暂不可用")
    return detail


@router.get("/syndromes/{name}", response_model=NodeDetail)
def syndrome(name: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    detail = knowledge_service.get_node_detail("Syndrome", name)
    if detail is None:
        raise HTTPException(status_code=404, detail="证型不存在或知识库暂不可用")
    return detail


@router.get("/stats", response_model=GraphStats)
def stats(user=Depends(get_current_user), db: Session = Depends(get_db)):
    data = knowledge_service.stats()
    return GraphStats(**data)


@router.get("/symptoms/{name}", response_model=NodeDetail)
def symptom(name: str, user=Depends(get_current_user)):
    detail = knowledge_service.get_node_detail("Symptom", name)
    if detail is None:
        raise HTTPException(status_code=404, detail="症状不存在或知识库暂不可用")
    return detail
