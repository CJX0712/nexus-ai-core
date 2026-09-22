"""知识库路由（单一职责：只暴露入库与检索接口）。

作者: 晨星
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.schemas import (
    AskRequest,
    AskResponse,
    IngestResponse,
    IngestTextRequest,
    SearchHit,
    SearchRequest,
)
from app.container import Container, get_container

router = APIRouter(prefix="/v1/rag", tags=["rag"])


@router.post("/ingest", response_model=IngestResponse)
def ingest_text(req: IngestTextRequest,
                c: Container = Depends(get_container)) -> IngestResponse:
    res = c.rag.ingest_text(req.text, source=req.source, doc_id=req.doc_id,
                            metadata=req.metadata)
    c.persist()
    return IngestResponse(doc_id=res.doc_id, n_chunks=res.n_chunks,
                          source=res.source)


@router.post("/ingest-file", response_model=IngestResponse)
async def ingest_file(file: UploadFile = File(...),
                      c: Container = Depends(get_container)) -> IngestResponse:
    suffix = Path(file.filename or "upload.txt").suffix.lower() or ".txt"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        res = c.rag.ingest_file(tmp_path, source=file.filename)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    c.persist()
    return IngestResponse(doc_id=res.doc_id, n_chunks=res.n_chunks,
                          source=res.source)


@router.post("/search", response_model=list[SearchHit])
def search(req: SearchRequest,
           c: Container = Depends(get_container)) -> list[SearchHit]:
    return [SearchHit(**h) for h in c.rag.search(req.query, top_k=req.top_k)]


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, c: Container = Depends(get_container)) -> AskResponse:
    res = c.rag.answer(req.question, c.gateway, top_k=req.top_k)
    return AskResponse(answer=res.answer, provider=res.provider,
                       model=res.model, sources=res.sources,
                       latency_ms=res.latency_ms)
