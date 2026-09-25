# ============================================================
# database/crud.py
# ============================================================
# STEP 4: Database CRUD Operations
#
# CRUD = Create, Read, Update, Delete
# This module contains all functions that interact with the
# SQLite database via SQLAlchemy sessions.
#
# Each function follows this pattern:
#   1. Accept a 'db' session (from get_db())
#   2. Perform the database operation
#   3. Commit or query, then return the result
#
# WHY SEPARATE CRUD: Keeps all DB logic in one place.
# The UI (app.py) and services never write raw SQL.
# ============================================================

import pandas as pd
from sqlalchemy.orm import Session
from models import Meeting, Task


# ============================================================
# CREATE OPERATIONS
# ============================================================

def create_meeting(db: Session, title: str, summary: str, decisions: str) -> Meeting:
    """
    STEP 4.1: Insert a new Meeting record into the database.

    Called after LLM successfully extracts meeting data.
    Returns the newly created Meeting object (with its auto-ID).

    WARNING: This function flushes but does NOT commit.
    The caller MUST call db.commit() after this function
    to persist the data, or it will be lost when the session closes.
    """
    # Create a new Meeting ORM object with the extracted data
    new_meeting = Meeting(
        title=title,
        summary=summary,
        decisions=decisions
    )
    # Add to the session (stages the INSERT)
    db.add(new_meeting)
    # Flush so SQLite assigns an ID (needed before adding tasks)
    db.flush()
    return new_meeting


def create_task(db: Session, meeting_id: int, task_data: dict) -> Task:
    """
    STEP 4.2: Insert a single Task record linked to a Meeting.

    Called in a loop after create_meeting() to add each task.
    task_data is a dict matching the Task model fields.

    WARNING: This function flushes but does NOT commit.
    The caller MUST call db.commit() to persist the data.
    """
    new_task = Task(
        meeting_id=meeting_id,
        name=task_data.get("name", "Unnamed Task"),
        assignee=task_data.get("assignee", "Unassigned"),
        priority=task_data.get("priority", "Medium"),
        due_date=task_data.get("due_date", None),
        description=task_data.get("description", ""),
        status="Todo"  # All newly extracted tasks start as Todo
    )
    db.add(new_task)
    db.flush()  # Ensure auto-ID is assigned immediately
    return new_task


# ============================================================
# READ OPERATIONS
# ============================================================

def get_all_meetings(db: Session) -> list[Meeting]:
    """
    STEP 4.3: Fetch all Meeting records from the database.

    Returns a list ordered by newest first (desc created_at).
    Used to populate the meeting history dropdown in the sidebar.
    """
    return (
        db.query(Meeting)
        .order_by(Meeting.created_at.desc())
        .all()
    )


def get_meeting_by_id(db: Session, meeting_id: int) -> Meeting | None:
    """
    STEP 4.4: Fetch a single Meeting by its primary key ID.

    Returns the Meeting object or None if not found.
    """
    return db.query(Meeting).filter(Meeting.id == meeting_id).first()


def get_tasks_by_meeting(db: Session, meeting_id: int) -> list[Task]:
    """
    STEP 4.5: Fetch all Tasks linked to a specific Meeting ID.

    Returns a list of Task objects ordered by creation time.
    Used to populate the st.data_editor table in the UI.
    """
    return (
        db.query(Task)
        .filter(Task.meeting_id == meeting_id)
        .order_by(Task.created_at.asc())
        .all()
    )


def tasks_to_dataframe(tasks: list[Task]) -> pd.DataFrame:
    """
    STEP 4.6: Convert a list of Task ORM objects into a DataFrame.

    The DataFrame is what Streamlit's st.data_editor renders.
    We include the task ID so we can map edits back to DB rows.
    """
    if not tasks:
        # Return an empty DataFrame with correct columns
        return pd.DataFrame(columns=[
            "id", "name", "assignee", "priority",
            "due_date", "description", "status"
        ])

    records = []
    for task in tasks:
        records.append({
            "id": task.id,
            "name": task.name,
            "assignee": task.assignee or "Unassigned",
            "priority": task.priority or "Medium",
            "due_date": task.due_date or "",
            "description": task.description or "",
            "status": task.status or "Todo",
        })
    return pd.DataFrame(records)


# ============================================================
# UPDATE OPERATIONS
# ============================================================

# Whitelist of fields that can be updated via update_task_field()
ALLOWED_UPDATE_FIELDS = {"name", "assignee", "priority", "due_date", "description", "status"}


def update_task_field(db: Session, task_id: int, field: str, value) -> bool:
    """
    STEP 4.7: Update a single field of a specific Task record.

    Used when the user edits a cell directly in the Kanban board.
    Returns True if task was found and updated, False otherwise.
    Only fields in ALLOWED_UPDATE_FIELDS can be modified.
    """
    # Validate field name against whitelist to prevent attribute injection
    if field not in ALLOWED_UPDATE_FIELDS:
        raise ValueError(f"Cannot update field: '{field}'. Allowed: {ALLOWED_UPDATE_FIELDS}")

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return False
    try:
        setattr(task, field, value)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return True


def bulk_update_tasks(db: Session, edited_df: pd.DataFrame) -> None:
    """
    STEP 4.8: Sync an edited DataFrame back to SQLite.

    Called when the user clicks "Save Changes" after editing
    tasks in st.data_editor. Iterates each row and updates
    the matching Task row in the database by its 'id' column.
    """
    # Validate that all required columns exist before iterating
    required_cols = {"id", "name", "assignee", "priority", "due_date", "description", "status"}
    missing = required_cols - set(edited_df.columns)
    if missing:
        raise ValueError(f"Missing required columns in DataFrame: {missing}")

    try:
        for _, row in edited_df.iterrows():
            task_id = int(row["id"])
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                # Update each editable field from the DataFrame row
                task.name = row["name"]
                task.assignee = row["assignee"]
                task.priority = row["priority"]
                task.due_date = row["due_date"] if row["due_date"] else None
                task.description = row["description"]
                task.status = row["status"]
        # Commit all updates in one transaction for efficiency
        db.commit()
    except Exception:
        db.rollback()
        raise


# ============================================================
# DELETE OPERATIONS
# ============================================================

def delete_meeting(db: Session, meeting_id: int) -> bool:
    """
    STEP 4.9: Delete a Meeting and ALL its child Tasks.

    Because cascade="all, delete-orphan" is set in models.py,
    SQLAlchemy automatically deletes all linked Tasks when the
    Meeting is deleted. No manual task cleanup needed.
    Returns True if found and deleted, False otherwise.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        return False
    try:
        db.delete(meeting)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return True


def delete_task(db: Session, task_id: int) -> bool:
    """
    STEP 4.10: Delete a single Task record by its ID.

    Called when a user removes a task from the data editor.
    Returns True if found and deleted, False otherwise.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return False
    try:
        db.delete(task)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return True
