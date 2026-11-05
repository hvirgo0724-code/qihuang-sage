"""LangGraph 编排层：有界智能体与诊断链路图。

- ``BoundedToolExecutor`` 是唯一的有界工具调用原语：构造时按 agent 各自声明的白名单
  与独立调用预算绑定，运行时只查自身状态；并记录 OpenTelemetry span 与 Prometheus 指标。
  它取代原先的 AgentRuntime，供图节点与 inquiry 流式追问使用。
- ``build_diagnosis_graph`` 用 LangGraph 的 StateGraph 把 syndrome→care 的多节点
  诊断链路建模为共享状态的图：状态在 retrieve/differentiate/recommend 节点间传递，
  图本身无环（有界），真正进入 LangChain/LangGraph 1.x 的编排体系。

三个专职智能体与工具白名单保持不变：
  inquiry  -> load_memory / save_memory / extract_symptoms / ask
  syndrome -> embed / retrieve / differentiate
  care     -> recommend
"""
from contextlib import closing, contextmanager
from dataclasses import dataclass, field
from operator import add
from time import perf_counter
from typing import Annotated, Any, Callable, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from opentelemetry import trace
from prometheus_client import Counter, Histogram

from app.core.config import settings

logger = __import__("logging").getLogger("app.graph")

@dataclass(frozen=True)
class AgentSpec:
    """单个智能体的工具白名单（稳定顺序）与独立调用预算。"""

    name: str
    tools: tuple[str, ...]
    budget: int


# 每个 agent 各自声明工具集与预算；dict 插入顺序即稳定枚举顺序（管理后台/审计展示用）。
AGENTS: dict[str, AgentSpec] = {
    "inquiry": AgentSpec("inquiry", ("load_memory", "save_memory", "extract_symptoms", "ask"), settings.agent_max_tool_calls),
    "syndrome": AgentSpec("syndrome", ("embed", "retrieve", "differentiate"), settings.agent_max_tool_calls),
    "care": AgentSpec("care", ("recommend",), settings.agent_max_tool_calls),
}

# 派生枚举视图（稳定顺序），仅供审计/展示/兼容测试；运行时白名单与预算以 AGENTS 为准。
AGENT_TOOLS: dict[str, tuple[str, ...]] = {name: spec.tools for name, spec in AGENTS.items()}
CALLS = Counter("tcm_agent_tool_calls_total", "Bounded agent tool calls", ["agent", "tool", "outcome"])
LATENCY = Histogram("tcm_agent_tool_duration_seconds", "Tool latency", ["agent", "tool"])


class ToolBudgetExceeded(RuntimeError):
    """调用预算耗尽：保持有界，不允许无界工具调用。"""


@dataclass
class BoundedToolExecutor:
    """单个智能体的有界工具执行器：构造时按 agent 绑定白名单与预算，运行时只查自身状态。"""

    agent: str
    calls: int = 0
    bindings: dict = field(default_factory=dict)

    def __post_init__(self):
        spec = AGENTS.get(self.agent)
        if spec is None:
            raise ValueError("unknown agent role")
        self._allowlist = frozenset(spec.tools)
        self.budget = spec.budget

    def bind(self, **tools) -> "BoundedToolExecutor":
        if not set(tools) <= self._allowlist:
            raise ValueError("tool outside role allowlist")
        self.bindings.update(tools)
        return self

    @contextmanager
    def _execution(self, tool: str):
        if tool not in self.bindings:
            raise PermissionError("tool is not bound to this agent")
        if self.calls >= self.budget:
            raise ToolBudgetExceeded("agent tool budget exhausted")
        self.calls += 1
        started, outcome = perf_counter(), "error"
        try:
            with trace.get_tracer(__name__).start_as_current_span(f"agent.{self.agent}.{tool}"):
                yield self.bindings[tool]
                outcome = "success"
        finally:
            CALLS.labels(self.agent, tool, outcome).inc()
            LATENCY.labels(self.agent, tool).observe(perf_counter() - started)

    def call(self, tool: str, *args, **kwargs):
        with self._execution(tool) as fn:
            return fn(*args, **kwargs)

    def stream(self, tool: str, *args, **kwargs):
        with self._execution(tool) as fn:
            with closing(fn(*args, **kwargs)) as chunks:
                yield from chunks


class DiagnosisState(TypedDict, total=False):
    """diagnosis 图共享状态：各节点读取前序节点写入的字段并在节点间传递。"""

    db: Any
    complaint: str
    symptoms: list[str]
    inquiry: dict
    patient_messages: list[str]
    recognitions: list[dict]
    risk: str
    embedding: Optional[list[float]]
    kg: dict
    syndrome: Optional[str]
    evidence: list
    differential: list
    confidence: Optional[float]
    treatment: dict
    tool_calls: Annotated[int, add]


def build_diagnosis_graph(
    retrieve: Callable[[dict], dict],
    differentiate: Callable[[dict], dict],
    recommend: Callable[[dict], dict],
):
    """构建 syndrome→care 的有界诊断图；节点函数由调用方注入以复用其模块级依赖。"""
    g = StateGraph(DiagnosisState)
    g.add_node("retrieve", retrieve)
    g.add_node("differentiate", differentiate)
    g.add_node("recommend", recommend)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "differentiate")
    g.add_edge("differentiate", "recommend")
    g.add_edge("recommend", END)
    return g.compile()
