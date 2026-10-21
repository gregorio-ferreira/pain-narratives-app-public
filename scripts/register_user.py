#!/usr/bin/env python3
"""
User registration script for pain narratives application.

This script allows you to register new users (both admin and regular users)
with interactive prompts for username, password, and admin privileges.
"""

import getpass
import sys

from sqlmodel import select

from pain_narratives.core.database import DatabaseManager
from pain_narratives.core.security import MIN_PASSWORD_LENGTH
from pain_narratives.db.models_sqlmodel import User


def get_user_input() -> tuple[str, str, bool]:
    """Get user registration details through interactive prompts."""
    print("🔐 User Registration for Pain Narratives")
    print("=" * 40)

    # Get username
    while True:
        username = input("Enter username: ").strip()
        if username:
            break
        print("❌ Username cannot be empty. Please try again.")

    # Get password
    while True:
        password = getpass.getpass("Enter password: ")
        if len(password) < MIN_PASSWORD_LENGTH:
            print(f"❌ Password must be at least {MIN_PASSWORD_LENGTH} characters long. Please try again.")
            continue

        confirm_password = getpass.getpass("Confirm password: ")
        if password == confirm_password:
            break
        print("❌ Passwords do not match. Please try again.")

    # Get admin privileges
    while True:
        admin_choice = input("Grant admin privileges? (y/N): ").strip().lower()
        if admin_choice in ["y", "yes"]:
            is_admin = True
            break
        elif admin_choice in ["n", "no", ""]:
            is_admin = False
            break
        print("❌ Please enter 'y' for yes or 'n' for no.")

    return username, password, is_admin


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
        print(f"❌ Failed to create user: {type(e).__name__}")
        sys.exit(1)


def display_user_info(user: User) -> None:
    """Display created user information."""
    print("\n" + "=" * 40)
    print("✅ User created successfully!")
    print(f"   Username: {user.username}")
    print(f"   User ID: {user.id}")
    print(f"   Admin: {'Yes' if user.is_admin else 'No'}")
    print("=" * 40)


def main():
    """Main function for user registration."""
    try:
        # Initialize database connection
        print("Connecting to database...")
        db_manager = DatabaseManager()
        print("✅ Database connection established.\n")

        # Get user input
        username, password, is_admin = get_user_input()

        # Check if user already exists
        if check_user_exists(db_manager, username):
            print(f"\n❌ User '{username}' already exists!")
            print("Please choose a different username.")
            sys.exit(1)

        # Create the user
        print(f"\nCreating user '{username}'...")
        user = create_user_account(db_manager, username, password, is_admin)

        # Display success information
        display_user_info(user)

        if is_admin:
            print("This user can now:")
            print("- Access all experiment groups")
            print("- Manage other users")
            print("- Perform administrative tasks")
        else:
            print("This user can now:")
            print("- Login to the application")
            print("- Create and manage their own experiment groups")
            print("- Run evaluations and experiments")

        print("\nThe user can now login to the Streamlit application.")

    except KeyboardInterrupt:
        print("\n\n👋 User registration cancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Registration failed: {type(e).__name__}")
        print("\nMake sure:")
        print("1. PostgreSQL is running")
        print("2. Database configuration is correct")
        print("3. You have run database migrations")
        sys.exit(1)


if __name__ == "__main__":
    main()
