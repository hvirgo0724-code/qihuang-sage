import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from pydantic import ValidationError
from app.api.memory import RememberRequest, suggestions


class MemoryApiTests(unittest.TestCase):
    def test_consent_and_content_required(self):
        for payload in ({'key': 'note', 'content': 'text'},
                        {'key': 'note', 'content': 'text', 'consent': False},
                        {'key': 'note', 'content': '  ', 'consent': True}):
            with self.assertRaises(ValidationError):
                RememberRequest(**payload)

    def test_unowned_session_never_reads_memory(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        with patch('app.api.memory.MemoryStore') as store:
            with self.assertRaises(HTTPException) as caught:
                suggestions(99, SimpleNamespace(tenant_id=1, user_id=2), db)
            self.assertEqual(caught.exception.status_code, 404)
            store.assert_not_called()
