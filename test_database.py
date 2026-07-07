# ============================================================
# tests/test_database.py
# ============================================================
# TESTS: Database CRUD Operations (SQLite In-Memory)
#
# All tests use sqlite:///:memory: so NO files are written to
# disk. The database is created fresh for every test function
# via a pytest fixture, ensuring full isolation between tests.
#
# TESTS COVER:
#   - Creating meeting records
#   - Creating tasks linked to meetings
#   - Reading all meetings and tasks
#   - Updating task fields
#   - Bulk updating tasks from a DataFrame
#   - Cascade delete (deleting a meeting deletes all its tasks)
#   - Deleting a single task
#   - tasks_to_dataframe() conversion utility
# ============================================================

import pytest
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import ORM base and models
from database.connection import Base
from database.models import Meeting, Task
from database import crud


# ============================================================
# PYTEST FIXTURE: In-Memory SQLite Session
# ============================================================
@pytest.fixture
def db_session():
    """
    Create a fresh in-memory SQLite database for each test.

    STEP: This fixture:
      1. Creates a new engine pointing to sqlite:///:memory:
      2. Creates all ORM tables (Meeting, Task)
      3. Yields a session to the test
      4. Drops all tables and closes connection after the test
    This ensures every test runs on a clean, isolated database.
    """
    # Create in-memory engine — no file is written to disk
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    # Register all ORM models to this engine's metadata
    Base.metadata.create_all(bind=engine)

    # Create a session factory bound to this engine
    TestSession = sessionmaker(bind=engine)
    session = TestSession()

    yield session  # Provide the session to the test

    # Teardown: clean up after test completes
    session.close()
    Base.metadata.drop_all(bind=engine)


# ============================================================
# SAMPLE TASK DATA
# ============================================================
SAMPLE_TASK = {
    "name": "Fix login bug",
    "assignee": "Alice",
    "priority": "High",
    "due_date": "2026-07-15",
    "description": "Mobile users cannot log in.",
    "status": "Todo"
}

SAMPLE_TASK_2 = {
    "name": "Update API docs",
    "assignee": "Bob",
    "priority": "Medium",
    "due_date": None,
    "description": "Swagger docs are outdated.",
    "status": "Todo"
}


# ============================================================
# TEST GROUP 1: CREATE Operations
# ============================================================

class TestCreateOperations:
    """Tests for creating meeting and task records."""

    def test_create_meeting_returns_object(self, db_session):
        """STEP: create_meeting() should return a Meeting ORM object."""
        meeting = crud.create_meeting(
            db=db_session,
            title="Sprint Planning",
            summary="We planned Q3 tasks.",
            decisions="• Use microservices\n• Freeze new features"
        )
        assert meeting is not None
        assert isinstance(meeting, Meeting)

    def test_create_meeting_has_correct_title(self, db_session):
        """STEP: The created meeting title should match the input."""
        meeting = crud.create_meeting(
            db=db_session, title="Daily Standup",
            summary="Quick sync.", decisions=""
        )
        assert meeting.title == "Daily Standup"

    def test_create_meeting_gets_auto_id(self, db_session):
        """STEP: Meeting should receive an auto-incremented integer ID."""
        meeting = crud.create_meeting(
            db=db_session, title="M1", summary="S", decisions=""
        )
        db_session.commit()
        assert meeting.id is not None
        assert isinstance(meeting.id, int)

    def test_create_task_linked_to_meeting(self, db_session):
        """STEP: Task should be linked to the meeting via meeting_id FK."""
        meeting = crud.create_meeting(
            db=db_session, title="M1", summary="S", decisions=""
        )
        db_session.commit()

        task = crud.create_task(
            db=db_session,
            meeting_id=meeting.id,
            task_data=SAMPLE_TASK
        )
        db_session.commit()

        assert task.meeting_id == meeting.id
        assert task.name == "Fix login bug"
        assert task.assignee == "Alice"
        assert task.priority == "High"

    def test_create_multiple_tasks_for_one_meeting(self, db_session):
        """STEP: Multiple tasks can be linked to the same meeting."""
        meeting = crud.create_meeting(
            db=db_session, title="M1", summary="S", decisions=""
        )
        db_session.commit()

        crud.create_task(db=db_session, meeting_id=meeting.id, task_data=SAMPLE_TASK)
        crud.create_task(db=db_session, meeting_id=meeting.id, task_data=SAMPLE_TASK_2)
        db_session.commit()

        tasks = crud.get_tasks_by_meeting(db_session, meeting.id)
        assert len(tasks) == 2


