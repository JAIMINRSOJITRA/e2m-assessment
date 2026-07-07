# ============================================================
# llm/extractor.py
# ============================================================
# STEP 6C: LLM Client & Extraction Orchestrator
#
# This module is the bridge between the application and the
# LLM provider. It sends the meeting notes prompt to either:
#   1. Google Gemini (primary — via google-genai SDK)
#   2. Local Ollama (secondary — via ollama Python SDK)
#
# FLOW:
#   Meeting notes (plain text)
#       ↓
#   get_user_prompt() + get_system_prompt()  [from prompt.py]
#       ↓
#   call_gemini() or call_ollama()
#       ↓
#   Raw JSON string response
#       ↓
#   parse_llm_response()                    [from parser.py]
#       ↓
#   MeetingOutput (validated Python object)
# ============================================================

import google.genai as genai
import ollama

from llm.prompt import get_system_prompt, get_user_prompt
from llm.parser import parse_llm_response, MeetingOutput
from config import GEMINI_API_KEY, GEMINI_MODEL, OLLAMA_BASE_URL, OLLAMA_MODEL


# ============================================================
# STEP 6C.1: Gemini Extraction Function
# ============================================================
def call_gemini(meeting_notes: str, model: str = None) -> str:
    """
    STEP 6C.1: Send meeting notes to Google Gemini and get JSON.

    Uses the google-genai SDK to call Gemini with structured
    output instructions. Returns the raw JSON string response.

    Args:
        meeting_notes (str): Clean plain text from input processors.
        model (str): Gemini model name (overrides config default).

    Returns:
        str: Raw JSON string from Gemini.

    Raises:
        ValueError: If API key is missing or call fails.
    """
    # STEP 6C.1.1: Validate API key exists
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not set. "
            "Please add it to your .env file or Streamlit secrets."
        )

    # STEP 6C.1.2: Initialize Gemini client with the API key
    client = genai.Client(api_key=GEMINI_API_KEY)

    # STEP 6C.1.3: Select the model (use config default if not specified)
    selected_model = model or GEMINI_MODEL

    # STEP 6C.1.4: Build the combined system + user prompt
    # Gemini receives the system instructions and meeting notes together
    system_prompt = get_system_prompt()
    user_prompt = get_user_prompt(meeting_notes)
    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    # STEP 6C.1.5: Call the Gemini API
    try:
        response = client.models.generate_content(
            model=selected_model,
            contents=full_prompt,
        )
    except Exception as e:
        raise ValueError(f"Gemini API call failed: {e}") from e

    # STEP 6C.1.6: Extract the text content from the response
    raw_text = response.text
    if not raw_text or not raw_text.strip():
        raise ValueError("Gemini returned an empty response.")

    return raw_text.strip()


# ============================================================
# STEP 6C.2: Ollama (Local LLM) Extraction Function
# ============================================================
def call_ollama(meeting_notes: str, model: str = None) -> str:
    """
    STEP 6C.2: Send meeting notes to a local Ollama model.

    Uses the ollama Python SDK to call a locally running model.
    Requires Ollama desktop app to be installed and running at
    http://localhost:11434 with the target model already pulled.

    Args:
        meeting_notes (str): Clean plain text from input processors.
        model (str): Ollama model name (overrides config default).

    Returns:
        str: Raw JSON string from the local model.

    Raises:
        ValueError: If Ollama is not running or call fails.
    """
    # STEP 6C.2.1: Select the model (use config default if not specified)
    selected_model = model or OLLAMA_MODEL

    # STEP 6C.2.2: Build combined prompt for the local model
    system_prompt = get_system_prompt()
    user_prompt = get_user_prompt(meeting_notes)

    # STEP 6C.2.3: Call the Ollama SDK
    # Using chat interface: provides system + user message roles
    try:
        client = ollama.Client(host=OLLAMA_BASE_URL)
        response = client.chat(
            model=selected_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
    except Exception as e:
        raise ValueError(
            f"Ollama call failed. Is Ollama running at {OLLAMA_BASE_URL}? "
            f"Error: {e}"
        ) from e

    # STEP 6C.2.4: Extract the text response from the Ollama message
    raw_text = response["message"]["content"]
    if not raw_text or not raw_text.strip():
        raise ValueError("Ollama returned an empty response.")

    return raw_text.strip()


# ============================================================
# STEP 6C.3: Main Entry Point — extract_meeting_data()
# ============================================================
def extract_meeting_data(
    meeting_notes: str,
    provider: str = "Gemini (Google)",
    model: str = None
) -> MeetingOutput:
    """
    STEP 6C.3: Orchestrate LLM extraction and JSON validation.

    This is the main function called by services/task_service.py.
    It selects the correct LLM provider, sends the notes,
    receives the raw JSON, and validates it with Pydantic.

    Args:
        meeting_notes (str): Clean plain text from input processors.
        provider (str): "Gemini (Google)" or "Local LLM (Ollama)".
        model (str): Optional model name override.

    Returns:
        MeetingOutput: Fully validated meeting extraction result.

    Raises:
        ValueError: If LLM call fails or JSON is invalid.
    """
    # STEP 6C.3.1: Guard — reject empty input before API call
    if not meeting_notes or not meeting_notes.strip():
        raise ValueError(
            "Meeting notes are empty. "
            "Please provide text before extracting tasks."
        )

    # STEP 6C.3.2: Route to the correct LLM provider
    if provider == "Gemini (Google)":
        raw_json = call_gemini(meeting_notes, model=model)
    elif provider == "Local LLM (Ollama)":
        raw_json = call_ollama(meeting_notes, model=model)
    else:
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. "
            "Choose 'Gemini (Google)' or 'Local LLM (Ollama)'."
        )

    # STEP 6C.3.3: Parse and validate the raw JSON response
    # parse_llm_response() will raise ValueError if JSON is bad
    meeting_output = parse_llm_response(raw_json)

    return meeting_output
