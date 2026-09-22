"""记忆路由（单一职责：只暴露会话记忆的读写接口）。

作者: 晨星
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.schemas import MemoryAddRequest, MemoryItem
from app.container import Container, get_container

router = APIRouter(prefix="/v1/memory", tags=["memory"])


@router.get("/{session_id}", response_model=list[MemoryItem])
def read(session_id: str, n: int = Query(20, ge=1, le=200),
         c: Container = Depends(get_container)) -> list[MemoryItem]:
    return [MemoryItem(**i) for i in c.memory.recent(session_id, n=n)]


@router.post("/{session_id}", response_model=dict)
def write(session_id: str, req: MemoryAddRequest,
          c: Container = Depends(get_container)) -> dict:
    mid = c.memory.add(session_id, req.role, req.content, kind=req.kind)
    return {"id": mid, "session_id": session_id}


@router.post("/{session_id}/recall", response_model=list[MemoryItem])
def recall(session_id: str, query: str = Query(..., min_length=1),
           limit: int = Query(5, ge=1, le=50),
           c: Container = Depends(get_container)) -> list[MemoryItem]:
    return [MemoryItem(**i) for i in c.memory.recall(session_id, query, limit=limit)]


@router.delete("/{session_id}", response_model=dict)
def clear(session_id: str,
          c: Container = Depends(get_container)) -> dict:
    return {"deleted": c.memory.clear(session_id), "session_id": session_id}