# ============================================================
# TEST GROUP 2: READ Operations
# ============================================================

class TestReadOperations:
    """Tests for reading meeting and task records."""

    def test_get_all_meetings_returns_list(self, db_session):
        """STEP: get_all_meetings() returns a list."""
        result = crud.get_all_meetings(db_session)
        assert isinstance(result, list)

    def test_get_all_meetings_returns_all_records(self, db_session):
        """STEP: All created meetings appear in get_all_meetings()."""
        crud.create_meeting(db=db_session, title="M1", summary="S1", decisions="")
        crud.create_meeting(db=db_session, title="M2", summary="S2", decisions="")
        db_session.commit()

        meetings = crud.get_all_meetings(db_session)
        assert len(meetings) == 2

    def test_get_meeting_by_id_returns_correct_meeting(self, db_session):
        """STEP: get_meeting_by_id() returns the exact meeting."""
        meeting = crud.create_meeting(
            db=db_session, title="Unique Meeting", summary="S", decisions=""
        )
        db_session.commit()

        fetched = crud.get_meeting_by_id(db_session, meeting.id)
        assert fetched is not None
        assert fetched.title == "Unique Meeting"

    def test_get_meeting_by_id_returns_none_for_invalid_id(self, db_session):
        """STEP: Fetching non-existent ID should return None."""
        result = crud.get_meeting_by_id(db_session, 99999)
        assert result is None

    def test_get_tasks_by_meeting_returns_correct_tasks(self, db_session):
        """STEP: Tasks returned belong to the correct meeting."""
        m1 = crud.create_meeting(db=db_session, title="M1", summary="S", decisions="")
        m2 = crud.create_meeting(db=db_session, title="M2", summary="S", decisions="")
        db_session.commit()

        crud.create_task(db=db_session, meeting_id=m1.id, task_data=SAMPLE_TASK)
        crud.create_task(db=db_session, meeting_id=m2.id, task_data=SAMPLE_TASK_2)
        db_session.commit()

        tasks_m1 = crud.get_tasks_by_meeting(db_session, m1.id)
        assert len(tasks_m1) == 1
        assert tasks_m1[0].name == "Fix login bug"

    def test_tasks_to_dataframe_returns_dataframe(self, db_session):
        """STEP: tasks_to_dataframe() returns a pandas DataFrame."""
        meeting = crud.create_meeting(db=db_session, title="M", summary="S", decisions="")
        db_session.commit()
        crud.create_task(db=db_session, meeting_id=meeting.id, task_data=SAMPLE_TASK)
        db_session.commit()

        tasks = crud.get_tasks_by_meeting(db_session, meeting.id)
        df = crud.tasks_to_dataframe(tasks)

        assert isinstance(df, pd.DataFrame)
        assert "name" in df.columns
        assert len(df) == 1

    def test_tasks_to_dataframe_empty_returns_empty_df(self, db_session):
        """STEP: Empty task list returns empty DataFrame with correct columns."""
        df = crud.tasks_to_dataframe([])
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert "name" in df.columns


# ============================================================
# TEST GROUP 3: UPDATE Operations
# ============================================================

