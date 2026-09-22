"""智能体测试：工具注册表 / 计算器安全 / ReAct 循环。

作者: 晨星
"""
from __future__ import annotations

import pytest

from app.agent.react import ReactAgent
from app.agent.tools import ToolRegistry, build_default_registry, calculator
from app.core.errors import BadRequestError
from app.gateway.llm import ChatResult


# ---------------- 工具 ----------------
def test_calculator_basic():
    assert calculator("2+3*4") == "14"
    assert calculator("(1+2)*3") == "9"


def test_calculator_rejects_code_injection():
    for expr in ["__import__('os').system('dir')", "open('x').read()", "1;rm -rf /"]:
        with pytest.raises(BadRequestError):
            calculator(expr)


def test_registry_duplicate_and_unknown():
    reg = ToolRegistry()
    reg.register_fn("now", "时间", {}, lambda: "t")
    with pytest.raises(BadRequestError):
        reg.register_fn("now", "重复", {}, lambda: "t")
    with pytest.raises(BadRequestError):
        reg.call("not_exist")


def test_default_registry_contains_builtin_tools(container):
    reg = build_default_registry(rag_service=container.rag,
                                 memory_store=container.memory)
    assert "calculator" in reg.list()
    assert "rag_search" in reg.list()
    assert "memory_remember" in reg.list()


def test_rag_search_tool_returns_sources(container):
    container.rag.ingest_text("报销流程需要提交发票与审批单。", source="hr.md")
    reg = build_default_registry(rag_service=container.rag)
    out = reg.call("rag_search", query="报销流程", top_k=2)
    assert "发票" in out


# ---------------- ReAct ----------------
class ScriptedGateway:
    """按脚本顺序返回固定文本，用于确定性地驱动 ReAct 循环。"""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def complete(self, messages, *, temperature=None, max_tokens=None, settings=None):
        self.calls += 1
        text = self.responses.pop(0) if self.responses else "Final Answer: done"
        return ChatResult(text=text, model="scripted", provider="scripted")


def test_react_runs_tool_then_finalizes(settings):
    reg = build_default_registry()
    gw = ScriptedGateway([
        'Thought: 需要计算\nAction: calculator\nAction Input: {"expression": "12*5"}',
        "Thought: 得到结果\nFinal Answer: 60",
    ])
    agent = ReactAgent(gw, reg, settings)
    result = agent.run("12 乘以 5 等于多少？")

    assert result.finished is True
    assert result.tool_calls == 1
    assert result.answer == "60"
    assert result.steps[0].observation == "60"


def test_react_final_answer_immediately(settings):
    reg = build_default_registry()
    gw = ScriptedGateway(["Thought: 无需工具\nFinal Answer: 直接回答"])
    result = ReactAgent(gw, reg, settings).run("你好")
    assert result.answer == "直接回答"
    assert result.tool_calls == 0


def test_react_malformed_output_treated_as_final(settings):
    gw = ScriptedGateway(["这不是标准格式的一句话回答"])
    result = ReactAgent(gw, build_default_registry(), settings).run("x")
    assert result.finished is True
    assert "不是标准格式" in result.answer


def test_react_stops_at_max_steps(settings):
    steps = ['Thought: 继续\nAction: calculator\nAction Input: {"expression": "1+1"}']
    gw = ScriptedGateway(steps * 10)
    result = ReactAgent(gw, build_default_registry(), settings).run("循环", max_steps=3)
    assert result.finished is False
    assert result.tool_calls == 3


def test_react_tool_error_becomes_observation(settings):
    gw = ScriptedGateway([
        'Thought: 试一下\nAction: calculator\nAction Input: {"expression": "os.system()"}',
        "Final Answer: 已处理错误",
    ])
    result = ReactAgent(gw, build_default_registry(), settings).run("x")
    assert "工具调用失败" in result.steps[0].observation
