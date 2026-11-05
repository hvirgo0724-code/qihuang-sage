import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, BigInteger
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.api import clinical, consultation
from app.api.deps import get_current_user
from app.core.database import Base, get_db
from app.models.entities import User, ConsultationSession, SyndromeAnalysis, ReportReview, ConsultationRecord, ClinicalEncounter


@compiles(BigInteger, 'sqlite')
def sqlite_bigint(element, compiler, **kw):
    return 'INTEGER'


class ClinicalTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, expire_on_commit=False)()
        self.users = [User(user_id=i, tenant_id=2 if i == 5 else 1, username=f'u{i}',
            password_hash='unused', role='DOCTOR' if i in (2, 3, 5) else 'USER', status='active') for i in range(1, 6)]
        self.db.add_all(self.users)
        self.db.add(ConsultationSession(session_id=10, tenant_id=1, user_id=1))
        self.db.commit()
        self.current = self.users[0]
        app = FastAPI()
        app.include_router(clinical.router)
        app.include_router(consultation.router)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.current
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def request(self):
        self.assertEqual(self.client.post('/clinical/sessions/10/request', json={'doctor_id': 2, 'consent': True}).status_code, 201)

    def test_complete_workflow(self):
        self.request()
        self.assertEqual(self.client.post('/clinical/sessions/10/messages', json={'content': 'hello'}).status_code, 409)
        self.current = self.users[1]
        self.assertEqual(self.client.post('/clinical/sessions/10/accept').status_code, 200)
        self.assertEqual(self.client.post('/clinical/sessions/10/messages', json={'content': '医生回复'}).status_code, 201)
        self.assertEqual(self.client.post('/clinical/sessions/10/close').status_code, 409)
        self.assertEqual(self.client.put('/clinical/sessions/10/review', json={'content': '审阅意见'}).status_code, 200)
        self.current = self.users[0]
        self.assertEqual(self.client.post('/clinical/sessions/10/messages', json={'content': '患者回复'}).status_code, 201)
        result = self.client.get('/clinical/sessions/10').json()
        self.assertEqual(len(result['messages']), 2)
        self.assertEqual(result['review'], '审阅意见')
        self.current = self.users[1]
        self.assertEqual(self.client.post('/clinical/sessions/10/close').status_code, 200)
        self.assertEqual(self.client.post('/clinical/sessions/10/messages', json={'content': 'late'}).status_code, 409)

    def test_history_uses_latest_report_and_does_not_expose_drafts(self):
        self.assertIsNone(self.client.get('/consultation/me').json()[0]['report_status'])
        self.db.add(SyndromeAnalysis(analysis_id=20, session_id=10, syndrome='私有草稿'))
        self.db.commit()
        row = self.client.get('/consultation/me').json()[0]
        self.assertEqual(row['report_status'], 'pending')
        self.assertEqual(row['analysis_id'], 20)
        self.assertNotIn('私有草稿', str(row))
        self.db.add(ReportReview(analysis_id=20, status='confirmed', report={'syndrome': '已确认'}))
        self.db.commit()
        self.assertEqual(self.client.get('/consultation/me').json()[0]['report_status'], 'confirmed')
        self.db.add(SyndromeAnalysis(analysis_id=21, session_id=10, syndrome='新版草稿'))
        self.db.commit()
        self.assertEqual(self.client.get('/consultation/me').json()[0]['report_status'], 'pending')
        self.current = self.users[3]
        self.assertEqual(self.client.get('/consultation/me').json(), [])

    def test_historical_unanswered_question_gets_current_buttons(self):
        self.db.add(ConsultationRecord(record_id=50, session_id=10, role='assistant', type='text',
                                       content='请告知性别、年龄。最不舒服的部位在哪里？'))
        self.db.commit()
        rows = self.client.get('/consultation/10/messages').json()
        groups = {q['id']: q for q in rows[-1]['meta']['choices']}
        self.assertTrue(groups['location']['multiple'])
        self.assertEqual(groups['age']['input_type'], 'age')
        self.db.add(ConsultationRecord(record_id=51, session_id=10, role='user', type='text', content='头痛'))
        self.db.commit()
        rows = self.client.get('/consultation/10/messages').json()
        self.assertIsNone(rows[0]['meta'])

    def test_assignment_tenant_and_revocation(self):
        self.request()
        for user in self.users[2:]:
            self.current = user
            self.assertEqual(self.client.get('/clinical/sessions/10').status_code, 404)
            if user.role == 'DOCTOR':
                self.assertEqual(self.client.get('/clinical/cases').json(), [])
                self.assertEqual(self.client.post('/clinical/sessions/10/accept').status_code, 404)
        self.current = self.users[0]
        self.assertEqual(self.client.post('/clinical/sessions/10/cancel').status_code, 200)
        self.current = self.users[1]
        self.assertEqual(self.client.get('/clinical/sessions/10').status_code, 404)

    def test_consent_roles_and_directory(self):
        self.assertEqual(self.client.post('/clinical/sessions/10/request', json={'doctor_id': 2, 'consent': False}).status_code, 422)
        self.assertEqual(self.client.post('/clinical/sessions/10/request', json={'doctor_id': 5, 'consent': True}).status_code, 404)
        self.assertEqual(self.client.get('/clinical/cases').status_code, 403)
        self.assertEqual(self.client.get('/clinical/admin/doctors').status_code, 403)
        self.assertEqual({d['user_id'] for d in self.client.get('/clinical/doctors').json()}, {2, 3})
        self.assertEqual(self.client.post('/clinical/sessions/10/messages', json={'content': '   '}).status_code, 422)

    def test_report_private_until_doctor_confirms(self):
        self.request()
        analysis = SyndromeAnalysis(analysis_id=20, session_id=10, syndrome='AI草稿', emergency_flag=False)
        self.db.add(analysis)
        self.db.add(ConsultationRecord(record_id=30, session_id=10, role='assistant', type='result',
                                       content='旧版未审核正文', meta={'syndrome': '旧版未审核正文'}))
        self.db.commit()
        # Legacy reports also fail closed until explicitly reviewed.
        result = self.client.get('/consultation/10/result').json()
        self.assertEqual(result['review_status'], 'pending')
        self.assertNotIn('syndrome', result)
        self.assertNotIn('旧版未审核正文', self.client.get('/consultation/10/messages').text)
        edit = {'revision': 0, 'report': {'syndrome': '医生修改结论', 'treatment_principle': '医生调养建议'}}
        path = '/clinical/sessions/10/reports/20'
        self.assertEqual(self.client.put(path, json=edit).status_code, 403)
        for user in (self.users[2], self.users[4]):
            self.current = user
            self.assertEqual(self.client.put(path, json=edit).status_code, 404)
        self.current = self.users[1]
        self.assertEqual(self.client.put(path, json=edit).status_code, 409)
        self.client.post('/clinical/sessions/10/accept')
        self.assertEqual(self.client.put(path, json=edit).status_code, 200)
        self.assertEqual(self.client.put(path, json=edit).status_code, 409)
        self.current = self.users[0]
        self.assertNotIn('syndrome', self.client.get('/consultation/10/result').json())
        self.current = self.users[1]
        self.assertEqual(self.client.post(path + '/confirm', json={'revision': 2}).status_code, 409)
        self.assertEqual(self.client.post(path + '/confirm', json={'revision': 1}).status_code, 200)
        self.assertEqual(self.client.post(path + '/confirm', json={'revision': 1}).status_code, 409)
        self.current = self.users[0]
        result = self.client.get('/consultation/10/result').json()
        self.assertEqual(result['review_status'], 'confirmed')
        self.assertEqual(result['syndrome'], '医生修改结论')
        self.assertEqual(self.db.get(SyndromeAnalysis, 20).syndrome, 'AI草稿')
        self.assertEqual(self.db.get(ConsultationSession, 10).status, 'completed')
        self.assertIn('医生审核确认', self.client.get('/clinical/sessions/10').text)

    def test_stale_report_and_revoked_consent_cannot_publish(self):
        self.request()
        self.db.add_all([SyndromeAnalysis(analysis_id=i, session_id=10) for i in (20, 21)])
        self.db.add(ReportReview(analysis_id=20, revision=1, report={'syndrome': 'old'}))
        self.db.commit()
        self.current = self.users[1]
        self.client.post('/clinical/sessions/10/accept')
        self.assertEqual(self.client.post('/clinical/sessions/10/reports/20/confirm', json={'revision': 1}).status_code, 409)
        self.current = self.users[0]
        self.client.post('/clinical/sessions/10/cancel')
        self.current = self.users[1]
        self.assertEqual(self.client.post('/clinical/sessions/10/reports/21/confirm', json={'revision': 1}).status_code, 404)


if __name__ == '__main__':
    unittest.main()
