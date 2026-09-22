"""模型网关测试：嵌入确定性 / 降级链 / 离线抽取式应答。

作者: 晨星
"""
from __future__ import annotations

import numpy as np
import pytest

from app.core.errors import ProviderUnavailableError
from app.gateway.embeddings import HashingEmbedding
from app.gateway.llm import (
    ChatMessage,
    LLMGateway,
    OfflineExtractiveLLM,
    build_llm_gateway,
)


# ---------------- 嵌入 ----------------
def test_hashing_embedding_is_deterministic():
    e = HashingEmbedding(dim=128)
    a = e.embed(["模块化 AI 能力中台"])
    b = e.embed(["模块化 AI 能力中台"])
    assert np.allclose(a, b), "同一文本必须得到同一向量"


def test_hashing_embedding_is_normalized():
    e = HashingEmbedding(dim=128)
    v = e.embed(["中文测试 text"])
    norm = np.linalg.norm(v[0])
    assert abs(norm - 1.0) < 1e-5, f"向量应为单位长度, 实际 {norm}"


def test_hashing_embedding_shape_and_dim():
    e = HashingEmbedding(dim=64)
    mat = e.embed(["a", "b", "c"])
    assert mat.shape == (3, 64)
    assert mat.dtype == np.float32


def test_similar_text_has_higher_cosine():
    e = HashingEmbedding(dim=128)
    v = e.embed(["知识检索与向量数据库", "知识检索与向量数据库相关", "今天天气不错"])
    sim_same = float(v[0] @ v[1])
    sim_diff = float(v[0] @ v[2])
    assert sim_same > sim_diff, "语义更近的文本余弦相似度应更高"


# ---------------- LLM 降级链 ----------------
class BoomProvider:
    name = "boom"

    def complete(self, messages, *, temperature=0.2, max_tokens=1024):
        raise RuntimeError("provider down")


def test_gateway_falls_back_to_next_provider():
    gw = LLMGateway([BoomProvider(), OfflineExtractiveLLM()])
    out = gw.complete([ChatMessage(role="user", content="你好")])
    assert out.provider == "offline_extractive"
    assert gw.last_provider == "offline_extractive"


def test_gateway_raises_when_all_providers_fail():
    gw = LLMGateway([BoomProvider()])
    with pytest.raises(ProviderUnavailableError):
        gw.complete([ChatMessage(role="user", content="你好")])


def test_build_gateway_offline_has_single_entry(settings):
    gw = build_llm_gateway(settings)
    names = [p.name for p in gw.providers]
    assert names.count("offline_extractive") == 1, f"兜底实现不应重复入链: {names}"


# ---------------- 离线抽取式应答 ----------------
def test_offline_extractive_uses_context():
    llm = OfflineExtractiveLLM()
    msg = ChatMessage(
        role="user",
        content="[CONTEXT]\n[1] source=a.md\nNexusAI 包含模型网关与知识检索。其它无关句子。\n[/CONTEXT]\n\nNexusAI 包含什么？",
    )
    out = llm.complete([msg])
    assert "模型网关" in out.text
    assert "offline-extractive" in out.text


def test_offline_extractive_without_context_is_explicit():
    llm = OfflineExtractiveLLM()
    out = llm.complete([ChatMessage(role="user", content="今天几号？")])
    assert "未配置任何在线模型" in out.text
