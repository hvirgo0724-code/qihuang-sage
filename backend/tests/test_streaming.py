import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.core import llm
from app.core.agents import AgentRuntime
from app.services import consultation_service as service


class StreamingTests(unittest.TestCase):
    def test_model_yields_before_completion(self):
        consumed = []
        def source():
            for text in ["你", "好"]:
                consumed.append(text)
                yield SimpleNamespace(content=text)
        with patch.object(llm, "_text_llm", return_value=SimpleNamespace(stream=lambda _: source())):
            stream = llm.stream_text([])
            self.assertEqual(next(stream), "你")
            self.assertEqual(consumed, ["你"])
            self.assertEqual(list(stream), ["好"])

    def test_no_fallback_after_first_chunk(self):
        def source():
            yield SimpleNamespace(content="部分")
            raise RuntimeError("disconnected")
        with patch.object(llm, "_text_llm", return_value=SimpleNamespace(stream=lambda _: source())) as factory:
            stream = llm.stream_text([])
            self.assertEqual(next(stream), "部分")
            with self.assertRaisesRegex(RuntimeError, "disconnected"):
                next(stream)
            factory.assert_called_once()

    def test_inquiry_streams_only_reply_before_json_finishes(self):
        consumed = []
        def source(*args, **kwargs):
            system = args[0][0]['content']
            self.assertIn('每轮只问1至2个具体问题', system)
            self.assertIn('最先确认性别和年龄', system)
            self.assertIn('也是有效回应，不要重复追问', system)
            for chunk in ['{"reply":"请', '描述睡眠', '\\n情况","slots":{},"ready":false}']:
                consumed.append(chunk)
                yield chunk
        with ExitStack() as stack:
            stack.enter_context(patch.object(service, "_add_record"))
            stack.enter_context(patch.object(service, "_get_recognitions", return_value=[]))
            stack.enter_context(patch.object(service, "_extract_symptoms_via_graph", return_value=["失眠"]))
            stack.enter_context(patch.object(service.safety_service, "check_input", return_value=SimpleNamespace(result="pass")))
            stack.enter_context(patch.object(service.prompt_service, "get_active_prompt", return_value="{message}"))
            stack.enter_context(patch.object(service.llm, "llm_configured", return_value=True))
            stack.enter_context(patch.object(service.llm, "stream_text", side_effect=source))
            memory = stack.enter_context(patch.object(service, "MemoryStore"))
            memory.return_value.read.return_value = []
            stream = service._chat_turn(Mock(), SimpleNamespace(tenant_id=1, user_id=1, session_id=1, complaint="失眠"), "睡不好")
            self.assertIn("phase", next(stream))
            self.assertEqual(consumed, [])
            self.assertIn('"text": "请"', next(stream))
            self.assertEqual(len(consumed), 1)
            remainder = list(stream)
            self.assertTrue(any("描述睡眠" in event for event in remainder))
            self.assertTrue(any("done" in event for event in remainder))
            self.assertFalse(any('"text": "slots' in event for event in remainder))

    def test_stream_close_releases_tool_generator(self):
        released = []
        def source():
            try:
                yield "one"
                yield "two"
            finally:
                released.append(True)
        runtime = AgentRuntime().bind("inquiry", ask=source)
        stream = runtime.stream("inquiry", "ask")
        self.assertEqual(next(stream), "one")
        stream.close()
        self.assertEqual(runtime.calls, 1)
        self.assertEqual(released, [True])
