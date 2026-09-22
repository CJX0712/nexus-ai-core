"""API 契约模型（单一职责：只定义请求/响应的数据结构）。

作者: 晨星
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------- 通用 ----------
class HealthResponse(BaseModel):
    status: str
    version: str
    embedding_provider: str
    llm_chain: list[str]
    rag_chunks: int
    documents: int


class StatsResponse(BaseModel):
    app: str
    version: str
    embedding: dict
    llm_chain: list[str]
    tools: list[str]
    rag: dict


class ModelInfo(BaseModel):
    provider: str
    model: str


# ---------- 对话 ----------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户输入")
    session_id: str = "default"
    use_rag: bool = False
    top_k: int = 4


class ChatResponse(BaseModel):
    answer: str
    provider: str
    model: str
    session_id: str
    sources: list[dict] = Field(default_factory=list)
    latency_ms: float = 0.0


# ---------- 知识库 ----------
class IngestTextRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source: str = "inline"
    doc_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class IngestResponse(BaseModel):
    doc_id: str
    n_chunks: int
    source: str


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = 4


class SearchHit(BaseModel):
    score: float
    text: str
    doc_id: str
    chunk_id: int
    metadata: dict = Field(default_factory=dict)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = 4


class AskResponse(BaseModel):
    answer: str
    provider: str
    model: str
    sources: list[dict] = Field(default_factory=list)
    latency_ms: float = 0.0


# ---------- 智能体 ----------
class AgentRequest(BaseModel):
    task: str = Field(..., min_length=1)
    session_id: str = "default"
    max_steps: int = 6


class AgentStepOut(BaseModel):
    thought: str = ""
    action: str = ""
    action_input: str = ""
    observation: str = ""
    final: str = ""


class AgentResponse(BaseModel):
    answer: str
    finished: bool
    tool_calls: int
    provider: str
    model: str
    steps: list[AgentStepOut] = Field(default_factory=list)


# ---------- 工作流 ----------
class WorkflowNodeIn(BaseModel):
    id: str
    kind: str = Field(..., description="llm | rag | tool | transform")
    params: dict = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)


class WorkflowRequest(BaseModel):
    nodes: list[WorkflowNodeIn]
    input: str = ""


class WorkflowResponse(BaseModel):
    order: list[str]
    outputs: dict[str, Any]


# ---------- 记忆 ----------
class MemoryAddRequest(BaseModel):
    role: str = "user"
    content: str = Field(..., min_length=1)
    kind: str = "chat"


class MemoryItem(BaseModel):
    role: str
    content: str
    kind: str
    ts: float
