"""Cloud entry point: wait for DB, migrate, then run exactly one service role."""

import os
import sys
import time
from openbil.db import engine, migrate
from sqlalchemy.exc import OperationalError


def command(role, port):
    if role == "collector":
        return ["openbil", "schedule"]
    if role != "dashboard":
        raise ValueError("APP_ROLE must be dashboard or collector")
    port = int(port)
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be in 1..65535")
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.address=0.0.0.0",
        f"--server.port={port}",
        "--browser.gatherUsageStats=false",
    ]


def main():
    if not os.environ.get("DATABASE_URL"):
        raise RuntimeError("Set DATABASE_URL before starting the service")
    argv = command(os.getenv("APP_ROLE", "dashboard"), os.getenv("PORT", "8501"))
    db = engine()
    for attempt in range(12):
        try:
            migrate(db)
            break
        except OperationalError:
            if attempt == 11:
                raise RuntimeError(
                    "Database unavailable after bounded startup retries"
                ) from None
            print("Database not ready; retrying startup.", flush=True)
            time.sleep(5)
    db.dispose()
    os.execvp(argv[0], argv)


if __name__ == "__main__":
    main()
