"""Verify raw byte hashes and reproduce every stored snapshot without network."""

import argparse
import hashlib
import json
from pathlib import Path
from sqlalchemy import select, text
from openbil.db import engine, dataset_versions, observations
from openbil.quality import normalize
from openbil.pipeline import canonical


def audit(url, root=Path(".")):
    e = engine(url)
    report = {
        "raw_files_verified": 0,
        "versions_verified": 0,
        "rows_verified": 0,
        "errors": [],
    }
    with e.connect() as c:
        for v in c.execute(select(dataset_versions)).mappings():
            try:
                records = []
                for item in json.loads(v["raw_manifest"]):
                    path = root / item["file"]
                    raw = path.read_bytes()
                    if hashlib.sha256(raw).hexdigest() != item["sha256"]:
                        raise ValueError("Raw hash mismatch: " + str(path))
                    report["raw_files_verified"] += 1
                    if "/country/" in item["url"]:
                        records.extend(
                            (r, item["url"]) for r in (json.loads(raw)[1] or [])
                        )
                scope = json.loads(v["scope"])
                rows = normalize(
                    v["dataset_id"],
                    scope["countries"],
                    scope["start"],
                    scope["end"],
                    records,
                    "unused-for-hash",
                )
                semantic = [
                    {k: val for k, val in r.items() if k != "source_url"}
                    for r in sorted(rows, key=lambda r: (r["country_id"], r["period"]))
                ]
                digest = hashlib.sha256(
                    canonical(
                        dict(
                            metadata=json.loads(v["metadata_json"]),
                            rows=semantic,
                            updated=v["source_updated_at"],
                        )
                    ).encode()
                ).hexdigest()
                if digest != v["digest"]:
                    raise ValueError("Semantic digest mismatch")
                stored = {
                    (r["country_id"], r["period"]): r
                    for r in c.execute(
                        select(observations).where(observations.c.version_id == v["id"])
                    ).mappings()
                }
                if len(stored) != len(rows):
                    raise ValueError("Row count differs")
                for row in rows:
                    old = stored[row["country_id"], row["period"]]
                    for key in [
                        "value",
                        "unit",
                        "data_status",
                        "source_status",
                        "footnote",
                    ]:
                        if row[key] != old[key]:
                            raise ValueError("Stored transformed value differs: " + key)
                report["versions_verified"] += 1
                report["rows_verified"] += len(rows)
            except Exception as exc:
                report["errors"].append({"version_id": v["id"], "error": str(exc)})
        report["coverage"] = [
            dict(r)
            for r in c.execute(
                text(
                    "SELECT indicator_id, COUNT(*) AS cells, COUNT(value) AS nonmissing, SUM(CASE WHEN quality_status='warning' THEN 1 ELSE 0 END) AS warnings, SUM(CASE WHEN quality_status='rejected' THEN 1 ELSE 0 END) AS rejected FROM current_observations GROUP BY indicator_id"
                )
            ).mappings()
        ]
        report["statuses"] = [
            dict(r)
            for r in c.execute(
                text(
                    "SELECT data_status, COUNT(*) AS cells FROM current_observations GROUP BY data_status"
                )
            ).mappings()
        ]
    e.dispose()
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--database-url", required=True)
    p.add_argument("--root", default=".")
    p.add_argument("--output", default="docs/snapshot-audit.json")
    a = p.parse_args()
    r = audit(a.database_url, Path(a.root))
    Path(a.output).write_text(json.dumps(r, indent=2))
    print(json.dumps(r))
    raise SystemExit(bool(r["errors"]))
