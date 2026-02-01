"""
Migration script to wrap all existing evaluation_results.result_json content under an 'en' key.
"""

import logging

from sqlmodel import select

from pain_narratives.core.database import DatabaseManager
from pain_narratives.db.models_sqlmodel import EvaluationResult


def migrate_result_json_to_multilang():
    logging.basicConfig(level=logging.INFO)
    db_manager = DatabaseManager()
    with db_manager.get_session() as session:
        results = session.exec(select(EvaluationResult)).all()
        count = 0
        for result in results:
            if result.result_json is not None and (
                not isinstance(result.result_json, dict) or "en" not in result.result_json
            ):
                # Only migrate if not already migrated
                original = result.result_json
                result.result_json = {"en": original}
                session.add(result)
                count += 1
        session.commit()
    logging.info(f"Migration complete. Updated {count} records.")


if __name__ == "__main__":
    migrate_result_json_to_multilang()
