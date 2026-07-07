# ============================================================
# tests/test_parser.py
# ============================================================
# TESTS: LLM JSON Parser & Pydantic Schema Validation
#
# These tests verify that the Pydantic parser in llm/parser.py:
#   - Accepts valid JSON and returns a MeetingOutput object
#   - Applies correct defaults for missing optional fields
#   - Strips markdown code fences if the LLM adds them
#   - Raises ValueError on invalid JSON or missing required fields
#   - Normalizes priority and due_date values correctly
# ============================================================

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.parser import parse_llm_response, MeetingOutput, TaskOutput


# ============================================================
# SAMPLE VALID JSON — used as base for tests
# ============================================================
VALID_JSON = """
{
  "title": "Sprint Planning Meeting",
  "summary": "The team discussed Q3 priorities and assigned action items.",
  "decisions": [
    "Adopt microservices architecture",
    "Freeze feature additions until end of July"
  ],
  "tasks": [
    {
      "name": "Fix login page bug",
      "assignee": "Alice",
      "priority": "High",
      "due_date": "2026-07-15",
      "description": "Users cannot log in on mobile browsers.",
      "status": "Todo"
    },
    {
      "name": "Update API documentation",
      "assignee": "Bob",
      "priority": "Medium",
      "due_date": null,
      "description": "Swagger docs are outdated.",
      "status": "Todo"
    }
  ]
}
"""


# ============================================================
# TEST GROUP 1: Valid JSON Parsing
# ============================================================

class TestValidJSONParsing:
    """Tests for successful parsing of well-formed LLM output."""

    def test_parses_valid_json_successfully(self):
        """STEP: Valid JSON should return a MeetingOutput object."""
        result = parse_llm_response(VALID_JSON)
        assert isinstance(result, MeetingOutput)

    def test_title_is_extracted(self):
        """STEP: Meeting title should match the JSON value."""
        result = parse_llm_response(VALID_JSON)
        assert result.title == "Sprint Planning Meeting"

    def test_summary_is_extracted(self):
        """STEP: Summary paragraph should be preserved."""
        result = parse_llm_response(VALID_JSON)
        assert "Q3 priorities" in result.summary

    def test_decisions_list_is_extracted(self):
        """STEP: Both decisions should be in the output list."""
        result = parse_llm_response(VALID_JSON)
        assert len(result.decisions) == 2
        assert "Adopt microservices architecture" in result.decisions

    def test_tasks_list_is_extracted(self):
        """STEP: Both tasks should be parsed into TaskOutput objects."""
        result = parse_llm_response(VALID_JSON)
        assert len(result.tasks) == 2
        assert isinstance(result.tasks[0], TaskOutput)

    def test_task_fields_are_correct(self):
        """STEP: All task fields should match JSON values."""
        result = parse_llm_response(VALID_JSON)
        task = result.tasks[0]
        assert task.name == "Fix login page bug"
        assert task.assignee == "Alice"
        assert task.priority == "High"
        assert task.due_date == "2026-07-15"

    def test_null_due_date_becomes_none(self):
        """STEP: JSON null due_date should become Python None."""
        result = parse_llm_response(VALID_JSON)
        task = result.tasks[1]
        assert task.due_date is None


# ============================================================
# TEST GROUP 2: Default Value Handling (Missing Optional Fields)
# ============================================================

