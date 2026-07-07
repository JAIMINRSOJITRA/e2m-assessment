# ============================================================
# tests/test_export_service.py
# ============================================================
# TESTS: Export Service — CSV & Markdown Generation
#
# Tests verify that:
#   - CSV export produces valid UTF-8 bytes
#   - CSV contains correct column headers and row data
#   - CSV excludes the internal 'id' column
#   - Markdown export produces valid bytes with correct sections
#   - Markdown handles empty task DataFrames gracefully
# ============================================================

import pytest
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.export_service import export_to_csv, export_to_markdown


# ============================================================
# SAMPLE TASKS DATAFRAME
# ============================================================
SAMPLE_DF = pd.DataFrame([
    {
        "id": 1,
        "name": "Fix login bug",
        "assignee": "Alice",
        "priority": "High",
        "due_date": "2026-07-15",
        "description": "Mobile login is broken.",
        "status": "Todo"
    },
    {
        "id": 2,
        "name": "Update API docs",
        "assignee": "Bob",
        "priority": "Medium",
        "due_date": "",
        "description": "Swagger docs need updating.",
        "status": "In Progress"
    }
])

EMPTY_DF = pd.DataFrame(columns=[
    "id", "name", "assignee", "priority", "due_date", "description", "status"
])


# ============================================================
# TEST GROUP 1: CSV Export
# ============================================================

class TestCSVExport:
    """Tests for export_to_csv() function."""

    def test_returns_bytes(self):
        """STEP: CSV export should return bytes, not a string."""
        result = export_to_csv(SAMPLE_DF)
        assert isinstance(result, bytes)

    def test_csv_is_utf8_decodable(self):
        """STEP: CSV bytes should decode as valid UTF-8."""
        result = export_to_csv(SAMPLE_DF)
        decoded = result.decode("utf-8")
        assert isinstance(decoded, str)

    def test_csv_contains_task_names(self):
        """STEP: CSV should contain all task names from DataFrame."""
        result = export_to_csv(SAMPLE_DF)
        decoded = result.decode("utf-8")
        assert "Fix login bug" in decoded
        assert "Update API docs" in decoded

    def test_csv_excludes_id_column(self):
        """STEP: Internal 'id' column should not appear in CSV export."""
        result = export_to_csv(SAMPLE_DF)
        decoded = result.decode("utf-8")
        # Check header line does not contain 'Id' column
        header_line = decoded.splitlines()[0]
        assert "Id" not in header_line.split(",")

    def test_csv_has_correct_column_headers(self):
        """STEP: Column headers should be title-cased readable names."""
        result = export_to_csv(SAMPLE_DF)
        decoded = result.decode("utf-8")
        header_line = decoded.splitlines()[0]
        assert "Name" in header_line
        assert "Assignee" in header_line
        assert "Priority" in header_line
        assert "Status" in header_line

    def test_csv_has_correct_row_count(self):
        """STEP: CSV should have header + 2 data rows = 3 total lines."""
        result = export_to_csv(SAMPLE_DF)
        decoded = result.decode("utf-8")
        lines = [l for l in decoded.splitlines() if l.strip()]
        # 1 header + 2 data rows
        assert len(lines) == 3

    def test_csv_export_works_with_empty_dataframe(self):
        """STEP: Empty DataFrame should produce a CSV with only headers."""
        result = export_to_csv(EMPTY_DF)
        decoded = result.decode("utf-8")
        lines = [l for l in decoded.splitlines() if l.strip()]
        assert len(lines) == 1  # Only the header line


# ============================================================
# TEST GROUP 2: Markdown Export
# ============================================================

class TestMarkdownExport:
    """Tests for export_to_markdown() function."""

    def test_returns_bytes(self):
        """STEP: Markdown export should return bytes."""
        result = export_to_markdown(
            title="Sprint Planning",
            summary="We planned Q3.",
            decisions="• Use microservices",
            tasks_df=SAMPLE_DF
        )
        assert isinstance(result, bytes)

    def test_markdown_is_utf8_decodable(self):
        """STEP: Markdown bytes should decode as valid UTF-8."""
        result = export_to_markdown("T", "S", "D", SAMPLE_DF)
        decoded = result.decode("utf-8")
        assert isinstance(decoded, str)

    def test_markdown_contains_title(self):
        """STEP: Meeting title should appear in the Markdown output."""
        result = export_to_markdown(
            title="Sprint Planning", summary="S", decisions="D", tasks_df=SAMPLE_DF
        )
        decoded = result.decode("utf-8")
        assert "Sprint Planning" in decoded

    def test_markdown_contains_summary(self):
        """STEP: Summary text should appear in the Markdown output."""
        result = export_to_markdown(
            title="T", summary="We discussed the API design.", decisions="", tasks_df=SAMPLE_DF
        )
        decoded = result.decode("utf-8")
        assert "We discussed the API design." in decoded

    def test_markdown_contains_decisions(self):
        """STEP: Decisions text should appear in the Markdown output."""
        result = export_to_markdown(
            title="T", summary="S",
            decisions="• Adopt microservices", tasks_df=SAMPLE_DF
        )
        decoded = result.decode("utf-8")
        assert "Adopt microservices" in decoded

    def test_markdown_contains_task_names(self):
        """STEP: All task names should appear in the Markdown table."""
        result = export_to_markdown("T", "S", "D", SAMPLE_DF)
        decoded = result.decode("utf-8")
        assert "Fix login bug" in decoded
        assert "Update API docs" in decoded

    def test_markdown_has_table_header(self):
        """STEP: Markdown output should contain a task table with headers."""
        result = export_to_markdown("T", "S", "D", SAMPLE_DF)
        decoded = result.decode("utf-8")
        assert "| Task |" in decoded
        assert "| Assignee |" in decoded
        assert "| Priority |" in decoded

    def test_markdown_handles_empty_dataframe(self):
        """STEP: Empty tasks DataFrame should produce a 'No tasks' message."""
        result = export_to_markdown("T", "S", "D", EMPTY_DF)
        decoded = result.decode("utf-8")
        assert "No tasks extracted" in decoded

    def test_markdown_contains_sections(self):
        """STEP: Markdown should contain all required section headings."""
        result = export_to_markdown("T", "S", "D", SAMPLE_DF)
        decoded = result.decode("utf-8")
        assert "## 📝 Meeting Summary" in decoded
        assert "## ✅ Key Decisions" in decoded
        assert "## 📌 Extracted Tasks" in decoded
