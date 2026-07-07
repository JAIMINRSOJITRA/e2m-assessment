# ============================================================
# llm/parser.py
# ============================================================
# STEP 6B: Pydantic Schema Definitions & JSON Validation
#
# This module defines the expected structure of the LLM's
# JSON output using Pydantic models.
#
# WHY PYDANTIC:
#   - Validates that the LLM returned the correct field types
#   - Applies default values for missing optional fields
#   - Raises clear errors if the JSON is malformed
#   - Acts as a safety gate BEFORE writing to the database
#
# FLOW:
#   LLM returns raw JSON string
#       ↓
#   parse_llm_response() is called
#       ↓
#   JSON string → dict → MeetingOutput Pydantic model
#       ↓
#   Returns validated Python object or raises error
# ============================================================

import json
import re
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


# ============================================================
# STEP 6B.1: Task Schema
# ============================================================
# Defines the structure for a single extracted task.
# Each field maps directly to a column in the 'tasks' table.
class TaskOutput(BaseModel):
    """
    Pydantic model representing one LLM-extracted task.
    Validates and normalizes each task field.
    """

    # Actionable task title — required, cannot be empty
    name: str = Field(..., description="Actionable task title")

    # Person responsible — defaults to 'Unassigned' if missing
    assignee: str = Field(default="Unassigned", description="Person responsible")

    # Priority level — validated to one of three values
    priority: str = Field(default="Medium", description="High, Medium, or Low")

    # Due date as ISO string or None if not mentioned
    due_date: Optional[str] = Field(default=None, description="YYYY-MM-DD or null")

    # Brief context description of the task
    description: Optional[str] = Field(default="", description="Task context")

    # Status always starts as Todo for new tasks
    status: str = Field(default="Todo", description="Always Todo for new tasks")

    # STEP 6B.1.1: Validate priority field values
    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v):
        """Ensure priority is one of the three allowed values."""
        allowed = {"High", "Medium", "Low"}
        if v not in allowed:
            # Fallback to Medium instead of raising a hard error
            return "Medium"
        return v

    # STEP 6B.1.2: Validate assignee is never empty string
    @field_validator("assignee")
    @classmethod
    def validate_assignee(cls, v):
        """Replace empty assignee with 'Unassigned'."""
        if not v or not v.strip():
            return "Unassigned"
        return v.strip()

    # STEP 6B.1.3: Validate due_date format (basic check)
    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v):
        """Ensure due_date is either None or YYYY-MM-DD format."""
        if not v or v.strip().lower() in ("null", "none", "tbd", "n/a", ""):
            return None
        # Keep if it roughly matches YYYY-MM-DD
        if re.match(r"^\d{4}-\d{2}-\d{2}$", v.strip()):
            return v.strip()
        return None  # Discard unrecognized date formats


# ============================================================
# STEP 6B.2: Meeting Schema
# ============================================================
# Defines the complete structure of the LLM's JSON response.
class MeetingOutput(BaseModel):
    """
    Pydantic model for the complete LLM extraction output.
    Contains metadata, summary, decisions, and a list of tasks.
    """

    # AI-generated short meeting title
    title: str = Field(..., description="Short meeting title")

    # Paragraph summary of the meeting
    summary: str = Field(..., description="Meeting summary paragraph")

    # List of decisions made — can be empty if no decisions found
    decisions: List[str] = Field(
        default_factory=list,
        description="List of decisions made"
    )

    # List of extracted tasks
    tasks: List[TaskOutput] = Field(
        default_factory=list,
        description="List of structured tasks"
    )


# ============================================================
# STEP 6B.3: Main Parsing Function
# ============================================================
def parse_llm_response(raw_response: str) -> MeetingOutput:
    """
    STEP 6B.3: Parse and validate the raw LLM JSON response.

    Converts a raw JSON string from the LLM into a validated
    MeetingOutput Pydantic model.

    Args:
        raw_response (str): Raw string output from the LLM.

    Returns:
        MeetingOutput: Validated and normalized meeting data.

    Raises:
        ValueError: If JSON is invalid or fails schema validation.
    """
    # STEP 6B.3.1: Strip markdown code fences if present
    # Some LLMs wrap JSON in ```json ... ``` blocks despite instructions
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        # Remove first line (```json) and last line (```)
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]).strip()

    # STEP 6B.3.2: Parse the JSON string into a Python dict
    try:
        data_dict = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM returned invalid JSON. Parse error: {e}\n"
            f"Raw response:\n{raw_response[:500]}"
        )

    # STEP 6B.3.3: Validate the dict against the MeetingOutput schema
    # Pydantic will raise ValidationError if required fields are missing
    try:
        meeting = MeetingOutput(**data_dict)
    except Exception as e:
        raise ValueError(
            f"LLM JSON does not match expected schema. Error: {e}"
        )

    return meeting
