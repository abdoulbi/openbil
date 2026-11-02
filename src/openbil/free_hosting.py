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
                    return {"url": url, "refreshed": False, "status": latest["status"]}
            client = connector or WorldBank(raw_dir=root / "raw")
            try:
                result = collect(db, connector=client)
            finally:
                if connector is None:
                    client.close()
            return {"url": url, "refreshed": True, "status": result["status"]}
        finally:
            db.dispose()
