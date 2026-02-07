#!/usr/bin/env python3
"""
Batch user registration script for AINarratives application.

This script allows you to create users via command line arguments,
useful for automation or batch user creation.

Usage:
    python register_user_batch.py <username> <password> [--admin]

Examples:
    python register_user_batch.py john_doe mypassword123
    python register_user_batch.py admin_user securepass --admin
"""

import argparse
import sys

from sqlmodel import select

from pain_narratives.core.database import DatabaseManager
from pain_narratives.db.models_sqlmodel import User


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Register a new user for the AINarratives application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s doctor_smith password123
  %(prog)s admin_user securepass --admin
  %(prog)s researcher01 mypass --admin
        """,
    )

    parser.add_argument("username", help="Username for the new user")

    parser.add_argument("password", help="Password for the new user")

    parser.add_argument("--admin", action="store_true", help="Grant admin privileges to the user")

    return parser.parse_args()


def validate_inputs(username: str, password: str) -> None:
    """Validate user inputs."""
    if not username.strip():
        print("❌ Username cannot be empty")
        sys.exit(1)

    if len(password) < 3:
        print("❌ Password must be at least 3 characters long")
        sys.exit(1)

    if len(username) > 255:
        print("❌ Username must be 255 characters or less")
        sys.exit(1)


def check_user_exists(db_manager: DatabaseManager, username: str) -> bool:
    """Check if a user with the given username already exists."""
    with db_manager.get_session() as session:
        existing_user = session.exec(select(User).where(User.username == username)).first()
        return existing_user is not None


def create_user_account(db_manager: DatabaseManager, username: str, password: str, is_admin: bool) -> User:
    """Create a new user account."""
    try:
        user = db_manager.create_user(username=username, password=password, is_admin=is_admin)
        return user
    except Exception as e:
        print(f"❌ Failed to create user: {e}")
        sys.exit(1)


def main():
    """Main function for batch user registration."""
    try:
        # Parse arguments
        args = parse_arguments()

        # Validate inputs
        validate_inputs(args.username, args.password)

        # Initialize database connection
        print("Connecting to database...")
        db_manager = DatabaseManager()
        print("✅ Database connection established.")

        # Check if user already exists
        if check_user_exists(db_manager, args.username):
            print(f"❌ User '{args.username}' already exists!")
            sys.exit(1)

        # Create the user
        print(f"Creating user '{args.username}' {'(admin)' if args.admin else '(regular)'}...")
        user = create_user_account(db_manager, args.username, args.password, args.admin)

        # Display success information
        print("✅ User created successfully!")
        print(f"   Username: {user.username}")
        print(f"   User ID: {user.id}")
        print(f"   Admin: {'Yes' if user.is_admin else 'No'}")

        print(f"\nUser '{args.username}' can now login to the Streamlit application.")

    except Exception as e:
        print(f"❌ Registration failed: {e}")
        print("\nMake sure:")
        print("1. PostgreSQL is running")
        print("2. Database configuration is correct")
        print("3. You have run database migrations")
        sys.exit(1)


if __name__ == "__main__":
    main()
