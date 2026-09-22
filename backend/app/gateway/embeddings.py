"""嵌入网关（单一职责：只负责把文本变成向量）。

三档实现，按可用性自动降级：
1. FastEmbedProvider  - Qdrant fastembed，ONNX 本地推理，CPU 友好、免 torch
2. OpenAICompatEmbedding - 任意 OpenAI 兼容 embedding 端点
3. HashingEmbedding  - 零依赖确定性哈希嵌入，保证离线/断网时链路仍可跑通

作者: 晨星
"""
from __future__ import annotations

import hashlib
import re
from typing import Protocol

import numpy as np

from app.core.errors import ProviderUnavailableError
from app.core.logging import get_logger

log = get_logger("gateway.embeddings")

_CJK = r"\u4e00-\u9fff"
_TOKEN_RE = re.compile(rf"[{_CJK}]|[a-zA-Z0-9_]+")


class EmbeddingProvider(Protocol):
    """嵌入提供方契约。"""

    name: str
    dim: int

    def embed(self, texts: list[str]) -> np.ndarray:
        """返回 shape=(len(texts), dim) 的 float32 矩阵，行已 L2 归一化。"""
        ...


def _l2_normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (mat / norms).astype(np.float32)


def _tokenize(text: str) -> list[str]:
    """中英混排分词：CJK 取单字+二元组，拉丁取词。"""
    toks: list[str] = []
    lowered = text.lower()
    chars = _TOKEN_RE.findall(lowered)
    i = 0
    while i < len(chars):
        c = chars[i]
        if re.match(rf"[{_CJK}]", c):
            toks.append(c)
            if i + 1 < len(chars) and re.match(rf"[{_CJK}]", chars[i + 1]):
                toks.append(c + chars[i + 1])
        else:
            toks.append(c)
        i += 1
    return toks


class HashingEmbedding:
    """零依赖确定性嵌入（离线兜底）。同一文本永远得到同一向量。"""

    name = "hashing"

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> np.ndarray:
        mat = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            for tok in _tokenize(text):
                digest = hashlib.md5(tok.encode("utf-8")).hexdigest()
                h = int(digest[:8], 16)
                idx = h % self.dim
                sign = 1.0 if (h >> 20) & 1 else -1.0
                mat[i, idx] += sign
        return _l2_normalize(mat)


class FastEmbedProvider:
    """fastembed 本地 ONNX 嵌入（Qdrant 开源方案，无需 torch）。"""

    name = "fastembed"

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5") -> None:
        from fastembed import TextEmbedding  # 延迟导入，避免启动开销

        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name)
        self.dim = self._probe_dim()

    def _probe_dim(self) -> int:
        vec = next(iter(self._model.embed(["dimension probe"])))
        return int(np.asarray(vec).shape[0])

    def embed(self, texts: list[str]) -> np.ndarray:
        rows = [np.asarray(v, dtype=np.float32) for v in self._model.embed(texts)]
        return _l2_normalize(np.vstack(rows))


class OpenAICompatEmbedding:
    """任意 OpenAI 兼容 /embeddings 端点。"""

    name = "openai_compat_embedding"

    def __init__(self, base_url: str, api_key: str, model: str, dim: int = 512,
                 timeout: float = 60.0) -> None:
        import httpx

        self.base_url = base_url.rstrip("/")
        if not self.base_url.endswith("/v1"):
            self.base_url += "/v1"
        self.api_key = api_key
        self.model = model
        self.dim = dim
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def embed(self, texts: list[str]) -> np.ndarray:
        resp = self._client.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "input": texts},
        )
        if resp.status_code >= 400:
            raise ProviderUnavailableError(
                f"embedding endpoint returned {resp.status_code}: {resp.text[:200]}"
            )
        data = resp.json().get("data", [])
        rows = [np.asarray(item["embedding"], dtype=np.float32) for item in data]
        self.dim = int(rows[0].shape[0])
        return _l2_normalize(np.vstack(rows))


def build_embedder(settings) -> EmbeddingProvider:
    """按配置与可用性构造嵌入器：auto 模式下逐级降级。"""
    provider = settings.embed_provider

    if provider == "hashing":
        return HashingEmbedding(dim=settings.embed_dim)

    if provider == "openai_compat":
        if not settings.embed_base_url or not settings.embed_model:
            raise ProviderUnavailableError(
                "embed_provider=openai_compat 需要 NEXUS_EMBED_BASE_URL 与 NEXUS_EMBED_MODEL"
            )
        return OpenAICompatEmbedding(
            settings.embed_base_url, settings.embed_api_key,
            settings.embed_model, settings.embed_dim, settings.llm_timeout,
        )

    if provider == "fastembed":
        try:
            return FastEmbedProvider(settings.embed_model)
        except Exception as exc:  # noqa: BLE001 - 降级边界
            raise ProviderUnavailableError(f"fastembed 初始化失败: {exc}") from exc

    # auto：fastembed -> openai 兼容 -> hashing
    try:
        return FastEmbedProvider(settings.embed_model)
    except Exception as exc:  # noqa: BLE001
        log.warning("fastembed 不可用，尝试 OpenAI 兼容端点: {}", exc)

    if settings.embed_base_url and settings.embed_model:
        try:
            emb = OpenAICompatEmbedding(
                settings.embed_base_url, settings.embed_api_key,
                settings.embed_model, settings.embed_dim, settings.llm_timeout,
            )
            emb.embed(["probe"])
            return emb
        except Exception as exc:  # noqa: BLE001
            log.warning("OpenAI 兼容嵌入不可用: {}", exc)

    log.warning("回退到离线哈希嵌入（HashingEmbedding），语义精度低于神经嵌入")
    return HashingEmbedding(dim=settings.embed_dim)
