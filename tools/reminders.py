from datetime import datetime
import threading
import time

from database import execute, fetch_one, fetch_all


DATE_TIME_FORMAT = "%Y-%m-%d %H:%M"

service_started = False
service_lock = threading.Lock()


# =========================================================
# CREATE REMINDER
# =========================================================

def create_reminder(message, reminder_time):

    if not message:
        raise ValueError("Reminder message is required.")

    if not reminder_time:
        raise ValueError("Reminder time is required.")

    try:
        scheduled_time = datetime.strptime(
            reminder_time,
            DATE_TIME_FORMAT
        )

    except ValueError:
        raise ValueError(
            "Reminder time must use "
            "YYYY-MM-DD HH:MM format."
        )

    reminder_id = execute(
        """
        INSERT INTO reminders (
            message,
            reminder_time,
            created_at,
            status
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            message,
            scheduled_time.strftime(DATE_TIME_FORMAT),
            datetime.now().isoformat(),
            "scheduled"
        )
    )

    return get_reminder(reminder_id)


# =========================================================
# GET ONE REMINDER
# =========================================================

def get_reminder(reminder_id):

    return fetch_one(
        """
        SELECT
            id,
            message,
            reminder_time AS time,
            created_at,
            status
        FROM reminders
        WHERE id = ?
        """,
        (reminder_id,)
    )


# =========================================================
# GET ALL REMINDERS
# =========================================================

def get_reminders():

    return fetch_all(
        """
        SELECT
            id,
            message,
            reminder_time AS time,
            created_at,
            status
        FROM reminders
        ORDER BY reminder_time ASC
        """
    )


# =========================================================
# GET DUE REMINDERS
# =========================================================

def get_due_reminders():

    return fetch_all(
        """
        SELECT
            id,
            message,
            reminder_time AS time,
            created_at,
            status
        FROM reminders
        WHERE status = 'due'
        ORDER BY reminder_time ASC
        """
    )


# =========================================================
# GET NEXT DUE REMINDER
# =========================================================

def get_next_due_reminder():

    return fetch_one(
        """
        SELECT
            id,
            message,
            reminder_time AS time,
            created_at,
            status
        FROM reminders
        WHERE status = 'due'
        ORDER BY reminder_time ASC
        LIMIT 1
        """
    )


# =========================================================
# UPDATE SCHEDULED REMINDERS TO DUE
# =========================================================

def update_due_reminders():

    current_time = datetime.now().strftime(
        DATE_TIME_FORMAT
    )

    execute(
        """
        UPDATE reminders
        SET status = 'due'
        WHERE status = 'scheduled'
        AND reminder_time <= ?
        """,
        (current_time,)
    )

    return get_due_reminders()


# =========================================================
# CANCEL REMINDER
# =========================================================

def cancel_reminder(reminder_id):

    reminder = get_reminder(reminder_id)

    if reminder is None:
        return None

    if reminder["status"] in {
        "scheduled",
        "due"
    }:

        execute(
            """
            UPDATE reminders
            SET status = 'cancelled'
            WHERE id = ?
            """,
            (reminder_id,)
        )

    return get_reminder(reminder_id)


# =========================================================
# MARK REMINDER COMPLETED
# =========================================================

def mark_reminder_completed(reminder_id):

    execute(
        """
        UPDATE reminders
        SET status = 'completed'
        WHERE id = ?
        """,
        (reminder_id,)
    )

    return get_reminder(reminder_id)


# =========================================================
# START REMINDER
# =========================================================

def start_reminder(reminder_id):

    reminder = get_reminder(reminder_id)

    if reminder is None:
        return None

    if reminder["status"] != "due":
        return reminder

    execute(
        """
        UPDATE reminders
        SET status = 'in_progress'
        WHERE id = ?
        """,
        (reminder_id,)
    )

    return get_reminder(reminder_id)


# =========================================================
# COMPLETE ACTIVE REMINDER
# =========================================================

def complete_reminder(reminder_id):

    reminder = get_reminder(reminder_id)

    if reminder is None:
        return None

    if reminder["status"] not in {
        "due",
        "in_progress"
    }:
        return reminder

    execute(
        """
        UPDATE reminders
        SET status = 'completed'
        WHERE id = ?
        """,
        (reminder_id,)
    )

    return get_reminder(reminder_id)


# =========================================================
# CHECK REMINDERS
# =========================================================

def check_reminders():

    return update_due_reminders()


# =========================================================
# REMINDER WORKER
# =========================================================

def reminder_worker():

    while True:

        try:
            check_reminders()

        except Exception as error:

            print(
                f"Reminder service error: {error}"
            )

        time.sleep(1)


# =========================================================
# START REMINDER SERVICE
# =========================================================

def start_reminder_service():

    global service_started

    with service_lock:

        if service_started:
            return

        service_started = True

        worker = threading.Thread(
            target=reminder_worker,
            daemon=True
        )

        worker.start()

        print(
            "Reminder service started."
        )