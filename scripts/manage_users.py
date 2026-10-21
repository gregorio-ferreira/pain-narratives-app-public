#!/usr/bin/env python3
"""
User management script for pain narratives application.

This script provides user management capabilities:
- List all users
- Show user details
- Delete users
- Change user admin status
- Reset user passwords

Usage:
    python manage_users.py list
    python manage_users.py show <username>
    python manage_users.py delete <username>
    python manage_users.py make-admin <username>
    python manage_users.py remove-admin <username>
    python manage_users.py reset-password <username>
    python manage_users.py import-csv <csv_path>
"""

import argparse
import csv
import getpass
import os
import re
import secrets
import string
import sys
from typing import Dict, List, Optional

from sqlmodel import select

from pain_narratives.core.database import DatabaseManager
from pain_narratives.core.security import MIN_PASSWORD_LENGTH
from pain_narratives.db.models_sqlmodel import User


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Manage users in the Pain Narratives application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  list                     List all users
  show <username>          Show details for a specific user
  delete <username>        Delete a user
  make-admin <username>    Grant admin privileges to a user
  remove-admin <username>  Remove admin privileges from a user
  reset-password <username>  Reset user password

Examples:
  %(prog)s list
  %(prog)s show doctor_smith
  %(prog)s delete old_user
  %(prog)s make-admin researcher01
  %(prog)s reset-password doctor_smith
        """,
    )

    parser.add_argument(
        "command",
        choices=[
            "list",
            "show",
            "delete",
            "make-admin",
            "remove-admin",
            "reset-password",
            "import-csv",
        ],
        help="Command to execute",
    )

    parser.add_argument("username", nargs="?", help="Username (required for commands except 'list' and 'import-csv')")

    parser.add_argument(
        "--password-stdin", action="store_true", help="Read a password from standard input for automation"
    )

    parser.add_argument("csv_path", nargs="?", help="Path to CSV file (required for 'import-csv' command)")

    args = parser.parse_args()
    args.password = None
    if args.command == "reset-password":
        args.password = sys.stdin.readline().rstrip("\n") if args.password_stdin else getpass.getpass("New password: ")
    return args


def validate_command_args(args: argparse.Namespace) -> None:
    """Validate command arguments."""
    if args.command not in ("list", "import-csv") and not args.username:
        print(f"❌ Username is required for '{args.command}' command")
        sys.exit(1)

    if args.command == "reset-password" and not args.password:
        print("❌ Password is required for 'reset-password' command")
        sys.exit(1)

    if args.command == "import-csv" and not args.csv_path:
        print("❌ CSV path is required for 'import-csv' command")
        sys.exit(1)


def get_user_by_username(db_manager: DatabaseManager, username: str) -> Optional[User]:
    """Get user by username."""
    with db_manager.get_session() as session:
        return session.exec(select(User).where(User.username == username)).first()


def list_users(db_manager: DatabaseManager) -> None:
    """List all users."""
    with db_manager.get_session() as session:
        users = list(session.exec(select(User)))

        if not users:
            print("No users found.")
            return

        print("\n👥 All Users:")
        print("=" * 60)
        print(f"{'ID':<5} {'Username':<20} {'Admin':<8} {'Experiments':<12}")
        print("-" * 60)

        for user in users:
            # Get experiment count within the session
            from pain_narratives.db.models_sqlmodel import ExperimentGroup

            exp_count = len(list(session.exec(select(ExperimentGroup).where(ExperimentGroup.owner_id == user.id))))
            admin_status = "Yes" if user.is_admin else "No"
            print(f"{user.id:<5} {user.username:<20} {admin_status:<8} {exp_count:<12}")


def show_user(db_manager: DatabaseManager, username: str) -> None:
    """Show detailed user information."""
    with db_manager.get_session() as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            print(f"❌ User '{username}' not found.")
            return

        from pain_narratives.db.models_sqlmodel import ExperimentGroup, UserPrompt

        # Get counts within the session
        exp_groups = list(session.exec(select(ExperimentGroup).where(ExperimentGroup.owner_id == user.id)))
        user_prompts = list(session.exec(select(UserPrompt).where(UserPrompt.user_id == user.id)))

        print(f"\n👤 User Details: {username}")
        print("=" * 40)
        print(f"User ID: {user.id}")
        print(f"Username: {user.username}")
        print(f"Admin: {'Yes' if user.is_admin else 'No'}")
        print(f"Experiment Groups: {len(exp_groups)}")
        print(f"User Prompts: {len(user_prompts)}")

        if exp_groups:
            print("\nExperiment Groups:")
            for group in exp_groups:
                status = "✅ Complete" if group.concluded else "🔄 Active"
                desc = group.description[:50] if group.description else "No description"
                print(f"  - ID {group.experiments_group_id}: {desc}... ({status})")


def delete_user(db_manager: DatabaseManager, username: str) -> None:
    """Delete a user."""
    with db_manager.get_session() as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            print(f"❌ User '{username}' not found.")
            return

        from pain_narratives.db.models_sqlmodel import ExperimentGroup

        # Check if user has experiment groups
        exp_groups = list(session.exec(select(ExperimentGroup).where(ExperimentGroup.owner_id == user.id)))
        if exp_groups:
            print(f"⚠️  Warning: User '{username}' has {len(exp_groups)} experiment group(s).")
            print("Deleting this user will also delete all their experiment groups and data.")
            confirm = input("Are you sure you want to continue? (yes/no): ").strip().lower()
            if confirm != "yes":
                print("❌ User deletion cancelled.")
                return

        try:
            session.delete(user)
            session.commit()
            print(f"✅ User '{username}' deleted successfully.")
        except Exception as e:
            print(f"❌ Failed to delete user: {type(e).__name__}")


def make_admin(db_manager: DatabaseManager, username: str) -> None:
    """Grant admin privileges to a user."""
    user = get_user_by_username(db_manager, username)
    if not user:
        print(f"❌ User '{username}' not found.")
        return

    if user.is_admin:
        print(f"ℹ️  User '{username}' is already an admin.")
        return

    try:
        with db_manager.get_session() as session:
            user.is_admin = True
            session.add(user)
            session.commit()
        print(f"✅ User '{username}' granted admin privileges.")
    except Exception as e:
        print(f"❌ Failed to grant admin privileges: {type(e).__name__}")


def remove_admin(db_manager: DatabaseManager, username: str) -> None:
    """Remove admin privileges from a user."""
    user = get_user_by_username(db_manager, username)
    if not user:
        print(f"❌ User '{username}' not found.")
        return

    if not user.is_admin:
        print(f"ℹ️  User '{username}' is not an admin.")
        return

    try:
        with db_manager.get_session() as session:
            user.is_admin = False
            session.add(user)
            session.commit()
        print(f"✅ Admin privileges removed from user '{username}'.")
    except Exception as e:
        print(f"❌ Failed to remove admin privileges: {type(e).__name__}")


def reset_password(db_manager: DatabaseManager, username: str, new_password: str) -> None:
    """Reset user password."""
    user = get_user_by_username(db_manager, username)
    if not user:
        print(f"❌ User '{username}' not found.")
        return

    if len(new_password) < MIN_PASSWORD_LENGTH:
        print(f"❌ Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
        return

    try:
        db_manager.reset_user_password(user.id, new_password)
        print(f"✅ Password reset for user '{username}'.")
    except Exception as e:
        print(f"❌ Failed to reset password: {type(e).__name__}")


def _sanitize_username(base: str) -> str:
    """Sanitize a username: lower-case, replace invalid chars with underscore, trim length."""
    username = base.strip().lower()
    # Allow a-z, 0-9, dot, underscore, hyphen
    username = re.sub(r"[^a-z0-9._-]", "_", username)
    return username[:255]


def _generate_password(length: int = 16) -> str:
    """Generate a secure password with letters and digits."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _ensure_unique_username(db_manager: DatabaseManager, base_username: str) -> str:
    """Ensure the username is unique by appending a numeric suffix if needed."""
    candidate = base_username
    suffix = 2
    with db_manager.get_session() as session:
        from pain_narratives.db.models_sqlmodel import User  # local import for session context

        while session.exec(select(User).where(User.username == candidate)).first() is not None:
            # Trim to leave room for suffix
            trimmed = base_username[: max(1, 255 - (len(str(suffix)) + 1))]
            candidate = f"{trimmed}-{suffix}"
            suffix += 1
    return candidate


