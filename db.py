import json
import os
import secrets
import string
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import psycopg2
import psycopg2.extras


def _connection_kwargs():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return {"dsn": database_url}

    host = os.getenv("PGHOST")
    port = os.getenv("PGPORT")
    user = os.getenv("PGUSER")
    password = os.getenv("PGPASSWORD")
    database = os.getenv("PGDATABASE")

    if not all([host, port, user, password, database]):
        raise RuntimeError(
            "Database config missing. Set DATABASE_URL or PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE."
        )

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "dbname": database,
    }


@contextmanager
def get_conn():
    conn = psycopg2.connect(**_connection_kwargs())
    try:
        yield conn
    finally:
        conn.close()


def _fetchone_dict(cursor):
    row = cursor.fetchone()
    if row is None:
        return None
    return dict(row)


def get_db_health():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT NOW() AS now")
            row = cur.fetchone()
            return {"now": row["now"].isoformat()}


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS user_keys (
                    user_id BIGINT PRIMARY KEY,
                    key_value TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    expires_at TIMESTAMPTZ NOT NULL
                );
                '''
            )
            cur.execute(
                '''
                CREATE INDEX IF NOT EXISTS idx_user_keys_key_value
                ON user_keys (key_value);
                '''
            )
            cur.execute(
                '''
                CREATE INDEX IF NOT EXISTS idx_user_keys_expires_at
                ON user_keys (expires_at);
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS bot_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL
                );
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS scripts (
                    script_key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    game_name TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    loader TEXT NOT NULL,
                    executors TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
                    key_command TEXT NOT NULL,
                    bug_channel_id BIGINT,
                    status TEXT NOT NULL DEFAULT 'stable',
                    updated_date DATE NOT NULL DEFAULT CURRENT_DATE,
                    notes TEXT NOT NULL DEFAULT '',
                    product_card_channel_id BIGINT,
                    product_card_message_id BIGINT,
                    style_color TEXT NOT NULL DEFAULT '',
                    style_thumbnail_url TEXT NOT NULL DEFAULT '',
                    style_image_url TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at_ts TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS faq_items (
                    id BIGSERIAL PRIMARY KEY,
                    script_key TEXT NOT NULL REFERENCES scripts(script_key) ON DELETE CASCADE,
                    item_order INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    UNIQUE (script_key, item_order)
                );
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS feature_items (
                    id BIGSERIAL PRIMARY KEY,
                    script_key TEXT NOT NULL REFERENCES scripts(script_key) ON DELETE CASCADE,
                    category TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    experimental BOOLEAN NOT NULL DEFAULT FALSE
                );
                '''
            )
            cur.execute(
                '''
                CREATE INDEX IF NOT EXISTS idx_feature_items_script_key
                ON feature_items (script_key);
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS published_pages (
                    page_type TEXT NOT NULL,
                    script_key TEXT NOT NULL REFERENCES scripts(script_key) ON DELETE CASCADE,
                    channel_id BIGINT,
                    message_ids_json TEXT NOT NULL DEFAULT '[]',
                    PRIMARY KEY (page_type, script_key)
                );
                '''
            )
        conn.commit()


def _generate_key(length=32):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_active_key_for_user(user_id: int):
    now = datetime.now(timezone.utc)
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''
                SELECT user_id, key_value, created_at, expires_at
                FROM user_keys
                WHERE user_id = %s AND expires_at > %s
                ''',
                (user_id, now),
            )
            return _fetchone_dict(cur)


def create_or_replace_key_for_user(user_id: int, hours_valid: int = 24):
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=hours_valid)
    key_value = _generate_key()

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("DELETE FROM user_keys WHERE user_id = %s", (user_id,))
            cur.execute(
                '''
                INSERT INTO user_keys (user_id, key_value, created_at, expires_at)
                VALUES (%s, %s, %s, %s)
                RETURNING user_id, key_value, created_at, expires_at
                ''',
                (user_id, key_value, now, expires_at),
            )
            row = cur.fetchone()
        conn.commit()
        return dict(row)


def validate_key(key_value: str):
    now = datetime.now(timezone.utc)
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''
                SELECT user_id, key_value, created_at, expires_at
                FROM user_keys
                WHERE key_value = %s AND expires_at > %s
                ''',
                (key_value, now),
            )
            return _fetchone_dict(cur)


def cleanup_expired_keys():
    now = datetime.now(timezone.utc)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_keys WHERE expires_at <= %s", (now,))
            deleted = cur.rowcount
        conn.commit()
        return deleted


def get_setting(key: str, default: str = ""):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT setting_value FROM bot_settings WHERE setting_key = %s",
                (key,),
            )
            row = cur.fetchone()
            if row is None:
                return default
            return row["setting_value"]


def set_setting(key: str, value: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO bot_settings (setting_key, setting_value)
                VALUES (%s, %s)
                ON CONFLICT (setting_key)
                DO UPDATE SET setting_value = EXCLUDED.setting_value
                ''',
                (key, value),
            )
        conn.commit()


