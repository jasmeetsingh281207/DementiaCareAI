import json
import uuid
from datetime import datetime
from pathlib import Path

from werkzeug.utils import secure_filename

from database import (
    execute,
    fetch_one,
    fetch_all
)


# =========================================================
# STORAGE DIRECTORIES
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

STORAGE_DIR = BASE_DIR / "storage"

STORAGE_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# ALLOWED MEDIA EXTENSIONS
# =========================================================

ALLOWED_PHOTO_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}

ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm"
}


# =========================================================
# INITIALIZE STORAGE
# =========================================================

def initialize_storage():
    """
    Create the memory storage directory if necessary.
    """

    STORAGE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    return True


# =========================================================
# MEMORY HELPERS
# =========================================================

def _memory_from_row(row):
    """
    Convert a database row into a normal dictionary.

    Also attaches all media belonging to the memory.
    """

    if row is None:
        return None

    memory = dict(row)

    try:

        memory["tags"] = json.loads(
            memory.get("tags") or "[]"
        )

    except Exception:

        memory["tags"] = []

    memory["media"] = get_memory_media(
        memory["id"]
    )

    return memory


# =========================================================
# ADD MEMORY
# =========================================================

def add_memory(
    category,
    name,
    relationship=None,
    description=None,
    event_date=None,
    tags=None,
    media=None
):
    """
    Create a new patient memory.

    media is optional existing media metadata.
    Normal uploads should use add_memory_media().
    """

    if not category:

        raise ValueError(
            "Memory category is required."
        )

    if not name:

        raise ValueError(
            "Memory name is required."
        )

    memory_id = str(
        uuid.uuid4()
    )

    now = datetime.now().isoformat()

    if tags is None:

        tags = []

    if not isinstance(
        tags,
        list
    ):

        tags = [tags]

    execute(
        """
        INSERT INTO memories (
            id,
            category,
            name,
            relationship,
            description,
            event_date,
            tags,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            memory_id,
            category,
            name,
            relationship,
            description,
            event_date,
            json.dumps(
                tags,
                ensure_ascii=False
            ),
            now,
            now
        )
    )

    # -----------------------------------------------------
    # OPTIONAL EXISTING MEDIA METADATA
    # -----------------------------------------------------

    if media:

        for item in media:

            if not isinstance(
                item,
                dict
            ):
                continue

            media_type = item.get(
                "media_type"
            )

            if media_type not in {
                "photo",
                "video"
            }:
                continue

            file_path = item.get(
                "file_path",
                ""
            )

            filename = item.get(
                "filename",
                ""
            )

            stored_filename = item.get(
                "stored_filename",
                filename
            )

            if not file_path:
                continue

            _insert_media_record(
                memory_id=memory_id,
                media_type=media_type,
                filename=filename,
                stored_filename=stored_filename,
                file_path=file_path,
                caption=item.get(
                    "caption"
                )
            )

    return get_memory(
        memory_id
    )


# =========================================================
# GET MEMORIES
# =========================================================

def get_memories(
    category=None
):
    """
    Return all memories.

    If category is supplied, only memories in that
    category are returned.
    """

    if category:

        rows = fetch_all(
            """
            SELECT *
            FROM memories
            WHERE category = ?
            ORDER BY created_at DESC
            """,
            (category,)
        )

    else:

        rows = fetch_all(
            """
            SELECT *
            FROM memories
            ORDER BY created_at DESC
            """
        )

    return [
        _memory_from_row(row)
        for row in rows
    ]


# =========================================================
# GET SINGLE MEMORY
# =========================================================

def get_memory(
    memory_id
):
    """
    Return one memory by ID.
    """

    if not memory_id:
        return None

    row = fetch_one(
        """
        SELECT *
        FROM memories
        WHERE id = ?
        """,
        (memory_id,)
    )

    return _memory_from_row(
        row
    )


# =========================================================
# DELETE MEMORY
# =========================================================

def delete_memory(
    memory_id
):
    """
    Delete a memory and all associated media.

    Physical media files are also removed.
    """

    memory = get_memory(
        memory_id
    )

    if memory is None:
        return None

    # -----------------------------------------------------
    # DELETE PHYSICAL MEDIA FILES
    # -----------------------------------------------------

    for media in memory.get(
        "media",
        []
    ):

        file_path = media.get(
            "file_path"
        )

        if not file_path:
            continue

        try:

            path = Path(
                file_path
            )

            if path.exists():

                path.unlink()

        except Exception as error:

            print(
                "Unable to delete media file:",
                error
            )

    # -----------------------------------------------------
    # DELETE DATABASE MEDIA RECORDS
    # -----------------------------------------------------

    execute(
        """
        DELETE FROM memory_media
        WHERE memory_id = ?
        """,
        (memory_id,)
    )

    # -----------------------------------------------------
    # DELETE MEMORY
    # -----------------------------------------------------

    execute(
        """
        DELETE FROM memories
        WHERE id = ?
        """,
        (memory_id,)
    )

    # -----------------------------------------------------
    # REMOVE EMPTY MEMORY DIRECTORY
    # -----------------------------------------------------

    memory_directory = (
        STORAGE_DIR / str(memory_id)
    )

    try:

        if (
            memory_directory.exists()
            and not any(
                memory_directory.iterdir()
            )
        ):

            memory_directory.rmdir()

    except Exception:
        pass

    return memory


# =========================================================
# INTERNAL MEDIA DATABASE INSERT
# =========================================================

def _insert_media_record(
    memory_id,
    media_type,
    filename,
    stored_filename,
    file_path,
    caption=None
):
    """
    Insert an already-stored media file into the database.
    """

    if not memory_id:

        raise ValueError(
            "Memory ID is required."
        )

    if media_type not in {
        "photo",
        "video"
    }:

        raise ValueError(
            "Media type must be 'photo' or 'video'."
        )

    media_id = str(
        uuid.uuid4()
    )

    now = datetime.now().isoformat()

    execute(
        """
        INSERT INTO memory_media (
            id,
            memory_id,
            media_type,
            filename,
            stored_filename,
            file_path,
            caption,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            media_id,
            memory_id,
            media_type,
            filename,
            stored_filename,
            file_path,
            caption,
            now
        )
    )

    return get_memory_media_by_id(
        media_id
    )


