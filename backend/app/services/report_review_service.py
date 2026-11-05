"""Only a doctor's immutable confirmed snapshot may be delivered to a patient."""
from app.models.entities import ReportReview, ClinicalEncounter


def patient_result(db, analysis):
    review = db.get(ReportReview, analysis.analysis_id)
    if review and review.status == "confirmed":
        return {**review.report, "analysis_id": analysis.analysis_id,
                "review_status": "confirmed", "confirmed_by": review.confirmed_by,
                "confirmed_at": review.confirmed_at.isoformat() if review.confirmed_at else None}
    encounter = db.get(ClinicalEncounter, analysis.session_id)
    assigned = encounter is not None and encounter.status != "cancelled"
    return {"analysis_id": analysis.analysis_id, "review_status": "pending",
            "message": "辨证分析已完成，正在等待医生确认。医生修改并确认后，您即可查看正式报告。" if assigned else
                       "辨证分析已完成，报告待医生确认。请先选择并授权医生审核，确认后即可查看正式报告。"}
