# ============================================================
# database/connection.py
# ============================================================
# STEP 2: Database Engine & Session Setup
#
# This module initializes the SQLAlchemy connection to SQLite.
# It is the foundation of the entire database layer.
#
# FLOW:
#   config.py (DATABASE_URL)
#       ↓
#   create_engine()   → Connects to SQLite file
#       ↓
#   SessionLocal()    → Factory to create DB sessions
#       ↓
#   get_db()          → Yields a session for each operation
#       ↓
#   init_db()         → Creates all tables on first run
# ============================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL

# ============================================================
# STEP 2.1: Create SQLAlchemy Engine
# ============================================================
# The engine is the core interface to the database.
# connect_args={"check_same_thread": False} is required for
# SQLite when used inside Streamlit, which can run callbacks
# from multiple threads simultaneously.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# ============================================================
# STEP 2.2: Create Session Factory
# ============================================================
# SessionLocal is a factory class. Every time we call
# SessionLocal(), it returns a new database session.
# autocommit=False → We manually control when to commit.
# autoflush=False  → We control when SQLAlchemy flushes queries.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ============================================================
# STEP 2.3: Create Declarative Base
# ============================================================
# Base is the parent class for all ORM models (Meeting, Task).
# When models.py imports Base, they register their table
# schemas into this shared metadata registry.
Base = declarative_base()

# ============================================================
# STEP 2.4: Session Context Manager (get_db)
# ============================================================
# get_db() is a generator function used to safely open and
# close a database session for every operation.
#
# WHY: This guarantees that every DB session is properly
# closed even if an exception occurs mid-operation, preventing
# database file locks on SQLite.
def get_db():
    """
    Yield a SQLAlchemy database session and ensure it is
    closed after the operation completes (success or failure).
    """
    db = SessionLocal()
    try:
        yield db     # hand the session to the calling function
    finally:
        db.close()   # always close to release the connection

# ============================================================
# STEP 2.5: Initialize Database Tables
# ============================================================
# init_db() is called once on app startup.
# It checks if the tables exist and creates them if not.
# We import models here (inside the function) to avoid
# circular import issues at module load time.
def init_db():
    """
    Create all database tables defined in models.py
    if they do not already exist.
    Called once at Streamlit app startup.
    """
    # Import models so SQLAlchemy registers their table schemas
    from database import models  # noqa: F401
    # Create all tables that are mapped to Base.metadata
    Base.metadata.create_all(bind=engine)