def get_script(script_key: str):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''
                SELECT
                    script_key,
                    name,
                    game_name,
                    summary,
                    loader,
                    executors,
                    key_command,
                    bug_channel_id,
                    status,
                    updated_date,
                    notes,
                    product_card_channel_id,
                    product_card_message_id,
                    style_color,
                    style_thumbnail_url,
                    style_image_url
                FROM scripts
                WHERE script_key = %s
                ''',
                (script_key,),
            )
            row = cur.fetchone()
            if row is None:
                return None

            return {
                "script_key": row["script_key"],
                "name": row["name"],
                "game_name": row["game_name"],
                "summary": row["summary"],
                "loader": row["loader"],
                "executors": row["executors"] or [],
                "key_command": row["key_command"],
                "bug_channel_id": row["bug_channel_id"],
                "status": row["status"],
                "updated_date": row["updated_date"].isoformat() if row["updated_date"] else "",
                "notes": row["notes"] or "",
                "product_card_channel_id": row["product_card_channel_id"],
                "product_card_message_id": row["product_card_message_id"],
                "style_color": row["style_color"] or "",
                "style_thumbnail_url": row["style_thumbnail_url"] or "",
                "style_image_url": row["style_image_url"] or "",
            }


def list_scripts():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''
                SELECT
                    script_key,
                    name,
                    game_name,
                    summary,
                    loader,
                    executors,
                    key_command,
                    bug_channel_id,
                    status,
                    updated_date,
                    notes,
                    product_card_channel_id,
                    product_card_message_id,
                    style_color,
                    style_thumbnail_url,
                    style_image_url
                FROM scripts
                ORDER BY LOWER(game_name), LOWER(name), LOWER(script_key)
                '''
            )
            rows = cur.fetchall()

    results = []
    for row in rows:
        results.append(
            {
                "script_key": row["script_key"],
                "name": row["name"],
                "game_name": row["game_name"],
                "summary": row["summary"],
                "loader": row["loader"],
                "executors": row["executors"] or [],
                "key_command": row["key_command"],
                "bug_channel_id": row["bug_channel_id"],
                "status": row["status"],
                "updated_date": row["updated_date"].isoformat() if row["updated_date"] else "",
                "notes": row["notes"] or "",
                "product_card_channel_id": row["product_card_channel_id"],
                "product_card_message_id": row["product_card_message_id"],
                "style_color": row["style_color"] or "",
                "style_thumbnail_url": row["style_thumbnail_url"] or "",
                "style_image_url": row["style_image_url"] or "",
            }
        )
    return results


def save_script(script: dict):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO scripts (
                    script_key,
                    name,
                    game_name,
                    summary,
                    loader,
                    executors,
                    key_command,
                    bug_channel_id,
                    status,
                    updated_date,
                    notes,
                    product_card_channel_id,
                    product_card_message_id,
                    style_color,
                    style_thumbnail_url,
                    style_image_url,
                    updated_at_ts
                )
                VALUES (
                    %(script_key)s,
                    %(name)s,
                    %(game_name)s,
                    %(summary)s,
                    %(loader)s,
                    %(executors)s,
                    %(key_command)s,
                    %(bug_channel_id)s,
                    %(status)s,
                    %(updated_date)s,
                    %(notes)s,
                    %(product_card_channel_id)s,
                    %(product_card_message_id)s,
                    %(style_color)s,
                    %(style_thumbnail_url)s,
                    %(style_image_url)s,
                    NOW()
                )
                ON CONFLICT (script_key)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    game_name = EXCLUDED.game_name,
                    summary = EXCLUDED.summary,
                    loader = EXCLUDED.loader,
                    executors = EXCLUDED.executors,
                    key_command = EXCLUDED.key_command,
                    bug_channel_id = EXCLUDED.bug_channel_id,
                    status = EXCLUDED.status,
                    updated_date = EXCLUDED.updated_date,
                    notes = EXCLUDED.notes,
                    product_card_channel_id = EXCLUDED.product_card_channel_id,
                    product_card_message_id = EXCLUDED.product_card_message_id,
                    style_color = EXCLUDED.style_color,
                    style_thumbnail_url = EXCLUDED.style_thumbnail_url,
                    style_image_url = EXCLUDED.style_image_url,
                    updated_at_ts = NOW()
                ''',
                {
                    "script_key": script["script_key"],
                    "name": script["name"],
                    "game_name": script["game_name"],
                    "summary": script["summary"],
                    "loader": script["loader"],
                    "executors": script.get("executors", []),
                    "key_command": script["key_command"],
                    "bug_channel_id": script.get("bug_channel_id"),
                    "status": script["status"],
                    "updated_date": script["updated_date"],
                    "notes": script.get("notes", ""),
                    "product_card_channel_id": script.get("product_card_channel_id"),
                    "product_card_message_id": script.get("product_card_message_id"),
                    "style_color": script.get("style_color", ""),
                    "style_thumbnail_url": script.get("style_thumbnail_url", ""),
                    "style_image_url": script.get("style_image_url", ""),
                },
            )
        conn.commit()


def upsert_faq_item(script_key: str, item_order: int, question: str, answer: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO faq_items (script_key, item_order, question, answer)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (script_key, item_order)
                DO UPDATE SET
                    question = EXCLUDED.question,
                    answer = EXCLUDED.answer
                ''',
                (script_key, item_order, question, answer),
            )
        conn.commit()


