"""AgentRuntime 兼容外壳。

编排实现已迁至 ``app.core.graph``（LangGraph StateGraph + BoundedToolExecutor）。
保留此模块仅作兼容封装：既有调用点与测试仍以 ``bind(agent, **tools)`` /
``call(agent, tool)`` / ``stream(agent, tool)`` 的旧形态访问，实际执行统一委托
给 graph.BoundedToolExecutor（白名单 + 调用预算语义不变）。
新代码请直接使用 app.core.graph 中的类与函数。
"""
from app.core.graph import AGENT_TOOLS, BoundedToolExecutor, ToolBudgetExceeded  # noqa: F401

__all__ = ["AgentRuntime", "AGENT_TOOLS", "ToolBudgetExceeded"]


class AgentRuntime:
    """多智能体有界执行的外观：维护每个角色的 BoundedToolExecutor 并转发调用。"""

    def __init__(self):
        self._executors: dict[str, BoundedToolExecutor] = {}

    @property
    def calls(self) -> int:
        return sum(executor.calls for executor in self._executors.values())

    def bind(self, agent: str, **tools) -> "AgentRuntime":
        if agent not in AGENT_TOOLS:
            raise ValueError("unknown agent role")
        if agent not in self._executors:
            self._executors[agent] = BoundedToolExecutor(agent)
        self._executors[agent].bind(**tools)
        return self

    def call(self, agent: str, tool: str, *args, **kwargs):
        if agent not in self._executors:
            raise PermissionError("tool is not bound to this agent")
        return self._executors[agent].call(tool, *args, **kwargs)

    def stream(self, agent: str, tool: str, *args, **kwargs):
        if agent not in self._executors:
            raise PermissionError("tool is not bound to this agent")
        yield from self._executors[agent].stream(tool, *args, **kwargs)