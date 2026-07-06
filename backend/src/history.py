from __future__ import annotations

import json

from .database import get_connection
from .models import AnalysisSession, Diagnosis, VisionExtractionResult


def save_session(session: AnalysisSession) -> AnalysisSession:
    user_id = session.metadata.get("user_id") if isinstance(session.metadata, dict) else None
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO analysis_sessions
            (id, user_id, created_at, image_filename, extraction_json, diagnoses_json, report, metadata_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                user_id = EXCLUDED.user_id,
                created_at = EXCLUDED.created_at,
                image_filename = EXCLUDED.image_filename,
                extraction_json = EXCLUDED.extraction_json,
                diagnoses_json = EXCLUDED.diagnoses_json,
                report = EXCLUDED.report,
                metadata_json = EXCLUDED.metadata_json
            """,
            (
                session.id,
                user_id,
                session.created_at,
                session.image_filename,
                session.extraction.model_dump_json(),
                json.dumps([diagnosis.model_dump() for diagnosis in session.diagnoses], ensure_ascii=False),
                session.report,
                json.dumps(session.metadata, ensure_ascii=False),
            ),
        )
        conn.commit()
    return session


def _row_to_session(row) -> AnalysisSession:
    metadata = json.loads(row["metadata_json"])
    if row.get("user_id") and "user_id" not in metadata:
        metadata["user_id"] = row["user_id"]
    return AnalysisSession(
        id=row["id"],
        created_at=row["created_at"],
        image_filename=row["image_filename"],
        extraction=VisionExtractionResult.model_validate_json(row["extraction_json"]),
        diagnoses=[Diagnosis.model_validate(item) for item in json.loads(row["diagnoses_json"])],
        report=row["report"],
        metadata=metadata,
    )


def list_sessions(limit: int = 20) -> list[AnalysisSession]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM analysis_sessions ORDER BY created_at DESC LIMIT %s",
            (limit,),
        ).fetchall()
    return [_row_to_session(row) for row in rows]


def get_session(session_id: str) -> AnalysisSession | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM analysis_sessions WHERE id = %s", (session_id,)).fetchone()
    return _row_to_session(row) if row else None