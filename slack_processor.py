# ============================================================
# input_processors/slack_processor.py
# ============================================================
# STEP 5E: Slack Thread Input Processor
#
# The user pastes a copy of a Slack channel or thread discussion
# containing a team meeting, standup, or decision conversation.
#
# RESPONSIBILITY:
#   Parse the pasted Slack message dump, preserve the author +
#   message format, strip Slack system messages (joined/left),
#   and return a clean formatted conversation log for the LLM.
#
# FORMAT ASSUMPTION:
#   Pasted Slack threads typically look like:
#     John Doe  10:30 AM
#     Let's discuss the API issue today.
#
#     Jane Smith  10:32 AM
#     Agreed, I'll prepare the report by Friday.
# ============================================================

import re


def process_slack(raw_slack: str) -> str:
    """
    STEP 5E.1: Clean and format a pasted Slack thread.

    Args:
        raw_slack (str): Copy-pasted Slack thread text from
                         the Streamlit text area widget.

    Returns:
        str: Formatted Slack conversation log as plain text.
        Returns empty string if input is blank.
    """
    # STEP 5E.1.1: Guard — return empty if nothing was entered
    if not raw_slack or not raw_slack.strip():
        return ""

    # STEP 5E.1.2: Split into individual lines for processing
    lines = raw_slack.splitlines()

    # STEP 5E.1.3: Define Slack system message patterns to skip
    # These are auto-generated notifications from Slack itself
    # that carry no meeting content.
    system_patterns = [
        r".*joined the channel.*",
        r".*left the channel.*",
        r".*set the channel topic.*",
        r".*pinned a message.*",
        r".*added an integration.*",
        r".*uploaded a file.*",
        r".*has joined.*",
        r".*has left.*",
    ]
    compiled_patterns = [
        re.compile(p, re.IGNORECASE)
        for p in system_patterns
    ]

    # STEP 5E.1.4: Filter lines — skip system messages
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()

        # Check if this line matches any Slack system pattern
        is_system = any(p.match(stripped) for p in compiled_patterns)
        if is_system:
            continue  # Drop system notifications

        cleaned_lines.append(stripped)

    # STEP 5E.1.5: Collapse consecutive blank lines into one
    # This tidies up gaps left by removed system messages
    result_lines = []
    previous_blank = False
    for line in cleaned_lines:
        if line == "":
            if not previous_blank:
                result_lines.append(line)
            previous_blank = True
        else:
            result_lines.append(line)
            previous_blank = False

    # STEP 5E.1.6: Add a header label so the LLM understands
    # the input format (Slack thread = conversation, not prose)
    header = "=== Slack Thread / Channel Conversation ===\n"
    body = "\n".join(result_lines).strip()

    return header + body
