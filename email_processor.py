# ============================================================
# input_processors/email_processor.py
# ============================================================
# STEP 5D: Email Body Input Processor
#
# The user pastes a copy of an email thread or email body
# containing meeting notes, action item emails, or follow-ups.
#
# RESPONSIBILITY:
#   Strip irrelevant email header lines (To, From, Subject,
#   Date, CC) and trim quoted reply sections (lines starting
#   with ">") to extract only the relevant body content.
#   Returns clean plain text for the LLM.
# ============================================================



def process_email(raw_email: str) -> str:
    """
    STEP 5D.1: Extract the clean body text from a pasted email.

    Args:
        raw_email (str): Raw copy-pasted email content from the
                         Streamlit text area widget.

    Returns:
        str: Cleaned email body text without headers or quotes.
        Returns empty string if input is blank.
    """
    # STEP 5D.1.1: Guard — return empty if nothing was entered
    if not raw_email or not raw_email.strip():
        return ""

    # STEP 5D.1.2: Split into individual lines for processing
    lines = raw_email.splitlines()

    # STEP 5D.1.3: Define email header prefixes to skip
    # These are standard email client header labels that add no
    # meeting content value for the LLM.
    header_prefixes = (
        "from:", "to:", "cc:", "bcc:", "subject:",
        "date:", "sent:", "reply-to:", "message-id:",
        "mime-version:", "content-type:"
    )

    # STEP 5D.1.4: Filter lines — remove headers and quoted replies
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()

        # Skip empty lines (will be re-added as paragraph breaks)
        if not stripped:
            cleaned_lines.append("")
            continue

        # Skip standard email header lines (case-insensitive match)
        if stripped.lower().startswith(header_prefixes):
            continue

        # Skip quoted reply lines (Gmail/Outlook use ">" prefix)
        if stripped.startswith(">"):
            continue

        # Skip common email signature separators
        if stripped in ("--", "___", "---", "***"):
            break  # Everything after this is likely a signature

        cleaned_lines.append(stripped)

    # STEP 5D.1.5: Collapse multiple blank lines into one
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

    # STEP 5D.1.6: Join the cleaned lines back into a string
    return "\n".join(result_lines).strip()