class TestMissingFieldDefaults:
    """Tests that verify Pydantic applies correct defaults."""

    def test_missing_assignee_defaults_to_unassigned(self):
        """STEP: If assignee is missing, default to 'Unassigned'."""
        json_str = """
        {
          "title": "Test",
          "summary": "Summary",
          "decisions": [],
          "tasks": [{"name": "Do something"}]
        }
        """
        result = parse_llm_response(json_str)
        assert result.tasks[0].assignee == "Unassigned"

    def test_missing_priority_defaults_to_medium(self):
        """STEP: If priority is missing, default to 'Medium'."""
        json_str = """
        {
          "title": "Test",
          "summary": "Summary",
          "decisions": [],
          "tasks": [{"name": "Do something"}]
        }
        """
        result = parse_llm_response(json_str)
        assert result.tasks[0].priority == "Medium"

    def test_empty_assignee_string_becomes_unassigned(self):
        """STEP: Empty string assignee should be replaced with 'Unassigned'."""
        json_str = """
        {
          "title": "T", "summary": "S", "decisions": [],
          "tasks": [{"name": "Task", "assignee": ""}]
        }
        """
        result = parse_llm_response(json_str)
        assert result.tasks[0].assignee == "Unassigned"

    def test_invalid_priority_defaults_to_medium(self):
        """STEP: Unrecognized priority values should become 'Medium'."""
        json_str = """
        {
          "title": "T", "summary": "S", "decisions": [],
          "tasks": [{"name": "Task", "priority": "URGENT"}]
        }
        """
        result = parse_llm_response(json_str)
        assert result.tasks[0].priority == "Medium"

    def test_tbd_due_date_becomes_none(self):
        """STEP: 'TBD' due_date strings should become None."""
        json_str = """
        {
          "title": "T", "summary": "S", "decisions": [],
          "tasks": [{"name": "Task", "due_date": "TBD"}]
        }
        """
        result = parse_llm_response(json_str)
        assert result.tasks[0].due_date is None

    def test_empty_decisions_list_is_valid(self):
        """STEP: A meeting with no decisions should still parse successfully."""
        json_str = """
        {
          "title": "T", "summary": "S", "decisions": [], "tasks": []
        }
        """
        result = parse_llm_response(json_str)
        assert result.decisions == []

    def test_empty_tasks_list_is_valid(self):
        """STEP: A meeting with no tasks should still parse successfully."""
        json_str = """
        {
          "title": "T", "summary": "S", "decisions": [], "tasks": []
        }
        """
        result = parse_llm_response(json_str)
        assert result.tasks == []


# ============================================================
# TEST GROUP 3: Code Fence Stripping
# ============================================================

class TestCodeFenceStripping:
    """Tests that markdown code fences are removed before parsing."""

    def test_strips_json_code_fences(self):
        """STEP: ```json ... ``` wrappers should be stripped automatically."""
        fenced = '```json\n' + VALID_JSON.strip() + '\n```'
        result = parse_llm_response(fenced)
        assert result.title == "Sprint Planning Meeting"

    def test_strips_plain_code_fences(self):
        """STEP: ``` ... ``` wrappers without 'json' should also be stripped."""
        fenced = '```\n' + VALID_JSON.strip() + '\n```'
        result = parse_llm_response(fenced)
        assert result.title == "Sprint Planning Meeting"


# ============================================================
# TEST GROUP 4: Error Handling
# ============================================================

class TestErrorHandling:
    """Tests that invalid inputs raise clear ValueError exceptions."""

    def test_raises_on_invalid_json(self):
        """STEP: Malformed JSON should raise ValueError."""
        with pytest.raises(ValueError, match="invalid JSON"):
            parse_llm_response("This is not JSON at all")

    def test_raises_on_missing_required_title(self):
        """STEP: Missing 'title' field should raise ValueError."""
        json_no_title = """
        {
          "summary": "Some summary",
          "decisions": [],
          "tasks": []
        }
        """
        with pytest.raises(ValueError):
            parse_llm_response(json_no_title)

    def test_raises_on_missing_required_summary(self):
        """STEP: Missing 'summary' field should raise ValueError."""
        json_no_summary = """
        {
          "title": "Meeting",
          "decisions": [],
          "tasks": []
        }
        """
        with pytest.raises(ValueError):
            parse_llm_response(json_no_summary)

    def test_raises_on_empty_string(self):
        """STEP: Empty string input should raise ValueError."""
        with pytest.raises(ValueError):
            parse_llm_response("")
