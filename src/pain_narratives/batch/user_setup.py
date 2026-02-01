"""
Batch user setup utilities.

Provides functions to create and manage the dedicated batch processing user.
"""

import logging
from typing import Optional

from pain_narratives.core.database import DatabaseManager

logger = logging.getLogger(__name__)

# Default batch user credentials
BATCH_USER_USERNAME = "batch_processor"
BATCH_USER_PASSWORD = "batch_processor_2025"  # Not used for login, just for creation


def get_or_create_batch_user(
    db_manager: Optional[DatabaseManager] = None,
    username: str = BATCH_USER_USERNAME,
    is_admin: bool = True,  # Admin to create experiment groups
) -> int:
    """
    Get or create the dedicated batch processing user.
    
    Args:
        db_manager: Database manager instance (creates one if not provided)
        username: Username for the batch user
        is_admin: Whether the user should have admin privileges
        
    Returns:
        User ID of the batch user
    """
    if db_manager is None:
        db_manager = DatabaseManager()
    
    # Try to find existing user
    with db_manager.get_session() as session:
        from sqlmodel import select

        from pain_narratives.db.models_sqlmodel import User
        
        user = session.exec(
            select(User).where(User.username == username)
        ).first()
        
        if user:
            logger.info(f"Found existing batch user: {username} (ID: {user.id})")
            return user.id
    
    # Create new user
    logger.info(f"Creating new batch user: {username}")
    new_user = db_manager.create_user(
        username=username,
        password=BATCH_USER_PASSWORD,
        is_admin=is_admin,
    )
    
    logger.info(f"Created batch user: {username} (ID: {new_user.id})")
    return new_user.id


def get_batch_user_id(
    db_manager: Optional[DatabaseManager] = None,
    username: str = BATCH_USER_USERNAME,
) -> Optional[int]:
    """
    Get the batch user ID without creating if it doesn't exist.
    
    Args:
        db_manager: Database manager instance
        username: Username to look up
        
    Returns:
        User ID if found, None otherwise
    """
    if db_manager is None:
        db_manager = DatabaseManager()
    
    with db_manager.get_session() as session:
        from sqlmodel import select

        from pain_narratives.db.models_sqlmodel import User
        
        user = session.exec(
            select(User).where(User.username == username)
        ).first()
        
        return user.id if user else None
        
        return user.id if user else None
        
        return user.id if user else None
