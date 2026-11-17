import os
from pathlib import Path

# Base paths
FRONTEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = FRONTEND_DIR.parent
DATA_DIR = FRONTEND_DIR / "data"
ASSETS_DIR = FRONTEND_DIR / "assets"
HISTORY_FILE = DATA_DIR / "history.json"
QUARANTINE_DIR = PROJECT_DIR / "data" / "quarantine"

# Backend configuration
DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
DEFAULT_TIMEOUT = 15  # seconds

# Sample Clinical Presets for Quick Testing & Demonstration
SAMPLE_PRESETS = {
    "Preset 1: Carbamazepine SJS/TEN (Urgent Review)": {
        "case_id": "PV-2026-CBZ-001",
        "drug_name": "Carbamazepine",
        "reaction_description": (
            "Patient developed high fever, widespread mucosal erosions, and severe skin peeling "
            "consistent with Stevens-Johnson syndrome and toxic epidermal necrolysis 12 days after "
            "starting carbamazepine therapy for trigeminal neuralgia."
        ),
        "patient_age": 42,
        "reporter_type": "doctor",
        "outcome": "not_recovered",
        "event_onset_days": 12,
        "hospitalization": True,
        "death": False,
    },
    "Preset 2: Routine Mild Dermatitis (Routine Review)": {
        "case_id": "PV-2026-DERM-002",
        "drug_name": "Cetirizine",
        "reaction_description": (
            "Patient reported mild localized pruritus and transient dry mouth. "
            "Symptoms resolved spontaneously upon dosage reduction."
        ),
        "patient_age": 28,
        "reporter_type": "patient",
        "outcome": "recovered",
        "event_onset_days": 3,
        "hospitalization": False,
        "death": False,
    },
    "Preset 3: Severe Fatal Reaction (Seriousness: Death)": {
        "case_id": "PV-2026-FATAL-003",
        "drug_name": "Carbamazepine",
        "reaction_description": (
            "Patient experienced acute respiratory collapse and severe anaphylaxis with diffuse "
            "skin blistering following initial dose escalation. Patient expired in the intensive care unit."
        ),
        "patient_age": 67,
        "reporter_type": "doctor",
        "outcome": "death",
        "event_onset_days": 2,
        "hospitalization": True,
        "death": True,
    },
    "Preset 4: Pediatric Dyspnea (Urgent Review)": {
        "case_id": "PV-2026-PED-004",
        "drug_name": "Amoxicillin",
        "reaction_description": (
            "Child presented with acute urticaria, facial edema, and difficulty breathing within "
            "30 minutes of oral administration. Required emergency epinephrine."
        ),
        "patient_age": 7,
        "reporter_type": "pharmacist",
        "outcome": "recovering",
        "event_onset_days": 1,
        "hospitalization": True,
        "death": False,
    },
}
