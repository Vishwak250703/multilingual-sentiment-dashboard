"""Wait for PostgreSQL to be ready before starting the app."""
import time
import psycopg2
import os
import sys


def wait_for_db(max_retries: int = 30, delay: int = 2):
    db_url = os.environ.get("DATABASE_URL_SYNC", "")
    # Parse from env vars as fallback
    host = os.environ.get("POSTGRES_HOST", "postgres")
    port = int(os.environ.get("POSTGRES_PORT", 5432))
    user = os.environ.get("POSTGRES_USER", "sentimentuser")
    password = os.environ.get("POSTGRES_PASSWORD", "sentimentpass")
    dbname = os.environ.get("POSTGRES_DB", "sentimentdb")

    print(f"Waiting for PostgreSQL at {host}:{port}...")
    for attempt in range(1, max_retries + 1):
        try:
            conn = psycopg2.connect(
                host=host, port=port, user=user, password=password, dbname=dbname
            )
            conn.close()
            print(f"PostgreSQL is ready after {attempt} attempt(s).")
            return
        except psycopg2.OperationalError as e:
            print(f"Attempt {attempt}/{max_retries}: DB not ready yet — {e}")
            time.sleep(delay)

    print("PostgreSQL did not become ready in time. Exiting.")
    sys.exit(1)


if __name__ == "__main__":
    wait_for_db()
