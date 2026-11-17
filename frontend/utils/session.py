import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import streamlit as st

from frontend.config import DATA_DIR, HISTORY_FILE, QUARANTINE_DIR, DEFAULT_BACKEND_URL
from frontend.api_client import APIClient

logger = logging.getLogger(__name__)


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_persistent_history() -> List[Dict[str, Any]]:
    """Load persistent report history from disk."""
    ensure_data_dir()
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception as e:
        logger.error(f"Failed to load persistent history: {e}")
    return []


def save_persistent_history(history: List[Dict[str, Any]]):
    """Save report history to disk."""
    ensure_data_dir()
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to save persistent history: {e}")


def load_quarantined_reports() -> List[Dict[str, Any]]:
    """Load rejected reports stored in data/quarantine."""
    if not QUARANTINE_DIR.exists():
        return []
    quarantined = []
    for filepath in QUARANTINE_DIR.glob("*.json"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                record = json.load(f)
                record["filename"] = filepath.name
                quarantined.append(record)
        except Exception as e:
            logger.warning(f"Failed to read quarantine file {filepath}: {e}")
    # Sort descending by received_at
    quarantined.sort(key=lambda x: x.get("received_at", ""), reverse=True)
    return quarantined


def init_session_state():
    """Initialize Streamlit session state."""
    if "backend_url" not in st.session_state:
        st.session_state.backend_url = DEFAULT_BACKEND_URL

    if "api_client" not in st.session_state:
        st.session_state.api_client = APIClient(st.session_state.backend_url)

    if "history" not in st.session_state:
        st.session_state.history = load_persistent_history()

    if "active_case" not in st.session_state:
        # If history exists, set latest as active
        if st.session_state.history:
            st.session_state.active_case = st.session_state.history[0]
        else:
            st.session_state.active_case = None


def add_or_update_history_record(record: Dict[str, Any]):
    """Add new record or update existing one in session state and disk."""
    ensure_data_dir()
    history = st.session_state.get("history", [])

    # Check if record with same run_id or case_id exists
    found_idx = None
    if record.get("run_id"):
        for i, item in enumerate(history):
            if item.get("run_id") == record["run_id"]:
                found_idx = i
                break
    elif record.get("case_id"):
        for i, item in enumerate(history):
            if item.get("case_id") == record["case_id"] and item.get("submitted_at") == record.get("submitted_at"):
                found_idx = i
                break

    if found_idx is not None:
        history[found_idx].update(record)
    else:
        history.insert(0, record)

    st.session_state.history = history
    st.session_state.active_case = record
    save_persistent_history(history)


def sync_runs_with_backend():
    """
    Query backend for the latest status of any queued or running reports.
    Updates persistent storage with latest Redis data.
    """
    client: APIClient = st.session_state.get("api_client")
    if not client:
        return

    history = st.session_state.get("history", [])
    updated = False

    for item in history:
        run_id = item.get("run_id")
        # Only poll if we have a run_id and status is queued or running
        if run_id and item.get("status") in ("queued", "running"):
            res = client.get_run_status(run_id)
            if res.get("success") and res.get("data"):
                data = res["data"]
                item["status"] = data.get("status", item["status"])
                item["updated_at"] = data.get("updated_at")
                if data.get("result"):
                    item["result"] = data["result"]
                    # Extract priority & verification
                    triage = data["result"].get("triage_result") or {}
                    verification = data["result"].get("verification_result") or {}
                    item["priority"] = triage.get("priority", item.get("priority"))
                    item["verified"] = verification.get("verified", item.get("verified"))
                if data.get("error"):
                    item["error"] = data["error"]
                updated = True

    if updated:
        st.session_state.history = history
        save_persistent_history(history)
