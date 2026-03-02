"""
Pre-startup script: terminates idle-in-transaction connections so that
alembic upgrade head does not hang waiting for locks on alembic_version.
"""
import os
import sys

import psycopg2


def get_sync_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASSWORD", "password")
        name = os.getenv("DB_NAME", "chm_krypton")
        url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("postgres://", "postgresql://")
    return url


def main() -> None:
    url = get_sync_url()
    print(f">>> prestart: connecting to database...", flush=True)
    try:
        conn = psycopg2.connect(url, connect_timeout=10)
        conn.autocommit = True
        cur = conn.cursor()

        # Kill connections that are stuck in an open transaction
        cur.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE state IN ('idle in transaction', 'idle in transaction (aborted)')
              AND query_start < NOW() - INTERVAL '30 seconds'
              AND pid <> pg_backend_pid()
        """)
        killed = cur.rowcount
        if killed:
            print(f">>> prestart: terminated {killed} idle-in-transaction connection(s)", flush=True)
        else:
            print(">>> prestart: no stale connections found", flush=True)

        cur.close()
        conn.close()
    except Exception as e:
        # Non-fatal: log and continue — alembic will fail with a clear error if DB is down
        print(f">>> prestart: WARNING — could not clean connections: {e}", flush=True)


if __name__ == "__main__":
    main()