class TestUpdateOperations:
    """Tests for updating task fields."""

    def test_update_task_field_changes_status(self, db_session):
        """STEP: update_task_field() should change a task's status."""
        meeting = crud.create_meeting(db=db_session, title="M", summary="S", decisions="")
        db_session.commit()
        task = crud.create_task(db=db_session, meeting_id=meeting.id, task_data=SAMPLE_TASK)
        db_session.commit()

        # Update status from "Todo" to "In Progress"
        result = crud.update_task_field(db_session, task.id, "status", "In Progress")
        assert result is True

        # Verify the change was committed
        updated = db_session.query(Task).filter(Task.id == task.id).first()
        assert updated.status == "In Progress"

    def test_update_task_field_returns_false_for_invalid_id(self, db_session):
        """STEP: Updating non-existent task ID should return False."""
        result = crud.update_task_field(db_session, 99999, "status", "Done")
        assert result is False

    def test_bulk_update_tasks_syncs_changes(self, db_session):
        """STEP: bulk_update_tasks() should commit DataFrame changes to DB."""
        meeting = crud.create_meeting(db=db_session, title="M", summary="S", decisions="")
        db_session.commit()
        task = crud.create_task(db=db_session, meeting_id=meeting.id, task_data=SAMPLE_TASK)
        db_session.commit()

        # Build a modified DataFrame
        tasks = crud.get_tasks_by_meeting(db_session, meeting.id)
        df = crud.tasks_to_dataframe(tasks)
        df.loc[0, "status"] = "Done"
        df.loc[0, "assignee"] = "Charlie"

        # Bulk sync the changes
        crud.bulk_update_tasks(db_session, df)

        # Verify changes persisted in DB
        updated = db_session.query(Task).filter(Task.id == task.id).first()
        assert updated.status == "Done"
        assert updated.assignee == "Charlie"


# ============================================================
# TEST GROUP 4: DELETE Operations
# ============================================================

class TestDeleteOperations:
    """Tests for deleting meetings and tasks."""

    def test_delete_meeting_removes_record(self, db_session):
        """STEP: delete_meeting() removes the meeting from the database."""
        meeting = crud.create_meeting(db=db_session, title="M", summary="S", decisions="")
        db_session.commit()
        meeting_id = meeting.id

        result = crud.delete_meeting(db_session, meeting_id)
        assert result is True

        # Verify it no longer exists
        fetched = crud.get_meeting_by_id(db_session, meeting_id)
        assert fetched is None

    def test_delete_meeting_cascades_to_tasks(self, db_session):
        """STEP: Deleting a meeting should also delete all its tasks (cascade)."""
        meeting = crud.create_meeting(db=db_session, title="M", summary="S", decisions="")
        db_session.commit()

        crud.create_task(db=db_session, meeting_id=meeting.id, task_data=SAMPLE_TASK)
        crud.create_task(db=db_session, meeting_id=meeting.id, task_data=SAMPLE_TASK_2)
        db_session.commit()

        # Verify tasks exist before deletion
        tasks_before = crud.get_tasks_by_meeting(db_session, meeting.id)
        assert len(tasks_before) == 2

        # Delete the meeting
        crud.delete_meeting(db_session, meeting.id)

        # Verify ALL tasks were cascade-deleted
        remaining_tasks = db_session.query(Task).filter(
            Task.meeting_id == meeting.id
        ).all()
        assert len(remaining_tasks) == 0

    def test_delete_single_task_removes_only_that_task(self, db_session):
        """STEP: delete_task() removes only the target task, not others."""
        meeting = crud.create_meeting(db=db_session, title="M", summary="S", decisions="")
        db_session.commit()

        task1 = crud.create_task(db=db_session, meeting_id=meeting.id, task_data=SAMPLE_TASK)
        task2 = crud.create_task(db=db_session, meeting_id=meeting.id, task_data=SAMPLE_TASK_2)
        db_session.commit()

        # Delete only task1
        crud.delete_task(db_session, task1.id)

        # Verify task2 still exists
        remaining = crud.get_tasks_by_meeting(db_session, meeting.id)
        assert len(remaining) == 1
        assert remaining[0].id == task2.id

    def test_delete_meeting_returns_false_for_invalid_id(self, db_session):
        """STEP: Deleting non-existent meeting should return False."""
        result = crud.delete_meeting(db_session, 99999)
        assert result is False

    def test_delete_task_returns_false_for_invalid_id(self, db_session):
        """STEP: Deleting non-existent task should return False."""
        result = crud.delete_task(db_session, 99999)
        assert result is False
