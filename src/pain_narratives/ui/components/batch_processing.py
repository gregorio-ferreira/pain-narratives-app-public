"""Batch processing component for running evaluations on multiple narratives."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import pandas as pd
import streamlit as st


def run_batch_evaluation(
    df: "pd.DataFrame",
    config: Dict[str, Any],
    delay: float,
    save_to_db: bool,
    openai_client: Any,
    db_manager: Any,
    prompt: str,
) -> tuple[list[dict[str, Any]], int, int]:
    """Run batch evaluation on DataFrame and return results."""
    # Add translator
    from pain_narratives.ui.utils.localization import get_translator

    t = get_translator(st.session_state.get("language", "en"))

    st.subheader(t("ui_text.batch_processing_progress"))
    progress_bar = st.progress(0)
    status_text = st.empty()
    batch_results = []
    success_count = 0
    error_count = 0
    for idx, (i, row) in enumerate(df.iterrows()):
        status_text.text(f"Processing narrative {idx + 1}/{len(df)}")
        try:
            formatted_prompt = prompt.format(narrative=row["narrative"])
            response = openai_client.create_completion(
                messages=[{"role": "user", "content": formatted_prompt}],
                model=config["model"],
                temperature=config["temperature"],
            )
            content = response["choices"][0]["message"]["content"]
            result = json.loads(content)
            batch_results.append(
                {
                    "id": row.get("id", i),
                    "category": row.get("category", "Unknown"),
                    "narrative": row["narrative"],
                    "evaluation": result,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            success_count += 1
            if save_to_db and db_manager:
                db_manager.save(
                    {
                        "narrative": row["narrative"],
                        "result": result,
                        "model": config["model"],
                        "temperature": config["temperature"],
                        "timestamp": datetime.now().isoformat(),
                    }
                )
        except Exception as e:
            error_count += 1
            batch_results.append(
                {
                    "id": row.get("id", i),
                    "category": row.get("category", "Unknown"),
                    "narrative": row["narrative"],
                    "evaluation": {"error": str(e)},
                    "timestamp": datetime.now().isoformat(),
                }
            )
        progress_bar.progress((idx + 1) / len(df))
        if delay > 0 and idx < len(df) - 1:
            time.sleep(delay)
    status_text.text("✅ Batch processing completed!")
    return batch_results, success_count, error_count


def process_batch(
    input_file: Path, output_file: Path, process_func: Any, batch_size: int = 10
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Process a batch of narratives from input_file using process_func and save results to output_file.
    Returns a tuple of (results, error_message).
    """
    try:
        df = pd.read_csv(input_file)
        results: List[Dict[str, Any]] = []
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i : i + batch_size]
            batch_results = process_func(batch)
            results.extend(batch_results)
        pd.DataFrame(results).to_csv(output_file, index=False)
        return results, None
    except Exception as e:
        return [], str(e)


def load_batch_results(output_file: Path) -> List[Dict[str, Any]]:
    """
    Load batch results from a CSV file and return as a list of dicts.
    """
    df = pd.read_csv(output_file)
    return cast(List[Dict[str, Any]], df.to_dict(orient="records"))
    return cast(List[Dict[str, Any]], df.to_dict(orient="records"))
