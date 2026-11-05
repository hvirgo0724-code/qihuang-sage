import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, event, select, func
from sqlalchemy.orm import Session
from app.core.database import Base
from app.models.entities import User, UserProfile, ConsultationSession, ConsultationRecord
from app.services.auth_service import delete_user_data


class DeleteUserDataTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        event.listen(self.engine, 'connect', lambda conn, _: conn.execute('PRAGMA foreign_keys=ON'))
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add_all([User(user_id=1, tenant_id=3, username='target', password_hash='test'),
                         User(user_id=2, tenant_id=4, username='other', password_hash='test')])
        self.db.flush()
        self.db.add_all([UserProfile(user_id=1), UserProfile(user_id=2),
                         ConsultationSession(session_id=10, user_id=1, tenant_id=3)])
        self.db.flush()
        self.db.add(ConsultationRecord(record_id=20, session_id=10, role='user'))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_loaded_and_unloaded_profile(self):
        for loaded in (False, True):
            with self.subTest(loaded=loaded):
                if loaded:
                    self.tearDown()
                    self.setUp()
                    self.assertIsNotNone(self.db.get(User, 1).profile)
                memory = MagicMock()
                with patch('app.core.memory.memory_engine', return_value=memory):
                    delete_user_data(self.db, 1)
                account = self.db.get(User, 1)
                self.assertIsNotNone(account)
                self.assertEqual(account.username, 'target')
                self.assertEqual(account.password_hash, 'test')
                self.assertEqual(account.status, 'active')
                self.assertIsNotNone(self.db.get(User, 2))
                self.assertEqual(self.db.scalar(select(func.count()).select_from(UserProfile)), 1)
                self.assertEqual(self.db.scalar(select(func.count()).select_from(ConsultationRecord)), 0)
                self.assertEqual(self.db.scalar(select(func.count()).select_from(ConsultationSession)), 0)
                args = memory.begin.return_value.__enter__.return_value.execute.call_args.args
                self.assertEqual(args[1], {'tenant': 3, 'user': 1})

    def test_memory_failure_rolls_back_business_deletion(self):
        with patch('app.core.memory.memory_engine', side_effect=RuntimeError('offline')):
            with self.assertRaises(RuntimeError):
                delete_user_data(self.db, 1)
        self.assertIsNotNone(self.db.get(User, 1))
        self.assertIsNotNone(self.db.get(UserProfile, 1))

    def test_flush_failure_does_not_touch_memory(self):
        with patch.object(self.db, 'flush', side_effect=RuntimeError('constraint')), \
             patch('app.core.memory.memory_engine') as memory:
            with self.assertRaises(RuntimeError):
                delete_user_data(self.db, 1)
            memory.assert_not_called()
