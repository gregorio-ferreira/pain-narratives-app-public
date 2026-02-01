import os

# Ensure src is in path
import sys

from sqlmodel import SQLModel, create_engine

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from pain_narratives.core.database import DatabaseManager
from pain_narratives.db.base import SCHEMA_NAME
from pain_narratives.db.models_sqlmodel import User, UserPrompt


def setup_in_memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        execution_options={"schema_translate_map": {SCHEMA_NAME: None}},
    )
    SQLModel.metadata.create_all(engine)
    return engine


def test_get_user_current_prompt():
    engine = setup_in_memory_db()
    db = DatabaseManager(engine)
    with db.get_session() as session:
        user = User(username="test", hashed_password="x", is_admin=False)
        session.add(user)
        session.commit()
        session.refresh(user)
        uid = user.id
        session.add_all(
            [
                UserPrompt(user_id=uid, prompt_name="p1", prompt_template="t1", is_current=True),
                UserPrompt(user_id=uid, prompt_name="p2", prompt_template="t2", is_current=False),
            ]
        )
        session.commit()

    assert db.get_user_current_prompt(uid) == "t1"
