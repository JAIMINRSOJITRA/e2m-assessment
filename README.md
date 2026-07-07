# 🤖 AI Project Manager

### Transform Meeting Notes into Structured Tasks using LLMs

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Gemini](https://img.shields.io/badge/Google_Gemini-2.5-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-000000?style=for-the-badge&logo=ollama&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

</div>

A production-ready **Streamlit** application that leverages **Google Gemini** or **local Ollama models** to automatically extract, structure, and manage project tasks from unstructured meeting content.

> **Problem Statement**: Project managers spend hours manually reviewing meeting notes, emails, and chat threads to identify action items, assign owners, set priorities, and track deadlines. This tool eliminates that manual work entirely by using AI to intelligently parse meeting content and produce structured, actionable task lists.

---

## 📑 Table of Contents

- [What This Application Does](#-what-this-application-does)
- [Core Features](#core-features)
- [System Architecture](#-system-architecture)
- [Quick Start](#-quick-start)
- [Sample Meeting Notes](#-sample-meeting-notes-for-quick-testing)
- [Tech Stack](#️-tech-stack)
- [Project Structure](#-project-structure)
- [Module Deep Dive](#-module-deep-dive)
- [Usage Guide](#-usage-guide)
- [Testing](#-testing)
- [Database Schema](#️-database-schema)
- [LLM Prompt Engineering](#-llm-prompt-engineering)
- [Security](#-security)
- [Environment Variables](#-environment-variables)
- [Troubleshooting](#-troubleshooting)
- [Deployment Options](#-deployment-options)
- [Changelog](#-changelog)
- [License](#-license)
- [Acknowledgments](#-acknowledgments)

---

## 🎯 What This Application Does

```
INPUT  →  Meeting notes (Text, PDF, DOCX, Email, Slack)
PROCESS →  AI extracts tasks with assignees, priorities, and deadlines
OUTPUT  →  Structured task list with Kanban board, Gantt chart, and export
```

The application follows a clean pipeline architecture:

```
User Input → Input Processors → LLM Extraction → Pydantic Validation → SQLite Storage → UI Rendering
```

### Core Features

| Feature | Description |
|---------|-------------|
| 📝 **5 Input Sources** | Plain Text, PDF (pypdf), Word DOCX (python-docx), Email threads, Slack conversations |
| 🤖 **Dual LLM Support** | Cloud-based Google Gemini (2.5-flash/pro/2.0-flash) or local privacy-first Ollama |
| 🧠 **Intelligent Extraction** | Identifies action items, infers priority from context, resolves relative dates (e.g., "next Monday" → `YYYY-MM-DD`) |
| ✏️ **Full CRUD Interface** | Add, edit, delete, filter, and search tasks with a rich interactive editor |
| 🗂️ **Kanban Board** | Visual board with Todo / In Progress / Done columns and priority badges |
| 📅 **Gantt Timeline** | Interactive Plotly timeline chart with color-coded priorities |
| 📥 **Export Options** | CSV (Excel/Jira-compatible) and formatted Markdown reports (Notion/GitHub/Obsidian) |
| 💾 **Persistent Storage** | SQLite database with full meeting history and session reload |
| 🔐 **Security Hardened** | XSS protection, SQL injection prevention, input validation, field whitelisting |
| 🧪 **Production Tested** | 71 unit tests covering all layers: database, parser, processors, and exports |
| 📊 **Smart Filtering** | Clickable metric cards for quick task filtering by status/priority |
| 🗑️ **Meeting Management** | Delete meetings with cascading task removal, load past meetings from history |

---

## 📐 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER INTERFACE (Streamlit)                    │
│  ┌──────────────┬────────────┬──────────────┬──────────────┐   │
│  │  📝 Process  │ 📋 Tasks   │ 📊 Visualize │  📥 Export   │   │
│  │    Notes     │  & Editor  │    Board     │    Data      │   │
│  └──────────────┴────────────┴──────────────┴──────────────┘   │
│  Sidebar: ⚙️ LLM Settings + 📂 Meeting History                │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────┐
│                  INPUT PROCESSORS LAYER                          │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐      │
│  │   Text   │   PDF    │   DOCX   │  Email   │  Slack   │      │
│  │ cleaner  │ (pypdf)  │ (docx)   │ header   │ system   │      │
│  │          │          │          │ stripper │ msg filter│      │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘      │
└────────────────────────────┬────────────────────────────────────┘
                             │ Clean Plain Text
┌────────────────────────────┴────────────────────────────────────┐
│                     LLM EXTRACTION LAYER                        │
│  ┌───────────────────┐        ┌───────────────────┐            │
│  │  Gemini (Cloud)   │        │  Ollama (Local)   │            │
│  │  google-genai SDK │        │  ollama Python SDK│            │
│  └─────────┬─────────┘        └─────────┬─────────┘            │
│            │   System Prompt (475 lines) │                      │
│            │   + User Prompt w/ today's  │                      │
│            │     date for relative dates │                      │
│            └────────────┬────────────────┘                      │
└─────────────────────────┬──────────────────────────────────────┘
                          │ Raw JSON Response
┌─────────────────────────┴──────────────────────────────────────┐
│  VALIDATION         SERVICES              DATABASE              │
│  ┌──────────┐     ┌──────────────┐     ┌──────────────────┐    │
│  │ Pydantic │ ──► │ task_service  │ ──► │ SQLAlchemy ORM   │    │
│  │ parser.py│     │ (atomic txn) │     │ (SQLite)         │    │
│  └──────────┘     ├──────────────┤     │  meetings table  │    │
│                   │export_service│     │  tasks table     │    │
│                   │ (CSV + MD)   │     │  (cascade delete)│    │
│                   └──────────────┘     └──────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

### Data Flow (Step-by-Step)

1. **User provides input** → selects source type (Text/PDF/DOCX/Email/Slack)
2. **Input Processor** → normalizes and cleans raw content into plain text
3. **Prompt Builder** → constructs system prompt (475 lines) + user prompt with today's date
4. **LLM Call** → Gemini API or Ollama local model generates structured JSON
5. **Pydantic Validation** → `MeetingOutput` schema validates fields, applies defaults, normalizes data
6. **Task Service** → orchestrates atomic DB write (Meeting + Tasks in one transaction)
7. **Database** → SQLAlchemy ORM persists to SQLite with cascade relationships
8. **UI Rendering** → Streamlit displays results across 4 tabs with session state management

---

## ⚡ Quick Start

### Prerequisites

- **Python 3.10+**
- **Gemini API Key** ([get one free](https://aistudio.google.com/app/apikey)) **OR** **Ollama** installed locally

### Installation

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd "AI Project Manager Meeting Notes to Structured Tasks using LLMs"

# 2. Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 5. Run the application
streamlit run app.py
```

Open browser at `http://localhost:8501`

### Optional: Setup Ollama (Local LLM)

```bash
# Download from https://ollama.com, then:
ollama pull phi3       # Microsoft Phi-3 (2.3 GB) — Recommended
ollama pull llama3     # Meta Llama 3 — Alternative
ollama serve           # Start the server
```

> **Tip**: Switch between Gemini and Ollama anytime via the sidebar dropdown — no restart needed.

---

## 📋 Sample Meeting Notes (For Quick Testing)

Paste this into the app to test immediately:

```
Sprint Planning Meeting - July 7, 2026

Attendees: Alice Chen, Bob Kumar, Carol Lee, Dave Wilson

Alice: Let's finalize the Q3 roadmap. Bob, can you handle the API gateway refactor? 
It's blocking the mobile team.

Bob: Yes, I'll start today. Should be done by Wednesday.

Alice: Great. Carol, please review the updated UI mockups by Friday. We need 
sign-off before the beta launch.

Carol: Will do. Are we still targeting August 15th for beta?

Alice: Yes, confirmed. Dave, we need the database migration script ready by 
next Monday. This is critical — the staging environment depends on it.

Dave: Got it. I'll also write the rollback procedure just in case.

Decisions:
- Beta launch confirmed for August 15th
- API gateway refactor is top priority (blocking mobile)
- All code must have unit tests before merge
```

**Expected Output:** 3 tasks extracted with assignees (Bob, Carol, Dave), priorities (High/Medium), and resolved deadlines.

---

## 🛠️ Tech Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| **Streamlit** | ≥1.35.0 | Web UI framework with reactive widgets and session state |
| **Google GenAI SDK** | ≥1.0.0 | Cloud LLM client for Gemini 2.5-flash/pro/2.0-flash |
| **Ollama** | ≥0.2.0 | Local/private LLM alternative via Python SDK |
| **SQLAlchemy** | ≥2.0.0 | Database ORM with declarative models and session management |
| **SQLite** | Built-in | Zero-config persistent storage (auto-created on first run) |
| **Pydantic** | ≥2.0.0 | Strict JSON schema validation for LLM outputs |
| **Pandas** | ≥2.0.0 | Tabular data manipulation for task DataFrames |
| **Plotly** | ≥5.20.0 | Interactive Gantt timeline chart with dark theme |
| **pypdf** | ≥4.0.0 | PDF text extraction (text-based PDFs only) |
| **python-docx** | ≥1.1.0 | Word .docx paragraph and table text extraction |
| **python-dotenv** | ≥1.0.0 | Environment variable loading from `.env` file |

---

## 📂 Project Structure

```
project_root/
│
├── app.py                          # 🎯 Streamlit UI entry point (941 lines)
│                                   #    4 tabs: Process Notes, Tasks & Editor,
│                                   #    Visualize, Export
│                                   #    Manages session state, CSS styling,
│                                   #    sidebar settings, and meeting history
│
├── config.py                       # ⚙️ Central configuration loader (71 lines)
│                                   #    Reads .env, exports all constants
│
├── requirements.txt                # 📦 Python dependencies (10 packages)
├── .env.example                    # 🔑 Environment template (copy to .env)
├── .gitignore                      # 🚫 Git exclusions (.env, *.db, __pycache__)
│
├── input_processors/               # 📥 Input format converters
│   ├── __init__.py                 #    Package initializer
│   ├── text_processor.py           #    Plain text cleaner (whitespace normalization)
│   ├── pdf_processor.py            #    PDF extractor via pypdf (page-by-page)
│   ├── docx_processor.py           #    Word document parser (paragraphs + tables)
│   ├── email_processor.py          #    Email thread cleaner (header/quote removal)
│   └── slack_processor.py          #    Slack message formatter (system msg filter)
│
├── llm/                            # 🤖 AI extraction layer
│   ├── __init__.py                 #    Package initializer
│   ├── prompt.py                   #    System prompt (475 lines) + user prompt builder
│   ├── extractor.py                #    Gemini & Ollama API clients + routing
│   └── parser.py                   #    Pydantic models (TaskOutput, MeetingOutput)
│                                   #    + JSON parsing with code-fence stripping
│
├── database/                       # 💾 Data persistence layer
│   ├── __init__.py                 #    Package initializer
│   ├── connection.py               #    SQLAlchemy engine, session factory, init_db()
│   ├── models.py                   #    Meeting & Task ORM models (cascade delete)
│   └── crud.py                     #    10 CRUD operations with rollback support
│
├── services/                       # ⚡ Business logic
│   ├── __init__.py                 #    Package initializer
│   ├── task_service.py             #    LLM → Validation → DB atomic pipeline
│   └── export_service.py           #    CSV & Markdown report generators
│
└── tests/                          # 🧪 Unit test suite (71 tests)
    ├── __init__.py                 #    Package initializer
    ├── test_database.py            #    20 tests — Meeting & Task CRUD operations
    ├── test_export_service.py      #    16 tests — CSV & Markdown output
    ├── test_input_processors.py    #    15 tests — All 5 input processors
    └── test_parser.py              #    20 tests — Pydantic validation & edge cases
```

---

## 🔬 Module Deep Dive

### Input Processors (`input_processors/`)

Each processor converts a specific input format into clean plain text for the LLM:

| Processor | Input Format | Key Operations |
|-----------|-------------|----------------|
| `text_processor.py` | Raw text | Strip whitespace, collapse blank lines |
| `pdf_processor.py` | PDF bytes | pypdf page-by-page extraction, page separators |
| `docx_processor.py` | DOCX bytes | Paragraph + table extraction, cell pipe-joining |
| `email_processor.py` | Email body | Header removal (From/To/CC/Subject/Date), quote stripping (`>`), signature detection |
| `slack_processor.py` | Slack thread | System message filtering (joined/left/pinned), conversation header labeling |

### LLM Layer (`llm/`)

| File | Purpose |
|------|---------|
| `prompt.py` | **475-line system prompt** defining the AI Project Manager role, task identification rules, priority detection keywords (High/Medium/Low), date normalization rules, and strict JSON output schema. Also injects today's date for relative date resolution. |
| `extractor.py` | Dual-provider routing: `call_gemini()` uses `google-genai` SDK, `call_ollama()` uses `ollama` Python SDK with chat interface. Both return raw JSON strings. |
| `parser.py` | Pydantic v2 models — `TaskOutput` (6 fields with validators for priority, assignee, due_date) and `MeetingOutput` (title, summary, decisions list, tasks list). Strips markdown code fences before parsing. |

### Database Layer (`database/`)

| File | Purpose |
|------|---------|
| `connection.py` | Creates SQLAlchemy engine with `check_same_thread=False` for Streamlit multi-thread safety. Provides `SessionLocal` factory, `Base` declarative base, and `get_db()` generator for safe session lifecycle management. |
| `models.py` | Two ORM models: `Meeting` (id, title, summary, decisions, created_at) and `Task` (id, meeting_id FK, name, assignee, priority, due_date, description, status, created_at). Uses `cascade="all, delete-orphan"` for parent-child cleanup. Timezone-aware UTC timestamps via `datetime.now(timezone.utc)`. |
| `crud.py` | 10 CRUD functions: `create_meeting`, `create_task`, `get_all_meetings`, `get_meeting_by_id`, `get_tasks_by_meeting`, `tasks_to_dataframe`, `update_task_field` (with whitelist), `bulk_update_tasks`, `delete_meeting`, `delete_task`. All mutations use try/except with rollback. |

### Services Layer (`services/`)

| File | Purpose |
|------|---------|
| `task_service.py` | `process_meeting()` — the main pipeline function. Calls LLM extractor → creates Meeting + Tasks in one atomic transaction → commits or rolls back entirely. Returns new meeting ID to the UI. |
| `export_service.py` | `export_to_csv()` — drops internal ID, renames columns to Title Case, returns UTF-8 bytes. `export_to_markdown()` — generates a full report with title, summary, decisions, and task table compatible with Notion/GitHub/Obsidian. |

---

## 🎮 Usage Guide

### Step-by-Step Workflow

1. **Select LLM Provider** (Sidebar) → Choose between Gemini (Cloud) or Ollama (Local)
2. **Choose Model** (Sidebar) → Gemini: `gemini-2.5-flash` / `gemini-2.5-pro` / `gemini-2.0-flash` | Ollama: any pulled model
3. **Select Input Source** (Tab 1) → Text, PDF, DOCX, Email, or Slack
4. **Paste or Upload Content** → Click **"✨ Generate Project Plan"**
5. **Review AI Results** → Meeting title, summary, decisions, and clickable metric cards
6. **Filter Tasks** → Click metric cards (Total / High Priority / Todo / Done) for quick filtering
7. **Manage Tasks** (Tab 2) → Advanced filter/search, add new tasks, edit or delete existing ones
8. **Visualize** (Tab 3) → Kanban board with drag-like columns + Plotly Gantt timeline
9. **Export** (Tab 4) → Download as CSV or Markdown report
10. **Meeting History** (Sidebar) → Load any previously processed meeting
11. **Delete Meeting** (Tab 4) → Permanently remove meeting and all its tasks

### Manual Task Management

- **Add tasks** without processing notes — the app auto-creates a "Manual Tasks" meeting container
- **Edit any field** — name, assignee, priority, status, due date, description
- **Delete individual tasks** — removes from database with instant UI refresh

---

## 🧪 Testing

```bash
# Run all 71 tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_parser.py -v

# Run with coverage (if coverage is installed)
python -m pytest tests/ -v --cov=.

# Expected output:
# 71 passed in ~4s ✅
```

### Test Coverage Breakdown

| Test File | Tests | What's Tested |
|-----------|-------|---------------|
| `test_database.py` | 20 | Meeting & Task CRUD, cascade delete, DataFrame conversion, rollback handling, edge cases |
| `test_export_service.py` | 16 | CSV generation, Markdown report formatting, UTF-8 encoding, empty DataFrame handling, column renaming |
| `test_input_processors.py` | 15 | All 5 processors: whitespace cleanup, header removal, system message filtering, empty input guards |
| `test_parser.py` | 20 | Pydantic validation, priority normalization, assignee defaults, date format validation, code-fence stripping, malformed JSON handling |

> **Note:** Tests use in-memory SQLite databases and don't require any LLM API keys.

---

## 🗄️ Database Schema

### Entity Relationship

```
┌──────────────────┐       ┌──────────────────────┐
│    meetings      │       │       tasks           │
├──────────────────┤       ├──────────────────────┤
│ id       (PK)   │──1:N─►│ id          (PK)     │
│ title    (255)   │       │ meeting_id  (FK) ────┘
│ summary  (TEXT)  │       │ name        (512)     │
│ decisions(TEXT)  │       │ assignee    (255)     │
│ created_at (UTC) │       │ priority    (50)      │
└──────────────────┘       │ due_date    (20)      │
                           │ description (TEXT)     │
                           │ status      (50)       │
                           │ created_at  (UTC)      │
                           └───────────────────────┘
```

### `meetings` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK, Auto-increment | Unique meeting identifier |
| `title` | VARCHAR(255) | NOT NULL, Default: "Untitled Meeting" | AI-generated meeting name |
| `summary` | TEXT | Nullable | AI-written paragraph summary (≤120 words) |
| `decisions` | TEXT | Nullable | Markdown bullet list of confirmed decisions |
| `created_at` | DATETIME (TZ) | Default: UTC now | Timezone-aware creation timestamp |

### `tasks` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK, Auto-increment | Unique task identifier |
| `meeting_id` | INTEGER | FK → meetings.id, CASCADE DELETE | Parent meeting reference |
| `name` | VARCHAR(512) | NOT NULL | Actionable task title (starts with verb) |
| `assignee` | VARCHAR(255) | Default: "Unassigned" | Person responsible |
| `priority` | VARCHAR(50) | Default: "Medium" | High / Medium / Low |
| `due_date` | VARCHAR(20) | Nullable | YYYY-MM-DD or null if unspecified |
| `description` | TEXT | Nullable | Brief context (1–2 sentences) |
| `status` | VARCHAR(50) | Default: "Todo" | Todo / In Progress / Done |
| `created_at` | DATETIME (TZ) | Default: UTC now | Timezone-aware creation timestamp |

> **Cascade Delete**: Deleting a meeting automatically deletes all its child tasks — both at the ORM level (`cascade="all, delete-orphan"`) and database level (`ondelete="CASCADE"`).

---

## 🧠 LLM Prompt Engineering

The system prompt (`llm/prompt.py`) is a **475-line professional prompt** that instructs the LLM to behave as an expert AI Project Manager. Key sections include:

| Section | Purpose |
|---------|---------|
| **Role Definition** | 10+ years experience in Agile Scrum, sprint planning, product development |
| **Task Identification Rules** | What qualifies as a task (verb-led action items) vs. what to ignore (greetings, opinions, questions) |
| **Priority Detection** | Keyword lists for High (urgent, blocker, ASAP), Medium (review, planned), Low (backlog, optional) |
| **Date Normalization** | Resolves "next Monday", "this Friday", "end of month" using injected today's date |
| **Assignee Extraction** | Named person or "Unassigned" — never invents names |
| **Duplicate Handling** | Merges repeated tasks, combines context into description |
| **JSON Schema** | Strict output format with title, summary, decisions[], tasks[] |
| **Quality Checklist** | 10-point self-validation before final output |

---

## 🔐 Security

| Protection | Implementation |
|-----------|----------------|
| **SQL Injection** | SQLAlchemy ORM with parameterized queries — no raw SQL anywhere |
| **XSS Prevention** | `html.escape()` on all LLM-generated content before HTML rendering |
| **Attribute Injection** | Field whitelist (`ALLOWED_UPDATE_FIELDS`) in `update_task_field()` |
| **Input Validation** | Pydantic v2 schemas with field validators for priority, assignee, due_date |
| **Date Validation** | Invalid dates filtered with `datetime.strptime()` before Gantt rendering |
| **API Key Safety** | `.env` file excluded via `.gitignore`; key validated before API call |
| **Transaction Safety** | All DB mutations wrapped in `try/except` with `db.rollback()` on failure |
| **Session Safety** | `get_db()` generator guarantees session closure via `finally` block |
| **Thread Safety** | SQLite engine configured with `check_same_thread=False` for Streamlit |

---

## 🔑 Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# --- PRIMARY LLM: Google Gemini ---
GEMINI_API_KEY=YOUR_API_KEY_HERE     # Required for Gemini provider
GEMINI_MODEL=gemini-2.5-flash        # Default model (fast + accurate)

# --- SECONDARY LLM: Local Ollama ---
OLLAMA_BASE_URL=http://localhost:11434  # Ollama server URL
OLLAMA_MODEL=phi3                       # Default local model

# --- DATABASE ---
DATABASE_URL=sqlite:///project_manager.db  # Auto-created on first run
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes (for Gemini) | `""` | Google AI Studio API key |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model variant |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server address |
| `OLLAMA_MODEL` | No | `llama3` | Default Ollama model name |
| `DATABASE_URL` | No | `sqlite:///project_manager.db` | SQLite database path |

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| `"GEMINI_API_KEY is not set"` | Ensure `.env` exists in the project root with a valid key. Restart the app after changes. |
| `"Ollama call failed"` | Run `ollama serve` first, then verify with `ollama list`. Check the `OLLAMA_BASE_URL` in `.env`. |
| `"LLM returned invalid JSON"` | Try a different model (e.g., switch from `phi3` to `llama3`), or simplify your input text. |
| `"No tasks extracted"` | Use explicit action language: *"John will..."*, *"by Friday"*, *"fix the bug"*. Vague notes produce fewer tasks. |
| PDF returns empty text | Scanned/image-only PDFs need OCR — use text-based PDFs or paste content directly. |
| Database locked error | Close other app instances or database browsers. Restart Streamlit with `streamlit run app.py`. |
| Gantt chart not showing | Ensure tasks have valid `YYYY-MM-DD` due dates. Tasks without dates are excluded from the timeline. |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` in your virtual environment. |
| Port 8501 already in use | Kill the existing process or use `streamlit run app.py --server.port 8502`. |

---

## 🚀 Deployment Options

### Streamlit Cloud (Free)

```bash
# 1. Push to GitHub
# 2. Deploy at https://share.streamlit.io
# 3. Add secrets in Settings → Secrets (TOML format):
#    GEMINI_API_KEY = "your-api-key-here"
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
# Build and run
docker build -t ai-project-manager .
docker run -p 8501:8501 --env-file .env ai-project-manager
```

### Railway / Render

```bash
# Add these environment variables in the platform dashboard:
# GEMINI_API_KEY=your-key
# Then set the start command:
streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

---

## 🔄 Changelog

### v1.1.0 (Current)
- 🛡️ XSS protection on all LLM-rendered HTML via `html.escape()`
- 🛡️ Attribute injection prevention with `ALLOWED_UPDATE_FIELDS` whitelist
- 🛡️ DataFrame column validation in `bulk_update_tasks()`
- 🐛 Gantt crash fix on invalid/malformed dates
- 🔧 Ollama client now respects configured `OLLAMA_BASE_URL`
- 🔧 Transaction rollbacks on all DB mutation operations
- 🔧 Exception chains preserved with `raise ... from e` for debugging
- 🔧 UTC timestamps consistent across exports (timezone-aware `datetime.now(timezone.utc)`)
- 📊 Clickable metric cards with CSS hover effects for task filtering
- ✏️ Full task CRUD: add, edit, delete individual tasks with form-based UI
- 🗑️ Meeting deletion with cascade cleanup and session state reset

### v1.0.0
- 🎉 Initial release with all core features
- 📝 5 input sources: Text, PDF, DOCX, Email, Slack
- 🤖 Dual LLM support: Gemini + Ollama
- 🗂️ Kanban board + Gantt timeline visualization
- 📥 CSV and Markdown export
- 🧪 71 unit tests with full layer coverage
- 💾 SQLite persistence with Pydantic validation

---

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **[Streamlit](https://streamlit.io)** — Python web UI framework
- **[Google Gemini](https://ai.google.dev)** — Cloud LLM API
- **[Ollama](https://ollama.com)** — Local LLM runtime
- **[SQLAlchemy](https://sqlalchemy.org)** — Python ORM
- **[Pydantic](https://docs.pydantic.dev)** — Data validation
- **[Plotly](https://plotly.com)** — Interactive charts
- **[pypdf](https://pypdf.readthedocs.io)** — PDF text extraction
- **[python-docx](https://python-docx.readthedocs.io)** — Word document parsing

---

<div align="center">

**Built with ❤️ for Project Managers who want to spend less time on notes and more time on execution.**

*Last Updated: July 7, 2026 · Version 1.1.0*

</div>
