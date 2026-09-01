import os
import sqlite3
import time
import asyncio
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "zerosess.db")

def _get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                created_at REAL,
                last_active REAL,
                generations_count INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                key TEXT PRIMARY KEY,
                count INTEGER DEFAULT 0
            )
        """)
        conn.commit()

# Run table creation on import
init_db()

def _sync_add_user(user_id: int, first_name: str = "", username: str = ""):
    now = time.time()
    with _get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, first_name, username, created_at, last_active)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                first_name = excluded.first_name,
                username = excluded.username,
                last_active = excluded.last_active
        """, (user_id, first_name, username, now, now))
        conn.commit()

async def add_user(user_id: int, first_name: str = "", username: str = ""):
    await asyncio.to_thread(_sync_add_user, user_id, first_name, username)

def _sync_remove_user(user_id: int):
    with _get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()

async def remove_user(user_id: int):
    await asyncio.to_thread(_sync_remove_user, user_id)

def _sync_get_all_user_ids() -> list[int]:
    with _get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        rows = cursor.fetchall()
        return [row["user_id"] for row in rows]

async def get_all_user_ids() -> list[int]:
    return await asyncio.to_thread(_sync_get_all_user_ids)

def _sync_increment_metric(key: str, by: int = 1):
    with _get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO metrics (key, count)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET count = count + ?
        """, (key, by, by))
        conn.commit()

async def increment_metric(key: str, by: int = 1):
    await asyncio.to_thread(_sync_increment_metric, key, by)

def _sync_get_analytics() -> dict:
    now = time.time()
    t_24h = now - 86400
    t_7d = now - (7 * 86400)
    with _get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as active_24h FROM users WHERE last_active >= ?", (t_24h,))
        active_24h = cursor.fetchone()["active_24h"]

        cursor.execute("SELECT COUNT(*) as active_7d FROM users WHERE last_active >= ?", (t_7d,))
        active_7d = cursor.fetchone()["active_7d"]

        cursor.execute("SELECT key, count FROM metrics")
        metrics_rows = cursor.fetchall()
        metrics = {row["key"]: row["count"] for row in metrics_rows}

        return {
            "total_users": total_users,
            "active_24h": active_24h,
            "active_7d": active_7d,
            "total_generations": metrics.get("sessions_generated", 0),
            "pyro_generations": metrics.get("sessions_pyro", 0),
            "tele_generations": metrics.get("sessions_tele", 0),
            "bot_generations": metrics.get("sessions_bot", 0),
            "total_checks": metrics.get("sessions_checked", 0),
        }

async def get_analytics() -> dict:
    return await asyncio.to_thread(_sync_get_analytics)
