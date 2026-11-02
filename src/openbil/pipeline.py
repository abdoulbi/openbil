import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, text
from . import __version__
from .catalog import COUNTRIES, INDICATORS, TERMS
from .db import (
    sources,
    datasets,
    indicators,
    countries,
    collection_runs,
    dataset_versions,
    observations,
    quality_checks,
    now,
)
from .quality import normalize, finish_quality
from .connectors.worldbank import WorldBank

LOG = logging.getLogger(__name__)


def uid():
    return str(uuid.uuid4())


def canonical(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def seed(c):
    if not c.execute(select(sources.c.id).where(sources.c.id == "worldbank")).first():
        c.execute(
            sources.insert().values(
                id="worldbank",
                name="World Bank",
                url="https://api.worldbank.org/v2",
                terms_url=TERMS,
                license="CC BY 4.0 by default + World Bank terms; third-party exceptions",
                reviewed_at="2026-11-02",
            )
        )
    for code, name in COUNTRIES.items():
        if not c.execute(select(countries.c.id).where(countries.c.id == code)).first():
            c.execute(
                countries.insert().values(
                    id=code,
                    name=name,
                    region="Eastern Africa" if code == "KEN" else "Western Africa",
                )
            )
    for code, (label, unit, kind) in INDICATORS.items():
        if not c.execute(select(datasets.c.id).where(datasets.c.id == code)).first():
            c.execute(
                datasets.insert().values(
                    id=code,
                    source_id="worldbank",
                    title="WDI: " + label,
                    citation="The World Bank: World Development Indicators; original providers in version metadata.",
                    license_note="Consult indicator sourceOrganization and terms before redistribution.",
                )
            )
            c.execute(
                indicators.insert().values(
                    id=code, dataset_id=code, label=label, unit=unit, methodology=kind
                )
            )


def collect(e, country_codes=None, codes=None, start=1960, end=None, connector=None):
    country_codes = sorted(country_codes or COUNTRIES)
    codes = list(codes or INDICATORS)
    end = end or datetime.now(timezone.utc).year - 1
    if (
        not set(country_codes) <= COUNTRIES.keys()
        or not set(codes) <= INDICATORS.keys()
    ):
        raise ValueError("Unknown reviewed country/indicator")
    if not 1900 <= start <= end <= datetime.now(timezone.utc).year:
        raise ValueError("Invalid historical interval")
    run = uid()
    errors = []
    statuses = []
    own = connector is None
    wb = connector or WorldBank()
    # Session advisory lock is released on disconnect even after a process crash.
    with e.connect() as lock:
        if e.dialect.name == "postgresql":
            if not lock.execute(text("SELECT pg_try_advisory_lock(875311)")).scalar():
                raise RuntimeError("Another collection is running")
            lock.commit()
        try:
            with e.begin() as c:
                seed(c)
                # Holding the global lock proves an earlier running job is orphaned.
                c.execute(
                    collection_runs.update()
                    .where(collection_runs.c.status == "running")
                    .values(
                        status="interrupted",
                        finished_at=now(),
                        error="Previous collector terminated before completion",
                    )
                )
                c.execute(
                    collection_runs.insert().values(
                        id=run,
                        started_at=now(),
                        status="running",
                        parameters=canonical(
                            dict(
                                countries=country_codes,
                                indicators=codes,
                                start=start,
                                end=end,
                            )
                        ),
                        software_version=__version__,
                    )
                )
            for code in codes:
                try:
                    meta, header, records, manifest = wb.collect(
                        code, country_codes, start, end
                    )
                    default = f"https://api.worldbank.org/v2/country/{';'.join(country_codes)}/indicator/{code}?source=2&date={start}:{end}&format=json"
                    rows = normalize(code, country_codes, start, end, records, default)
                    if not records:
                        raise ValueError("Empty response; previous snapshot retained")
                    scope = canonical(
                        dict(countries=country_codes, start=start, end=end)
                    )
                    semantic = [
                        {k: v for k, v in r.items() if k != "source_url"}
                        for r in sorted(
                            rows, key=lambda r: (r["country_id"], r["period"])
                        )
                    ]
                    digest = hashlib.sha256(
                        canonical(
                            dict(
                                metadata=meta,
                                rows=semantic,
                                updated=header.get("lastupdated"),
                            )
                        ).encode()
                    ).hexdigest()
                    with e.begin() as c:
                        latest = (
                            c.execute(
                                select(dataset_versions)
                                .where(dataset_versions.c.dataset_id == code)
                                .order_by(dataset_versions.c.collected_at.desc())
                            )
                            .mappings()
                            .first()
                        )
                        if (
                            latest
                            and latest["digest"] == digest
                            and latest["scope"] == scope
                        ):
                            c.execute(
                                quality_checks.insert().values(
                                    id=uid(),
                                    run_id=run,
                                    version_id=latest["id"],
                                    indicator_id=code,
                                    check_name="unchanged",
                                    status="pass",
                                    details=canonical({"manifest": manifest}),
                                )
                            )
                            statuses.append("unchanged")
                            continue
                        changed = bool(
                            latest and json.loads(latest["metadata_json"]) != meta
                        )
                        rows = finish_quality(rows, changed)
                        version = uid()
                        stamp = now()
                        c.execute(
                            dataset_versions.insert().values(
                                id=version,
                                dataset_id=code,
                                run_id=run,
                                collected_at=stamp,
                                digest=digest,
                                scope=scope,
                                raw_manifest=canonical(manifest),
                                metadata_json=canonical(meta),
                                source_updated_at=header.get("lastupdated"),
                                transform_version=__version__,
                            )
                        )
                        for row in rows:
                            row.update(
                                id=uid(),
                                version_id=version,
                                source_id="worldbank",
                                indicator_id=code,
                                collected_at=stamp,
                                published_at=None,
                            )
                        c.execute(observations.insert(), rows)
                        counts = {
                            s: sum(r["quality_status"] == s for r in rows)
                            for s in ["pass", "warning", "missing", "rejected"]
                        }
                        c.execute(
                            quality_checks.insert().values(
                                id=uid(),
                                run_id=run,
                                version_id=version,
                                indicator_id=code,
                                check_name="coverage_and_integrity",
                                status="warning"
                                if counts["warning"]
                                or counts["rejected"]
                                or counts["missing"]
                                else "pass",
                                details=canonical(
                                    {
                                        "counts": counts,
                                        "expected": len(country_codes)
                                        * (end - start + 1),
                                        "received": len(records),
                                        "definition_changed": changed,
                                    }
                                ),
                            )
                        )
                    statuses.append("created")
                    LOG.info(
                        canonical(
                            {
                                "event": "dataset_committed",
                                "run_id": run,
                                "indicator": code,
                                "rows": len(rows),
                                "quality": counts,
                            }
                        )
                    )
                except Exception as exc:
                    errors.append(
                        {"indicator": code, "error": f"{type(exc).__name__}: {exc}"}
                    )
                    LOG.exception("dataset_failed %s", code)
                    with e.begin() as c:
                        c.execute(
                            quality_checks.insert().values(
                                id=uid(),
                                run_id=run,
                                indicator_id=code,
                                check_name="collection",
                                status="failed",
                                details=canonical(errors[-1]),
                            )
                        )
            status = "success" if not errors else "partial" if statuses else "failed"
            with e.begin() as c:
                c.execute(
                    collection_runs.update()
                    .where(collection_runs.c.id == run)
                    .values(
                        status=status,
                        finished_at=now(),
                        error=canonical(errors) if errors else None,
                    )
                )
            return {
                "run_id": run,
                "status": status,
                "datasets": statuses,
                "errors": errors,
            }
        finally:
            if own:
                wb.close()
            if e.dialect.name == "postgresql":
                lock.execute(text("SELECT pg_advisory_unlock(875311)"))
                lock.commit()
