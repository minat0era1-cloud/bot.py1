import os
import sqlite3
import secrets
from datetime import datetime, timedelta, timezone

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Sirf isi Telegram ID ko access milega
AUTHORIZED_TELEGRAM_ID = "6667327731"

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

DB_FILE = "licenses.db"


def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            telegram_id TEXT NOT NULL,
            expires_at TEXT,
            used INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


@app.get("/")
def home():
    return "License server is running."


@app.post("/telegram/start")
def telegram_start():
    data = request.get_json(silent=True) or {}
    telegram_id = str(data.get("telegram_id", ""))

    if telegram_id != AUTHORIZED_TELEGRAM_ID:
        return jsonify({
            "status": "denied",
            "message": "Access denied."
        }), 403

    code = secrets.token_urlsafe(16)

    conn = db()
    conn.execute(
        "INSERT INTO licenses (code, telegram_id) VALUES (?, ?)",
        (code, telegram_id)
    )
    conn.commit()
    conn.close()

    if BOT_TOKEN:
        try:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": telegram_id,
                    "text": f"Your activation code:\n\n{code}"
                },
                timeout=10
            )
        except Exception:
            pass

    return jsonify({
        "status": "ok",
        "message": "Activation code generated."
    })


@app.post("/activate")
def activate():
    data = request.get_json(silent=True) or {}
    code = str(data.get("code", "")).strip()

    if not code:
        return jsonify({
            "status": "error",
            "message": "Activation code required."
        }), 400

    conn = db()

    row = conn.execute(
        "SELECT * FROM licenses WHERE code = ?",
        (code,)
    ).fetchone()

    if not row:
        conn.close()
        return jsonify({
            "status": "error",
            "message": "Invalid activation code."
        }), 403

    if row["used"]:
        conn.close()
        return jsonify({
            "status": "error",
            "message": "Activation code already used."
        }), 403

    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=1)
    ).isoformat()

    conn.execute(
        """
        UPDATE licenses
        SET used = 1, expires_at = ?
        WHERE code = ?
        """,
        (expires_at, code)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "status": "ok",
        "telegram_id": row["telegram_id"],
        "expires_at": expires_at
    })


init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
