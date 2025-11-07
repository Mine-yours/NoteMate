import os
import sqlite3
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