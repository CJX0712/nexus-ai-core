"""ReAct 智能体（单一职责：只负责"推理-行动-观察"循环控制）。

作者: 晨星
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from app.agent.tools import ToolRegistry
from app.core.logging import get_logger
from app.gateway.llm import ChatMessage

log = get_logger("agent.react")

REACT_SYSTEM = """你是一个使用工具解决问题的智能体。严格按以下格式之一输出，不要输出多余内容：

Thought: 你的推理
Action: 工具名
Action Input: JSON 对象参数

或当已有足够信息时：

Thought: 你的推理
Final Answer: 最终答案

可用工具：
{tools}

规则：
- 每次只调用一个工具
- Action Input 必须是合法 JSON
- 最多 {max_steps} 步，超出请直接给出 Final Answer
"""

_ACTION_RE = re.compile(
    r"Action:\s*(\w+)\s*\n\s*Action Input:\s*(\{.*?\}|[^\n]*)", re.S
)
_FINAL_RE = re.compile(r"Final Answer:\s*(.*)", re.S)


@dataclass
class Step:
    thought: str = ""
    action: str = ""
    action_input: str = ""
    observation: str = ""
    final: str = ""


@dataclass
class AgentRunResult:
    answer: str
    steps: list[Step] = field(default_factory=list)
    tool_calls: int = 0
    finished: bool = True
    provider: str = ""
    model: str = ""


class ReactAgent:
    """ReAct 循环执行器。LLM 与工具集均为注入依赖，可独立测试。"""

    def __init__(self, gateway, registry: ToolRegistry, settings) -> None:
        self.gateway = gateway
        self.registry = registry
        self.settings = settings

    def run(self, task: str, *, max_steps: int | None = None) -> AgentRunResult:
        limit = max_steps or self.settings.agent_max_steps
        system = REACT_SYSTEM.format(
            tools=self.registry.describe(), max_steps=limit
        )
        history: list[ChatMessage] = [
            ChatMessage(role="system", content=system),
            ChatMessage(role="user", content=f"任务：{task}"),
        ]
        steps: list[Step] = []
        tool_calls = 0
        provider = model = ""

        for _ in range(limit):
            result = self.gateway.complete(history, settings=self.settings)
            provider, model = result.provider, result.model
            text = result.text or ""
            step = Step()

            thought_m = re.search(r"Thought:\s*(.*?)(?=\n(?:Action|Final Answer):|$)",
                                  text, re.S)
            if thought_m:
                step.thought = thought_m.group(1).strip()

            final_m = _FINAL_RE.search(text)
            if final_m:
                step.final = final_m.group(1).strip()
                steps.append(step)
                return AgentRunResult(answer=step.final, steps=steps,
                                      tool_calls=tool_calls, finished=True,
                                      provider=provider, model=model)

            action_m = _ACTION_RE.search(text)
            if not action_m:
                # 模型未按格式输出：把原文当作最终答案，避免死循环
                step.final = text.strip()
                steps.append(step)
                return AgentRunResult(answer=step.final, steps=steps,
                                      tool_calls=tool_calls, finished=True,
                                      provider=provider, model=model)

            tool_name = action_m.group(1).strip()
            raw_input = action_m.group(2).strip()
            step.action = tool_name
            step.action_input = raw_input
            try:
                kwargs = json.loads(raw_input) if raw_input.startswith("{") else {}
                observation = self.registry.call(tool_name, **kwargs)
            except Exception as exc:  # noqa: BLE001 - 观察即错误信息
                observation = f"工具调用失败: {exc}"
            step.observation = observation
            steps.append(step)
            tool_calls += 1

            history.append(ChatMessage(role="assistant", content=text))
            history.append(
                ChatMessage(role="user", content=f"Observation: {observation}")
            )

        last = steps[-1].observation if steps else ""
        return AgentRunResult(
            answer=f"已达最大步数 {limit}，最后观察：{last[:500]}",
            steps=steps, tool_calls=tool_calls, finished=False,
            provider=provider, model=model,
        )
