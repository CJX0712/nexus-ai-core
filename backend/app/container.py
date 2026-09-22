"""组合根（单一职责：只负责把各模块装配成可运行系统）。

这是唯一做"依赖装配"的地方；业务模块之间不互相 new，全部由这里注入，
因此每个模块都能被独立实例化与验证。

作者: 晨星
"""
from __future__ import annotations

from pathlib import Path

from app.agent.tools import build_default_registry
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.gateway.embeddings import build_embedder
from app.gateway.llm import build_llm_gateway
from app.memory.store import MemoryStore
from app.rag.retriever import HybridRetriever
from app.rag.service import RAGService
from app.rag.vectorstore import FaissVectorStore
from app.workflow.engine import WorkflowEngine

log = get_logger("container")


class Container:
    """系统装配容器。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        settings.ensure_dirs()

        # M1 网关
        self.embedder = build_embedder(settings)
        self.gateway = build_llm_gateway(settings)

        # M2 知识检索
        index_dir = Path(settings.data_dir) / "index"
        self.store = FaissVectorStore(
            dim=getattr(self.embedder, "dim", settings.embed_dim),
            index_path=index_dir / "faiss.index",
            meta_path=index_dir / "meta.json",
        )
        if self.store.load():
            log.info("已加载向量库: {} 个片段", self.store.count())
        self.retriever = HybridRetriever(
            self.store, self.embedder,
            hybrid=settings.hybrid_enabled, rrf_k=settings.rrf_k,
        )
        self.retriever.rebuild_bm25()
        self.rag = RAGService(settings, self.embedder, self.store, self.retriever)

        # M5 记忆
        self.memory = MemoryStore(
            db_path=Path(settings.data_dir) / "memory" / "memory.db",
            max_turns=settings.memory_max_turns,
        )

        # M3/M4 工具与工作流
        self.registry = build_default_registry(
            rag_service=self.rag, memory_store=self.memory, session_id="default"
        )
        self.workflow = WorkflowEngine(
            gateway=self.gateway, rag_service=self.rag, registry=self.registry
        )

    def persist(self) -> None:
        """把向量库落盘。"""
        self.store.save()

    def describe(self) -> dict:
        return {
            "app": self.settings.app_name,
            "version": self.settings.version,
            "embedding": {
                "provider": getattr(self.embedder, "name", "unknown"),
                "dim": getattr(self.embedder, "dim", None),
            },
            "llm_chain": [p.name for p in self.gateway.providers],
            "tools": self.registry.list(),
            "rag": self.rag.stats(),
        }


_container: Container | None = None


def get_container() -> Container:
    global _container
    if _container is None:
        _container = Container(get_settings())
    return _container


def set_container(container: Container | None) -> None:
    """测试用：替换/清空容器。"""
    global _container
    _container = container
