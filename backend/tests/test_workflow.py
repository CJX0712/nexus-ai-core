"""工作流引擎测试：拓扑排序 / 环检测 / 节点执行与上下文传递。

作者: 晨星
"""
from __future__ import annotations

import pytest

from app.core.errors import WorkflowError
from app.workflow.engine import Node, WorkflowEngine, _render


def test_topo_sort_respects_dependencies():
    nodes = [
        Node(id="c", kind="transform", params={}, depends_on=["b"]),
        Node(id="a", kind="transform", params={}),
        Node(id="b", kind="transform", params={}, depends_on=["a"]),
    ]
    order = [n.id for n in WorkflowEngine.topo_sort(nodes)]
    assert order == ["a", "b", "c"]


def test_topo_sort_detects_cycle():
    nodes = [Node(id="a", kind="transform", depends_on=["b"]),
             Node(id="b", kind="transform", depends_on=["a"])]
    with pytest.raises(WorkflowError):
        WorkflowEngine.topo_sort(nodes)


def test_topo_sort_detects_duplicate_and_missing_dep():
    with pytest.raises(WorkflowError):
        WorkflowEngine.topo_sort([Node(id="a", kind="transform"),
                                  Node(id="a", kind="transform")])
    with pytest.raises(WorkflowError):
        WorkflowEngine.topo_sort([Node(id="a", kind="transform",
                                       depends_on=["ghost"])])


def test_render_replaces_placeholders():
    assert _render("{input} -> {a}", {"input": "X", "a": "Y"}) == "X -> Y"


def test_workflow_runs_and_passes_context(settings, container, offline_gateway):
    engine = WorkflowEngine(gateway=offline_gateway, rag_service=container.rag,
                            registry=container.registry)
    nodes = [
        Node(id="t1", kind="transform", params={"template": "主题:{input}"}),
        Node(id="t2", kind="transform", params={"template": "摘要:{t1}"},
             depends_on=["t1"]),
    ]
    result = engine.run(nodes, "模块化")
    assert result.order == ["t1", "t2"]
    assert result.outputs["t1"] == "主题:模块化"
    assert result.outputs["t2"] == "摘要:主题:模块化"


def test_workflow_tool_node(settings, container, offline_gateway):
    engine = WorkflowEngine(gateway=offline_gateway, rag_service=container.rag,
                            registry=container.registry)
    nodes = [Node(id="calc", kind="tool",
                  params={"name": "calculator", "args": {"expression": "7*6"}})]
    assert engine.run(nodes, "").outputs["calc"] == "42"


def test_workflow_llm_node_uses_gateway(settings, container, offline_gateway):
    engine = WorkflowEngine(gateway=offline_gateway, rag_service=container.rag,
                            registry=container.registry)
    nodes = [Node(id="gen", kind="llm", params={"prompt": "请总结：{input}"})]
    out = engine.run(nodes, "模块化架构").outputs["gen"]
    assert isinstance(out, str) and out


def test_workflow_unknown_node_type(settings, container, offline_gateway):
    engine = WorkflowEngine(gateway=offline_gateway, rag_service=container.rag,
                            registry=container.registry)
    with pytest.raises(WorkflowError):
        engine.run([Node(id="x", kind="nope")], "")


def test_workflow_rag_node_requires_service(offline_gateway):
    engine = WorkflowEngine(gateway=offline_gateway)
    with pytest.raises(WorkflowError):
        engine.run([Node(id="r", kind="rag")], "query")