# =========================================================
# ADD MEMORY MEDIA
# =========================================================

def add_memory_media(
    memory_id,
    file_storage,
    media_type=None,
    caption=None
):
    """
    Save an uploaded photo/video and create its
    database record.

    file_storage is normally Flask's uploaded FileStorage.
    """

    # -----------------------------------------------------
    # CHECK MEMORY
    # -----------------------------------------------------

    memory = get_memory(
        memory_id
    )

    if memory is None:

        raise ValueError(
            "Memory does not exist."
        )

    # -----------------------------------------------------
    # CHECK FILE
    # -----------------------------------------------------

    if file_storage is None:

        raise ValueError(
            "File is required."
        )

    original_filename = (
        file_storage.filename or ""
    ).strip()

    if not original_filename:

        raise ValueError(
            "Uploaded file has no filename."
        )

    # -----------------------------------------------------
    # SECURE ORIGINAL FILENAME
    # -----------------------------------------------------

    safe_filename = secure_filename(
        original_filename
    )

    if not safe_filename:

        raise ValueError(
            "Invalid filename."
        )

    # -----------------------------------------------------
    # GET EXTENSION
    # -----------------------------------------------------

    extension = Path(
        safe_filename
    ).suffix.lower()

    if not extension:

        raise ValueError(
            "Uploaded file has no extension."
        )

    # -----------------------------------------------------
    # DETERMINE MEDIA TYPE
    # -----------------------------------------------------

    if media_type:

        media_type = (
            media_type
            .lower()
            .strip()
        )

    if not media_type:

        if extension in ALLOWED_PHOTO_EXTENSIONS:

            media_type = "photo"

        elif extension in ALLOWED_VIDEO_EXTENSIONS:

            media_type = "video"

        else:

            raise ValueError(
                "Unsupported media format."
            )

    # -----------------------------------------------------
    # VALIDATE MEDIA TYPE
    # -----------------------------------------------------

    if media_type not in {
        "photo",
        "video"
    }:

        raise ValueError(
            "Media type must be 'photo' or 'video'."
        )

    # -----------------------------------------------------
    # VALIDATE EXTENSION
    # -----------------------------------------------------

    if media_type == "photo":

        allowed_extensions = (
            ALLOWED_PHOTO_EXTENSIONS
        )

    else:

        allowed_extensions = (
            ALLOWED_VIDEO_EXTENSIONS
        )

    if extension not in allowed_extensions:

        raise ValueError(
            "File extension does not match "
            "the selected media type."
        )

    # -----------------------------------------------------
    # CREATE MEMORY-SPECIFIC DIRECTORY
    # -----------------------------------------------------

    memory_directory = (
        STORAGE_DIR / str(memory_id)
    )

    memory_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    # -----------------------------------------------------
    # GENERATE UNIQUE STORED FILENAME
    # -----------------------------------------------------

    unique_name = (
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    destination = (
        memory_directory
        / unique_name
    )

    # -----------------------------------------------------
    # SAVE FILE
    # -----------------------------------------------------

    file_storage.save(
        str(destination)
    )

    # -----------------------------------------------------
    # STORE ABSOLUTE PATH
    # -----------------------------------------------------

    stored_path = str(
        destination.resolve()
    )

    # -----------------------------------------------------
    # DATABASE RECORD
    # -----------------------------------------------------

    try:

        media = _insert_media_record(

            memory_id=memory_id,

            media_type=media_type,

            filename=original_filename,

            stored_filename=unique_name,

            file_path=stored_path,

            caption=caption

        )

    except Exception:

        # Database insertion failed.
        # Remove the physical file so we do not
        # leave an orphaned upload.

        try:

            if destination.exists():

                destination.unlink()

        except Exception:
            pass

        raise

    return media


# =========================================================
# GET MEDIA BY ID
# =========================================================

def get_memory_media_by_id(
    media_id
):
    """
    Return one media record by media ID.
    """

    if not media_id:
        return None

    return fetch_one(
        """
        SELECT
            id,
            memory_id,
            media_type,
            filename,
            stored_filename,
            file_path,
            caption,
            created_at
        FROM memory_media
        WHERE id = ?
        """,
        (media_id,)
    )


# =========================================================
# GET ALL MEDIA FOR MEMORY
# =========================================================

def get_memory_media(
    memory_id
):
    """
    Return all photos/videos belonging to one memory.
    """

    if not memory_id:
        return []

    return fetch_all(
        """
        SELECT
            id,
            memory_id,
            media_type,
            filename,
            stored_filename,
            file_path,
            caption,
            created_at
        FROM memory_media
        WHERE memory_id = ?
        ORDER BY created_at ASC
        """,
        (memory_id,)
    )


# =========================================================
# COMPATIBILITY ALIAS
# =========================================================

def get_media_for_memory(
    memory_id
):
    """
    Compatibility wrapper.
    """

    return get_memory_media(
        memory_id
    )


# =========================================================
# DELETE MEDIA
# =========================================================

def delete_memory_media(
    memory_id,
    media_id
):
    """
    Delete one media item.

    The media must belong to the supplied memory.
    """

    media = get_memory_media_by_id(
        media_id
    )

    if media is None:

        return None

    # -----------------------------------------------------
    # SECURITY CHECK
    # -----------------------------------------------------

    if str(
        media["memory_id"]
    ) != str(
        memory_id
    ):

        return None

    # -----------------------------------------------------
    # DELETE PHYSICAL FILE
    # -----------------------------------------------------

    file_path = media.get(
        "file_path"
    )

    if file_path:

        try:

            path = Path(
                file_path
            )

            if path.exists():

                path.unlink()

        except Exception as error:

            print(
                "Unable to delete media file:",
                error
            )

    # -----------------------------------------------------
    # DELETE DATABASE RECORD
    # -----------------------------------------------------

    execute(
        """
        DELETE FROM memory_media
        WHERE id = ?
        AND memory_id = ?
        """,
        (
            media_id,
            memory_id
        )
    )

    # -----------------------------------------------------
    # REMOVE EMPTY MEMORY DIRECTORY
    # -----------------------------------------------------

    memory_directory = (
        STORAGE_DIR / str(memory_id)
    )

    try:

        if (
            memory_directory.exists()
            and not any(
                memory_directory.iterdir()
            )
        ):

            memory_directory.rmdir()

    except Exception:
        pass

    return media


# =========================================================
# UPDATE MEMORY
# =========================================================

def update_memory(
    memory_id,
    **updates
):
    """
    Update allowed memory fields.
    """

    allowed_fields = {

        "category",

        "name",

        "relationship",

        "description",

        "event_date",

        "tags"

    }

    memory = get_memory(
        memory_id
    )

    if memory is None:

        return None

    fields = []
    values = []

    for key, value in updates.items():

        if key not in allowed_fields:
            continue

        if key == "tags":

            if value is None:

                value = []

            elif not isinstance(
                value,
                list
            ):

                value = [value]

            value = json.dumps(
                value,
                ensure_ascii=False
            )

        fields.append(
            f"{key} = ?"
        )

        values.append(
            value
        )

    if not fields:

        return memory

    fields.append(
        "updated_at = ?"
    )

    values.append(
        datetime.now().isoformat()
    )

    values.append(
        memory_id
    )

    execute(
        f"""
        UPDATE memories
        SET {", ".join(fields)}
        WHERE id = ?
        """,
        tuple(values)
    )

    return get_memory(
        memory_id
    )


# =========================================================
# ATTACH MEDIA COMPATIBILITY FUNCTION
# =========================================================

def attach_media(
    memory_id,
    file_path,
    media_type,
    caption=None
):
    """
    Compatibility helper for older code.

    Registers an already-existing file.
    """

    memory = get_memory(
        memory_id
    )

    if memory is None:

        raise ValueError(
            "Memory does not exist."
        )

    path = Path(
        file_path
    )

    if not path.exists():

        raise ValueError(
            "Media file does not exist."
        )

    if media_type not in {
        "photo",
        "video"
    }:

        raise ValueError(
            "Media type must be 'photo' or 'video'."
        )

    filename = path.name

    return _insert_media_record(

        memory_id=memory_id,

        media_type=media_type,

        filename=filename,

        stored_filename=filename,

        file_path=str(
            path.resolve()
        ),

        caption=caption

    )


# =========================================================
# GET MEDIA COMPATIBILITY FUNCTION
# =========================================================

def get_media(
    memory_id
):
    """
    Compatibility wrapper returning all media
    for a memory.
    """

    return get_memory_media(
        memory_id
    )


# =========================================================
# REMOVE MEDIA COMPATIBILITY FUNCTION
# =========================================================

def remove_media(
    media_id
):
    """
    Compatibility wrapper for older code.

    Looks up the media first, then removes it safely.
    """

    media = get_memory_media_by_id(
        media_id
    )

    if media is None:

        return None

    return delete_memory_media(
        media["memory_id"],
        media_id
    )

