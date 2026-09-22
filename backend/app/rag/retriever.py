"""混合检索器（单一职责：只负责"给定 query 返回最相关片段"）。

稠密向量检索（FAISS） + 稀疏检索（BM25），用 RRF 加权融合，
兼顾语义相似与关键词精确命中。

作者: 晨星
"""
from __future__ import annotations

import re

import numpy as np

from app.core.logging import get_logger
from app.rag.vectorstore import FaissVectorStore, Hit

log = get_logger("rag.retriever")

_CJK = r"\u4e00-\u9fff"


def _tokenize(text: str) -> list[str]:
    lowered = text.lower()
    cjk = re.findall(rf"[{_CJK}]", lowered)
    latin = re.findall(r"[a-zA-Z0-9_]+", lowered)
    grams = [cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1)]
    return cjk + grams + latin


class HybridRetriever:
    """稠密 + 稀疏混合检索。"""

    def __init__(self, store: FaissVectorStore, embedder, *,
                 hybrid: bool = True, rrf_k: int = 60) -> None:
        self.store = store
        self.embedder = embedder
        self.hybrid = hybrid
        self.rrf_k = rrf_k
        self._bm25 = None
        self._corpus_tokens: list[list[str]] = []

    # ---------- BM25 ----------
    def rebuild_bm25(self) -> None:
        """用当前向量库语料重建 BM25 索引。"""
        if not self.hybrid:
            self._bm25 = None
            return
        try:
            from rank_bm25 import BM25Okapi
        except Exception:  # noqa: BLE001 - 可选依赖
            log.warning("rank_bm25 不可用，退化为纯稠密检索")
            self._bm25 = None
            return
        self._corpus_tokens = [_tokenize(t) for t in self.store.texts]
        self._bm25 = BM25Okapi(self._corpus_tokens) if self._corpus_tokens else None

    def _bm25_scores(self, query: str) -> list[float]:
        if self._bm25 is None:
            return []
        return list(self._bm25.get_scores(_tokenize(query)))

    # ---------- 检索 ----------
    def search(self, query: str, top_k: int = 4) -> list[Hit]:
        if self.store.count() == 0 or not query.strip():
            return []

        qvec = self.embedder.embed([query])[0]
        dense_hits = self.store.search(np.asarray(qvec, dtype=np.float32),
                                       top_k=max(top_k * 3, 10))
        if not self.hybrid or self._bm25 is None:
            return dense_hits[:top_k]

        bm25 = self._bm25_scores(query)
        bm25_rank = {
            idx: rank
            for rank, idx in enumerate(
                sorted(range(len(bm25)), key=lambda i: -bm25[i])[: top_k * 3]
            )
        }
        fused: dict[int, float] = {}
        for rank, hit in enumerate(dense_hits):
            fused[hit.chunk_id] = fused.get(hit.chunk_id, 0.0) + 1.0 / (self.rrf_k + rank + 1)
        for idx, rank in bm25_rank.items():
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (self.rrf_k + rank + 1)

        by_id = {h.chunk_id: h for h in dense_hits}
        ordered = sorted(fused.items(), key=lambda kv: -kv[1])[:top_k]
        results: list[Hit] = []
        for idx, score in ordered:
            if idx in by_id:
                hit = by_id[idx]
                results.append(Hit(score=score, text=hit.text,
                                   metadata=hit.metadata, doc_id=hit.doc_id,
                                   chunk_id=idx))
            else:  # 仅被 BM25 命中
                results.append(Hit(score=score, text=self.store.texts[idx],
                                   metadata=self.store.metadatas[idx],
                                   doc_id=self.store.doc_ids[idx], chunk_id=idx))
        return results
