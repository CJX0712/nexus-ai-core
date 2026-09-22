"""系统与可观测路由（单一职责：只暴露健康检查与系统自描述）。

作者: 晨星
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.schemas import HealthResponse, ModelInfo, StatsResponse
from app.container import Container, get_container

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(c: Container = Depends(get_container)) -> HealthResponse:
    stats = c.rag.stats()
    return HealthResponse(
        status="ok",
        version=c.settings.version,
        embedding_provider=getattr(c.embedder, "name", "unknown"),
        llm_chain=[p.name for p in c.gateway.providers],
        rag_chunks=int(stats["chunks"]),
        documents=int(stats["documents"]),
    )


@router.get("/v1/stats", response_model=StatsResponse)
def stats(c: Container = Depends(get_container)) -> StatsResponse:
    d = c.describe()
    return StatsResponse(**d)


@router.get("/v1/models", response_model=list[ModelInfo])
def models(c: Container = Depends(get_container)) -> list[ModelInfo]:
    return [ModelInfo(**m) for m in c.gateway.available_models()]
