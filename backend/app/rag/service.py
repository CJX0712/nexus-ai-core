"""RAG 服务（单一职责：只编排 加载->分块->嵌入->入库->检索->应答）。

作者: 晨星
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.core.errors import BadRequestError
from app.core.logging import get_logger
from app.gateway.llm import ChatMessage
from app.rag import chunker, loaders
from app.rag.retriever import HybridRetriever

log = get_logger("rag.service")

SYSTEM_PROMPT = (
    "你是 NexusAI 知识助手。严格依据 [CONTEXT] 中的资料回答问题；"
    "资料没有覆盖时就明确说明不知道，不要编造。回答简洁、结构化。"
)


@dataclass
class IngestResult:
    doc_id: str
    n_chunks: int
    source: str


@dataclass
class AnswerResult:
    answer: str
    provider: str
    model: str
    sources: list[dict] = field(default_factory=list)
    latency_ms: float = 0.0


class RAGService:
    """知识检索增强服务。依赖通过构造函数注入，便于独立验证。"""

    def __init__(self, settings, embedder, store, retriever: HybridRetriever) -> None:
        self.settings = settings
        self.embedder = embedder
        self.store = store
        self.retriever = retriever
        self.docs: dict[str, dict] = {}

    # ---------- 入库 ----------
    def ingest_text(self, text: str, *, source: str = "inline",
                    doc_id: str | None = None,
                    metadata: dict | None = None) -> IngestResult:
        if not text or not text.strip():
            raise BadRequestError("待入库文本为空")
        doc_id = doc_id or hashlib.sha1(
            f"{source}:{text[:512]}".encode()
        ).hexdigest()[:16]

        chunks = chunker.chunk_text(text, self.settings.chunk_size,
                                    self.settings.chunk_overlap)
        if not chunks:
            raise BadRequestError("文本分块结果为空")

        vectors = self.embedder.embed(chunks)
        metas = [
            {"doc_id": doc_id, "source": source, "chunk_index": i, **(metadata or {})}
            for i in range(len(chunks))
        ]
        self.store.add(vectors, chunks, metas, [doc_id] * len(chunks))
        self.retriever.rebuild_bm25()
        self.docs[doc_id] = {"source": source, "n_chunks": len(chunks),
                             **(metadata or {})}
        log.info("入库完成 doc={} chunks={}", doc_id, len(chunks))
        return IngestResult(doc_id=doc_id, n_chunks=len(chunks), source=source)

    def ingest_file(self, path: str | Path, source: str | None = None) -> IngestResult:
        """入库文件。source 默认取真实文件名（保留上传时的原始名以便溯源）。"""
        p = Path(path)
        text = loaders.load_text(p)
        return self.ingest_text(text, source=source or p.name)

    # ---------- 检索 ----------
    def search(self, query: str, top_k: int | None = None) -> list[dict]:
        k = top_k or self.settings.top_k
        hits = self.retriever.search(query, top_k=k)
        return [
            {
                "score": round(h.score, 6),
                "text": h.text,
                "doc_id": h.doc_id,
                "chunk_id": h.chunk_id,
                "metadata": h.metadata,
            }
            for h in hits
        ]

    @staticmethod
    def build_context(hits: list[dict]) -> str:
        parts = []
        for i, h in enumerate(hits, 1):
            src = h.get("metadata", {}).get("source", h.get("doc_id", "unknown"))
            parts.append(f"[{i}] source={src}\n{h['text']}")
        return "\n\n".join(parts)

    # ---------- 问答 ----------
    def answer(self, query: str, gateway, *, top_k: int | None = None) -> AnswerResult:
        started = time.perf_counter()
        hits = self.search(query, top_k=top_k)
        context = self.build_context(hits)
        user_content = (
            f"[CONTEXT]\n{context}\n[/CONTEXT]\n\n问题：{query}"
            if context else f"问题：{query}"
        )
        messages = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="user", content=user_content),
        ]
        result = gateway.complete(messages, settings=self.settings)
        return AnswerResult(
            answer=result.text,
            provider=result.provider,
            model=result.model,
            sources=[
                {"doc_id": h["doc_id"], "score": h["score"],
                 "source": h.get("metadata", {}).get("source", ""),
                 "snippet": h["text"][:200]}
                for h in hits
            ],
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    def stats(self) -> dict:
        return {
            "documents": len(self.docs),
            "chunks": self.store.count(),
            "embedding_dim": getattr(self.embedder, "dim", None),
            "embedding_provider": getattr(self.embedder, "name", "unknown"),
        }
