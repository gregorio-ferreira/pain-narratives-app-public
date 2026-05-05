#!/usr/bin/env python3
"""
Script     Args:
        file_path: Path to Excel file
        sheet_name: Name of the sheet to read
        column_name: Name of the column containing text
        model: Model name for tokenizer (default: gpt-5)unt tokens in files or Excel data using tiktoken.

Usage:
    # For text files:
    python scripts/tokens_count.py <file_path> [--model MODEL_NAME]

    # For Excel files:
    python scripts/tokens_count.py <excel_path> --excel --sheet SHEET_NAME --column COLUMN_NAME [--model MODEL_NAME]

Examples:
    python scripts/tokens_count.py docs/strategy.md
    python scripts/tokens_count.py data/pain_narratives_core_data.xlsx --excel --sheet data --column Narrative
    uv run python scripts/tokens_count.py \
        data/pain_narratives_core_data.xlsx \
        --excel --sheet data --column Narrative --model gpt-4
"""

import argparse
import statistics
import sys
from pathlib import Path

import pandas as pd
import tiktoken


def count_tokens_per_row(
    file_path: Path, sheet_name: str, column_name: str, model: str = "gpt-5"
) -> None:
    """
    Count tokens for each text entry in an Excel column.

    Args:
        file_path: Path to file to count tokens in
        model: Model name for tokenizer (default: gpt-5)

    Returns:
        Tuple of (list of token counts, original text series)
    """
    try:
        # Get the encoding for the specified model
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base encoding (used by gpt-4, gpt-3.5-turbo)
        print(f"⚠️  Model '{model}' not found, using cl100k_base encoding")
        encoding = tiktoken.get_encoding("cl100k_base")

    # Read the Excel file
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
    except Exception as e:
        raise ValueError(f"Error reading Excel file: {e}")

    # Check if column exists
    if column_name not in df.columns:
        available_columns = list(df.columns)
        raise ValueError(f"Column '{column_name}' not found. Available columns: {available_columns}")

    # Get the text column and drop any NaN values
    text_series = df[column_name].dropna()

    if text_series.empty:
        raise ValueError(f"No valid text data found in column '{column_name}'")

    # Count tokens for each text entry
    token_counts = []
    for text in text_series:
        # Convert to string if not already
        text_str = str(text)
        tokens = encoding.encode(text_str)
        token_counts.append(len(tokens))

    return token_counts, text_series


def analyze_token_counts(token_counts: list[int]) -> dict:
    """
    Analyze token count statistics.

    Args:
        token_counts: List of token counts

    Returns:
        Dictionary with statistical measures
    """
    if not token_counts:
        return {}

    return {
        "minimum": min(token_counts),
        "maximum": max(token_counts),
        "mean": statistics.mean(token_counts),
        "median": statistics.median(token_counts),
        "total": sum(token_counts),
        "count": len(token_counts),
    }


