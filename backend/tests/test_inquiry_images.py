import json
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.services import consultation_service as service


class InquiryImageTests(unittest.TestCase):
    def test_latest_recognitions_keep_database_type_without_mutating_result(self):
        latest = {"tongue_color": "淡红", "image_type": "face"}
        db = Mock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            SimpleNamespace(image_type="tongue", analysis_result=latest),
            SimpleNamespace(image_type="face", analysis_result={"complexion": "红润"}),
            SimpleNamespace(image_type="tongue", analysis_result={"tongue_color": "红"}),
        ]
        self.assertEqual(service._get_recognitions(db, 7), [
            {"tongue_color": "淡红", "image_type": "tongue"},
            {"complexion": "红润", "image_type": "face"},
        ])
        self.assertEqual(latest["image_type"], "face")

    def test_each_turn_receives_current_images_even_with_existing_prompt_and_memory(self):
        images = [
            {"image_type": "tongue", "tongue_color": "淡红", "coating": "薄白", "confidence": 0.9},
            {"image_type": "face", "complexion": "红润", "confidence": 0.9},
        ]
        with ExitStack() as stack:
            stack.enter_context(patch.object(service, "_add_record"))
            load = stack.enter_context(patch.object(service, "_get_recognitions", side_effect=[[], images]))
            stack.enter_context(patch.object(service, "_extract_symptoms_via_graph", return_value=["失眠"]))
            stack.enter_context(patch.object(service.safety_service, "check_input", return_value=SimpleNamespace(result="pass")))
            # Existing DB prompts need no migration/new placeholder.
            stack.enter_context(patch.object(service.prompt_service, "get_active_prompt", return_value="已有信息：{slots}；输入：{message}"))
            stack.enter_context(patch.object(service.llm, "llm_configured", return_value=True))
            ask = stack.enter_context(patch.object(service.llm, "stream_text", side_effect=lambda *a, **k: (chunk for chunk in [
                '{"reply":"睡眠情况如何？","slots":{"symptoms":["失眠"]},"ready":false}'
            ])))
            memory = stack.enter_context(patch.object(service, "MemoryStore"))
            memory.return_value.read.side_effect = [[{"value": {"complaint": "睡不好"}}], []] * 2
            session = SimpleNamespace(tenant_id=1, user_id=1, session_id=7, complaint="睡不好")
            for _ in range(2):
                events = list(service._chat_turn(Mock(), session, "睡不好"))
                self.assertTrue(any("done" in event for event in events))
            first = ask.call_args_list[0].args[0][1]["content"]
            second = ask.call_args_list[1].args[0][1]["content"]
            self.assertNotIn("淡红", first)
            self.assertIn(json.dumps(images, ensure_ascii=False), second)
            self.assertEqual(load.call_count, 2)


if __name__ == "__main__":
    unittest.main()
