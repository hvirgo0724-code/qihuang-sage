from contextlib import nullcontext
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from tests.test_delete_user_data import DeleteUserDataTests
from app.api.consultation import delete_session
from app.models.entities import User, ConsultationSession, ConsultationRecord, SyndromeAnalysis, ReportReview


class DeleteSessionTests(DeleteUserDataTests):
    def test_only_owned_session_and_report_removed(self):
        self.db.add(ConsultationSession(session_id=11, user_id=1, tenant_id=3))
        self.db.add(SyndromeAnalysis(analysis_id=30, session_id=10))
        self.db.flush()
        self.db.add(ReportReview(analysis_id=30, report={}, status='confirmed'))
        self.db.commit()
        memory = MagicMock()
        with patch('app.core.memory.session_lock', return_value=nullcontext()), \
             patch('app.core.memory.memory_engine', return_value=memory), \
             patch('app.api.consultation.audit_service.record'):
            delete_session(10, self.db.get(User, 1), self.db)
        self.assertIsNotNone(self.db.get(User, 1))
        self.assertIsNone(self.db.get(ConsultationSession, 10))
        self.assertIsNotNone(self.db.get(ConsultationSession, 11))
        self.assertIsNone(self.db.get(ConsultationRecord, 20))
        self.assertIsNone(self.db.get(ReportReview, 30))
        args = memory.begin.return_value.__enter__.return_value.execute.call_args.args
        self.assertEqual(args[1], {'tenant': 3, 'user': 1, 'namespace': '10'})
        self.assertIn("kind='short'", str(args[0]))

    def test_other_owner_rejected(self):
        with patch('app.core.memory.memory_engine') as memory:
            with self.assertRaises(HTTPException) as caught:
                delete_session(10, self.db.get(User, 2), self.db)
            self.assertEqual(caught.exception.status_code, 404)
            memory.assert_not_called()
        self.assertIsNotNone(self.db.get(ConsultationSession, 10))
