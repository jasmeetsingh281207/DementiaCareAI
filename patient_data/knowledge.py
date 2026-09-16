"""Read-only access to the team's external patient database.

This module never writes to data/dementiacare.db. It reads only:
    data/ext_dementia_app
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ext_dementia_app"


def get_connection() -> sqlite3.Connection:
    """Open the team DB read-only."""
    uri = DB_PATH.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def _rows(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    try:
        with get_connection() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except Exception:
        return []


def get_patient(patient_id: int = 1) -> dict[str, Any]:
    rows = _rows("""
        SELECT patient_id, full_name, preferred_name, gender, date_of_birth,
               language_code, profile_photo_url, emergency_notes
        FROM patients WHERE patient_id = ? LIMIT 1
    """, (patient_id,))
    return rows[0] if rows else {}


def get_family_members(patient_id: int = 1) -> list[dict[str, Any]]:
    # The supplied team DB uses family_members without a patient_id column.
    return _rows("""
        SELECT family_member_id, name, name_hindi, relation, relation_hindi,
               status, snippet, audio_voice_text, call_label, photo_url, is_favorite
        FROM family_members ORDER BY is_favorite DESC, family_member_id
    """)


def get_caregivers(patient_id: int = 1) -> list[dict[str, Any]]:
    return _rows("""
        SELECT c.caregiver_id, c.full_name, c.relation, c.phone, c.email,
               c.role, c.is_primary, pc.permissions
        FROM caregivers c
        LEFT JOIN patient_caregivers pc ON pc.caregiver_id = c.caregiver_id
        ORDER BY c.is_primary DESC, c.caregiver_id
    """)


def get_medications(patient_id: int = 1) -> list[dict[str, Any]]:
    return _rows("""
        SELECT medication_id, medicine_name, dosage, instructions,
               prescribed_by, start_date, end_date, is_active
        FROM medications ORDER BY is_active DESC, medication_id
    """)


def get_medication_reminders(patient_id: int = 1) -> list[dict[str, Any]]:
    return _rows("""
        SELECT mr.medication_reminder_id, m.medicine_name, m.dosage,
               mr.reminder_time, mr.dosage_instruction
        FROM medication_reminders mr
        LEFT JOIN medications m ON m.medication_id = mr.medication_id
        ORDER BY mr.reminder_time
    """)


def get_daily_routines(patient_id: int = 1) -> list[dict[str, Any]]:
    return _rows("""
        SELECT routine_id, routine_name, description, routine_time,
               category, is_active
        FROM daily_routines ORDER BY routine_time, routine_id
    """)


def get_reminders(patient_id: int = 1) -> list[dict[str, Any]]:
    return _rows("""
        SELECT reminder_id, title, description, reminder_date, reminder_time,
               category, is_completed, is_active
        FROM reminders ORDER BY reminder_date, reminder_time, reminder_id
    """, ())


def get_memories(patient_id: int = 1) -> list[dict[str, Any]]:
    return _rows("""
        SELECT milestone_id, year, category, title, location, description,
               photo_url, recall_rate
        FROM memory_milestones ORDER BY year, milestone_id
    """)


def get_memory_questions(patient_id: int = 1) -> list[dict[str, Any]]:
    return _rows("""
        SELECT q.question_id, q.milestone_id, q.question_text,
               q.question_text_hindi, q.question_type, q.points,
               o.option_id, o.option_text, o.option_text_hindi, o.is_correct
        FROM memory_questions q
        LEFT JOIN memory_question_options o ON o.question_id = q.question_id
        ORDER BY q.question_id, o.option_id
    """)


def get_emergency_contacts(patient_id: int = 1) -> list[dict[str, Any]]:
    return _rows("""
        SELECT emergency_contact_id, name, relation, phone, priority, is_active
        FROM emergency_contacts ORDER BY priority, emergency_contact_id
    """)


def get_appointments(patient_id: int = 1) -> list[dict[str, Any]]:
    return _rows("""
        SELECT appointment_id, doctor_name, hospital_name, appointment_date,
               appointment_time, appointment_type, notes, status
        FROM appointments ORDER BY appointment_date, appointment_time
    """)


def get_journal_entries(patient_id: int = 1) -> list[dict[str, Any]]:
    return _rows("""
        SELECT journal_id, title, content, mood, created_at, updated_at
        FROM journal_entries ORDER BY created_at DESC
    """)


def get_emotional_checkins(patient_id: int = 1) -> list[dict[str, Any]]:
    return _rows("""
        SELECT checkin_id, mood, note, recorded_at
        FROM emotional_checkins ORDER BY recorded_at DESC
    """)


def get_accessibility_settings(patient_id: int = 1) -> dict[str, Any]:
    rows = _rows("""
        SELECT language_code, text_size, voice_tone, speech_speed, volume,
               hands_free, speak_typed_replies
        FROM accessibility_settings LIMIT 1
    """)
    return rows[0] if rows else {}


def get_patient_context(patient_id: int = 1) -> dict[str, Any]:
    """Return a compact, safe structured context for Gemini."""
    return {
        "patient": get_patient(patient_id),
        "family_members": get_family_members(patient_id),
        "caregivers": get_caregivers(patient_id),
        "medications": get_medications(patient_id),
        "medication_reminders": get_medication_reminders(patient_id),
        "daily_routines": get_daily_routines(patient_id),
        "reminders": get_reminders(patient_id),
        "memories": get_memories(patient_id),
        "emergency_contacts": get_emergency_contacts(patient_id),
        "appointments": get_appointments(patient_id),
        "journal_entries": get_journal_entries(patient_id),
        "emotional_checkins": get_emotional_checkins(patient_id),
        "accessibility_settings": get_accessibility_settings(patient_id),
    }


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def search_patient_facts(message: str, patient_id: int = 1) -> list[dict[str, Any]]:
    """Find likely relevant facts without using an LLM or writing to the DB."""
    q = _norm(message)
    tokens = set(re.findall(r"[\w]+", q, flags=re.UNICODE))
    ctx = get_patient_context(patient_id)
    results: list[dict[str, Any]] = []

    def add(kind: str, item: dict[str, Any], searchable: list[Any]) -> None:
        text = _norm(" ".join(str(x) for x in searchable if x is not None))
        if any(t in text for t in tokens) or any(key in q for key in (
            "name", "family", "daughter", "son", "medicine", "medication",
            "memory", "graduation", "wedding", "birthday", "routine",
            "reminder", "appointment", "doctor", "hospital", "emergency",
            "caregiver", "journal", "mood", "feeling", "language",
            "बेटी", "बेटा", "पोता", "बहन",
            "মেয়ে", "ছেলে", "নাতি", "বোন",
            "ਧੀ", "ਪੁੱਤਰ", "ਪੋਤਾ", "ਭੈਣ",
            "மகள்", "மகன்", "பேரன்", "சகோதரி",
        )):
            results.append({"type": kind, "data": item})

    patient = ctx["patient"]
    if patient:
        add("patient", patient, patient.values())
    for item in ctx["family_members"]:
        add("family_member", item, item.values())
    for item in ctx["medications"]:
        add("medication", item, item.values())
    for item in ctx["medication_reminders"]:
        add("medication_reminder", item, item.values())
    for item in ctx["daily_routines"]:
        add("routine", item, item.values())
    for item in ctx["reminders"]:
        add("reminder", item, item.values())
    for item in ctx["memories"]:
        add("memory", item, item.values())
    for item in ctx["emergency_contacts"]:
        add("emergency_contact", item, item.values())
    for item in ctx["appointments"]:
        add("appointment", item, item.values())
    for item in ctx["journal_entries"]:
        add("journal", item, item.values())
    for item in ctx["emotional_checkins"][:5]:
        add("emotional_checkin", item, item.values())
    if ctx["accessibility_settings"]:
        add("accessibility", ctx["accessibility_settings"], ctx["accessibility_settings"].values())

    # Keep prompt size predictable.
    return results[:25]
