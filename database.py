"""
db/database.py
──────────────
Shared SQLAlchemy engine and session factory.
Reads DATABASE_URL from Streamlit secrets (or falls back to SQLite).
"""
import os
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ── Connection URL ──────────────────────────────────────────────────────────
def _get_database_url() -> str:
    try:
        return st.secrets["DATABASE_URL"]
    except (KeyError, FileNotFoundError):
        return os.environ.get("DATABASE_URL", "sqlite:///presenze.db")

DATABASE_URL = _get_database_url()

# SQLite needs check_same_thread=False for Streamlit's threading model
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine  = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base    = declarative_base()


def get_session():
    """Return a new database session. Always close it in a finally block."""
    return Session()


def init_db():
    """Create all tables if they don't exist yet. Safe to call multiple times."""
    from db.models import Student, SessionModel, Attendance  # noqa: F401
    Base.metadata.create_all(engine)
