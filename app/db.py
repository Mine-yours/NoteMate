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