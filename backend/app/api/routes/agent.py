"""智能体路由（单一职责：只暴露 ReAct 智能体执行接口）。

作者: 晨星
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.agent.react import ReactAgent
from app.agent.tools import build_default_registry
from app.api.schemas import AgentRequest, AgentResponse, AgentStepOut
from app.container import Container, get_container

router = APIRouter(prefix="/v1/agent", tags=["agent"])


@router.post("/run", response_model=AgentResponse)
def run(req: AgentRequest, c: Container = Depends(get_container)) -> AgentResponse:
    registry = build_default_registry(
        rag_service=c.rag, memory_store=c.memory, session_id=req.session_id
    )
    agent = ReactAgent(c.gateway, registry, c.settings)
    result = agent.run(req.task, max_steps=req.max_steps)

    c.memory.add(req.session_id, "user", req.task)
    c.memory.add(req.session_id, "assistant", result.answer)

    return AgentResponse(
        answer=result.answer,
        finished=result.finished,
        tool_calls=result.tool_calls,
        provider=result.provider,
        model=result.model,
        steps=[AgentStepOut(**s.__dict__) for s in result.steps],
    )
