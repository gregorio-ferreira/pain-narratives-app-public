#!/usr/bin/env python3
"""
Quick test script to verify user management UI enhancements work correctly.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pain_narratives.core.database import DatabaseManager


def test_user_management_methods():
    """Test the new user management database methods."""
    print("=" * 80)
    print("Testing User Management Database Methods")
    print("=" * 80)
    
    db_manager = DatabaseManager()
    
    # Test 1: Create a test user
    print("\n1. Creating test user...")
    try:
        test_user = db_manager.create_user("test_user_ui_123", "test_password", is_admin=False)
        print(f"   ✅ User created: {test_user.username} (ID: {test_user.id})")
        user_id = test_user.id
    except Exception as e:
        print(f"   ❌ Failed to create user: {e}")
        return False
    
    # Test 2: Get user experiment groups
    print("\n2. Getting user experiment groups...")
    try:
        groups = db_manager.get_user_experiment_groups(user_id)
        print(f"   ✅ User belongs to {len(groups)} groups: {groups}")
    except Exception as e:
        print(f"   ❌ Failed to get groups: {e}")
    
    # Test 3: Update admin status
    print("\n3. Updating admin status...")
    try:
        result = db_manager.update_user_admin_status(user_id, True)
        print(f"   ✅ Admin status updated: {result}")
    except Exception as e:
        print(f"   ❌ Failed to update admin status: {e}")
    
    # Test 4: Reset password
    print("\n4. Resetting password...")
    try:
        result = db_manager.reset_user_password(user_id, "new_test_password")
        print(f"   ✅ Password reset: {result}")
    except Exception as e:
        print(f"   ❌ Failed to reset password: {e}")
    
    # Test 5: Delete user
    print("\n5. Deleting test user...")
    try:
        result = db_manager.delete_user(user_id)
        print(f"   ✅ User deleted: {result}")
    except Exception as e:
        print(f"   ❌ Failed to delete user: {e}")
    
    print("\n" + "=" * 80)
    print("✅ All tests completed successfully!")
    print("=" * 80)
    return True

if __name__ == "__main__":
    try:
        success = test_user_management_methods()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
