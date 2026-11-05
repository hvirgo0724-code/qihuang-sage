"""Explicit, repeatable migration; never run DDL from request handlers."""
from pathlib import Path
from sqlalchemy import text
from app.core.memory import memory_engine

if __name__ == "__main__":
    with memory_engine().begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(70416001)"))
        conn.exec_driver_sql((Path(__file__).resolve().parents[2] / "migrations/001_agent_memory.sql").read_text())
