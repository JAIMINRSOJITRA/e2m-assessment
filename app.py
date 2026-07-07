# ============================================================
# app.py
# ============================================================
# STEP 8: Streamlit Main Application Entry Point
#
# This is the file you run to launch the application:
#   streamlit run app.py
#
# WHAT THIS FILE DOES:
#   - Initializes the database on first run
#   - Sets up the page layout and custom CSS styling
#   - Renders the sidebar (LLM settings + meeting history)
#   - Renders 4 main tabs:
#       1. 📝 Process Notes  — Input + LLM Extraction
#       2. 📋 Tasks          — Interactive editor + filters
#       3. 📊 Visualize      — Kanban board + Gantt timeline
#       4. 📥 Export         — CSV + Markdown downloads
#   - Manages Streamlit session state across tab switches
#
# MODULE FLOW:
#   app.py → input_processors/ → llm/ → services/ → database/
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from html import escape

# --- Internal modules (in correct dependency order) ---
from config import (
    APP_TITLE, APP_SUBTITLE, LLM_PROVIDERS,
    PRIORITY_OPTIONS, STATUS_OPTIONS, INPUT_SOURCES,
    GEMINI_MODEL, OLLAMA_MODEL
)
from database.connection import init_db, get_db
from database import crud
from services.task_service import process_meeting
from services.export_service import export_to_csv, export_to_markdown

# --- Input processors (one per input source type) ---
from input_processors.text_processor import process_text
from input_processors.pdf_processor import process_pdf
from input_processors.docx_processor import process_docx
from input_processors.email_processor import process_email
from input_processors.slack_processor import process_slack


# ============================================================
# STEP 8.1: Page Configuration
# ============================================================
# Must be the FIRST Streamlit call in the script.
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# STEP 8.2: Database Initialization
# ============================================================
# Creates SQLite tables if they don't exist yet.
# Called only once at app startup.
init_db()


