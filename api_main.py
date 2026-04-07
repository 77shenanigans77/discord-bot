import os

from flask import Flask, jsonify, request

from db import get_db_health, init_db, validate_key

app = Flask(__name__)


@app.route("/")
def home():
    return "key-api is running"


@app.route("/check")
def check_key():
    key_value = request.args.get("key", "").strip()

    if not key_value:
        return jsonify({
            "ok": False,
            "valid": False,
            "error": "Missing key"
        }), 400

    try:
        row = validate_key(key_value)

        if not row:
            return jsonify({
                "ok": True,
                "valid": False
            }), 200

        return jsonify({
            "ok": True,
            "valid": True,
            "user_id": row["user_id"],
            "key": row["key_value"],
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
            "expires_at": row["expires_at"].isoformat() if row.get("expires_at") else None
        }), 200

    except Exception as exc:
        return jsonify({
            "ok": False,
            "valid": False,
            "error": str(exc)
        }), 500


@app.route("/health")
def health():
    try:
        health_info = get_db_health()
        return jsonify({
            "ok": True,
            "database": health_info
        }), 200
    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)
        }), 500


def main():
    try:
        init_db()
        print("Database initialized")
    except Exception as exc:
        print(f"Database init failed: {repr(exc)}")

    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
