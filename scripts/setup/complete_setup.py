#!/usr/bin/env python3
"""
Complete setup script for AINarratives application.

This script:
1. Runs database migrations
2. Initializes the database with default data
3. Provides instructions for running the app
"""

import os
import subprocess
from pathlib import Path


def run_uv_command(command: str, description: str) -> bool:
    """Run a UV command and return success status."""
    print(f"📋 {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True, cwd=project_root)
        if result.stdout:
            print(f"✅ {description} completed successfully")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"   Error: {e.stderr}")
        return False


def main():
    """Main setup function."""
    print("🏥 AINarratives Application Setup")
    print("=" * 50)

    # Set project root as global variable
    global project_root
    project_root = Path(__file__).parent.parent.parent
    print(f"📁 Working directory: {project_root}")

    # Change to project root
    os.chdir(project_root)

    # Step 0: Check UV environment
    print("\n0. Checking UV environment...")
    if not run_uv_command("uv --version", "UV version check"):
        print("   Please install UV first: https://docs.astral.sh/uv/getting-started/installation/")
        return False

    # Step 1: Run Alembic migrations
    print("\n1. Running database migrations...")
    if not run_uv_command("uv run alembic upgrade head", "Database migration"):
        print("   Make sure PostgreSQL is running and your database configuration is correct.")
        return False

    # Step 2: Initialize database with default data
    print("\n2. Initializing database with default data...")
    if not run_uv_command("uv run python scripts/setup/init_database_with_auth.py", "Database initialization"):
        return False

    # Step 3: Success message and instructions
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Run the Streamlit app:")
    print("   uv run streamlit run scripts/run_app.py")
    print("\n2. Or use the console script:")
    print("   uv run pain-narratives-app")
    print("\n3. Login with default credentials:")
    print("   Username: admin")
    print("   Password: admin123")
    print("\n4. Configure your OpenAI API key in the sidebar")
    print("\nEnjoy using the AINarratives Evaluation Platform! 🚀")


if __name__ == "__main__":
    main()
