"""知识检索测试：向量库 / 混合检索 / RAG 服务编排。

作者: 晨星
"""
from __future__ import annotations

import numpy as np
import pytest

from app.core.errors import BadRequestError
from app.gateway.embeddings import HashingEmbedding
from app.rag.retriever import HybridRetriever
from app.rag.service import RAGService
from app.rag.vectorstore import FaissVectorStore


@pytest.fixture()
def store(tmp_path):
    return FaissVectorStore(dim=64, index_path=tmp_path / "i.index",
                            meta_path=tmp_path / "m.json")


def _vec(dim, seed):
    rng = np.random.default_rng(seed)
    v = rng.random(dim).astype(np.float32)
    return v / np.linalg.norm(v)


# ---------------- 向量库 ----------------
def test_vectorstore_add_and_search(store):
    vecs = np.vstack([_vec(64, 1), _vec(64, 1), _vec(64, 2)])
    ids = store.add(vecs, ["doc-a", "doc-a-copy", "doc-b"],
                    [{"doc_id": "a"}, {"doc_id": "a"}, {"doc_id": "b"}],
                    ["a", "a", "b"])
    assert ids == [0, 1, 2]
    assert store.count() == 3

    hits = store.search(_vec(64, 1), top_k=2)
    assert len(hits) == 2
    assert hits[0].score > 0.99, "与自身相同的向量余弦应接近 1"


def test_vectorstore_search_empty_returns_empty(store):
    assert store.search(_vec(64, 9), top_k=3) == []


def test_vectorstore_rejects_wrong_dim(store):
    with pytest.raises(ValueError):
        store.add(np.zeros((1, 32), dtype=np.float32), ["x"])


def test_vectorstore_persist_and_reload(tmp_path):
    s1 = FaissVectorStore(dim=64, index_path=tmp_path / "i.index",
                          meta_path=tmp_path / "m.json")
    s1.add(np.vstack([_vec(64, 5)]), ["持久化文本"], [{"doc_id": "p"}], ["p"])
    s1.save()

    s2 = FaissVectorStore(dim=64, index_path=tmp_path / "i.index",
                          meta_path=tmp_path / "m.json")
    assert s2.load() is True
    assert s2.count() == 1
    assert s2.texts[0] == "持久化文本"


def test_vectorstore_load_missing_returns_false(tmp_path):
    s = FaissVectorStore(dim=64, index_path=tmp_path / "none.index",
                         meta_path=tmp_path / "none.json")
    assert s.load() is False


# ---------------- 混合检索 ----------------
def test_hybrid_retriever_returns_ranked_hits(store):
    emb = HashingEmbedding(dim=64)
    texts = ["向量数据库负责相似度检索", "今天深圳天气晴朗", "检索增强生成提升答案准确性"]
    vecs = emb.embed(texts)
    store.add(vecs, texts, [{"doc_id": f"d{i}"} for i in range(3)], ["d0", "d1", "d2"])
    retriever = HybridRetriever(store, emb, hybrid=True, rrf_k=60)
    retriever.rebuild_bm25()

    hits = retriever.search("检索", top_k=2)
    assert hits, "应返回命中"
    assert hits[0].score >= hits[-1].score, "结果必须按融合分数降序"


def test_hybrid_retriever_empty_store_returns_empty(store):
    retriever = HybridRetriever(store, HashingEmbedding(dim=64))
    retriever.rebuild_bm25()
    assert retriever.search("任意查询") == []


# ---------------- RAG 服务 ----------------
def test_rag_service_ingest_and_search(settings, tmp_path, container):
    store, emb = container.store, container.embedder
    retriever = HybridRetriever(store, emb, hybrid=True, rrf_k=60)
    rag = RAGService(settings, emb, store, retriever)

    res = rag.ingest_text("知识库第一条：模块化设计原则。", source="t1.md")
    assert res.n_chunks >= 1
    assert rag.stats()["documents"] == 1

    hits = rag.search("模块化设计")
    assert hits and "模块化" in hits[0]["text"]


def test_rag_service_ingest_empty_raises(settings, container):
    rag = RAGService(settings, container.embedder, container.store,
                     HybridRetriever(container.store, container.embedder))
    with pytest.raises(BadRequestError):
        rag.ingest_text("   ")


def test_rag_service_answer_with_offline_llm(settings, container, offline_gateway):
    rag = RAGService(settings, container.embedder, container.store,
                     HybridRetriever(container.store, container.embedder))
    rag.ingest_text("NexusAI 的五个模块是模型网关、知识检索、智能体、工作流、记忆。",
                    source="m.md")
    out = rag.answer("NexusAI 有哪五个模块？", offline_gateway)
    assert "模块" in out.answer
    assert out.sources, "应答必须带溯源"
    assert out.latency_ms >= 0
