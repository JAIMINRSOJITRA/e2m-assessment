# ============================================================
# services/task_service.py
# ============================================================
# STEP 7A: Business Logic Orchestrator
#
# This is the coordinator between the LLM layer and the
# database layer. It glues them together so that app.py
# only needs to call one function per operation.
#
# RESPONSIBILITIES:
#   - Call the LLM extractor with meeting notes
#   - Write the extracted meeting + tasks to SQLite in a
#     single atomic database transaction
#   - Rollback if any step fails (keeps DB clean)
#   - Return the new meeting ID to the UI
#
# FLOW:
#   Plain text notes + provider settings
#       ↓
#   extract_meeting_data()      [llm/extractor.py]
#       ↓
#   MeetingOutput (validated)
#       ↓
#   create_meeting() + create_task()  [database/crud.py]
#       ↓
#   db.commit()
#       ↓
#   meeting.id  →  returned to app.py
# ============================================================

from sqlalchemy.orm import Session
from llm.extractor import extract_meeting_data
from database import crud


def process_meeting(
    db: Session,
    meeting_notes: str,
    provider: str = "Gemini (Google)",
    model: str = None
) -> int:
    """
    STEP 7A.1: Full pipeline — extract notes and save to DB.

    This is the main function called from app.py when the user
    clicks the "Generate Project Plan" button.

    Args:
        db (Session): Active SQLAlchemy database session.
        meeting_notes (str): Cleaned plain text from input processors.
        provider (str): Selected LLM provider ("Gemini (Google)" or
                        "Local LLM (Ollama)").
        model (str): Optional model name override.

    Returns:
        int: The database ID of the newly created Meeting record.

    Raises:
        ValueError: If LLM extraction or DB write fails.
    """
    # ----------------------------------------------------------
    # STEP 7A.1.1: Call LLM to extract structured data
    # ----------------------------------------------------------
    # This sends the meeting notes to Gemini or Ollama and
    # returns a validated MeetingOutput Pydantic object.
    # Raises ValueError if the API call or JSON parsing fails.
    meeting_output = extract_meeting_data(
        meeting_notes=meeting_notes,
        provider=provider,
        model=model
    )

    # ----------------------------------------------------------
    # STEP 7A.1.2: Begin database write transaction
    # ----------------------------------------------------------
    # All database writes happen inside a try-except block.
    # If anything fails after db.flush(), we call db.rollback()
    # to undo all partial writes — keeping the DB clean.
    try:
        # Format decisions list as Markdown bullet points for storage
        decisions_text = "\n".join(
            f"• {d}" for d in meeting_output.decisions
        ) if meeting_output.decisions else "No decisions recorded."

        # STEP 7A.1.3: Create the Meeting record in the database
        # crud.create_meeting() flushes (gets an ID) but does not commit
        meeting_record = crud.create_meeting(
            db=db,
            title=meeting_output.title,
            summary=meeting_output.summary,
            decisions=decisions_text
        )

        # STEP 7A.1.4: Create each Task linked to this Meeting
        # Iterates the validated tasks list and inserts one row per task
        for task in meeting_output.tasks:
            crud.create_task(
                db=db,
                meeting_id=meeting_record.id,
                task_data={
                    "name": task.name,
                    "assignee": task.assignee,
                    "priority": task.priority,
                    "due_date": task.due_date,
                    "description": task.description,
                    "status": task.status,
                }
            )

        # STEP 7A.1.5: Commit all inserts in one atomic transaction
        # Either ALL records are saved, or NONE are (atomicity).
        db.commit()

        # Return the new meeting ID for the UI to use
        return meeting_record.id

    except Exception as e:
        # STEP 7A.1.6: Rollback on any failure
        # This ensures no partial or corrupt records remain in SQLite.
        db.rollback()
        raise ValueError(f"Database write failed: {e}") from e
