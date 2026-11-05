"""Additive migration; never resets existing patient data."""
from sqlalchemy import text
from app.core.database import engine
from app.models.entities import ClinicalEncounter, ClinicalMessage, ReportReview


def main():
    with engine.connect() as connection:
        if connection.execute(text("SELECT GET_LOCK('tcm_clinical_migrate', 60)")).scalar() != 1:
            raise RuntimeError("Could not acquire clinical migration lock")
        try:
            ClinicalEncounter.__table__.create(connection, checkfirst=True)
            ClinicalMessage.__table__.create(connection, checkfirst=True)
            ReportReview.__table__.create(connection, checkfirst=True)
            connection.commit()
        finally:
            connection.execute(text("SELECT RELEASE_LOCK('tcm_clinical_migrate')"))
    print("Clinical migration complete")


if __name__ == "__main__":
    main()
