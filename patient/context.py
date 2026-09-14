from datetime import datetime

from database import execute, fetch_one, fetch_all


PATIENT_ID = 1


LIST_TYPES = {
    "daily_routine",
    "important_people",
    "important_places",
    "important_events",
    "interests",
    "favorite_music",
    "favorite_movies",
    "favorite_activities",
    "notes"
}


def _get_patient():
    patient = fetch_one(
        """
        SELECT
            id,
            name,
            preferred_language,
            caregiver_name,
            created_at,
            updated_at
        FROM patient
        WHERE id = ?
        """,
        (PATIENT_ID,)
    )

    if patient is None:
        now = datetime.now().isoformat()

        execute(
            """
            INSERT INTO patient (
                id,
                name,
                preferred_language,
                caregiver_name,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                PATIENT_ID,
                "Patient",
                "English",
                None,
                now,
                now
            )
        )

        patient = fetch_one(
            """
            SELECT
                id,
                name,
                preferred_language,
                caregiver_name,
                created_at,
                updated_at
            FROM patient
            WHERE id = ?
            """,
            (PATIENT_ID,)
        )

    return patient


def get_patient_context():
    patient = _get_patient()

    context = {
        "name": patient["name"],
        "preferred_language": patient[
            "preferred_language"
        ],
        "caregiver_name": patient[
            "caregiver_name"
        ]
    }

    for list_type in LIST_TYPES:
        rows = fetch_all(
            """
            SELECT value
            FROM patient_lists
            WHERE patient_id = ?
              AND list_type = ?
            ORDER BY id ASC
            """,
            (
                PATIENT_ID,
                list_type
            )
        )

        context[list_type] = [
            row["value"]
            for row in rows
        ]

    return context


def update_patient_context(key, value):
    if key in {
        "name",
        "preferred_language",
        "caregiver_name"
    }:
        allowed = {
            "name",
            "preferred_language",
            "caregiver_name"
        }

        if key not in allowed:
            raise ValueError(
                f"Unknown patient context field: {key}"
            )

        execute(
            f"""
            UPDATE patient
            SET {key} = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                value,
                datetime.now().isoformat(),
                PATIENT_ID
            )
        )

        return get_patient_context()

    if key in LIST_TYPES:
        if not isinstance(value, list):
            raise ValueError(
                f"{key} must be a list."
            )

        execute(
            """
            DELETE FROM patient_lists
            WHERE patient_id = ?
              AND list_type = ?
            """,
            (
                PATIENT_ID,
                key
            )
        )

        for item in value:
            execute(
                """
                INSERT INTO patient_lists (
                    patient_id,
                    list_type,
                    value,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    PATIENT_ID,
                    key,
                    str(item),
                    datetime.now().isoformat()
                )
            )

        return get_patient_context()

    raise ValueError(
        f"Unknown patient context field: {key}"
    )


def add_to_patient_context(key, value):
    if key not in LIST_TYPES:
        raise ValueError(
            f"{key} is not a list field."
        )

    execute(
        """
        INSERT INTO patient_lists (
            patient_id,
            list_type,
            value,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            PATIENT_ID,
            key,
            str(value),
            datetime.now().isoformat()
        )
    )

    return get_patient_context()


def remove_from_patient_context(key, value):
    if key not in LIST_TYPES:
        raise ValueError(
            f"{key} is not a list field."
        )

    execute(
        """
        DELETE FROM patient_lists
        WHERE id = (
            SELECT id
            FROM patient_lists
            WHERE patient_id = ?
              AND list_type = ?
              AND value = ?
            ORDER BY id
            LIMIT 1
        )
        """,
        (
            PATIENT_ID,
            key,
            str(value)
        )
    )

    return get_patient_context()