def import_users_from_csv(db_manager: DatabaseManager, csv_path: str) -> None:
    """Import users and write passwords only to a separate mode-600 credential file.

    Expected CSV columns (case-sensitive preferred):
    - 'Name Surname'
    - 'Email'
    - 'Title'
    Optional output columns:
    - 'User' or 'User ' (a column named with trailing space is tolerated)
    - 'Password'
    """
    if not os.path.exists(csv_path):
        print(f"❌ CSV file not found: {csv_path}")
        sys.exit(1)

    credentials_path = csv_path + ".credentials.csv"
    # Reserve a private output before creating accounts; never overwrite credentials.
    descriptor = os.open(credentials_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    os.chmod(csv_path, 0o600)
    created: List[Dict[str, str]] = []

    # Read CSV
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    # Normalize output column names
    user_col = None
    for cand in ("User", "User "):
        if cand in fieldnames:
            user_col = cand
            break
    if user_col is None:
        user_col = "User"
        fieldnames.append(user_col)

    password_col = "Password"
    fieldnames = [name for name in fieldnames if name != password_col]
    for row in rows:
        row.pop(password_col, None)

    # Process rows
    for row in rows:
        email = (row.get("Email") or "").strip()
        if not email or "@" not in email:
            row[user_col] = row.get(user_col, "")
            continue

        # If user already present in CSV, skip creating to avoid unintended resets
        if (row.get(user_col) or "").strip():
            continue

        local_part = email.split("@", 1)[0]
        base_username = _sanitize_username(local_part)
        username = _ensure_unique_username(db_manager, base_username)
        password = _generate_password()

        # Create user (non-admin)
        try:
            db_manager.create_user(username=username, password=password, is_admin=False)
        except Exception as e:
            print(f"❌ Failed to create user for email {email}: {type(e).__name__}")
            continue

        # Update row
        row[user_col] = username
        with open(credentials_path, "a", newline="", encoding="utf-8") as credentials:
            writer = csv.writer(credentials)
            if credentials.tell() == 0:
                writer.writerow(["username", "password"])
            writer.writerow([username, password])
        created.append({"email": email, "username": username})

    # Write back CSV (overwrite)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Private credential file: {credentials_path}; distribute securely and delete after delivery.")
    # Summary
    print(f"✅ Completed CSV import. Created {len(created)} user(s).")
    if created:
        for item in created:
            print(f" - {item['username']} ({item['email']})")


def main():
    """Main function for user management."""
    try:
        # Parse arguments
        args = parse_arguments()
        # Backward/positional compatibility: allow using the first positional as csv_path for import-csv
        if args.command == "import-csv" and not args.csv_path and args.username:
            args.csv_path = args.username
            args.username = None
        validate_command_args(args)

        # Initialize database connection
        print("Connecting to database...")
        db_manager = DatabaseManager()
        print("✅ Database connection established.")

        # Execute command
        if args.command == "list":
            list_users(db_manager)
        elif args.command == "show":
            assert args.username is not None
            show_user(db_manager, args.username)
        elif args.command == "delete":
            assert args.username is not None
            delete_user(db_manager, args.username)
        elif args.command == "make-admin":
            assert args.username is not None
            make_admin(db_manager, args.username)
        elif args.command == "remove-admin":
            assert args.username is not None
            remove_admin(db_manager, args.username)
        elif args.command == "reset-password":
            assert args.username is not None and args.password is not None
            reset_password(db_manager, args.username, args.password)
        elif args.command == "import-csv":
            import_users_from_csv(db_manager, args.csv_path)

    except Exception as e:
        print(f"❌ Operation failed: {type(e).__name__}")
        print("\nMake sure:")
        print("1. PostgreSQL is running")
        print("2. Database configuration is correct")
        print("3. You have run database migrations")
        sys.exit(1)


if __name__ == "__main__":
    main()
