#!/bin/bash
# ==============================================================================
# Run All Analysis Notebooks
# ==============================================================================
# This script executes all numbered analysis notebooks (01-14) in sequence.
# Each notebook is converted to a Python script and executed.
#
# Usage: ./scripts/run_all_notebooks.sh [--continue-on-error]
#
# Options:
#   --continue-on-error    Continue running remaining notebooks even if one fails
#
# Requirements:
#   - UV package manager
#   - nbconvert (pip install nbconvert)
#   - Jupyter kernel configured
#
# Created: 2025-12-01
# ==============================================================================

set -e  # Exit on error by default

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
CONTINUE_ON_ERROR=false
if [[ "$1" == "--continue-on-error" ]]; then
    CONTINUE_ON_ERROR=true
    set +e  # Don't exit on error
fi

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NOTEBOOKS_DIR="$PROJECT_ROOT/notebooks"
LOG_DIR="$PROJECT_ROOT/notebooks/outputs/logs"

# Create log directory
mkdir -p "$LOG_DIR"

# Timestamp for this run
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
MASTER_LOG="$LOG_DIR/notebook_run_$TIMESTAMP.log"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}Running Analysis Notebooks${NC}"
echo -e "${BLUE}============================================================${NC}"
echo -e "Project Root: $PROJECT_ROOT"
echo -e "Notebooks Dir: $NOTEBOOKS_DIR"
echo -e "Log File: $MASTER_LOG"
echo -e "Continue on Error: $CONTINUE_ON_ERROR"
echo ""

# Log start
echo "Notebook execution started at $(date)" > "$MASTER_LOG"
echo "============================================================" >> "$MASTER_LOG"

# List of notebooks to run in order (Software Impacts publication set)
NOTEBOOKS=(
    "01_pain_narratives_mapping_description_author_demographics.ipynb"
    "02_patient_demographics_for_publication.ipynb"
    "03_expert_feedback_for_publication.ipynb"
    "04_batch_repetitions_data.ipynb"
    "05_real_vs_synthetic.ipynb"
    "06_analyses_consolidation.ipynb"
)

# Counters
TOTAL=${#NOTEBOOKS[@]}
SUCCESS=0
FAILED=0
SKIPPED=0

# Function to run a single notebook
run_notebook() {
    local notebook="$1"
    local notebook_path="$NOTEBOOKS_DIR/$notebook"
    local notebook_name="${notebook%.ipynb}"
    local log_file="$LOG_DIR/${notebook_name}_$TIMESTAMP.log"
    
    echo -e "\n${YELLOW}────────────────────────────────────────────────────────────${NC}"
    echo -e "${YELLOW}Running: $notebook${NC}"
    echo -e "${YELLOW}────────────────────────────────────────────────────────────${NC}"
    
    # Check if notebook exists
    if [[ ! -f "$notebook_path" ]]; then
        echo -e "${RED}  ✗ Notebook not found: $notebook_path${NC}"
        echo "SKIPPED: $notebook (not found)" >> "$MASTER_LOG"
        ((SKIPPED++))
        return 1
    fi
    
    # Run notebook using jupyter nbconvert
    echo "  Starting at $(date +"%H:%M:%S")..."
    echo "" >> "$MASTER_LOG"
    echo "Running: $notebook at $(date)" >> "$MASTER_LOG"
    
    cd "$NOTEBOOKS_DIR"
    
    # Execute notebook and capture output
    if uv run jupyter nbconvert --to notebook --execute --inplace \
        --ExecutePreprocessor.timeout=600 \
        --ExecutePreprocessor.kernel_name=python3 \
        "$notebook" >> "$log_file" 2>&1; then
        
        echo -e "${GREEN}  ✓ Completed successfully${NC}"
        echo "  SUCCESS: $notebook" >> "$MASTER_LOG"
        ((SUCCESS++))
        return 0
    else
        echo -e "${RED}  ✗ Failed (see log: $log_file)${NC}"
        echo "  FAILED: $notebook" >> "$MASTER_LOG"
        ((FAILED++))
        return 1
    fi
}

# Main execution loop
echo -e "\n${BLUE}Starting execution of $TOTAL notebooks...${NC}\n"

for notebook in "${NOTEBOOKS[@]}"; do
    if ! run_notebook "$notebook"; then
        if [[ "$CONTINUE_ON_ERROR" == "false" ]]; then
            echo -e "\n${RED}Stopping due to error. Use --continue-on-error to continue.${NC}"
            break
        fi
    fi
done

# Summary
echo -e "\n${BLUE}============================================================${NC}"
echo -e "${BLUE}Execution Summary${NC}"
echo -e "${BLUE}============================================================${NC}"
echo -e "Total notebooks: $TOTAL"
echo -e "${GREEN}Successful: $SUCCESS${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo -e "${YELLOW}Skipped: $SKIPPED${NC}"
echo -e "\nLog file: $MASTER_LOG"
echo -e "Individual logs: $LOG_DIR/"

# Log summary
echo "" >> "$MASTER_LOG"
echo "============================================================" >> "$MASTER_LOG"
echo "Execution completed at $(date)" >> "$MASTER_LOG"
echo "Total: $TOTAL, Success: $SUCCESS, Failed: $FAILED, Skipped: $SKIPPED" >> "$MASTER_LOG"

# Exit with appropriate code
if [[ $FAILED -gt 0 ]]; then
    exit 1
else
    exit 0
fi