def count_tokens(file_path: Path, model: str = "gpt-5") -> tuple[int, str]:
    """
    Count tokens in a file using tiktoken.

    Args:
        file_path: Path to the file to analyze
        model: Model name for tokenizer (default: gpt-4)

    Returns:
        Tuple of (token_count, file_content)
    """
    try:
        # Get the encoding for the specified model
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base encoding (used by gpt-4, gpt-3.5-turbo)
        print(f"⚠️  Model '{model}' not found, using cl100k_base encoding")
        encoding = tiktoken.get_encoding("cl100k_base")

    # Read the file content
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        # Try with different encoding if UTF-8 fails
        with open(file_path, "r", encoding="latin-1") as f:
            content = f.read()

    # Count tokens
    tokens = encoding.encode(content)
    token_count = len(tokens)

    return token_count, content


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def main():
    parser = argparse.ArgumentParser(
        description="Count tokens in files or Excel data using tiktoken",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s docs/strategy.md
  %(prog)s src/agents/utils.py --model gpt-4
  %(prog)s data/pain_narratives_core_data.xlsx --excel --sheet data --column Narrative
  %(prog)s data/pain_narratives_core_data.xlsx --excel --sheet data --column Narrative --model gpt-3.5-turbo
        """,
    )

    parser.add_argument("file_path", type=Path, help="Path to the file to analyze (text file or Excel file)")

    parser.add_argument("--model", type=str, default="gpt-5", help="Model name for tokenizer (default: gpt-5)")

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show additional details like file size and content preview"
    )

    # Excel-specific arguments
    parser.add_argument("--excel", action="store_true", help="Treat input file as Excel file")

    parser.add_argument("--sheet", type=str, default="data", help="Sheet name for Excel files (default: data)")

    parser.add_argument(
        "--column", type=str, default="Narrative", help="Column name for Excel files (default: Narrative)"
    )

    args = parser.parse_args()

    # Check if file exists
    if not args.file_path.exists():
        print(f"❌ Error: File '{args.file_path}' does not exist")
        sys.exit(1)

    if not args.file_path.is_file():
        print(f"❌ Error: '{args.file_path}' is not a file")
        sys.exit(1)

    try:
        if args.excel:
            # Handle Excel file
            print(f"📊 Processing Excel file: {args.file_path}")
            print(f"📋 Sheet: {args.sheet}")
            print(f"📝 Column: {args.column}")
            print(f"🤖 Model: {args.model}")
            print()

            token_counts, text_series = count_tokens_in_excel(args.file_path, args.sheet, args.column, args.model)

            # Calculate statistics
            stats = analyze_token_counts(token_counts)

            # Display results
            print(f"📄 Total entries processed: {stats['count']:,}")
            print(f"🔢 Total tokens: {stats['total']:,}")
            print()
            print("📊 Token Count Statistics:")
            print(f"   Minimum: {stats['minimum']:,} tokens")
            print(f"   Maximum: {stats['maximum']:,} tokens")
            print(f"   Mean: {stats['mean']:.1f} tokens")
            print(f"   Median: {stats['median']:.1f} tokens")

            if args.verbose:
                print("\n📋 Sample entries with token counts:")
                # Show first 5 entries with their token counts
                for i in range(min(5, len(text_series))):
                    text = str(text_series.iloc[i])
                    preview = text[:100] + "..." if len(text) > 100 else text
                    print(f"   Entry {i+1}: {token_counts[i]:,} tokens")
                    print(f'      "{preview}"')
                    print()

                if len(text_series) > 5:
                    print(f"   ... and {len(text_series) - 5} more entries")

            # Cost estimation for popular models (approximate rates)
            cost_per_1k_tokens = {
                "gpt-5": 0.03,
                "gpt-5-mini": 0.01,
                "gpt-5-nano": 0.005,
                "gpt-3.5-turbo": 0.0015,
                "text-davinci-003": 0.02,
            }

            if args.model in cost_per_1k_tokens:
                cost = (stats["total"] / 1000) * cost_per_1k_tokens[args.model]
                print(f"\n💰 Estimated total cost: ${cost:.4f} (input tokens only)")
                avg_cost = cost / stats["count"]
                print(f"💰 Estimated cost per entry: ${avg_cost:.6f}")

        else:
            # Handle regular text file (original functionality)
            token_count, content = count_tokens(args.file_path, args.model)

            # Get file stats
            file_size = args.file_path.stat().st_size
            line_count = len(content.splitlines())
            char_count = len(content)

            # Display results
            print(f"📄 File: {args.file_path}")
            print(f"🤖 Model: {args.model}")
            print(f"🔢 Tokens: {token_count:,}")

            if args.verbose:
                print(f"📏 File size: {format_file_size(file_size)}")
                print(f"📝 Lines: {line_count:,}")
                print(f"🔤 Characters: {char_count:,}")
                print(f"📊 Tokens per line: {token_count/max(line_count, 1):.1f}")
                print(f"📊 Characters per token: {char_count/max(token_count, 1):.1f}")

                # Show content preview
                preview_lines = content.splitlines()[:5]
                if preview_lines:
                    print("\n📋 Content preview:")
                    for i, line in enumerate(preview_lines, 1):
                        print(f"  {i}: {line[:80]}{'...' if len(line) > 80 else ''}")
                    if len(content.splitlines()) > 5:
                        print(f"  ... ({len(content.splitlines()) - 5} more lines)")

            # Cost estimation for popular models (approximate rates)
            cost_per_1k_tokens = {
                "gpt-5": 0.03,
                "gpt-5-mini": 0.01,
                "gpt-5-nano": 0.005,
                "gpt-3.5-turbo": 0.0015,
                "text-davinci-003": 0.02,
            }

            if args.model in cost_per_1k_tokens:
                cost = (token_count / 1000) * cost_per_1k_tokens[args.model]
                print(f"💰 Estimated cost: ${cost:.4f} (input tokens only)")

    except (FileNotFoundError, PermissionError, UnicodeDecodeError, ValueError) as e:
        print(f"❌ Error processing file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
