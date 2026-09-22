"""向量库（单一职责：只负责向量的写入、检索与持久化）。

基于 Meta FAISS IndexFlatIP；向量已 L2 归一化，内积即余弦相似度。

作者: 晨星
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from app.core.logging import get_logger

log = get_logger("rag.vectorstore")


@dataclass
class Hit:
    score: float
    text: str
    metadata: dict[str, Any]
    doc_id: str
    chunk_id: int


class FaissVectorStore:
    """FAISS 向量库 + JSON 元数据，支持 save/load 落盘。"""

    def __init__(self, dim: int, index_path: Path, meta_path: Path) -> None:
        import faiss

        self.dim = dim
        self.index_path = Path(index_path)
        self.meta_path = Path(meta_path)
        self._index = faiss.IndexFlatIP(dim)
        self.texts: list[str] = []
        self.metadatas: list[dict[str, Any]] = []
        self.doc_ids: list[str] = []

    # ---------- 写入 ----------
    def add(self, vectors: np.ndarray, texts: list[str],
            metadatas: list[dict[str, Any]] | None = None,
            doc_ids: list[str] | None = None) -> list[int]:
        if vectors.ndim != 2 or vectors.shape[1] != self.dim:
            raise ValueError(f"向量维度不符: 期望 {self.dim}, 实际 {vectors.shape}")
        if len(texts) != vectors.shape[0]:
            raise ValueError("文本数量与向量数量不一致")
        metadatas = metadatas or [{} for _ in texts]
        doc_ids = doc_ids or [m.get("doc_id", "") for m in metadatas]
        start = self._index.ntotal
        self._index.add(vectors.astype(np.float32))
        self.texts.extend(texts)
        self.metadatas.extend(metadatas)
        self.doc_ids.extend(doc_ids)
        return list(range(start, self._index.ntotal))

    # ---------- 检索 ----------
    def search(self, query_vec: np.ndarray, top_k: int = 4) -> list[Hit]:
        if self._index.ntotal == 0:
            return []
        q = np.asarray(query_vec, dtype=np.float32).reshape(1, -1)
        k = min(top_k, self._index.ntotal)
        scores, idxs = self._index.search(q, k)
        hits: list[Hit] = []
        for score, idx in zip(scores[0], idxs[0], strict=False):
            if idx < 0:
                continue
            hits.append(
                Hit(
                    score=float(score),
                    text=self.texts[idx],
                    metadata=self.metadatas[idx],
                    doc_id=self.doc_ids[idx],
                    chunk_id=int(idx),
                )
            )
        return hits

    # ---------- 元数据 ----------
    def count(self) -> int:
        return int(self._index.ntotal)

    def save(self) -> None:
        import faiss

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self.index_path))
        self.meta_path.write_text(
            json.dumps(
                {"dim": self.dim, "texts": self.texts,
                 "metadatas": self.metadatas, "doc_ids": self.doc_ids},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def load(self) -> bool:
        """加载落盘数据；不存在返回 False。"""
        import faiss

        if not (self.index_path.exists() and self.meta_path.exists()):
            return False
        self._index = faiss.read_index(str(self.index_path))
        meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
        self.dim = int(meta.get("dim", self.dim))
        self.texts = meta.get("texts", [])
        self.metadatas = meta.get("metadatas", [])
        self.doc_ids = meta.get("doc_ids", [])
        return True
