"""LLM 网关（单一职责：只负责对话补全，屏蔽 provider 差异）。

降级链（auto）：OpenAI 兼容云端 -> 本地 GGUF(llama.cpp) -> 离线抽取式应答。
无论有无 API Key、有无网络，链路都不中断。

作者: 晨星
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.errors import ProviderUnavailableError
from app.core.logging import get_logger

log = get_logger("gateway.llm")

_CJK = r"\u4e00-\u9fff"
_SENT_SPLIT = re.compile(r"(?<=[。！？!?；;\n])")


@dataclass
class ChatMessage:
    role: str  # system | user | assistant
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class ChatResult:
    text: str
    model: str
    provider: str
    usage: dict[str, int] = field(default_factory=dict)


class LLMProvider(Protocol):
    """LLM 提供方契约。"""

    name: str

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> ChatResult:
        ...


class OpenAICompatLLM:
    """OpenAI 兼容 Chat Completions 端点。

    覆盖 OpenAI / DeepSeek / 通义千问 / Moonshot / Groq / Ollama / vLLM 等，
    它们共享同一套 /v1/chat/completions 协议。
    """

    name = "openai_compat"

    def __init__(self, base_url: str, api_key: str, model: str,
                 timeout: float = 60.0) -> None:
        import httpx

        base = base_url.rstrip("/")
        if not base.endswith("/v1"):
            base += "/v1"
        self.base_url = base
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def complete(self, messages, *, temperature=0.2, max_tokens=1024) -> ChatResult:
        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        resp = self._client.post(
            f"{self.base_url}/chat/completions", headers=headers, json=payload
        )
        if resp.status_code >= 400:
            raise ProviderUnavailableError(
                f"llm endpoint {resp.status_code}: {resp.text[:200]}"
            )
        body = resp.json()
        text = body["choices"][0]["message"]["content"] or ""
        usage = body.get("usage", {}) or {}
        return ChatResult(
            text=text,
            model=body.get("model", self.model),
            provider=self.name,
            usage={
                "prompt_tokens": int(usage.get("prompt_tokens", 0)),
                "completion_tokens": int(usage.get("completion_tokens", 0)),
            },
        )


class LlamaCppLLM:
    """本地 GGUF 推理（llama.cpp 官方 Python 绑定），CPU 可跑。"""

    name = "llama_cpp"

    def __init__(self, model_path: str, n_ctx: int = 2048, n_threads: int = 4) -> None:
        from llama_cpp import Llama

        self.model_path = model_path
        self._llm = Llama(
            model_path=model_path, n_ctx=n_ctx, n_threads=n_threads, verbose=False
        )

    def complete(self, messages, *, temperature=0.2, max_tokens=1024) -> ChatResult:
        out = self._llm.create_chat_completion(
            messages=[m.to_dict() for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = out["choices"][0]["message"]["content"] or ""
        return ChatResult(text=text, model=self.model_path, provider=self.name)


class OfflineExtractiveLLM:
    """离线抽取式应答器（最终兜底）。

    无 Key、无网络、无本地模型时仍产出可验证答案：
    从上下文（用户消息中 [CONTEXT] 段）抽取与问题重叠度最高的句子。
    """

    name = "offline_extractive"

    @staticmethod
    def _tokens(text: str) -> set[str]:
        lowered = text.lower()
        cjk = re.findall(rf"[{_CJK}]", lowered)
        latin = re.findall(r"[a-zA-Z0-9_]+", lowered)
        grams = {cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1)}
        return set(cjk) | grams | set(latin)

    def complete(self, messages, *, temperature=0.2, max_tokens=1024) -> ChatResult:
        user_msg = next((m.content for m in reversed(messages) if m.role == "user"), "")
        context = ""
        mt = re.search(r"\[CONTEXT\](.*?)\[/CONTEXT\]", user_msg, re.S)
        if mt:
            context = mt.group(1).strip()
            question = re.sub(r"\[CONTEXT\].*?\[/CONTEXT\]", "", user_msg, flags=re.S)
        else:
            question = user_msg
        question = question.strip()

        if not context:
            answer = (
                "[offline-extractive] 当前未配置任何在线模型，且上下文中没有可抽取的知识。"
                f"已收到问题：{question[:200]}。请配置 NEXUS_LLM_API_KEY 或 NEXUS_LOCAL_GGUF_PATH 以启用生成式回答。"
            )
            return ChatResult(text=answer, model=self.name, provider=self.name)

        sents = [
            s.strip()
            for s in _SENT_SPLIT.split(context)
            if s.strip() and not re.match(r"^\[\d+\]\s*source=", s.strip())
        ]
        qtoks = self._tokens(question)
        scored = []
        for idx, sent in enumerate(sents):
            stoks = self._tokens(sent)
            overlap = len(qtoks & stoks)
            score = overlap / (len(qtoks) + 1e-9)
            scored.append((score, idx, sent))
        scored.sort(key=lambda x: (-x[0], x[1]))
        picked = [s for _, _, s in scored[:3] if scored[0][0] > 0]
        if not picked:
            picked = sents[:2]
        body = "\n".join(f"- {s}" for s in picked)
        answer = (
            f"[offline-extractive] 基于已检索上下文的抽取式回答：\n{body}"
        )
        return ChatResult(text=answer, model=self.name, provider=self.name)


class LLMGateway:
    """模型网关：持有降级链，逐个尝试直到成功。"""

    def __init__(self, providers: Iterable[LLMProvider]) -> None:
        self.providers: list[LLMProvider] = list(providers)
        self.last_provider: str = ""

    def complete(
        self,
        messages: list[ChatMessage] | list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        settings=None,
    ) -> ChatResult:
        msgs = [
            m if isinstance(m, ChatMessage) else ChatMessage(**m) for m in messages
        ]
        if settings is not None:
            temperature = settings.llm_temperature if temperature is None else temperature
            max_tokens = settings.llm_max_tokens if max_tokens is None else max_tokens
        temperature = 0.2 if temperature is None else temperature
        max_tokens = 1024 if max_tokens is None else max_tokens

        errors: list[str] = []
        for provider in self.providers:
            try:
                result = provider.complete(
                    msgs, temperature=temperature, max_tokens=max_tokens
                )
                self.last_provider = provider.name
                return result
            except Exception as exc:  # noqa: BLE001 - 降级边界必须宽捕获
                errors.append(f"{provider.name}: {exc}")
                log.warning("provider {} 失败，降级中: {}", provider.name, exc)

        raise ProviderUnavailableError(
            "所有 LLM provider 均不可用", detail=errors
        )

    def available_models(self) -> list[dict[str, Any]]:
        return [{"provider": p.name, "model": getattr(p, "model", p.name)}
                for p in self.providers]


def build_llm_gateway(settings) -> LLMGateway:
    """按配置构造网关；auto 模式自动探测可用 provider。"""
    provider = settings.llm_provider
    chain: list[LLMProvider] = []

    def try_cloud() -> None:
        """配置了端点即入链；实际可用性在请求时判定并由网关降级。"""
        if not settings.llm_base_url or not settings.llm_model:
            return
        chain.append(
            OpenAICompatLLM(
                settings.llm_base_url, settings.llm_api_key,
                settings.llm_model, settings.llm_timeout,
            )
        )

    def try_local() -> None:
        if not settings.local_gguf_path:
            return
        try:
            chain.append(
                LlamaCppLLM(
                    settings.local_gguf_path,
                    settings.local_ctx_size,
                    settings.local_threads,
                )
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("本地 GGUF 加载失败: {}", exc)

    if provider == "openai_compat":
        if not settings.llm_base_url or not settings.llm_model:
            raise ProviderUnavailableError(
                "llm_provider=openai_compat 需要 NEXUS_LLM_BASE_URL 与 NEXUS_LLM_MODEL"
            )
        chain.append(OpenAICompatLLM(
            settings.llm_base_url, settings.llm_api_key,
            settings.llm_model, settings.llm_timeout))
    elif provider == "llama_cpp":
        try_local()
        if not chain:
            raise ProviderUnavailableError("llm_provider=llama_cpp 但 GGUF 加载失败")
    elif provider == "offline":
        chain.append(OfflineExtractiveLLM())
    else:  # auto
        try_cloud()
        if not chain:
            try_local()

    if not any(isinstance(p, OfflineExtractiveLLM) for p in chain):
        chain.append(OfflineExtractiveLLM())
    return LLMGateway(chain)
