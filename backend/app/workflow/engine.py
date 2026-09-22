"""工作流引擎（单一职责：只负责 DAG 的拓扑调度与节点执行）。

节点类型：llm / rag / tool / transform。节点间通过上下文 dict 传递数据。

作者: 晨星
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.errors import WorkflowError
from app.core.logging import get_logger
from app.gateway.llm import ChatMessage

log = get_logger("workflow.engine")


@dataclass
class Node:
    id: str
    kind: str  # llm | rag | tool | transform
    params: dict = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)


@dataclass
class WorkflowResult:
    outputs: dict[str, Any] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)


def _render(template: str, ctx: dict) -> str:
    """用上下文渲染 {key} 占位符；未知键保留原样。"""
    out = template
    for key, value in ctx.items():
        out = out.replace("{" + key + "}", str(value))
    return out


class WorkflowEngine:
    """DAG 执行器。依赖注入 gateway / rag / registry，便于单独验证。"""

    def __init__(self, gateway, rag_service=None, registry=None) -> None:
        self.gateway = gateway
        self.rag_service = rag_service
        self.registry = registry

    # ---------- 调度 ----------
    @staticmethod
    def topo_sort(nodes: list[Node]) -> list[Node]:
        by_id = {n.id: n for n in nodes}
        if len(by_id) != len(nodes):
            raise WorkflowError("存在重复节点 id")
        for n in nodes:
            for dep in n.depends_on:
                if dep not in by_id:
                    raise WorkflowError(f"节点 {n.id} 依赖不存在的节点 {dep}")

        indeg = {n.id: len(n.depends_on) for n in nodes}
        queue = [n.id for n in nodes if indeg[n.id] == 0]
        order: list[Node] = []
        while queue:
            nid = queue.pop(0)
            order.append(by_id[nid])
            for n in nodes:
                if nid in n.depends_on:
                    indeg[n.id] -= 1
                    if indeg[n.id] == 0:
                        queue.append(n.id)
        if len(order) != len(nodes):
            raise WorkflowError("工作流存在环，无法拓扑排序")
        return order

    # ---------- 执行 ----------
    def run(self, nodes: list[Node], input_text: str) -> WorkflowResult:
        ordered = self.topo_sort(nodes)
        ctx: dict[str, Any] = {"input": input_text}
        result = WorkflowResult()

        for node in ordered:
            ctx["input"] = input_text
            output = self._run_node(node, ctx)
            ctx[node.id] = output
            result.outputs[node.id] = output
            result.order.append(node.id)
            log.info("节点 {} ({}) 执行完成", node.id, node.kind)
        return result

    def _run_node(self, node: Node, ctx: dict) -> Any:
        if node.kind == "llm":
            prompt = _render(node.params.get("prompt", "{input}"), ctx)
            res = self.gateway.complete(
                [ChatMessage(role="user", content=prompt)]
            )
            return res.text

        if node.kind == "rag":
            if self.rag_service is None:
                raise WorkflowError(f"节点 {node.id} 需要 rag_service，但未注入")
            query = _render(node.params.get("query", "{input}"), ctx)
            hits = self.rag_service.search(query,
                                           top_k=int(node.params.get("top_k", 4)))
            return hits

        if node.kind == "tool":
            if self.registry is None:
                raise WorkflowError(f"节点 {node.id} 需要工具注册表，但未注入")
            name = node.params.get("name", "")
            args = {k: _render(str(v), ctx)
                    for k, v in node.params.get("args", {}).items()}
            return self.registry.call(name, **args)

        if node.kind == "transform":
            template = node.params.get("template", "{input}")
            return _render(template, ctx)

        raise WorkflowError(f"未知节点类型: {node.kind}")
