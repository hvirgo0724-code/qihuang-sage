import unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.core import llm


class VisionTests(unittest.TestCase):
    def test_empty_primary_uses_fallback(self):
        clients = [Mock(), Mock()]
        clients[0].invoke.return_value = SimpleNamespace(content="")
        clients[1].invoke.return_value = SimpleNamespace(content='{"confidence":0}')
        with patch.object(llm.settings, 'vision_model_fallback', 'backup'), \
                patch.object(llm, '_vision_llm', side_effect=clients), \
                patch.object(llm, 'llm_trace', return_value=nullcontext()):
            self.assertEqual(llm.invoke_vision([], model='primary'), '{"confidence":0}')

    def test_failures_explain_status_without_provider_body(self):
        error = RuntimeError('secret provider payload')
        error.status_code = 400
        client = Mock()
        client.invoke.side_effect = error
        with patch.object(llm.settings, 'vision_model_fallback', ''), \
                patch.object(llm, '_vision_llm', return_value=client), \
                patch.object(llm, 'llm_trace', return_value=nullcontext()):
            with self.assertRaises(RuntimeError) as raised:
                llm.invoke_vision([], model='primary')
        self.assertIn('HTTP 400', str(raised.exception))
        self.assertNotIn('secret', str(raised.exception))

    def test_timeout_is_actionable(self):
        error = type('APITimeoutError', (Exception,), {})()
        self.assertIn('VISION_TIMEOUT_SECONDS', llm._vision_error_reason(error))
