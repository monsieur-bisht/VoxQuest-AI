from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

DB_PATH = Path(os.getenv("VOXQUEST_DB_PATH", Path(__file__).resolve().parent.parent / "voxquest.db"))


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                current_scene TEXT NOT NULL,
                relationship_score INTEGER NOT NULL,
                decisions_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS benchmark_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                transcript TEXT NOT NULL,
                expected_transcript TEXT,
                confidence REAL NOT NULL,
                wer REAL,
                latency_ms REAL NOT NULL,
                language_mode TEXT NOT NULL,
                noise_level TEXT,
                accent_tag TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS dataset_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                transcript TEXT NOT NULL,
                language_tag TEXT NOT NULL,
                noise_level TEXT NOT NULL,
                accent_tag TEXT NOT NULL,
                anonymized_audio_id TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS speech_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                transcript TEXT NOT NULL,
                audio_b64 TEXT NOT NULL,
                language_mode TEXT NOT NULL,
                noise_level TEXT,
                accent_tag TEXT,
                created_at TEXT NOT NULL
            );
            """
        )


def upsert_session(data: Dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sessions (id, current_scene, relationship_score, decisions_json, updated_at)
            VALUES (:id, :current_scene, :relationship_score, :decisions_json, :updated_at)
            ON CONFLICT(id) DO UPDATE SET
                current_scene=excluded.current_scene,
                relationship_score=excluded.relationship_score,
                decisions_json=excluded.decisions_json,
                updated_at=excluded.updated_at
            """,
            data,
        )


def fetch_session(session_id: str) -> Dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "current_scene": row["current_scene"],
        "relationship_score": row["relationship_score"],
        "decisions": json.loads(row["decisions_json"]),
        "updated_at": row["updated_at"],
    }


def insert_benchmark(entry: Dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO benchmark_logs (
                session_id, transcript, expected_transcript, confidence, wer,
                latency_ms, language_mode, noise_level, accent_tag, created_at
            ) VALUES (
                :session_id, :transcript, :expected_transcript, :confidence, :wer,
                :latency_ms, :language_mode, :noise_level, :accent_tag, :created_at
            )
            """,
            entry,
        )


def insert_dataset_entry(entry: Dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO dataset_entries (
                session_id, transcript, language_tag, noise_level, accent_tag,
                anonymized_audio_id, created_at
            ) VALUES (
                :session_id, :transcript, :language_tag, :noise_level, :accent_tag,
                :anonymized_audio_id, :created_at
            )
            """,
            entry,
        )


def insert_speech_sample(entry: Dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO speech_samples (
                session_id, transcript, audio_b64, language_mode, noise_level, accent_tag, created_at
            ) VALUES (
                :session_id, :transcript, :audio_b64, :language_mode, :noise_level, :accent_tag, :created_at
            )
            """,
            entry,
        )


def export_dataset_json() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM dataset_entries ORDER BY id ASC").fetchall()
    return [dict(row) for row in rows]


def export_dataset_csv() -> str:
    rows = export_dataset_json()
    if not rows:
        return "id,session_id,transcript,language_tag,noise_level,accent_tag,anonymized_audio_id,created_at\n"

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
