# ============================================================
# tests/test_input_processors.py
# ============================================================
# TESTS: Input Processor Modules
#
# Tests all 5 input processors to ensure each one:
#   - Returns a clean string for valid inputs
#   - Returns empty string for blank/None inputs
#   - Correctly strips unwanted content
# ============================================================

import pytest
import sys
import os

# Add project root to path so imports work from tests folder
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from input_processors.text_processor import process_text
from input_processors.email_processor import process_email
from input_processors.slack_processor import process_slack


# ============================================================
# TEST GROUP 1: text_processor.py
# ============================================================

class TestTextProcessor:
    """Tests for the plain text cleaning processor."""

    def test_returns_empty_for_blank_input(self):
        """STEP: Empty string input should return empty string."""
        assert process_text("") == ""
        assert process_text("   ") == ""
        assert process_text(None) == ""

    def test_strips_leading_trailing_whitespace(self):
        """STEP: Each line should have its whitespace trimmed."""
        raw = "   Hello World   \n   Action item here   "
        result = process_text(raw)
        assert "   Hello World   " not in result
        assert "Hello World" in result

    def test_collapses_multiple_blank_lines(self):
        """STEP: Multiple consecutive blank lines should become one."""
        raw = "Line one\n\n\n\nLine two"
        result = process_text(raw)
        assert "\n\n\n" not in result
        assert "Line one" in result
        assert "Line two" in result

    def test_normal_text_passes_through(self):
        """STEP: Valid meeting notes should pass through mostly unchanged."""
        raw = "John: Fix the login bug by Friday.\nJane: Review the API design."
        result = process_text(raw)
        assert "Fix the login bug" in result
        assert "Review the API design" in result

    def test_preserves_single_blank_lines(self):
        """STEP: One blank line between paragraphs should be preserved."""
        raw = "Para one.\n\nPara two."
        result = process_text(raw)
        assert "\n\n" in result


# ============================================================
# TEST GROUP 2: email_processor.py
# ============================================================

class TestEmailProcessor:
    """Tests for the email body extraction processor."""

    def test_returns_empty_for_blank_input(self):
        """STEP: Empty or whitespace input returns empty string."""
        assert process_email("") == ""
        assert process_email("   ") == ""

    def test_strips_email_headers(self):
        """STEP: Standard email headers should be removed."""
        raw = (
            "From: manager@company.com\n"
            "To: team@company.com\n"
            "Subject: Sprint Planning\n"
            "Date: Monday July 7, 2026\n"
            "\n"
            "Hi team, please fix the login issue by Friday."
        )
        result = process_email(raw)
        assert "From:" not in result
        assert "To:" not in result
        assert "Subject:" not in result
        assert "Date:" not in result
        assert "fix the login issue" in result

    def test_strips_quoted_reply_lines(self):
        """STEP: Lines starting with '>' (quoted replies) should be removed."""
        raw = (
            "Thanks for the update.\n"
            "> On Monday, John wrote:\n"
            "> Please fix the bug.\n"
            "I will handle it by end of day."
        )
        result = process_email(raw)
        assert "> On Monday" not in result
        assert "> Please fix" not in result
        assert "I will handle it" in result

    def test_strips_signature_separator(self):
        """STEP: Content after '--' separator should be removed."""
        raw = (
            "Meeting action items:\n"
            "Fix login bug.\n"
            "--\n"
            "John Doe | Manager | Company Inc."
        )
        result = process_email(raw)
        assert "Fix login bug" in result
        assert "John Doe | Manager" not in result

    def test_body_content_preserved(self):
        """STEP: Actual email body text should survive filtering."""
        raw = "From: a@b.com\n\nAction item: Update the database schema."
        result = process_email(raw)
        assert "Update the database schema" in result


# ============================================================
# TEST GROUP 3: slack_processor.py
# ============================================================

class TestSlackProcessor:
    """Tests for the Slack thread consolidation processor."""

    def test_returns_empty_for_blank_input(self):
        """STEP: Empty string returns empty string."""
        assert process_slack("") == ""
        assert process_slack("   ") == ""

    def test_adds_slack_header(self):
        """STEP: Output should include the Slack context header."""
        raw = "John  10:00 AM\nLet's fix the bug today."
        result = process_slack(raw)
        assert "Slack Thread" in result

    def test_removes_system_messages(self):
        """STEP: 'joined the channel' type messages should be removed."""
        raw = (
            "John  10:00 AM\n"
            "Let's fix the login bug.\n"
            "John Doe joined the channel.\n"
            "Jane  10:05 AM\n"
            "I'll handle it by Friday."
        )
        result = process_slack(raw)
        assert "joined the channel" not in result
        assert "fix the login bug" in result
        assert "handle it by Friday" in result

    def test_preserves_conversation_content(self):
        """STEP: Actual messages should be kept in the output."""
        raw = "Alice  9:30 AM\nThe API needs to be updated before the demo."
        result = process_slack(raw)
        assert "API needs to be updated" in result

    def test_collapses_blank_lines(self):
        """STEP: Multiple consecutive blank lines collapse to one."""
        raw = "Line A\n\n\n\nLine B"
        result = process_slack(raw)
        assert "\n\n\n" not in result
