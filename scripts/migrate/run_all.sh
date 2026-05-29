#!/bin/bash
# Full ingestion of ai_narratives_original from scratch.
#
# Order:
#   1. apply alembic migrations (creates schema if needed)
#   2. ingest real-patient data from Data_real_sample.xlsx
#   3. ingest LLM synthetic data for all 3 models from pain_narratives_app
#   4. ingest expert feedback (dimension + questionnaire)
#   5. print final row counts per table

set -e
cd "$(dirname "$0")/../.."

echo "================================================================================"
echo "[$(date '+%F %T')] === ai_narratives_original full ingest ==="
echo "================================================================================"

echo ""
echo "--- Step 1: alembic upgrade head ---"
(cd src/pain_narratives/db && uv run alembic upgrade head)

echo ""
echo "--- Step 2: ingest_real_from_xlsx ---"
uv run python scripts/migrate/ingest_real_from_xlsx.py

echo ""
echo "--- Step 3: ingest_llm_from_db ---"
uv run python scripts/migrate/ingest_llm_from_db.py

echo ""
echo "--- Step 4: ingest_expert_feedback ---"
uv run python scripts/migrate/ingest_expert_feedback.py

echo ""
echo "--- Step 5: final row counts ---"
uv run python - <<'PY'
import sys
sys.path.insert(0, "src")
from sqlalchemy import text
from pain_narratives.core.database import DatabaseManager
SCHEMA = "ai_narratives_original"
db = DatabaseManager()
with db.engine.connect() as conn:
    for table in ("narratives",
                  "real_patient_demographics", "real_patient_pcs",
                  "real_patient_bpi", "real_patient_tsk",
                  "llm_dimension_evaluation", "llm_pcs_results",
                  "llm_bpi_results", "llm_tsk_results",
                  "expert_dimension_evaluation", "expert_questionnaire_feedback",
                  "sus_usability_results"):
        n = conn.execute(text(f"SELECT COUNT(*) FROM {SCHEMA}.{table}")).scalar()
        print(f"  {table:<32} {n}")
PY

echo ""
echo "[$(date '+%F %T')] === Done ==="