def remove_faq_item(script_key: str, item_order: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                DELETE FROM faq_items
                WHERE script_key = %s AND item_order = %s
                ''',
                (script_key, item_order),
            )
            deleted = cur.rowcount
        conn.commit()
        return deleted


def list_faq_items(script_key: str):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''
                SELECT item_order, question, answer
                FROM faq_items
                WHERE script_key = %s
                ORDER BY item_order ASC
                ''',
                (script_key,),
            )
            rows = cur.fetchall()

    return [
        {
            "order": row["item_order"],
            "question": row["question"],
            "answer": row["answer"],
        }
        for row in rows
    ]


def upsert_feature_item(
    script_key: str,
    category: str,
    name: str,
    description: str,
    experimental: bool,
):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''
                SELECT id
                FROM feature_items
                WHERE script_key = %s AND LOWER(name) = LOWER(%s)
                LIMIT 1
                ''',
                (script_key, name),
            )
            existing = cur.fetchone()

            if existing:
                cur.execute(
                    '''
                    UPDATE feature_items
                    SET category = %s,
                        name = %s,
                        description = %s,
                        experimental = %s
                    WHERE id = %s
                    ''',
                    (category, name, description, experimental, existing["id"]),
                )
            else:
                cur.execute(
                    '''
                    INSERT INTO feature_items (script_key, category, name, description, experimental)
                    VALUES (%s, %s, %s, %s, %s)
                    ''',
                    (script_key, category, name, description, experimental),
                )
        conn.commit()


def remove_feature_item(script_key: str, name: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                DELETE FROM feature_items
                WHERE script_key = %s AND LOWER(name) = LOWER(%s)
                ''',
                (script_key, name),
            )
            deleted = cur.rowcount
        conn.commit()
        return deleted


def list_feature_items(script_key: str):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''
                SELECT category, name, description, experimental
                FROM feature_items
                WHERE script_key = %s
                ORDER BY LOWER(category), LOWER(name)
                ''',
                (script_key,),
            )
            rows = cur.fetchall()

    return [
        {
            "category": row["category"],
            "name": row["name"],
            "description": row["description"] or "",
            "experimental": bool(row["experimental"]),
        }
        for row in rows
    ]


def get_published_page(page_type: str, script_key: str):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''
                SELECT channel_id, message_ids_json
                FROM published_pages
                WHERE page_type = %s AND script_key = %s
                ''',
                (page_type, script_key),
            )
            row = cur.fetchone()
            if row is None:
                return {"channel_id": None, "message_ids": []}

            try:
                message_ids = json.loads(row["message_ids_json"] or "[]")
            except json.JSONDecodeError:
                message_ids = []

            return {
                "channel_id": row["channel_id"],
                "message_ids": message_ids,
            }


def save_published_page(page_type: str, script_key: str, channel_id, message_ids):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO published_pages (page_type, script_key, channel_id, message_ids_json)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (page_type, script_key)
                DO UPDATE SET
                    channel_id = EXCLUDED.channel_id,
                    message_ids_json = EXCLUDED.message_ids_json
                ''',
                (page_type, script_key, channel_id, json.dumps(message_ids)),
            )
        conn.commit()
