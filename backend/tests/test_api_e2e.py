"""端到端 API 测试：全链路跑通 入库->检索->应答->智能体->工作流->记忆。

作者: 晨星
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.container import get_container

DOC = (
    "NexusAI 是一个模块化 AI 能力中台。"
    "它包含五个核心模块：模型网关、知识检索、智能体编排、工作流引擎与记忆模块。"
    "模型网关支持云端 API 与本地 GGUF 两级降级。"
)


@pytest.fixture()
def client(container):
    app.dependency_overrides[get_container] = lambda: container
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------- 系统 ----------------
def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["embedding_provider"] == "hashing"
    assert "offline_extractive" in body["llm_chain"]


def test_stats_and_models(client):
    assert client.get("/v1/stats").json()["version"]
    models = client.get("/v1/models").json()
    assert any(m["provider"] == "offline_extractive" for m in models)


# ---------------- 知识库 ----------------
def test_rag_ingest_search_ask(client):
    assert client.post("/v1/rag/ingest", json={"text": DOC, "source": "doc.md"}).json()[
        "n_chunks"
    ] >= 1

    hits = client.post("/v1/rag/search", json={"query": "核心模块", "top_k": 2}).json()
    assert hits and "模块" in hits[0]["text"]

    ask = client.post("/v1/rag/ask", json={"question": "NexusAI 有哪五个模块？"}).json()
    assert "模块" in ask["answer"]
    assert ask["sources"], "应答必须带溯源来源"


def test_rag_ingest_file_upload(client):
    files = {"file": ("note.txt", "上传文件内容：向量库使用 FAISS。".encode(),
                      "text/plain")}
    r = client.post("/v1/rag/ingest-file", files=files)
    assert r.status_code == 200
    assert r.json()["source"] == "note.txt"


def test_rag_ingest_rejects_empty(client):
    assert client.post("/v1/rag/ingest", json={"text": ""}).status_code == 422


def test_rag_ingest_file_rejects_unsupported(client):
    files = {"file": ("a.exe", b"MZ\x00\x00", "application/octet-stream")}
    r = client.post("/v1/rag/ingest-file", files=files)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_request"


# ---------------- 对话 ----------------
def test_chat_without_rag(client):
    r = client.post("/v1/chat", json={"message": "你好", "session_id": "s1"})
    assert r.status_code == 200
    assert r.json()["answer"]
    assert r.json()["session_id"] == "s1"


def test_chat_with_rag(client):
    client.post("/v1/rag/ingest", json={"text": DOC, "source": "doc.md"})
    r = client.post("/v1/chat", json={"message": "有哪些模块？", "use_rag": True})
    body = r.json()
    assert body["sources"], "开启 RAG 后应答必须带来源"


def test_chat_requires_non_empty_message(client):
    assert client.post("/v1/chat", json={"message": ""}).status_code == 422


# ---------------- 智能体 / 工作流 / 记忆 ----------------
def test_agent_run_endpoint(client):
    r = client.post("/v1/agent/run", json={"task": "计算 8 乘以 7", "max_steps": 3})
    assert r.status_code == 200
    body = r.json()
    assert "answer" in body and "tool_calls" in body


def test_workflow_run_endpoint(client):
    payload = {
        "input": "模块化",
        "nodes": [
            {"id": "a", "kind": "transform", "params": {"template": "主题:{input}"}},
            {"id": "b", "kind": "tool", "depends_on": ["a"],
             "params": {"name": "calculator", "args": {"expression": "5+5"}}},
        ],
    }
    r = client.post("/v1/workflow/run", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["order"] == ["a", "b"]
    assert body["outputs"]["b"] == "10"


def test_workflow_cycle_returns_domain_error(client):
    payload = {"input": "", "nodes": [
        {"id": "a", "kind": "transform", "depends_on": ["b"]},
        {"id": "b", "kind": "transform", "depends_on": ["a"]},
    ]}
    r = client.post("/v1/workflow/run", json=payload)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "workflow_error"


def test_memory_crud(client):
    sid = "mem-session"
    client.post(f"/v1/memory/{sid}", json={"role": "user", "content": "记住向量库选型"})
    items = client.get(f"/v1/memory/{sid}").json()
    assert items and items[0]["content"] == "记住向量库选型"

    recalled = client.post(f"/v1/memory/{sid}/recall",
                           params={"query": "向量库"}).json()
    assert recalled and "向量库" in recalled[0]["content"]

    assert client.delete(f"/v1/memory/{sid}").json()["deleted"] == 1
    assert client.get(f"/v1/memory/{sid}").json() == []


def test_openapi_schema_available(client):
    spec = client.get("/openapi.json").json()
    assert "/v1/rag/ask" in spec["paths"]
    assert "/v1/agent/run" in spec["paths"]
