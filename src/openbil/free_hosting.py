"""Rebuildable, visit-triggered data cache for a single free web instance.

This is intentionally not a persistent database or an unattended scheduler.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import Lock
from sqlalchemy import select
from .db import engine, migrate, collection_runs
from .pipeline import collect
from .connectors.worldbank import WorldBank

_LOCK = Lock()


def collection_state(url, refreshed, latest):
    started = datetime.fromisoformat(latest["started_at"])
    ttl = timedelta(hours=24 if latest["status"] == "success" else 1)
    return {
        "url": url,
        "refreshed": refreshed,
        "status": latest["status"],
        "last_attempt_at": started.isoformat(),
        "next_eligible_at": (started + ttl).isoformat(),
    }


def ensure_data(root="data/free", connector=None, clock=None):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    url = "sqlite:///" + str(root / "openbil.sqlite")
    current = clock or datetime.now(timezone.utc)
    with _LOCK:
        db = engine(url)
        try:
            migrate(db)
            with db.connect() as c:
                latest = (
                    c.execute(
                        select(collection_runs).order_by(
                            collection_runs.c.started_at.desc()
                        )
                    )
                    .mappings()
                    .first()
                )
            if latest:
                age = current - datetime.fromisoformat(latest["started_at"])
                ttl = timedelta(hours=24 if latest["status"] == "success" else 1)
                if age < ttl:
                    return collection_state(url, False, latest)
            client = connector or WorldBank(raw_dir=root / "raw")
            try:
                collect(db, connector=client)
            finally:
                if connector is None:
                    client.close()
            with db.connect() as c:
                latest = c.execute(
                    select(collection_runs).order_by(collection_runs.c.started_at.desc())
                ).mappings().first()
            return collection_state(url, True, latest)
        finally:
            db.dispose()
