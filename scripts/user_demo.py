#!/usr/bin/env python3
"""
Quick demo of the interactive user registration script.

This shows how to use the register_user.py script with sample inputs.
"""

print(
    """
🔐 AINarratives User Registration Scripts Demo
================================================

The following scripts are available for user management:

1. Interactive Registration (register_user.py):
   - Prompts for username, password, and admin status
   - Validates inputs and checks for duplicates
   - Secure password entry (hidden input)

2. Batch Registration (register_user_batch.py):
   - Command-line interface for programmatic user creation
   - Usage: python scripts/register_user_batch.py <username> <password> [--admin]

3. User Management (manage_users.py):
   - List, show, delete, and modify existing users
   - Change admin status and reset passwords
   - Usage: python scripts/manage_users.py <command> [args]

Examples:
---------

# Interactive registration
python scripts/register_user.py

# Batch registration
python scripts/register_user_batch.py doctor_smith mypassword123
python scripts/register_user_batch.py admin_user securepass --admin

# User management
python scripts/manage_users.py list
python scripts/manage_users.py show admin
python scripts/manage_users.py make-admin doctor_smith
python scripts/manage_users.py reset-password doctor_smith newpass123

All users can immediately login to the Streamlit application!
"""
)


def main():
    choice = input("Would you like to run the interactive registration now? (y/N): ").strip().lower()
    if choice in ["y", "yes"]:
        import subprocess
        import sys
        from pathlib import Path

        script_path = Path(__file__).parent / "register_user.py"
        subprocess.run([sys.executable, str(script_path)])
    else:
        print("👋 You can run any of the scripts above when ready!")


if __name__ == "__main__":
    main()
