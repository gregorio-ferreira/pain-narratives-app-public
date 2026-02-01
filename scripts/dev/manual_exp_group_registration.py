"""
Manual experiment group registration script for development/testing.
Usage: Run this script to insert a new experiment group into the database.
"""

from pain_narratives.core.database import get_database_manager

if __name__ == "__main__":
    db_manager = get_database_manager()
    description = "Manual group for Streamlit UI dev"
    system_role = "You are a medical expert evaluating pain narratives."
    base_prompt = "Please analyze the following narrative and provide structured scores."
    group_id = db_manager.register_new_experiments_group(description, system_role, base_prompt)
    print(f"Registered new experiment group with ID: {group_id}")
