# ============================================================
# input_processors/text_processor.py
# ============================================================
# STEP 5A: Plain Text Input Processor
#
# The simplest processor. The user pastes raw meeting notes,
# transcripts, or any free-form text directly into a text area.
#
# RESPONSIBILITY:
#   Clean and normalize raw text input before sending to LLM.
#   - Remove excessive blank lines
#   - Strip leading/trailing whitespace per line
#   - Return a clean, normalized string
# ============================================================


def process_text(raw_text: str) -> str:
    """
    STEP 5A.1: Clean and normalize raw plain text input.

    Args:
        raw_text (str): Raw text from Streamlit text_area widget.

    Returns:
        str: Cleaned plain text ready to send to the LLM.
        Returns empty string if input is blank.
    """
    # STEP 5A.1.1: Guard — return empty if nothing was entered
    if not raw_text or not raw_text.strip():
        return ""

    # STEP 5A.1.2: Split text into individual lines
    lines = raw_text.splitlines()

    # STEP 5A.1.3: Strip leading/trailing whitespace from each line
    cleaned_lines = [line.strip() for line in lines]

    # STEP 5A.1.4: Remove consecutive blank lines (collapse to one)
    result_lines = []
    previous_blank = False
    for line in cleaned_lines:
        if line == "":
            if not previous_blank:
                result_lines.append(line)  # Keep one blank line max
            previous_blank = True
        else:
            result_lines.append(line)
            previous_blank = False

    # STEP 5A.1.5: Join lines back into a single text string
    return "\n".join(result_lines).strip()
