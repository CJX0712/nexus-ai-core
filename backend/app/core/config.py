"""全局配置模块（单一职责：只负责配置的读取与规范化）。

作者: 晨星
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = _env(name)
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name).lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return default


class Settings(BaseModel):
    """应用配置。所有字段均可通过 NEXUS_* 环境变量覆盖。"""

    app_name: str = "NexusAI Capability Platform"
    version: str = "1.0.0"
    env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000

    # ---------- 存储 ----------
    data_dir: Path = Path("./data")

    # ---------- LLM 网关 (M1) ----------
    llm_provider: str = "auto"  # auto | openai_compat | llama_cpp | offline
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1024
    llm_timeout: float = 60.0

    # 本地 GGUF 兜底
    local_gguf_path: str = ""
    local_ctx_size: int = 2048
    local_threads: int = 4

    # ---------- 嵌入 (M2 依赖) ----------
    embed_provider: str = "auto"  # auto | fastembed | openai_compat | hashing
    embed_model: str = "BAAI/bge-small-zh-v1.5"
    embed_dim: int = 512
    embed_base_url: str = ""
    embed_api_key: str = ""

    # ---------- RAG (M2) ----------
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 4
    hybrid_enabled: bool = True
    rrf_k: int = 60

    # ---------- 智能体 (M3) ----------
    agent_max_steps: int = 6

    # ---------- 记忆 (M5) ----------
    memory_max_turns: int = 20

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv(override=False)  # 支持仓库根目录 .env，环境变量优先
        s = cls()
        s.env = _env("NEXUS_ENV", s.env)
        s.host = _env("NEXUS_HOST", s.host)
        s.port = _env_int("NEXUS_PORT", s.port)
        data_dir = _env("NEXUS_DATA_DIR")
        if data_dir:
            s.data_dir = Path(data_dir)

        s.llm_provider = _env("NEXUS_LLM_PROVIDER", s.llm_provider)
        s.llm_base_url = _env("NEXUS_LLM_BASE_URL", s.llm_base_url)
        s.llm_api_key = _env("NEXUS_LLM_API_KEY", s.llm_api_key)
        s.llm_model = _env("NEXUS_LLM_MODEL", s.llm_model)
        s.llm_temperature = _env_float("NEXUS_LLM_TEMPERATURE", s.llm_temperature)
        s.llm_max_tokens = _env_int("NEXUS_LLM_MAX_TOKENS", s.llm_max_tokens)
        s.llm_timeout = _env_float("NEXUS_LLM_TIMEOUT", s.llm_timeout)

        s.local_gguf_path = _env("NEXUS_LOCAL_GGUF_PATH", s.local_gguf_path)
        s.local_ctx_size = _env_int("NEXUS_LOCAL_CTX_SIZE", s.local_ctx_size)
        s.local_threads = _env_int("NEXUS_LOCAL_THREADS", s.local_threads)

        s.embed_provider = _env("NEXUS_EMBED_PROVIDER", s.embed_provider)
        s.embed_model = _env("NEXUS_EMBED_MODEL", s.embed_model)
        s.embed_dim = _env_int("NEXUS_EMBED_DIM", s.embed_dim)
        s.embed_base_url = _env("NEXUS_EMBED_BASE_URL", s.embed_base_url)
        s.embed_api_key = _env("NEXUS_EMBED_API_KEY", s.embed_api_key)

        s.chunk_size = _env_int("NEXUS_CHUNK_SIZE", s.chunk_size)
        s.chunk_overlap = _env_int("NEXUS_CHUNK_OVERLAP", s.chunk_overlap)
        s.top_k = _env_int("NEXUS_TOP_K", s.top_k)
        s.hybrid_enabled = _env_bool("NEXUS_HYBRID_ENABLED", s.hybrid_enabled)
        s.rrf_k = _env_int("NEXUS_RRF_K", s.rrf_k)

        s.agent_max_steps = _env_int("NEXUS_AGENT_MAX_STEPS", s.agent_max_steps)
        s.memory_max_turns = _env_int("NEXUS_MEMORY_MAX_TURNS", s.memory_max_turns)
        return s

    def ensure_dirs(self) -> None:
        """确保数据目录存在（向量库/记忆库落盘位置）。"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "index").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "memory").mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def reset_settings() -> None:
    """测试用：清空单例。"""
    global _settings
    _settings = None
