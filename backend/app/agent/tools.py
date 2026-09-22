"""工具注册表（单一职责：只负责工具的注册、描述与调用）。

工具描述采用 JSON Schema 风格，可直接映射为 MCP / function-calling 协议。

作者: 晨星
"""
from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from app.core.errors import BadRequestError


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict = field(default_factory=dict)
    func: Callable[..., str] = None  # type: ignore[assignment]

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def run(self, **kwargs) -> str:
        if self.func is None:
            raise BadRequestError(f"工具 {self.name} 未绑定实现")
        return str(self.func(**kwargs))


class ToolRegistry:
    """工具注册表：单一职责管理可调用能力。"""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise BadRequestError(f"工具重复注册: {tool.name}")
        self._tools[tool.name] = tool

    def register_fn(self, name: str, description: str,
                    parameters: dict, func: Callable[..., str]) -> None:
        self.register(Tool(name=name, description=description,
                           parameters=parameters, func=func))

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise BadRequestError(
                f"未知工具: {name}，可用: {', '.join(self._tools)}"
            )
        return self._tools[name]

    def call(self, name: str, **kwargs) -> str:
        return self.get(name).run(**kwargs)

    def list(self) -> list[str]:
        return sorted(self._tools)

    def schemas(self) -> list[dict]:
        return [self._tools[n].schema() for n in sorted(self._tools)]

    def describe(self) -> str:
        lines = []
        for name in sorted(self._tools):
            t = self._tools[name]
            params = ", ".join(t.parameters.get("properties", {}).keys())
            lines.append(f"- {name}({params}): {t.description}")
        return "\n".join(lines)


# ---------------- 内置工具 ----------------

_SAFE_EXPR = re.compile(r"^[0-9\.\+\-\*/\(\)\s%]+$")


def calculator(expression: str) -> str:
    """安全求值四则运算，禁止任意代码执行。"""
    expr = expression.strip()
    if not expr or not _SAFE_EXPR.match(expr):
        raise BadRequestError(f"表达式不合法: {expression}")
    try:
        value = eval(expr, {"__builtins__": {}}, {  # noqa: S307 - 已做字符白名单
            "abs": abs, "round": round, "min": min, "max": max,
            "pow": pow, "sqrt": math.sqrt,
        })
    except Exception as exc:  # noqa: BLE001
        raise BadRequestError(f"计算失败: {exc}") from exc
    return str(value)


def now(_: str = "") -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def make_rag_search_tool(rag_service) -> Tool:
    """把 RAG 检索能力包装成智能体可调用的工具。"""

    def _search(query: str, top_k: int = 4) -> str:
        hits = rag_service.search(query, top_k=int(top_k))
        if not hits:
            return "未检索到相关内容。"
        return "\n".join(
            f"[{i}] ({h['metadata'].get('source', h['doc_id'])}) {h['text'][:300]}"
            for i, h in enumerate(hits, 1)
        )

    return Tool(
        name="rag_search",
        description="在知识库中检索与 query 相关的原文片段，返回带来源的内容列表。",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索关键词或问题"},
                "top_k": {"type": "integer", "description": "返回条数，默认 4"},
            },
            "required": ["query"],
        },
        func=_search,
    )


def make_memory_tools(memory_store, session_id: str) -> list[Tool]:
    """把记忆读写包装成工具。"""

    def _recall(query: str, limit: int = 5) -> str:
        items = memory_store.recall(session_id, query, limit=int(limit))
        return "\n".join(f"- {i['content'][:200]}" for i in items) or "无相关记忆。"

    def _remember(content: str) -> str:
        memory_store.remember(session_id, content)
        return "已记住。"

    return [
        Tool(
            name="memory_recall",
            description="回忆本会话中与 query 相关的历史内容。",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
                "required": ["query"],
            },
            func=_recall,
        ),
        Tool(
            name="memory_remember",
            description="把一条重要信息写入长期记忆。",
            parameters={
                "type": "object",
                "properties": {"content": {"type": "string"}},
                "required": ["content"],
            },
            func=_remember,
        ),
    ]


def build_default_registry(rag_service=None, memory_store=None,
                           session_id: str = "default") -> ToolRegistry:
    """组装默认工具集。"""
    reg = ToolRegistry()
    reg.register_fn(
        "calculator",
        "计算数学表达式，支持 + - * / % 与 abs/round/min/max/pow/sqrt。",
        {"type": "object", "properties": {"expression": {"type": "string"}},
         "required": ["expression"]},
        calculator,
    )
    reg.register_fn(
        "now",
        "获取当前日期时间。",
        {"type": "object", "properties": {}},
        now,
    )
    if rag_service is not None:
        reg.register(make_rag_search_tool(rag_service))
    if memory_store is not None:
        for t in make_memory_tools(memory_store, session_id):
            reg.register(t)
    return reg
