# ============================================================
# database/models.py
# ============================================================
# STEP 3: SQLAlchemy ORM Table Definitions
#
# This module defines the structure (schema) of all database
# tables as Python classes (ORM Models).
#
# TABLES DEFINED:
#   - Meeting : Stores metadata, summary, decisions per session
#   - Task    : Stores individual tasks linked to a meeting
#
# RELATIONSHIP:
#   Meeting (1) ──────── (Many) Task
#   One meeting can have many tasks.
#   Deleting a meeting automatically deletes all its tasks
#   (cascade="all, delete-orphan").
# ============================================================

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from connection import Base


# Helper: returns current UTC time as a timezone-aware datetime object.
# WHY: datetime.utcnow() is deprecated in Python 3.12+. Using
# datetime.now(timezone.utc) is the modern, recommended replacement.
def _utcnow():
    return datetime.now(timezone.utc)

# ============================================================
# STEP 3.1: Meeting Model
# ============================================================
# Represents a single meeting processing session.
# Stores the AI-generated title, summary, and decisions.
class Meeting(Base):
    """
    ORM model for the 'meetings' table.
    Each record represents one processed meeting transcript.
    """

    # Table name in SQLite database
    __tablename__ = "meetings"

    # --- Primary Key: Auto-incremented unique ID ---
    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Meeting title (AI-generated short name) ---
    title = Column(String(255), nullable=False, default="Untitled Meeting")

    # --- AI-extracted paragraph summary of the meeting ---
    summary = Column(Text, nullable=True)

    # --- AI-extracted key decisions as Markdown bullet text ---
    decisions = Column(Text, nullable=True)

    # --- Timestamp of when this meeting was processed ---
    # Defaults to current UTC time automatically on creation
    # Timezone-aware UTC timestamp set automatically on record creation
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # --------------------------------------------------------
    # STEP 3.2: One-to-Many Relationship
    # --------------------------------------------------------
    # 'tasks' gives us access to all Task objects linked to
    # this meeting via meeting.tasks (a Python list).
    # cascade="all, delete-orphan" ensures that when a Meeting
    # is deleted, all its child Task records are also deleted.
    tasks = relationship(
        "Task",
        back_populates="meeting",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Meeting id={self.id} title='{self.title}'>"


# ============================================================
# STEP 3.3: Task Model
# ============================================================
# Represents a single actionable task extracted from a meeting.
# Each task is linked back to its parent Meeting via meeting_id.
class Task(Base):
    """
    ORM model for the 'tasks' table.
    Each record is one structured task extracted by the LLM.
    """

    # Table name in SQLite database
    __tablename__ = "tasks"

    # --- Primary Key: Auto-incremented unique ID ---
    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Foreign Key: Links this task to its parent meeting ---
    # ondelete="CASCADE" ensures database-level cascade deletion
    meeting_id = Column(
        Integer,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False
    )

    # --- Task name: The actionable title of this task ---
    name = Column(String(512), nullable=False)

    # --- Assignee: Person responsible for this task ---
    # Defaults to "Unassigned" if LLM finds no owner mention
    assignee = Column(String(255), nullable=True, default="Unassigned")

    # --- Priority: Urgency level of this task ---
    # Values: "High", "Medium", "Low"
    priority = Column(String(50), nullable=True, default="Medium")

    # --- Due Date: Deadline in ISO format YYYY-MM-DD ---
    # Stored as string for flexibility; null = no deadline (TBD)
    due_date = Column(String(20), nullable=True)

    # --- Description: Brief context or rationale for this task ---
    description = Column(Text, nullable=True)

    # --- Status: Current workflow state of this task ---
    # Values: "Todo", "In Progress", "Done"
    # Defaults to "Todo" since all newly extracted tasks are new
    status = Column(String(50), nullable=True, default="Todo")

    # --- Timestamp: When this task record was created ---
    # Timezone-aware UTC timestamp set automatically on record creation
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # --------------------------------------------------------
    # STEP 3.4: Back-Reference to Parent Meeting
    # --------------------------------------------------------
    # 'meeting' allows us to access the parent Meeting object
    # from any Task record via task.meeting.
    meeting = relationship("Meeting", back_populates="tasks")

    def __repr__(self):
        return f"<Task id={self.id} name='{self.name}' status='{self.status}'>"
