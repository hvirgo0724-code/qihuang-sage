import json
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.services import consultation_service as service


class ReportCommandTests(unittest.TestCase):
    def test_report_skips_inquiry_and_restores_expired_memory(self):
        for saved in ([], [{"value": {"symptoms": ["失眠"], "complaint": "睡不好"}}]):
            with self.subTest(saved=bool(saved)), ExitStack() as stack:
                db = Mock()
                db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
                    SimpleNamespace(role="assistant", meta={"slots": {"symptoms": ["失眠"], "complaint": "睡不好"}})
                ]
                stack.enter_context(patch.object(service, "_add_record"))
                stack.enter_context(patch.object(service, "get_latest_analysis", return_value=None))
                stack.enter_context(patch.object(service, "_get_recognitions", return_value=[]))
                stack.enter_context(patch.object(service.safety_service, "check_input", return_value=SimpleNamespace(result="pass")))
                stack.enter_context(patch.object(service.safety_service, "check_output", return_value=SimpleNamespace(result="pass")))
                stack.enter_context(patch.object(service.prompt_service, "get_active_prompt_version", return_value="test"))
                fallback = stack.enter_context(patch.object(service, "_fallback_inquiry"))
                ask = stack.enter_context(patch.object(service.llm, "stream_text"))
                memory = stack.enter_context(patch.object(service, "MemoryStore"))
                memory.return_value.read.side_effect = [saved, []]
                analyze = stack.enter_context(patch.object(service.syndrome_service, "analyze", return_value={"risk_level": "low"}))
                session = SimpleNamespace(tenant_id=0, user_id=1, session_id=9, complaint=None, risk_level=None)
                events = list(service._chat_turn(db, session, "生成报告"))
                fallback.assert_not_called()
                ask.assert_not_called()
                self.assertEqual(analyze.call_args.args[1]["symptoms"], ["失眠"])
                self.assertEqual(analyze.call_args.args[2], "睡不好")
                written = memory.return_value.write.call_args.args[-1]
                self.assertEqual(written["complaint"], "睡不好")
                self.assertIn('"phase": "syndrome"', events[0])
                self.assertTrue(any(event.startswith("event: review_pending") for event in events))
                self.assertFalse(any(event.startswith("event: result") for event in events))
                chunks = [json.loads(event.split("data: ")[1])["text"] for event in events if event.startswith("event: chunk")]
                self.assertFalse(any("请继续描述" in chunk for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
