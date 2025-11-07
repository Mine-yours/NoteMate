import os
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATABASE = os.path.join(BASE_DIR, 'database.db')


def create_table() -> None:
    con = sqlite3.connect(DATABASE)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS lecture_files (
            lecture_id        TEXT PRIMARY KEY,
            original_filename TEXT NOT NULL,
            stored_filename   TEXT NOT NULL,
            uploaded_at       TEXT NOT NULL
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS lecture_notes (
            lecture_id  TEXT PRIMARY KEY,
            content     TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS lecture_glossary_cache (
            lecture_id  TEXT NOT NULL,
            page_key    TEXT NOT NULL,
            items_json  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            PRIMARY KEY (lecture_id, page_key)
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS lecture_note_images (
            image_id          TEXT PRIMARY KEY,
            lecture_id        TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            stored_filename   TEXT NOT NULL,
            uploaded_at       TEXT NOT NULL
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS glossary_dictionary (
            dictionary_id TEXT PRIMARY KEY,
            lecture_id    TEXT NOT NULL,
            term          TEXT NOT NULL,
            definition    TEXT NOT NULL,
            context       TEXT,
            saved_at      TEXT NOT NULL,
            UNIQUE (lecture_id, term, definition)
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS lecture_glossary_dictionary (
            lecture_id  TEXT NOT NULL,
            term        TEXT NOT NULL,
            definition  TEXT,
            context     TEXT,
            saved_at    TEXT NOT NULL,
            PRIMARY KEY (lecture_id, term)
        )
        """
    )
    con.commit()
    con.close()


def insert_pdf(lecture_id: str, original_filename: str, stored_filename: str, uploaded_at: datetime) -> None:
    con = sqlite3.connect(DATABASE)
    con.execute(
        """
        INSERT INTO lecture_files (lecture_id, original_filename, stored_filename, uploaded_at)
        VALUES (?, ?, ?, ?)
        """,
        (lecture_id, original_filename, stored_filename, uploaded_at.isoformat())
    )
    con.commit()
    con.close()


def get_all_pdfs() -> List[Dict[str, str]]:
    con = sqlite3.connect(DATABASE)
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT lecture_id, original_filename, stored_filename, uploaded_at
        FROM lecture_files
        ORDER BY uploaded_at DESC
        """
    )
    rows = cursor.fetchall()
    con.close()

    return [
        {
            'lecture_id': row[0],
            'original_filename': row[1],
            'stored_filename': row[2],
            'uploaded_at': row[3],
        }
        for row in rows
    ]


def get_pdf_by_id(lecture_id: str) -> Optional[Dict[str, str]]:
    con = sqlite3.connect(DATABASE)
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT lecture_id, original_filename, stored_filename, uploaded_at
        FROM lecture_files
        WHERE lecture_id = ?
        """,
        (lecture_id,)
    )
    row = cursor.fetchone()
    con.close()

    if not row:
        return None

    return {
        'lecture_id': row[0],
        'original_filename': row[1],
        'stored_filename': row[2],
        'uploaded_at': row[3],
    }


def get_note_for_lecture(lecture_id: str) -> Optional[Dict[str, str]]:
    con = sqlite3.connect(DATABASE)
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT content, updated_at
        FROM lecture_notes
        WHERE lecture_id = ?
        """,
        (lecture_id,),
    )
    row = cursor.fetchone()
    con.close()
    if not row:
        return None
    return {
        'content': row[0],
        'updated_at': row[1],
    }


def upsert_note_for_lecture(lecture_id: str, content: str, updated_at: datetime) -> None:
    con = sqlite3.connect(DATABASE)
    con.execute(
        """
        INSERT INTO lecture_notes (lecture_id, content, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(lecture_id)
        DO UPDATE SET content = excluded.content, updated_at = excluded.updated_at
        """,
        (lecture_id, content, updated_at.isoformat()),
    )
    con.commit()
    con.close()


def get_glossary_cache(lecture_id: str, page_key: str) -> Optional[Dict[str, str]]:
    con = sqlite3.connect(DATABASE)
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT items_json, updated_at
        FROM lecture_glossary_cache
        WHERE lecture_id = ? AND page_key = ?
        """,
        (lecture_id, page_key),
    )
    row = cursor.fetchone()
    con.close()
    if not row:
        return None
    try:
        items = json.loads(row[0])
    except json.JSONDecodeError:
        items = []
    return {
        'items': items,
        'updated_at': row[1],
    }


def upsert_glossary_cache(lecture_id: str, page_key: str, items: List[Dict[str, str]], updated_at: datetime) -> None:
    con = sqlite3.connect(DATABASE)
    payload = json.dumps(items, ensure_ascii=False)
    con.execute(
        """
        INSERT INTO lecture_glossary_cache (lecture_id, page_key, items_json, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(lecture_id, page_key)
        DO UPDATE SET items_json = excluded.items_json, updated_at = excluded.updated_at
        """,
        (lecture_id, page_key, payload, updated_at.isoformat()),
    )
    con.commit()
    con.close()


def update_pdf_filename(lecture_id: str, new_name: str) -> None:
    con = sqlite3.connect(DATABASE)
    con.execute(
        """
        UPDATE lecture_files
        SET original_filename = ?
        WHERE lecture_id = ?
        """,
        (new_name, lecture_id),
    )
    con.commit()
    con.close()


def insert_note_image(lecture_id: str, image_id: str, original_filename: str, stored_filename: str, uploaded_at: datetime) -> None:
    con = sqlite3.connect(DATABASE)
    con.execute(
        """
        INSERT INTO lecture_note_images (image_id, lecture_id, original_filename, stored_filename, uploaded_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (image_id, lecture_id, original_filename, stored_filename, uploaded_at.isoformat()),
    )
    con.commit()
    con.close()


def list_note_images(lecture_id: str) -> List[Dict[str, str]]:
    con = sqlite3.connect(DATABASE)
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT image_id, original_filename, stored_filename, uploaded_at
        FROM lecture_note_images
        WHERE lecture_id = ?
        ORDER BY uploaded_at DESC
        """,
        (lecture_id,),
    )
    rows = cursor.fetchall()
    con.close()

    return [
        {
            "image_id": row[0],
            "original_filename": row[1],
            "stored_filename": row[2],
            "uploaded_at": row[3],
        }
        for row in rows
    ]


def upsert_glossary_dictionary_item(
    dictionary_id: str,
    lecture_id: str,
    term: str,
    definition: str,
    context: Optional[str],
    saved_at: datetime,
) -> None:
    con = sqlite3.connect(DATABASE)
    con.execute(
        """
        INSERT INTO glossary_dictionary (dictionary_id, lecture_id, term, definition, context, saved_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (lecture_id, term, definition)
        DO UPDATE SET context = excluded.context,
                      saved_at = excluded.saved_at,
                      dictionary_id = excluded.dictionary_id
        """,
        (dictionary_id, lecture_id, term, definition, context, saved_at.isoformat()),
    )
    con.commit()
    con.close()


def list_glossary_dictionary(lecture_id: Optional[str] = None) -> List[Dict[str, str]]:
    con = sqlite3.connect(DATABASE)
    cursor = con.cursor()
    if lecture_id:
        cursor.execute(
            """
            SELECT dictionary_id, lecture_id, term, definition, context, saved_at
            FROM glossary_dictionary
            WHERE lecture_id = ?
            ORDER BY saved_at DESC
            """,
            (lecture_id,),
        )
    else:
        cursor.execute(
            """
            SELECT dictionary_id, lecture_id, term, definition, context, saved_at
            FROM glossary_dictionary
            ORDER BY saved_at DESC
            """
        )

    rows = cursor.fetchall()
    con.close()
    return [
        {
            "dictionary_id": row[0],
            "lecture_id": row[1],
            "term": row[2],
            "definition": row[3],
            "context": row[4],
            "saved_at": row[5],
        }
        for row in rows
    ]


def delete_pdf_record(lecture_id: str) -> None:
    con = sqlite3.connect(DATABASE)
    con.execute(
        """
        DELETE FROM lecture_files WHERE lecture_id = ?
        """,
        (lecture_id,),
    )
    con.commit()
    con.close()

