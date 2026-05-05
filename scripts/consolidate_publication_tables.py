#!/usr/bin/env python3
"""
Consolidate Publication CSV Files into Excel Workbook
======================================================

This script collects all relevant CSV files from the publication outputs
and consolidates them into a single Excel workbook with multiple sheets.

Usage:
    uv run python scripts/consolidate_publication_tables.py [--output OUTPUT_PATH]

Options:
    --output    Path for output Excel file (default: notebooks/outputs/publication/publication_tables.xlsx)

Created: 2025-12-01
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# Configuration: CSV files to include and their sheet names
# Format: (filename, sheet_name, description)
CSV_FILES_CONFIG = [
    # Sample characteristics and main results (from Notebook 04)
    ("table1_sample_characteristics.csv", "T1_Sample", 
     "Table 1: Sample characteristics - Overview of narratives processed (N=152), models used, and basic statistics"),
    ("table1_enhanced_sample_characteristics.csv", "T1_Enhanced", 
     "Table 1 Enhanced: Patient demographics including age, gender, education, employment, pain duration, and narrative word counts"),
    ("table2_dimension_results.csv", "T2_Dimensions", 
     "Table 2: LLM dimension evaluation - Mean scores (0-10) and SD for 7 pain dimensions across 152 narratives"),
    ("table3_questionnaire_results.csv", "T3_Questionnaires", 
     "Table 3: LLM questionnaire impersonation - PCS, BPI-IS, TSK-11SV synthetic scores with means and SDs"),
    ("table4_correlation_matrix.csv", "T4_Correlations", 
     "Table 4: Correlation matrix between LLM dimensions and questionnaire total scores"),
    
    # Expert feedback analysis (from Notebooks 07-08)
    ("table5_dimension_feedback.csv", "T5_DimFeedback", 
     "Table 5: Expert feedback on dimension evaluations - Agreement ratings (1-5) from 14 experts on 37 narratives"),
    ("table6_dimension_correlations.csv", "T6_DimCorr", 
     "Table 6: Correlations between LLM dimension scores and expert agreement ratings"),
    ("table7_questionnaire_feedback.csv", "T7_QuestFeedback", 
     "Table 7: Expert feedback on questionnaire impersonation - Agreement with LLM-generated questionnaire responses"),
    ("table8_questionnaire_correlations.csv", "T8_QuestCorr", 
     "Table 8: Correlations between LLM questionnaire scores and expert agreement"),
    
    # Usability and reliability (from Notebooks 09-10)
    ("table10_sus_results.csv", "T10_SUS", 
     "Table 10: System Usability Scale (SUS) results - Mean score 78.8 (SD=10.2), N=14 experts"),
    ("table_sus_item_statistics.csv", "T10_SUS_Items", 
     "Table 10 Supplement: SUS item-level statistics - Individual item means and SDs"),
    ("table11_reliability_comparison.csv", "T11_Reliability", 
     "Table 11: Internal consistency comparison - Cronbach's α for real patient vs LLM-synthetic questionnaire responses"),
    ("table12_real_synthetic_correlations.csv", "T12_RealSynth", 
     "Table 12: Correlation patterns between real patient questionnaire scores and LLM-synthetic scores"),
    ("table_12b_real_synthetic_agreement.csv", "T12b_Agreement", 
     "Table 12b: Narrative-level agreement - Direct correlations between matched patient questionnaire scores (N=152)"),
    
    # LLM vs Expert agreement (from Notebooks 13-14)
    ("table13_llm_internal_consistency.csv", "T13_LLMConsist", 
     "Table 13: LLM internal consistency - Test-retest reliability of dimension evaluations (Pearson r, ICC)"),
    ("table14_llm_expert_agreement.csv", "T14_LLMExpert", 
     "Table 14: LLM-Expert agreement - Correlation between LLM dimension scores and expert ratings"),
    
    # Detailed data exports - Questionnaire results (152 narratives)
    ("pcs_results.csv", "Data_PCS", 
     "PCS Data: Pain Catastrophizing Scale - LLM-generated 13-item responses (0-4) for each narrative, with total scores"),
    ("bpi_results.csv", "Data_BPI", 
     "BPI Data: Brief Pain Inventory Interference Scale - LLM-generated 11-item responses (0-10) for each narrative"),
    ("tsk_results.csv", "Data_TSK", 
     "TSK Data: Tampa Scale of Kinesiophobia - LLM-generated 11-item responses (1-4) for each narrative"),
    ("questionnaire_merged_results.csv", "Data_QuestMerged", 
     "Merged questionnaire data: All PCS, BPI-IS, TSK-11SV results combined with narrative IDs and total scores"),
    
    # Matching and correlation details (37 matched narratives)
    ("matched_narratives.csv", "Data_Matched", 
     "Matched narratives: 37 narratives evaluated by both LLM (batch) and experts, with dimension scores from both"),
    ("matched_synthetic_llm_dimension_data.csv", "Data_SynthLLMDim", 
     "Synthetic-LLM dimension data: Detailed dimension scores for 37 matched narratives"),
    ("llm_expert_agreement_data.csv", "Data_LLMExpert", 
     "LLM-Expert agreement data: Raw data for calculating agreement between LLM and expert evaluations"),
    
    # Detailed correlations
    ("detailed_correlations_llm_consistency.csv", "Corr_LLMConsist", 
     "Detailed LLM consistency correlations: Per-dimension Pearson r, Spearman ρ, and ICC values"),
    ("detailed_correlations_llm_expert.csv", "Corr_LLMExpert", 
     "Detailed LLM-expert correlations: Per-dimension agreement metrics between LLM and expert ratings"),
    
    # Cleaned real data
    ("real_questionnaire_data_cleaned.csv", "Data_RealQuest", 
     "Real patient questionnaire data: Actual PCS, BPI, TSK responses from 152 chronic pain patients"),
    
    # Summary and completeness reports
    ("master_summary_statistics.csv", "Summary_Stats", 
     "Master summary: Key statistics across all analyses - sample sizes, means, correlations, reliability metrics"),
    ("data_completeness_report.csv", "Data_Complete", 
     "Data completeness: Status of all publication tables (Tables 1-14) with source notebook references"),
    
    # Expert custom dimensions analysis (from Notebook 15)
    ("table_15a_custom_dimensions_catalog.csv", "T15a_DimCatalog", 
     "Table 15a: Expert custom dimensions catalog - All custom dimensions created by experts with definitions"),
    ("table_15b_custom_dimension_feedback_summary.csv", "T15b_DimFbSummary", 
     "Table 15b: Custom dimension feedback summary - Aggregated expert ratings for each custom dimension"),
    ("table_15c_custom_dimension_feedback_detail.csv", "T15c_DimFbDetail", 
     "Table 15c: Custom dimension feedback detail - Individual feedback records for custom dimensions"),
    ("table_15d_promising_custom_dimensions.csv", "T15d_Promising", 
     "Table 15d: Promising custom dimensions - Dimensions with positive expert reception (usage intent >= 5.0)"),
    ("table_15e_custom_dimensions_by_expert.csv", "T15e_ByExpert", 
     "Table 15e: Custom dimensions by expert - Summary of which experts created which custom dimensions"),
    ("table_15f_custom_dimensions_by_theme.csv", "T15f_ByTheme", 
     "Table 15f: Custom dimensions by theme - Clinical themes (psychological, social, functional, etc.)"),
]

# Additional data files from other locations (relative to project root)
ADDITIONAL_DATA_FILES = [
    ("data/excel_id_to_db_mapping.csv", "Map_ExcelToDB", 
     "ID Mapping: Links Excel row IDs from pain_narratives_20251126.xlsx to database narrative_hash values (152 rows)"),
    ("data/sus_responses.csv", "Data_SUS", 
     "SUS Raw Data: Individual expert responses (q1-q10) with calculated SUS scores - 14 experts, mean=78.8"),
]


def load_csv_safe(filepath: Path) -> Optional[pd.DataFrame]:
    """Load a CSV file with error handling."""
    try:
        df = pd.read_csv(filepath)
        return df
    except Exception as e:
        print(f"  ⚠️  Could not load {filepath.name}: {e}")
        return None


def create_index_sheet(included_files: list) -> pd.DataFrame:
    """Create an index sheet with information about all included sheets."""
    data = []
    for i, (filename, sheet_name, description, status) in enumerate(included_files, 1):
        data.append({
            "Index": i,
            "Sheet Name": sheet_name,
            "Source File": filename,
            "Description": description,
            "Status": status
        })
    
    df = pd.DataFrame(data)
    return df


def consolidate_csvs(
    output_dir: Path,
    output_file: Path,
    project_root: Path,
    verbose: bool = True
) -> bool:
    """
    Consolidate CSV files into a single Excel workbook.
    
    Parameters:
    -----------
    output_dir : Path
        Directory containing the CSV files
    output_file : Path
        Path for the output Excel file
    project_root : Path
        Project root directory for additional data files
    verbose : bool
        Whether to print progress messages
        
    Returns:
    --------
    bool : True if successful, False otherwise
    """
    if verbose:
        print("=" * 70)
        print("Consolidating Publication CSV Files to Excel")
        print("=" * 70)
        print(f"Source directory: {output_dir}")
        print(f"Output file: {output_file}")
        print()
    
    # Track which files were included
    included_files = []
    
    # Create Excel writer
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            sheets_created = 0
            
            # Process main publication files
            if verbose:
                print("Processing publication tables...")
            
            for filename, sheet_name, description in CSV_FILES_CONFIG:
                filepath = output_dir / filename
                
                if filepath.exists():
                    df = load_csv_safe(filepath)
                    if df is not None:
                        # Write to Excel (sheet names max 31 chars)
                        df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
                        sheets_created += 1
                        included_files.append((filename, sheet_name, description, "✓ Included"))
                        if verbose:
                            print(f"  ✓ {sheet_name}: {filename} ({len(df)} rows)")
                    else:
                        included_files.append((filename, sheet_name, description, "⚠️ Load error"))
                else:
                    included_files.append((filename, sheet_name, description, "— Not found"))
                    if verbose:
                        print(f"  — {sheet_name}: {filename} (not found)")
            
            # Process additional files from project root
            if verbose:
                print("\nProcessing additional data files...")
            
            for rel_path, sheet_name, description in ADDITIONAL_DATA_FILES:
                filepath = project_root / rel_path
                
                if filepath.exists():
                    df = load_csv_safe(filepath)
                    if df is not None:
                        df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
                        sheets_created += 1
                        included_files.append((rel_path, sheet_name, description, "✓ Included"))
                        if verbose:
                            print(f"  ✓ {sheet_name}: {Path(rel_path).name} ({len(df)} rows)")
                    else:
                        included_files.append((rel_path, sheet_name, description, "⚠️ Load error"))
                else:
                    included_files.append((rel_path, sheet_name, description, "— Not found"))
                    if verbose:
                        print(f"  — {sheet_name}: {Path(rel_path).name} (not found)")
            
            # Create index sheet as the first sheet
            if verbose:
                print("\nCreating index sheet...")
            
            index_df = create_index_sheet(included_files)
            
            # Add metadata to index
            metadata = pd.DataFrame([
                {"Index": "", "Sheet Name": "", "Source File": "", "Description": "", "Status": ""},
                {"Index": "", "Sheet Name": "Generated", "Source File": str(datetime.now()), 
                 "Description": "Publication tables consolidated", "Status": ""},
            ])
            index_df = pd.concat([index_df, metadata], ignore_index=True)
            
            index_df.to_excel(writer, sheet_name="_Index", index=False)
            
            # Move index sheet to first position
            workbook = writer.book
            # Get the index sheet and move it to the beginning
            index_sheet = workbook["_Index"]
            workbook.move_sheet(index_sheet, offset=-len(workbook.sheetnames)+1)
            
            if verbose:
                print(f"\n{'=' * 70}")
                print(f"✅ Excel workbook created successfully!")
                print(f"   Total sheets: {sheets_created + 1} (including index)")
                print(f"   Output: {output_file}")
                print(f"{'=' * 70}")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Error creating Excel file: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Consolidate publication CSV files into Excel workbook"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output Excel file path"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output"
    )
    
    args = parser.parse_args()
    
    # Determine paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    output_dir = project_root / "notebooks" / "outputs" / "publication"
    
    if args.output:
        output_file = Path(args.output)
    else:
        output_file = output_dir / "publication_tables.xlsx"
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if source directory exists
    if not output_dir.exists():
        print(f"❌ Source directory not found: {output_dir}")
        print("   Please run the analysis notebooks first to generate CSV files.")
        sys.exit(1)
    
    # Run consolidation
    success = consolidate_csvs(
        output_dir=output_dir,
        output_file=output_file,
        project_root=project_root,
        verbose=not args.quiet
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
