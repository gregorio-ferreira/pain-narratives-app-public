"""Utilities for data handling in Streamlit app."""

import io
import json
from datetime import datetime
from typing import Any, Dict, List, Tuple, cast

import pandas as pd
import streamlit as st


def validate_csv_structure(df: "pd.DataFrame") -> Tuple[bool, List[str]]:
    """Validate CSV structure for batch evaluation.

    Args:
        df: DataFrame to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check required columns
    required_columns = ["narrative"]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")

    # Check for empty narratives
    if "narrative" in df.columns:
        empty_narratives = df["narrative"].isna().sum()
        if empty_narratives > 0:
            errors.append(f"{empty_narratives} empty narratives found")

        # Check narrative length
        very_short = (df["narrative"].str.len() < 10).sum()
        if very_short > 0:
            errors.append(f"{very_short} narratives are very short (<10 characters)")

        very_long = (df["narrative"].str.len() > 5000).sum()
        if very_long > 0:
            errors.append(f"{very_long} narratives are very long (>5000 characters)")

    # Check ID column if present
    if "id" in df.columns:
        duplicate_ids = df["id"].duplicated().sum()
        if duplicate_ids > 0:
            errors.append(f"{duplicate_ids} duplicate IDs found")

    return len(errors) == 0, errors


def prepare_batch_data(df: "pd.DataFrame") -> "pd.DataFrame":
    """Prepare batch data for evaluation.

    Args:
        df: Raw DataFrame

    Returns:
        Prepared DataFrame
    """
    df_clean = df.copy()

    # Add ID column if missing
    if "id" not in df_clean.columns:
        df_clean["id"] = range(1, len(df_clean) + 1)

    # Add category column if missing
    if "category" not in df_clean.columns:
        df_clean["category"] = "Unknown"

    # Clean narrative text
    if "narrative" in df_clean.columns:
        df_clean["narrative"] = df_clean["narrative"].astype(str)
        df_clean["narrative"] = df_clean["narrative"].str.strip()

        # Remove very short narratives
        df_clean = df_clean[df_clean["narrative"].str.len() >= 10]

    return df_clean


def export_results_to_csv(results: List[Dict[str, Any]]) -> str:
    """Export evaluation results to CSV format.

    Args:
        results: List of evaluation results

    Returns:
        CSV string
    """
    data = []

    for result in results:
        row = {
            "id": result.get("id", ""),
            "category": result.get("category", ""),
            "narrative_length": len(result.get("narrative", "")),
            "has_error": "error" in result.get("evaluation", {}),
        }

        # Add evaluation scores
        if "evaluation" in result and "error" not in result["evaluation"]:
            eval_result = result["evaluation"]
            for key, value in eval_result.items():
                if isinstance(value, (int, float)):
                    row[f"score_{key}"] = value
                elif key == "reasoning":
                    row["reasoning"] = value
                elif isinstance(value, list):
                    row[f"list_{key}"] = "; ".join(map(str, value))
        else:
            row["error"] = result.get("evaluation", {}).get("error", "")

        data.append(row)

    df = pd.DataFrame(data)
    return cast(str, df.to_csv(index=False))


def create_sample_csv() -> str:
    """Create a sample CSV for download."""
    sample_data = {
        "id": [1, 2, 3],
        "narrative": [
            (
                "I've been experiencing chronic pain in my lower back for the past 6 months. "
                "The pain is constant and affects my daily activities."
            ),
            (
                "The fibromyalgia pain is all over my body. Some days are better than others, "
                "but the fatigue is always there."
            ),
            (
                "My migraines have been getting worse. The pain is intense and comes with "
                "sensitivity to light and sound."
            ),
        ],
        "category": ["Back Pain", "Fibromyalgia", "Migraine"],
    }

    df = pd.DataFrame(sample_data)
    return cast(str, df.to_csv(index=False))


@st.cache_data
def load_narrative_examples() -> Dict[str, List[str]]:
    """Load example narratives by category."""
    return {
        "Fibromyalgia": [
            (
                "The pain is everywhere today. My joints ache, my muscles feel bruised, and even light touches hurt. "
                "I couldn't sleep last night because of the pain."
            ),
            (
                "I've been dealing with fibromyalgia for 3 years now. The worst part is the unpredictability - "
                "some days I feel almost normal, others I can barely get out of bed."
            ),
            (
                "The tender points are so sensitive today. Even wearing clothes feels uncomfortable. "
                "The fatigue makes everything worse."
            ),
        ],
        "Back Pain": [
            (
                "My lower back has been killing me for weeks. The pain shoots down my leg when I sit too long "
                "or try to bend over."
            ),
            (
                "I herniated a disc 6 months ago and I'm still not back to normal. The pain is constant and "
                "affects my work and sleep."
            ),
            (
                "The back pain started gradually but now it's severe. I can't lift anything or stand for "
                "long periods."
            ),
        ],
        "Migraine": [
            (
                "The migraine started with visual aura and now the pain is throbbing behind my right eye. "
                "Light and sound make it unbearable."
            ),
            (
                "I've had migraines for years but they're getting more frequent. The pain is so intense "
                "I have to miss work regularly."
            ),
            (
                "This migraine has lasted for 3 days. The pain is accompanied by nausea and I can't "
                "function normally."
            ),
        ],
        "Arthritis": [
            ("My arthritis pain is worse in the mornings. My hands are so stiff I can barely make a fist " "or write."),
            (
                "The joint pain from arthritis affects my knees and hips the most. Walking upstairs is "
                "becoming increasingly difficult."
            ),
            (
                "Rainy weather makes my arthritis flare up. The pain and stiffness in my joints is almost "
                "unbearable on those days."
            ),
        ],
    }


def format_evaluation_for_display(evaluation: Dict[str, Any]) -> Dict[str, Any]:
    """Format evaluation result for better display.

    Args:
        evaluation: Raw evaluation result

    Returns:
        Formatted evaluation
    """
    formatted = evaluation.copy()  # Format timestamp
    if "timestamp" in formatted:
        try:
            dt = datetime.fromisoformat(formatted["timestamp"])
            formatted["formatted_timestamp"] = dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            formatted["formatted_timestamp"] = formatted["timestamp"]

    # Format scores for display
    if "result" in formatted and isinstance(formatted["result"], dict):
        result = formatted["result"]
        formatted["score_summary"] = {}

        scores = []
        for key, value in result.items():
            if key != "reasoning" and isinstance(value, (int, float)):
                formatted["score_summary"][key.replace("_", " ").title()] = f"{value}/10"
                scores.append(value)

        if scores:
            formatted["average_score"] = sum(scores) / len(scores)
            formatted["formatted_average"] = f"{formatted['average_score']:.1f}/10"

    return formatted


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe download.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    import re

    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)

    # Limit length
    if len(sanitized) > 100:
        name, ext = sanitized.rsplit(".", 1) if "." in sanitized else (sanitized, "")
        sanitized = name[:95] + ("." + ext if ext else "")

    return sanitized


def compress_results(results: List[Dict[str, Any]]) -> bytes:
    """Compress results for download.

    Args:
        results: List of results to compress

    Returns:
        Compressed data as bytes
    """
    import zipfile

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Add CSV results
        csv_data = export_results_to_csv(results)
        zip_file.writestr("evaluation_results.csv", csv_data)

        # Add JSON results for full data
        json_data = json.dumps(results, indent=2, default=str)
        zip_file.writestr("evaluation_results.json", json_data)

        # Add summary report
        summary = generate_summary_report(results)
        zip_file.writestr("summary_report.txt", summary)

    buffer.seek(0)
    return buffer.getvalue()


def generate_summary_report(results: List[Dict[str, Any]]) -> str:
    """Generate a text summary report.

    Args:
        results: List of evaluation results

    Returns:
        Summary report as string
    """
    report = []
    report.append("EVALUATION SUMMARY REPORT")
    report.append("=" * 40)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")

    # Basic statistics
    total = len(results)
    successful = len([r for r in results if "error" not in r.get("evaluation", {})])
    error_rate = (total - successful) / total * 100 if total > 0 else 0

    report.append("BASIC STATISTICS")
    report.append("-" * 20)
    report.append(f"Total Evaluations: {total}")
    report.append(f"Successful: {successful}")
    report.append(f"Errors: {total - successful}")
    report.append(f"Error Rate: {error_rate:.1f}%")
    report.append("")

    # Score analysis
    if successful > 0:
        scores_data = []
        for result in results:
            if "error" not in result.get("evaluation", {}):
                eval_result = result["evaluation"]
                for key, value in eval_result.items():
                    if key != "reasoning" and isinstance(value, (int, float)):
                        scores_data.append({"dimension": key, "score": value})

        if scores_data:
            scores_df = pd.DataFrame(scores_data)

            report.append("SCORE ANALYSIS")
            report.append("-" * 20)

            for dimension in scores_df["dimension"].unique():
                dim_scores = scores_df[scores_df["dimension"] == dimension]["score"]
                report.append(f"{dimension.replace('_', ' ').title()}:")
                report.append(f"  Mean: {dim_scores.mean():.2f}")
                report.append(f"  Std:  {dim_scores.std():.2f}")
                report.append(f"  Min:  {dim_scores.min():.2f}")
                report.append(f"  Max:  {dim_scores.max():.2f}")
                report.append("")

    # Category analysis if available
    categories = [r.get("category", "Unknown") for r in results]
    if len(set(categories)) > 1:
        report.append("CATEGORY DISTRIBUTION")
        report.append("-" * 20)
        cat_counts = pd.Series(categories).value_counts()
        for cat, count in cat_counts.items():
            report.append(f"{cat}: {count} ({count / total * 100:.1f}%)")
        report.append("")

    return "\n".join(report)


class DataValidator:
    """Validator for data quality checks."""

    @staticmethod
    def check_narrative_quality(narrative: str) -> Dict[str, Any]:
        """Check quality of a single narrative.

        Args:
            narrative: Narrative text to check

        Returns:
            Quality assessment dictionary
        """
        issues = []
        warnings = []

        # Length checks
        if len(narrative) < 20:
            issues.append("Narrative is very short")
        elif len(narrative) < 50:
            warnings.append("Narrative is quite short")

        if len(narrative) > 3000:
            warnings.append("Narrative is very long")

        # Content checks
        if not any(word in narrative.lower() for word in ["pain", "hurt", "ache", "sore"]):
            warnings.append("No clear pain descriptors found")

        # Readability
        sentences = narrative.count(".") + narrative.count("!") + narrative.count("?")
        if sentences == 0:
            warnings.append("No sentence structure detected")

        # Language quality
        words = narrative.split()
        if len(words) < 10:
            issues.append("Very few words in narrative")

        return {
            "length": len(narrative),
            "word_count": len(words),
            "sentence_count": sentences,
            "issues": issues,
            "warnings": warnings,
            "quality_score": max(0, 10 - len(issues) * 3 - len(warnings)),
        }

    @staticmethod
    def batch_quality_check(df: pd.DataFrame) -> pd.DataFrame:
        """Run quality checks on a batch of narratives.

        Args:
            df: DataFrame with narratives

        Returns:
            DataFrame with quality metrics added
        """
        quality_results = []

        for idx, row in df.iterrows():
            if "narrative" in row:
                quality = DataValidator.check_narrative_quality(row["narrative"])
                quality_results.append(quality)
            else:
                quality_results.append({"quality_score": 0, "issues": ["No narrative found"]})

        quality_df = pd.DataFrame(quality_results)
        return pd.concat([df, quality_df], axis=1)
