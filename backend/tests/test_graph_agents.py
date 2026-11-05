"""离线单测：LangGraph 编排与「每 agent 独立绑定」语义（不依赖 LLM/DB/Neo4j/Milvus）。"""
import unittest

from app.core.graph import (
    AGENTS,
    BoundedToolExecutor,
    build_diagnosis_graph,
)


class AgentBindingTests(unittest.TestCase):
    def test_unknown_agent_raises_value_error(self):
        with self.assertRaises(ValueError):
            BoundedToolExecutor("no-such-agent")

    def test_bind_unregistered_tool_raises_value_error(self):
        executor = BoundedToolExecutor("care")
        with self.assertRaises(ValueError):
            executor.bind(execute_sql=lambda: None)

    def test_call_unbound_tool_raises_permission_error(self):
        executor = BoundedToolExecutor("care")
        with self.assertRaises(PermissionError):
            executor.call("recommend")

    def test_agents_enumerable_with_stable_order(self):
        self.assertEqual(list(AGENTS.keys()), ["inquiry", "syndrome", "care"])
        self.assertEqual(AGENTS["inquiry"].tools, ("load_memory", "save_memory", "extract_symptoms", "ask"))
        self.assertEqual(AGENTS["syndrome"].tools, ("embed", "retrieve", "differentiate"))
        self.assertEqual(AGENTS["care"].tools, ("recommend",))
        self.assertEqual([len(spec.tools) for spec in AGENTS.values()], [4, 3, 1])

    def test_budget_is_counted_independently_per_agent(self):
        inquiry = BoundedToolExecutor("inquiry").bind(ask=lambda: "inquiry-ok")
        care = BoundedToolExecutor("care").bind(recommend=lambda: "care-ok")
        inquiry.budget = 1
        self.assertEqual(inquiry.call("ask"), "inquiry-ok")
        with self.assertRaises(RuntimeError):
            inquiry.call("ask")
        # care 拥有独立预算与计数，不受 inquiry 耗尽影响
        self.assertEqual(care.call("recommend"), "care-ok")
        self.assertEqual(care.calls, 1)


class DiagnosisGraphTests(unittest.TestCase):
    def test_nodes_pass_state_through_three_stages(self):
        seen = {}

        def retrieve(state):
            seen["retrieve"] = dict(state)
            return {"kg": {"retrieved": True}}

        def differentiate(state):
            seen["differentiate"] = dict(state)
            return {"syndrome": "气血两虚", "evidence": [{"source": "kg"}]}

        def recommend(state):
            seen["recommend"] = dict(state)
            return {"treatment": {"syndrome": state.get("syndrome")}}

        graph = build_diagnosis_graph(retrieve, differentiate, recommend)
        final = graph.invoke({"complaint": "失眠", "symptoms": ["失眠", "乏力"]})

        self.assertEqual(final["kg"], {"retrieved": True})
        self.assertEqual(final["syndrome"], "气血两虚")
        self.assertEqual(final["evidence"], [{"source": "kg"}])
        self.assertEqual(final["treatment"], {"syndrome": "气血两虚"})
        # 状态沿节点传递：后续节点能看到前序节点写入的字段
        self.assertNotIn("kg", seen["retrieve"])
        self.assertIn("kg", seen["differentiate"])
        self.assertEqual(seen["recommend"]["syndrome"], "气血两虚")


if __name__ == "__main__":
    unittest.main()