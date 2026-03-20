"""
modules/db.py — Generic repository base + table-specific repositories.

Usage:
    from modules.db import UserRepo, SiteRepo, ResultRepo, SecretRepo, init_db

    user    = UserRepo.get(1)
    users   = UserRepo.all()
    UserRepo.create(username="alice", email="a@b.com", password="hashed", role="viewer")
    UserRepo.update(1, role="admin")
    UserRepo.delete(1)
"""
import os
import sqlite3
from typing import Any
from werkzeug.security import generate_password_hash

# ------------------------------------------------------------------ #
# Connection
# ------------------------------------------------------------------ #

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH   = os.environ.get("DB_PATH") or os.path.join(_BASE_DIR, "ssl_monitor.db")


def _dict_factory(cursor, row):
    """Return rows as plain dicts so they work after connection closes."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = _dict_factory
    return conn


# ------------------------------------------------------------------ #
# Generic Repository base
# ------------------------------------------------------------------ #

class Repository:
    """
    Generic CRUD repository for a single SQLite table.

    Subclass it and set `table` and `pk` at the class level:

        class UserRepo(Repository):
            table = "users"
            pk    = "id"
    """
    table: str = ""
    pk:    str = "id"

    # ── Read ──────────────────────────────────────────────────────

    @classmethod
    def get(cls, pk_value: Any) -> sqlite3.Row | None:
        """Return a single row by primary key, or None."""
        with _connect() as conn:
            return conn.execute(
                f"SELECT * FROM {cls.table} WHERE {cls.pk} = ?", (pk_value,)
            ).fetchone()

    @classmethod
    def find(cls, **kwargs) -> sqlite3.Row | None:
        """Return the first row matching all keyword filters, or None.

        Example: UserRepo.find(username="alice")
        """
        where  = " AND ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values())
        with _connect() as conn:
            return conn.execute(
                f"SELECT * FROM {cls.table} WHERE {where}", values
            ).fetchone()

    @classmethod
    def filter(cls, **kwargs) -> list[sqlite3.Row]:
        """Return all rows matching keyword filters.

        Example: UserRepo.filter(role="admin")
        """
        where  = " AND ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values())
        with _connect() as conn:
            return conn.execute(
                f"SELECT * FROM {cls.table} WHERE {where}", values
            ).fetchall()

    @classmethod
    def all(cls, order_by: str = "") -> list[sqlite3.Row]:
        """Return every row in the table."""
        sql = f"SELECT * FROM {cls.table}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        with _connect() as conn:
            return conn.execute(sql).fetchall()

    @classmethod
    def query(cls, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Run any arbitrary SELECT and return all rows.

        Use for joins or complex queries that don't fit the above.
        Example:
            SiteRepo.query(
                "SELECT s.*, r.days_left FROM sites s LEFT JOIN results r ON s.url = r.site"
            )
        """
        with _connect() as conn:
            return conn.execute(sql, params).fetchall()

    @classmethod
    def count(cls, **kwargs) -> int:
        """Return row count, optionally filtered."""
        if kwargs:
            where  = " AND ".join(f"{k} = ?" for k in kwargs)
            values = list(kwargs.values())
            sql    = f"SELECT COUNT(*) FROM {cls.table} WHERE {where}"
        else:
            sql    = f"SELECT COUNT(*) FROM {cls.table}"
            values = []
        with _connect() as conn:
            return conn.execute(sql, values).fetchone()['COUNT(*)']

    # ── Write ─────────────────────────────────────────────────────

    @classmethod
    def create(cls, **kwargs) -> int:
        """Insert a row and return the new row's id.

        Example: UserRepo.create(username="bob", password="hashed", role="viewer")
        """
        cols        = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" for _ in kwargs)
        values      = list(kwargs.values())
        with _connect() as conn:
            cur = conn.execute(
                f"INSERT INTO {cls.table} ({cols}) VALUES ({placeholders})", values
            )
            conn.commit()
            return cur.lastrowid

    @classmethod
    def update(cls, pk_value: Any, **kwargs) -> int:
        """Update columns for a row identified by primary key.
        Returns number of rows affected.

        Example: UserRepo.update(3, role="admin")
        """
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values     = list(kwargs.values()) + [pk_value]
        with _connect() as conn:
            cur = conn.execute(
                f"UPDATE {cls.table} SET {set_clause} WHERE {cls.pk} = ?", values
            )
            conn.commit()
            return cur.rowcount

    @classmethod
    def update_where(cls, filters: dict, **kwargs) -> int:
        """Update columns for all rows matching filters.
        Returns number of rows affected.

        Example: ResultRepo.update_where({"site": "example.com"}, alert_sent=None)
        """
        set_clause   = ", ".join(f"{k} = ?" for k in kwargs)
        where_clause = " AND ".join(f"{k} = ?" for k in filters)
        values       = list(kwargs.values()) + list(filters.values())
        with _connect() as conn:
            cur = conn.execute(
                f"UPDATE {cls.table} SET {set_clause} WHERE {where_clause}", values
            )
            conn.commit()
            return cur.rowcount

    @classmethod
    def delete(cls, pk_value: Any) -> int:
        """Delete a row by primary key. Returns number of rows affected."""
        with _connect() as conn:
            cur = conn.execute(
                f"DELETE FROM {cls.table} WHERE {cls.pk} = ?", (pk_value,)
            )
            conn.commit()
            return cur.rowcount

    @classmethod
    def delete_where(cls, **kwargs) -> int:
        """Delete all rows matching keyword filters.
        Returns number of rows affected.

        Example: ResultRepo.delete_where(site="example.com")
        """
        where  = " AND ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values())
        with _connect() as conn:
            cur = conn.execute(
                f"DELETE FROM {cls.table} WHERE {where}", values
            )
            conn.commit()
            return cur.rowcount

    @classmethod
    def execute(cls, sql: str, params: tuple = ()) -> int:
        """Run any arbitrary write statement (INSERT/UPDATE/DELETE).
        Returns rowcount.

        Use for upserts or multi-step writes that don't fit the above.
        """
        with _connect() as conn:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur.rowcount