# ============================================================
# STEP 8.3: Custom CSS Styling
# ============================================================
# Inject CSS to enhance the default Streamlit visual style.
st.markdown("""
<style>
    /* ---- Global font and background ---- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ---- App main header ---- */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        border: 1px solid #30363d;
    }
    .main-header h1 {
        color: #e2e8f0;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
    }
    .main-header p {
        color: #94a3b8;
        font-size: 1rem;
        margin: 0.3rem 0 0 0;
    }
    .accent { color: #60a5fa; }

    /* ---- Metric cards ---- */
    .metric-card {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        text-align: center;
    }
    .metric-card h3 { color: #60a5fa; font-size: 2rem; margin: 0; }
    .metric-card p { color: #94a3b8; font-size: 0.85rem; margin: 0; }

    /* ---- Summary card ---- */
    .summary-card {
        background: #0f172a;
        border-left: 4px solid #60a5fa;
        border-radius: 8px;
        padding: 1rem 1.5rem;
        margin: 0.5rem 0;
        color: #cbd5e1;
        line-height: 1.7;
    }

    /* ---- Kanban columns ---- */
    .kanban-col {
        background: #1e293b;
        border-radius: 12px;
        padding: 1rem;
        min-height: 200px;
        border: 1px solid #334155;
    }
    .kanban-col-header {
        font-weight: 600;
        font-size: 0.9rem;
        padding: 0.4rem 0.8rem;
        border-radius: 8px;
        margin-bottom: 0.8rem;
        text-align: center;
    }

    /* ---- Task cards in Kanban ---- */
    .task-card {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.6rem;
    }
    .task-card h4 { color: #e2e8f0; font-size: 0.88rem; margin: 0 0 0.3rem 0; }
    .task-card p  { color: #64748b; font-size: 0.78rem; margin: 0.1rem 0; }

    /* ---- Priority badges ---- */
    .badge-high   { background:#7f1d1d; color:#fca5a5; padding:2px 8px; border-radius:12px; font-size:0.75rem; }
    .badge-medium { background:#78350f; color:#fcd34d; padding:2px 8px; border-radius:12px; font-size:0.75rem; }
    .badge-low    { background:#14532d; color:#86efac; padding:2px 8px; border-radius:12px; font-size:0.75rem; }

    /* ---- Section divider ---- */
    .section-divider {
        border: none;
        border-top: 1px solid #334155;
        margin: 1.5rem 0;
    }

    /* ---- Streamlit tab text ---- */
    button[data-baseweb="tab"] { font-weight: 500; font-size: 0.92rem; }

    /* ---- Clickable Metric Cards styling ---- */
    .metric-row-sentinel {
        display: none;
    }
    
    /* Target the horizontal block that comes immediately after our sentinel div */
    .element-container:has(.metric-row-sentinel) + .element-container div[data-testid="stHorizontalBlock"] button {
        background: linear-gradient(135deg, #1e293b, #0f172a) !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        padding: 1.2rem 1rem !important;
        height: 120px !important;
        width: 100% !important;
        color: #e2e8f0 !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
        text-align: center !important;
        white-space: pre-line !important; /* Allow newlines to render as line breaks */
        line-height: 1.4 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
    }

    .element-container:has(.metric-row-sentinel) + .element-container div[data-testid="stHorizontalBlock"] button:hover {
        border-color: #60a5fa !important;
        color: #60a5fa !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 15px -3px rgba(96, 165, 250, 0.15) !important;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# STEP 8.4: Session State Initialization
# ============================================================
# Initialize keys in st.session_state if they don't exist yet.
# Session state persists values across Streamlit re-runs
# (tab switches, button clicks, widget interactions).
def init_session_state():
    """Initialize all session state variables on first load."""
    defaults = {
        "current_meeting_id": None,   # ID of the loaded/active meeting
        "meeting_title": "",          # Title of the active meeting
        "meeting_summary": "",        # Summary text
        "meeting_decisions": "",      # Decisions bullet text
        "tasks_df": pd.DataFrame(),   # Tasks as DataFrame for editor
        "extraction_done": False,     # Flag: has extraction been run?
        "selected_provider": LLM_PROVIDERS[0],  # Default: Gemini
        "selected_model": GEMINI_MODEL,          # Default model
        "notes_task_filter": "All",   # Task filter on the Process Notes tab
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()


# ============================================================
# STEP 8.5: Sidebar — LLM Settings & Meeting History
# ============================================================
with st.sidebar:
    st.markdown("## ⚙️ Settings")

    # --- STEP 8.5.1: LLM Provider Selection ---
    st.session_state.selected_provider = st.selectbox(
        "🤖 LLM Provider",
        options=LLM_PROVIDERS,
        index=LLM_PROVIDERS.index(st.session_state.selected_provider),
        help="Choose between Google Gemini or a local Ollama model"
    )

    # --- STEP 8.5.2: Model Selection (changes based on provider) ---
    if st.session_state.selected_provider == "Gemini (Google)":
        st.session_state.selected_model = st.selectbox(
            "🧠 Gemini Model",
            options=["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
            index=0,
            help="gemini-2.5-flash is recommended (fast + accurate)"
        )
    else:
        st.session_state.selected_model = st.text_input(
            "🧠 Ollama Model Name",
            value=OLLAMA_MODEL,
            help="Enter the model name you have pulled in Ollama (e.g. llama3, mistral)"
        )

    st.markdown("---")

    # --- STEP 8.5.3: Meeting History ---
    st.markdown("## 📂 Meeting History")

    db_gen = get_db()
    db = next(db_gen)
    try:
        all_meetings = crud.get_all_meetings(db)
    finally:
        db.close()

    if all_meetings:
        # Build a label → ID mapping for the selectbox
        meeting_options = {
            f"{m.title} ({m.created_at.strftime('%b %d, %Y')})" : m.id
            for m in all_meetings
        }
        selected_label = st.selectbox(
            "Load a past meeting:",
            options=list(meeting_options.keys())
        )

        if st.button("📂 Load Meeting", use_container_width=True):
            # Load the selected meeting's data into session state
            mid = meeting_options[selected_label]
            db_gen2 = get_db()
            db2 = next(db_gen2)
            try:
                meeting = crud.get_meeting_by_id(db2, mid)
                tasks = crud.get_tasks_by_meeting(db2, mid)
                tasks_df = crud.tasks_to_dataframe(tasks)
            finally:
                db2.close()

            if meeting:
                st.session_state.current_meeting_id = meeting.id
                st.session_state.meeting_title = meeting.title
                st.session_state.meeting_summary = meeting.summary or ""
                st.session_state.meeting_decisions = meeting.decisions or ""
                st.session_state.tasks_df = tasks_df
                st.session_state.extraction_done = True
                st.success(f"✅ Loaded: {meeting.title}")
                st.rerun()
    else:
        st.info("No meetings yet. Process your first meeting above!")


# ============================================================
# STEP 8.6: Main Application Header
# ============================================================
st.markdown(f"""
<div class="main-header">
    <h1>🤖 <span class="accent">{APP_TITLE}</span></h1>
    <p>{APP_SUBTITLE}</p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# STEP 8.7: Main Tabs Layout
# ============================================================
# Four tabs divide the app into logical sections.
tab_notes, tab_tasks, tab_visual, tab_export = st.tabs([
    "📝 Process Notes",
    "📋 Tasks & Editor",
    "📊 Visualize",
    "📥 Export"
])


# ============================================================
# TAB 1: Process Notes
# ============================================================
with tab_notes:
    st.markdown("### 📝 Step 1: Choose Your Input Source")
    st.caption("Select the format of your meeting notes and paste or upload them below.")

    # --- STEP 8.7.1: Input Source Selector ---
    input_source = st.radio(
        "Input Type:",
        options=INPUT_SOURCES,
        horizontal=True,
        label_visibility="collapsed"
    )

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # --- STEP 8.7.2: Render the correct input widget ---
    plain_text = ""  # Will hold the processed plain text for LLM

    if input_source == "📝 Text":
        # Plain text area — simplest input method
        raw_text = st.text_area(
            "Paste your meeting notes or transcript here:",
            height=280,
            placeholder="Example:\nJohn: We need to fix the login bug before Friday.\nJane: I'll handle the API integration by next week..."
        )
        if raw_text:
            plain_text = process_text(raw_text)

    elif input_source == "📄 PDF":
        # PDF file uploader
        pdf_file = st.file_uploader(
            "Upload a PDF meeting document:",
            type=["pdf"]
        )
        if pdf_file:
            plain_text = process_pdf(pdf_file.read())
            st.success(f"✅ PDF loaded: {pdf_file.name} ({len(plain_text)} characters extracted)")

    elif input_source == "📃 DOCX":
        # Word document uploader
        docx_file = st.file_uploader(
            "Upload a Word (.docx) meeting document:",
            type=["docx"]
        )
        if docx_file:
            plain_text = process_docx(docx_file.read())
            st.success(f"✅ DOCX loaded: {docx_file.name} ({len(plain_text)} characters extracted)")

    elif input_source == "📧 Email":
        # Email body text area
        raw_email = st.text_area(
            "Paste your email thread here:",
            height=280,
            placeholder="From: manager@company.com\nTo: team@company.com\nSubject: Sprint Planning\n\nHi team, let's discuss the following tasks..."
        )
        if raw_email:
            plain_text = process_email(raw_email)
            st.caption(f"📧 {len(plain_text)} characters extracted after header/quote removal")

    elif input_source == "💬 Slack":
        # Slack thread text area
        raw_slack = st.text_area(
            "Paste your Slack thread or channel messages here:",
            height=280,
            placeholder="John Doe  10:30 AM\nLet's fix the API issue today.\n\nJane Smith  10:32 AM\nI'll prepare the report by Friday."
        )
        if raw_slack:
            plain_text = process_slack(raw_slack)
            st.caption(f"💬 {len(plain_text)} characters after Slack system message cleanup")

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # --- STEP 8.7.3: Preview extracted text (optional) ---
    if plain_text:
        with st.expander("👁️ Preview Extracted Plain Text (sent to LLM)", expanded=False):
            st.text(plain_text[:2000] + ("..." if len(plain_text) > 2000 else ""))

    # --- STEP 8.7.4: Generate Button ---
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        generate_btn = st.button(
            "✨ Generate Project Plan",
            type="primary",
            use_container_width=True,
            disabled=not bool(plain_text)
        )
    with col_info:
        if not plain_text:
            st.warning("⚠️ Please provide meeting notes above before generating.")

    # --- STEP 8.7.5: Run LLM Extraction Pipeline ---
    if generate_btn and plain_text:
        with st.spinner(
            f"🤖 {st.session_state.selected_provider} is analyzing your meeting notes... "
            "This may take 10-30 seconds."
        ):
            try:
                # STEP: Call the full pipeline (LLM → validate → DB write)
                db_gen3 = get_db()
                db3 = next(db_gen3)
                try:
                    new_meeting_id = process_meeting(
                        db=db3,
                        meeting_notes=plain_text,
                        provider=st.session_state.selected_provider,
                        model=st.session_state.selected_model
                    )
                finally:
                    db3.close()

                # STEP: Load the newly saved meeting into session state
                db_gen4 = get_db()
                db4 = next(db_gen4)
                try:
                    meeting = crud.get_meeting_by_id(db4, new_meeting_id)
                    tasks = crud.get_tasks_by_meeting(db4, new_meeting_id)
                    tasks_df = crud.tasks_to_dataframe(tasks)
                finally:
                    db4.close()

                # STEP: Save to session state for other tabs to access
                st.session_state.current_meeting_id = new_meeting_id
                st.session_state.meeting_title = meeting.title
                st.session_state.meeting_summary = meeting.summary or ""
                st.session_state.meeting_decisions = meeting.decisions or ""
                st.session_state.tasks_df = tasks_df
                st.session_state.extraction_done = True

                st.success(f"✅ Success! Extracted **{len(tasks_df)}** tasks from your meeting.")
                st.rerun()

            except ValueError as e:
                st.error(f"❌ Extraction failed: {e}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {e}")

    # --- STEP 8.7.6: Show Results if extraction has been done ---
    if st.session_state.extraction_done:
        st.markdown("---")
        st.markdown(f"### 📋 {st.session_state.meeting_title}")

        # Meeting Summary Card
        st.markdown("**📝 Meeting Summary**")
        st.markdown(
            f"<div class='summary-card'>{escape(st.session_state.meeting_summary)}</div>",
            unsafe_allow_html=True
        )

        # Key Decisions
        st.markdown("**✅ Key Decisions**")
        st.markdown(st.session_state.meeting_decisions)

        # Summary metrics
        df = st.session_state.tasks_df
        if not df.empty:
            st.markdown("**📊 Extracted Tasks (Click a card to filter the list below)**")
            
            # Count the tasks for each category
            total_count = len(df)
            high_count = len(df[df["priority"] == "High"]) if "priority" in df.columns else 0
            todo_count = len(df[df["status"] == "Todo"]) if "status" in df.columns else 0
            done_count = len(df[df["status"] == "Done"]) if "status" in df.columns else 0
            
            # Read active filter state
            filter_state = st.session_state.notes_task_filter
            
            # Highlight the active filter using indicators
            ind_all = "⭐ " if filter_state == "All" else "📋 "
            ind_high = "⭐ " if filter_state == "High Priority" else "🔥 "
            ind_todo = "⭐ " if filter_state == "Todo" else "⏳ "
            ind_done = "⭐ " if filter_state == "Done" else "✅ "
            
            # Write a sentinel class before st.columns to target with CSS
            st.markdown('<div class="metric-row-sentinel"></div>', unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if st.button(f"{ind_all}{total_count}\nTotal Tasks", key="btn_filter_all", use_container_width=True):
                    st.session_state.notes_task_filter = "All"
                    st.rerun()
            with c2:
                if st.button(f"{ind_high}{high_count}\nHigh Priority", key="btn_filter_high", use_container_width=True):
                    st.session_state.notes_task_filter = "High Priority"
                    st.rerun()
            with c3:
                if st.button(f"{ind_todo}{todo_count}\nTodo Tasks", key="btn_filter_todo", use_container_width=True):
                    st.session_state.notes_task_filter = "Todo"
                    st.rerun()
            with c4:
                if st.button(f"{ind_done}{done_count}\nDone Tasks", key="btn_filter_done", use_container_width=True):
                    st.session_state.notes_task_filter = "Done"
                    st.rerun()

            st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

            # Apply the filter to the tasks DataFrame for display
            if filter_state == "High Priority":
                filtered_notes_df = df[df["priority"] == "High"]
            elif filter_state == "Todo":
                filtered_notes_df = df[df["status"] == "Todo"]
            elif filter_state == "Done":
                filtered_notes_df = df[df["status"] == "Done"]
            else:
                filtered_notes_df = df

            st.markdown(f"#### 📌 Tasks: {filter_state}")
            if filtered_notes_df.empty:
                st.info(f"No tasks found for category '{filter_state}'.")
            else:
                # We show a clean read-only dataframe
                st.dataframe(
                    filtered_notes_df.drop(columns=["id"]) if "id" in filtered_notes_df.columns else filtered_notes_df,
                    use_container_width=True,
                    column_config={
                        "name": st.column_config.TextColumn("Task Name", width="large"),
                        "assignee": st.column_config.TextColumn("Assignee"),
                        "priority": st.column_config.TextColumn("Priority"),
                        "due_date": st.column_config.TextColumn("Due Date (YYYY-MM-DD)"),
                        "status": st.column_config.TextColumn("Status"),
                        "description": st.column_config.TextColumn("Description", width="large"),
                    }
                )


# ============================================================
# TAB 2: Tasks & Editor
# ============================================================
with tab_tasks:
    # Get active tasks DataFrame
    df = st.session_state.tasks_df.copy() if st.session_state.extraction_done else pd.DataFrame()

    # --- Section 1: Task List (Only visible if tasks exist) ---
    if not df.empty:
        st.markdown(f"### 📋 Tasks — {st.session_state.meeting_title}")

        # --- Filters Row ---
        st.markdown("#### 🔍 Filter & Search Tasks")
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)

        with f_col1:
            search_q = st.text_input("🔎 Search", placeholder="keyword...")
        with f_col2:
            filter_status = st.multiselect("Status", STATUS_OPTIONS, default=[])
        with f_col3:
            filter_priority = st.multiselect("Priority", PRIORITY_OPTIONS, default=[])
        with f_col4:
            all_assignees = sorted(df["assignee"].dropna().unique().tolist())
            filter_assignee = st.multiselect("Assignee", all_assignees, default=[])

        # --- Apply filters ---
        filtered_df = df.copy()
        if search_q:
            mask = (
                filtered_df["name"].str.contains(search_q, case=False, na=False) |
                filtered_df["assignee"].str.contains(search_q, case=False, na=False) |
                filtered_df["description"].str.contains(search_q, case=False, na=False)
            )
            filtered_df = filtered_df[mask]
        if filter_status:
            filtered_df = filtered_df[filtered_df["status"].isin(filter_status)]
        if filter_priority:
            filtered_df = filtered_df[filtered_df["priority"].isin(filter_priority)]
        if filter_assignee:
            filtered_df = filtered_df[filtered_df["assignee"].isin(filter_assignee)]

        st.caption(f"Showing {len(filtered_df)} of {len(df)} tasks")

        # --- Read-only Dataframe ---
        st.dataframe(
            filtered_df.drop(columns=["id"]) if "id" in filtered_df.columns else filtered_df,
            use_container_width=True,
            column_config={
                "name":        st.column_config.TextColumn("Task Name", width="large"),
                "assignee":    st.column_config.TextColumn("Assignee"),
                "priority":    st.column_config.TextColumn("Priority"),
                "due_date":    st.column_config.TextColumn("Due Date (YYYY-MM-DD)"),
                "status":      st.column_config.TextColumn("Status"),
                "description": st.column_config.TextColumn("Description", width="large"),
            }
        )
    else:
        st.info("💡 No tasks to display yet. You can add one manually below or process notes in the **📝 Process Notes** tab.")

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # --- Section 2: Form columns for Edit, Add, and Delete ---
    col_add, col_edit = st.columns(2)

    # --- Left Column: ADD NEW TASK ---
    with col_add:
        st.markdown("### ➕ Add New Task")
        with st.form("add_task_form", clear_on_submit=True):
            new_name = st.text_input("Task Name*", placeholder="e.g. Fix login bug")
            new_assignee = st.text_input("Assignee", placeholder="e.g. John Doe")
            new_priority = st.selectbox("Priority", options=PRIORITY_OPTIONS, index=1)
            new_due_date = st.text_input("Due Date (YYYY-MM-DD)", placeholder="e.g. 2026-07-15")
            new_desc = st.text_area("Description", placeholder="Provide context...")
            
            submit_add = st.form_submit_button("➕ Add Task & Save", use_container_width=True)

            if submit_add:
                if not new_name.strip():
                    st.error("Task Name is required.")
                else:
                    db_gen = get_db()
                    db_session = next(db_gen)
                    try:
                        # If no meeting is active, create a "Manual Tasks" holding meeting
                        if not st.session_state.current_meeting_id:
                            manual_meeting = crud.create_meeting(
                                db=db_session,
                                title="Manual Tasks",
                                summary="Tasks added manually by the project manager outside of meeting notes.",
                                decisions=""
                            )
                            db_session.commit()
                            st.session_state.current_meeting_id = manual_meeting.id
                            st.session_state.meeting_title      = manual_meeting.title
                            st.session_state.meeting_summary    = manual_meeting.summary or ""
                            st.session_state.meeting_decisions  = ""
                            st.session_state.extraction_done    = True

                        crud.create_task(
                            db=db_session,
                            meeting_id=st.session_state.current_meeting_id,
                            task_data={
                                "name": new_name.strip(),
                                "assignee": new_assignee.strip() if new_assignee.strip() else "Unassigned",
                                "priority": new_priority,
                                "due_date": new_due_date.strip() if new_due_date.strip() else None,
                                "description": new_desc.strip()
                            }
                        )
                        db_session.commit()
                        
                        # Refresh session state cache
                        updated_tasks = crud.get_tasks_by_meeting(db_session, st.session_state.current_meeting_id)
                        st.session_state.tasks_df = crud.tasks_to_dataframe(updated_tasks)
                        st.session_state.extraction_done = True
                        st.success(f"✅ Added task: '{new_name}'")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to save: {e}")
                    finally:
                        db_session.close()

    # --- Right Column: EDIT / DELETE TASK ---
    with col_edit:
        st.markdown("### ✏️ Edit or Delete Task")
        
        if df.empty:
            st.info("No tasks available to edit or delete yet.")
        else:
            # Build list of tasks for the selection dropdown
            task_options = {
                f"{row['name']} ({row['assignee']})": index
                for index, row in df.iterrows()
            }
            
            selected_task_label = st.selectbox(
                "Choose task to edit or delete:",
                options=list(task_options.keys())
            )

            if selected_task_label:
                task_idx = task_options[selected_task_label]
                task_row = df.loc[task_idx]
                task_id = int(task_row["id"])

                with st.form("edit_task_form"):
                    edit_name = st.text_input("Task Name*", value=task_row["name"])
                    edit_assignee = st.text_input("Assignee", value=task_row["assignee"])
                    
                    # Find index for selectbox options
                    p_idx = PRIORITY_OPTIONS.index(task_row["priority"]) if task_row["priority"] in PRIORITY_OPTIONS else 1
                    s_idx = STATUS_OPTIONS.index(task_row["status"]) if task_row["status"] in STATUS_OPTIONS else 0
                    
                    edit_priority = st.selectbox("Priority", options=PRIORITY_OPTIONS, index=p_idx)
                    edit_status = st.selectbox("Status", options=STATUS_OPTIONS, index=s_idx)
                    edit_due_date = st.text_input("Due Date (YYYY-MM-DD)", value=task_row["due_date"])
                    edit_desc = st.text_area("Description", value=task_row["description"])

                    c_save, c_delete = st.columns(2)
                    with c_save:
                        submit_edit = st.form_submit_button("💾 Save Edits", use_container_width=True)
                    with c_delete:
                        submit_delete = st.form_submit_button("🗑️ Delete Task", use_container_width=True)

                    if submit_edit:
                        if not edit_name.strip():
                            st.error("Task Name is required.")
                        else:
                            db_gen = get_db()
                            db_session = next(db_gen)
                            try:
                                # Fetch existing task from database
                                db_task = db_session.query(crud.Task).filter(crud.Task.id == task_id).first()
                                if db_task:
                                    db_task.name = edit_name.strip()
                                    db_task.assignee = edit_assignee.strip() if edit_assignee.strip() else "Unassigned"
                                    db_task.priority = edit_priority
                                    db_task.status = edit_status
                                    db_task.due_date = edit_due_date.strip() if edit_due_date.strip() else None
                                    db_task.description = edit_desc.strip()
                                    db_session.commit()
                                    
                                    # Refresh session state cache
                                    updated_tasks = crud.get_tasks_by_meeting(db_session, st.session_state.current_meeting_id)
                                    st.session_state.tasks_df = crud.tasks_to_dataframe(updated_tasks)
                                    st.success("✅ Changes saved successfully!")
                                    st.rerun()
                                else:
                                    st.error("Task not found in database.")
                            except Exception as e:
                                st.error(f"❌ Edit failed: {e}")
                            finally:
                                db_session.close()

                    if submit_delete:
                        db_gen = get_db()
                        db_session = next(db_gen)
                        try:
                            success = crud.delete_task(db_session, task_id)
                            if success:
                                # Refresh session state cache
                                updated_tasks = crud.get_tasks_by_meeting(db_session, st.session_state.current_meeting_id)
                                st.session_state.tasks_df = crud.tasks_to_dataframe(updated_tasks)
                                st.success("🗑️ Task deleted successfully!")
                                st.rerun()
                            else:
                                st.error("Task not found.")
                        except Exception as e:
                            st.error(f"❌ Delete failed: {e}")
                        finally:
                            db_session.close()


# ============================================================
# TAB 3: Visualize — Kanban Board + Gantt Timeline
# ============================================================
with tab_visual:
    if not st.session_state.extraction_done:
        st.info("💡 Process meeting notes in the **📝 Process Notes** tab first.")
    else:
        df = st.session_state.tasks_df

        viz_tab1, viz_tab2 = st.tabs(["🗂️ Kanban Board", "📅 Timeline"])

        # --- STEP 8.9.1: Kanban Board ---
        with viz_tab1:
            st.markdown("### 🗂️ Kanban Board")
            k_col1, k_col2, k_col3 = st.columns(3)

            priority_badge = {
                "High": "badge-high",
                "Medium": "badge-medium",
                "Low": "badge-low"
            }

            for col_widget, status_label, col_color in [
                (k_col1, "Todo", "#1e40af"),
                (k_col2, "In Progress", "#92400e"),
                (k_col3, "Done", "#14532d"),
            ]:
                with col_widget:
                    status_tasks = df[df["status"] == status_label] if not df.empty else pd.DataFrame()
                    st.markdown(
                        f"<div class='kanban-col-header' style='background:{col_color};color:white;'>"
                        f"{status_label} ({len(status_tasks)})</div>",
                        unsafe_allow_html=True
                    )
                    if status_tasks.empty:
                        st.markdown("<p style='color:#4b5563;font-size:0.85rem;text-align:center;'>No tasks</p>", unsafe_allow_html=True)
                    else:
                        for _, row in status_tasks.iterrows():
                            badge_cls = priority_badge.get(row.get("priority", "Medium"), "badge-medium")
                            due = escape(str(row.get("due_date", "") or "TBD"))
                            task_name = escape(str(row.get('name', 'Unnamed')))
                            task_assignee = escape(str(row.get('assignee', 'Unassigned')))
                            task_priority = escape(str(row.get('priority', 'Medium')))
                            st.markdown(f"""
                            <div class='task-card'>
                                <h4>{task_name}</h4>
                                <p>👤 {task_assignee}</p>
                                <p>📅 {due}</p>
                                <p><span class='{badge_cls}'>{task_priority}</span></p>
                            </div>
                            """, unsafe_allow_html=True)

        # --- STEP 8.9.2: Gantt Timeline ---
        with viz_tab2:
            st.markdown("### 📅 Task Timeline")

            if df.empty:
                st.warning("No tasks to display on the timeline.")
            else:
                # Prepare timeline data — only tasks with valid due dates
                timeline_df = df[df["due_date"].notna() & (df["due_date"] != "")].copy()

                # Filter to only rows with valid YYYY-MM-DD dates (prevents Plotly crash)
                def _is_valid_date(d):
                    try:
                        datetime.strptime(str(d), "%Y-%m-%d")
                        return True
                    except (ValueError, TypeError):
                        return False

                timeline_df = timeline_df[timeline_df["due_date"].apply(_is_valid_date)].copy()

                if timeline_df.empty:
                    st.info("No tasks have due dates set. Add due dates to see the timeline.")
                else:
                    # Add a start date (today) and end date (due_date) for Gantt
                    timeline_df["Start"] = datetime.today().strftime("%Y-%m-%d")
                    timeline_df["Finish"] = timeline_df["due_date"]
                    timeline_df["Task"] = timeline_df["name"].str[:40]

                    # Build Plotly Gantt chart using timeline
                    fig = px.timeline(
                        timeline_df,
                        x_start="Start",
                        x_end="Finish",
                        y="Task",
                        color="priority",
                        color_discrete_map={
                            "High": "#ef4444",
                            "Medium": "#f59e0b",
                            "Low": "#22c55e"
                        },
                        hover_data=["assignee", "status", "description"],
                        title="Task Deadline Timeline"
                    )
                    fig.update_yaxes(autorange="reversed")
                    fig.update_layout(
                        plot_bgcolor="#0f172a",
                        paper_bgcolor="#0f172a",
                        font_color="#e2e8f0",
                        title_font_color="#60a5fa",
                        height=max(300, len(timeline_df) * 45)
                    )
                    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# TAB 4: Export
# ============================================================
with tab_export:
    if not st.session_state.extraction_done:
        st.info("💡 Process meeting notes in the **📝 Process Notes** tab first.")
    else:
        st.markdown("### 📥 Export Meeting Report")
        st.caption("Download your meeting summary and structured tasks.")

        df = st.session_state.tasks_df

        col_e1, col_e2 = st.columns(2)

        # --- STEP 8.10.1: CSV Export ---
        with col_e1:
            st.markdown("#### 📊 CSV Export")
            st.caption("Download tasks as a CSV file compatible with Excel, Sheets, Jira.")
            if not df.empty:
                csv_bytes = export_to_csv(df)
                st.download_button(
                    label="⬇️ Download Tasks CSV",
                    data=csv_bytes,
                    file_name=f"tasks_{st.session_state.meeting_title[:30].replace(' ','_')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.warning("No tasks to export.")

        # --- STEP 8.10.2: Markdown Export ---
        with col_e2:
            st.markdown("#### 📝 Markdown Report Export")
            st.caption("Download a formatted meeting report compatible with Notion, GitHub, Obsidian.")
            md_bytes = export_to_markdown(
                title=st.session_state.meeting_title,
                summary=st.session_state.meeting_summary,
                decisions=st.session_state.meeting_decisions,
                tasks_df=df
            )
            st.download_button(
                label="⬇️ Download Markdown Report",
                data=md_bytes,
                file_name=f"report_{st.session_state.meeting_title[:30].replace(' ','_')}.md",
                mime="text/markdown",
                use_container_width=True
            )

        # --- STEP 8.10.3: Delete Meeting ---
        st.markdown("---")
        st.markdown("#### 🗑️ Delete This Meeting")
        st.warning("⚠️ This will permanently delete the meeting and ALL its tasks from the database.")
        if st.button("🗑️ Delete Meeting", type="secondary"):
            if st.session_state.current_meeting_id:
                db_gen6 = get_db()
                db6 = next(db_gen6)
                try:
                    crud.delete_meeting(db6, st.session_state.current_meeting_id)
                finally:
                    db6.close()

                # Reset session state after deletion
                for key in ["current_meeting_id", "meeting_title", "meeting_summary",
                            "meeting_decisions", "extraction_done"]:
                    st.session_state[key] = "" if isinstance(st.session_state[key], str) else None
                st.session_state.tasks_df = pd.DataFrame()
                st.session_state.extraction_done = False
                st.success("✅ Meeting deleted.")
                st.rerun()
