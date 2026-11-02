import argparse
import json
import logging
import sys
from pathlib import Path
from .db import engine, migrate
from .pipeline import collect
from .connectors.worldbank import WorldBank


def refresh_catalog(output="data/catalog/worldbank.json"):
    wb = WorldBank()
    try:
        result = wb.discover()
        manifest = list(wb.manifest)
    finally:
        wb.close()
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    path.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2))
    print(
        f"{len(result)} catalogue entries; review required before enabling.", flush=True
    )
    return len(result)


def main():
    p = argparse.ArgumentParser(prog="openbil")
    p.add_argument("--database-url")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate")
    for name in ["collect", "schedule"]:
        s = sub.add_parser(name)
        s.add_argument("--countries", nargs="+")
        s.add_argument("--indicators", nargs="+")
        s.add_argument("--start", type=int, default=1960)
        s.add_argument("--end", type=int)
    d = sub.add_parser("discover")
    d.add_argument("--output", default="data/catalog/worldbank.json")
    args = p.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    if args.command == "discover":
        refresh_catalog(args.output)
        return
    e = engine(args.database_url)
    migrate(e)
    if args.command == "migrate":
        print("Migration 001 applied")
        return

    def job():
        if args.command == "schedule":
            try:
                refresh_catalog()
            except Exception:
                logging.exception(
                    "catalog_discovery_failed; collecting approved indicators anyway"
                )
        result = collect(e, args.countries, args.indicators, args.start, args.end)
        print(json.dumps(result), flush=True)
        return result

    if args.command == "collect":
        result = job()
        sys.exit(0 if result["status"] == "success" else 1)
    else:
        from apscheduler.schedulers.blocking import BlockingScheduler

        scheduler = BlockingScheduler(timezone="UTC")
        scheduler.add_job(
            job,
            "cron",
            hour=3,
            minute=0,
            id="worldbank_daily",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=3600,
        )
        # On restart, collect once; daily jobs re-fetch idempotently and resume failed datasets.
        job()
        scheduler.start()


if __name__ == "__main__":
    main()
