import io
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException, UploadFile
from app.api import consultation


class ImageUploadTests(unittest.TestCase):
    def upload(self, dispatch_error=None):
        db = MagicMock()
        db.refresh.side_effect = lambda image: setattr(image, "image_id", 123)
        job = SimpleNamespace(status="pending", error=None, finish_time=None)
        db.get.return_value = job
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(consultation, "UPLOAD_DIR", directory), \
                patch.object(consultation.consultation_service, "get_session", return_value=object()), \
                patch.object(consultation.image_analysis_service, "precheck_image", return_value=(True, "ok")), \
                patch.object(consultation.image_analysis_service, "normalize_image", return_value=b"test"), \
                patch.object(consultation.audit_service, "record"), \
                patch("app.tasks.jobs.analyze_image_task.delay", side_effect=dispatch_error) as dispatch:
            try:
                result = consultation.upload_image(1, "tongue", UploadFile(file=io.BytesIO(b"test")),
                                                   SimpleNamespace(user_id=1), db)
            except HTTPException as exc:
                return exc, job
            self.assertEqual(result.image_id, 123)
            dispatch.assert_called_once()
            return result, job

    def test_success_returns_job(self):
        result, job = self.upload()
        self.assertTrue(result.job_id)
        self.assertEqual(job.status, "pending")

    def test_dispatch_failure_returns_503_and_marks_job_failed(self):
        result, job = self.upload(RuntimeError("broker unavailable"))
        self.assertEqual(result.status_code, 503)
        self.assertEqual(job.status, "failed")
        self.assertIsNotNone(job.finish_time)


if __name__ == "__main__":
    unittest.main()