# ------------------------------------------------------------------ #
# ------------------------------------------------------------------ #
# Table repositories
# ------------------------------------------------------------------ #

class UserRepo(Repository):
    table = "users"
    pk    = "id"


class SiteRepo(Repository):
    table = "sites"
    pk    = "id"

    @classmethod
    def list_with_results(cls) -> list:
        """All sites joined with their latest scan result, ordered by urgency."""
        return cls.query("""
            SELECT s.name, s.url, r.ip, r.days_left, r.expiry,
                   r.alert_sent,
                   CASE
                       WHEN r.alert_sent IS NULL OR r.alert_sent = '' THEN 0
                       ELSE (LENGTH(r.alert_sent) - LENGTH(REPLACE(r.alert_sent, ',', '')) + 1)
                   END AS alerts_sent_count
            FROM sites s
            LEFT JOIN results r ON s.url = r.site
            ORDER BY r.days_left ASC NULLS LAST
        """)

    @classmethod
    def upsert(cls, name: str, url: str, ip_override):
        """Insert or update a site record."""
        cls.execute("""
            INSERT INTO sites (name, url, ip_override) VALUES (?, ?, ?)
            ON CONFLICT(url) DO UPDATE
              SET name=excluded.name, ip_override=excluded.ip_override
        """, (name, url, ip_override))

    @classmethod
    def delete_by_url(cls, url: str):
        """Delete a site and its scan result."""
        cls.delete_where(url=url)
        ResultRepo.delete_where(site=url)


class ResultRepo(Repository):
    table = "results"
    pk    = "site"

    @classmethod
    def get_stats(cls) -> dict:
        """Dashboard counts — total sites, healthy, warning, critical."""
        rows = cls.query("""
            SELECT
                SUM(CASE WHEN days_left > 30             THEN 1 ELSE 0 END) AS healthy,
                SUM(CASE WHEN days_left <= 30
                          AND days_left > 10             THEN 1 ELSE 0 END) AS warning,
                SUM(CASE WHEN days_left <= 10            THEN 1 ELSE 0 END) AS critical
            FROM results
        """)
        r = rows[0] if rows else None
        return dict(
            total_sites = SiteRepo.count(),
            healthy     = (r["healthy"]  or 0) if r else 0,
            warning     = (r["warning"]  or 0) if r else 0,
            critical    = (r["critical"] or 0) if r else 0,
        )

    @classmethod
    def upsert(cls, url: str, ip: str, expiry: str, days_left: int):
        """Insert or update a scan result."""
        cls.execute("""
            INSERT INTO results (site, ip, expiry, days_left, checked_on, alert_sent)
            VALUES (?, ?, ?, ?, datetime('now'), NULL)
            ON CONFLICT(site) DO UPDATE
              SET ip=excluded.ip, expiry=excluded.expiry,
                  days_left=excluded.days_left, checked_on=datetime('now')
        """, (url, ip, expiry, days_left))

    @classmethod
    def mark_alert_sent(cls, url: str, sent_days: set):
        """Record which alert milestones have been sent for a site."""
        value = ",".join(str(d) for d in sorted(sent_days, reverse=True))
        cls.update_where({"site": url}, alert_sent=value)

    @classmethod
    def clear_alert_sent(cls, url: str):
        """Reset alert history once a cert is renewed (>30 days)."""
        cls.update_where({"site": url}, alert_sent=None)


class SecretRepo(Repository):
    table = "secrets"
    pk    = "id"


# Schema + seed
# ------------------------------------------------------------------ #

def init_db():
    """Create all tables and seed default users if absent."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sites (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                url         TEXT UNIQUE NOT NULL,
                ip_override TEXT
            );

            CREATE TABLE IF NOT EXISTS results (
                site        TEXT PRIMARY KEY,
                ip          TEXT,
                expiry      TEXT,
                days_left   INTEGER,
                checked_on  TEXT,
                alert_sent  TEXT
            );

            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email    TEXT,
                password TEXT NOT NULL,
                role     TEXT NOT NULL DEFAULT 'viewer'
            );

            CREATE TABLE IF NOT EXISTS secrets (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                encrypted_value TEXT NOT NULL,
                created_at      TEXT DEFAULT (datetime('now'))
            );
        """)
        conn.commit()
        _seed_users(conn)


def _seed_users(conn: sqlite3.Connection):
    if conn.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
        return
    conn.executemany(
        "INSERT INTO users (username, email, password, role) VALUES (?,?,?,?)",
        [
            ("admin",  "admin@example.com",  generate_password_hash("admin@123"),  "admin"),
            ("viewer", "viewer@example.com", generate_password_hash("viewer@123"), "viewer"),
        ]
    )
    conn.commit()
    print("✅ Default users seeded (change passwords before going to production!)")
