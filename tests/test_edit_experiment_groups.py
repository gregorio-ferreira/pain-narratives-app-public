"""
Test script for editing user experiment groups functionality.
"""

import pytest

from pain_narratives.core.database import DatabaseManager


def test_update_user_experiment_groups():
    """Test updating user experiment groups with validation."""
    db_manager = DatabaseManager()
    
    # Get all available groups
    all_groups = db_manager.get_all_experiment_groups()
    print(f"\n✅ Found {len(all_groups)} experiment groups in database")
    
    if len(all_groups) > 0:
        print("\nAvailable groups:")
        for group in all_groups[:5]:  # Show first 5
            print(f"  - ID: {group.experiments_group_id}, Description: {group.description or 'No description'}")
    
    # Get all users
    with db_manager.get_session() as session:
        from sqlmodel import select

        from pain_narratives.db.models_sqlmodel import User
        users = list(session.exec(select(User)).all())
    
    print(f"\n✅ Found {len(users)} users in database")
    
    if len(users) == 0:
        print("⚠️  No users found. Please create a user first.")
        return
    
    # Use first user for testing
    test_user = users[0]
    print(f"\n📝 Testing with user: {test_user.username} (ID: {test_user.id})")
    
    # Get current groups
    current_groups = db_manager.get_user_experiment_groups(test_user.id)
    print(f"Current groups: {current_groups}")
    
    # Test 1: Update with valid group IDs
    if len(all_groups) >= 2:
        test_group_ids = [all_groups[0].experiments_group_id, all_groups[1].experiments_group_id]
        print(f"\n🧪 Test 1: Updating groups to {test_group_ids}")
        
        result = db_manager.update_user_experiment_groups(test_user.id, test_group_ids)
        assert result == True, "Update should succeed"
        
        # Verify the update
        updated_groups = db_manager.get_user_experiment_groups(test_user.id)
        assert set(updated_groups) == set(test_group_ids), f"Expected {test_group_ids}, got {updated_groups}"
        print(f"✅ Test 1 passed: Groups updated to {updated_groups}")
        
        # Test 2: Update with empty list (remove all groups)
        print(f"\n🧪 Test 2: Removing all groups")
        result = db_manager.update_user_experiment_groups(test_user.id, [])
        assert result == True, "Update should succeed"
        
        updated_groups = db_manager.get_user_experiment_groups(test_user.id)
        assert len(updated_groups) == 0, f"Expected empty list, got {updated_groups}"
        print(f"✅ Test 2 passed: All groups removed")
        
        # Test 3: Update with invalid group ID (should raise ValueError)
        print(f"\n🧪 Test 3: Testing with invalid group ID 99999")
        try:
            db_manager.update_user_experiment_groups(test_user.id, [99999])
            assert False, "Should have raised ValueError for invalid group ID"
        except ValueError as e:
            print(f"✅ Test 3 passed: Correctly raised ValueError: {e}")
        
        # Restore original groups
        if current_groups:
            print(f"\n🔄 Restoring original groups: {current_groups}")
            db_manager.update_user_experiment_groups(test_user.id, current_groups)
    else:
        print("⚠️  Need at least 2 experiment groups to run full tests")
    
    print("\n✅ All tests completed successfully!")


if __name__ == "__main__":
    test_update_user_experiment_groups()
