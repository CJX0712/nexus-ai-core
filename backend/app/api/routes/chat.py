"""对话路由（单一职责：只编排 网关 + 可选RAG + 记忆 的对话流程）。

作者: 晨星
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from app.api.schemas import ChatRequest, ChatResponse
from app.container import Container, get_container
from app.gateway.llm import ChatMessage

router = APIRouter(prefix="/v1", tags=["chat"])

SYSTEM = "你是 NexusAI，一个简洁、准确、结构化的中文 AI 助手。"


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, c: Container = Depends(get_container)) -> ChatResponse:
    started = time.perf_counter()
    sources: list[dict] = []

    if req.use_rag and c.rag.stats()["chunks"] > 0:
        res = c.rag.answer(req.message, c.gateway, top_k=req.top_k)
        answer, provider, model = res.answer, res.provider, res.model
        sources = res.sources
    else:
        history = c.memory.recent(req.session_id, n=c.settings.memory_max_turns)
        messages = [ChatMessage(role="system", content=SYSTEM)]
        for item in history:
            messages.append(ChatMessage(role=item["role"], content=item["content"]))
        messages.append(ChatMessage(role="user", content=req.message))
        out = c.gateway.complete(messages, settings=c.settings)
        answer, provider, model = out.text, out.provider, out.model

    c.memory.add(req.session_id, "user", req.message)
    c.memory.add(req.session_id, "assistant", answer)

    return ChatResponse(
        answer=answer, provider=provider, model=model,
        session_id=req.session_id, sources=sources,
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
    )
