import json
import math
from .catalog import INDICATORS


def normalize(code, countries, start, end, records, default_url):
    result = {}
    bounds = code in {"SL.UEM.TOTL.ZS", "SL.EMP.TOTL.SP.ZS"}
    for r, url in records:
        country = r.get("countryiso3code")
        year = str(r.get("date", ""))
        if (
            r.get("indicator", {}).get("id") != code
            or country not in countries
            or not year.isdigit()
        ):
            raise ValueError("Unexpected indicator, country or non-annual period")
        year = int(year)
        if not start <= year <= end:
            raise ValueError("Period outside requested scope")
        key = (country, year)
        if key in result:
            raise ValueError(f"Duplicate observation {key}")
        value = r.get("value")
        flags = []
        status = str(r.get("obs_status") or "").strip()
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(f"Nonfinite/non-numeric value {key}")
        kind = (
            "missing"
            if value is None
            else ("projected" if status == "F" else INDICATORS[code][2])
        )
        # Blank source status does NOT prove an observed measurement.
        if status and status != "F":
            flags.append("unmapped_source_status")
        note = str(r.get("footnote") or "")
        if note:
            flags.append("source_footnote_review")
        if value is not None and (
            (bounds and not 0 <= value <= 100)
            or (code == "NY.GDP.MKTP.CD" and value < 0)
        ):
            flags.append("domain_violation")
        result[key] = dict(
            country_id=country,
            period=year,
            value=value,
            unit=INDICATORS[code][1],
            source_url=url,
            data_status=kind,
            source_status=status,
            footnote=note,
            flags=flags,
        )
    for country in countries:
        for year in range(start, end + 1):
            result.setdefault(
                (country, year),
                dict(
                    country_id=country,
                    period=year,
                    value=None,
                    unit=INDICATORS[code][1],
                    source_url=default_url,
                    data_status="missing",
                    source_status="",
                    footnote="",
                    flags=["absent_from_response"],
                ),
            )
        previous = None
        for year in range(start, end + 1):
            row = result[country, year]
            v = row["value"]
            if (
                previous is not None
                and v is not None
                and abs(v - previous) > max(abs(previous) * 2, 20)
            ):
                row["flags"].append("large_change_review")
            previous = v
    return list(result.values())


def finish_quality(rows, definition_changed=False):
    for row in rows:
        if definition_changed:
            row["flags"].append("definition_changed_review")
        row["quality_status"] = (
            "missing"
            if row["value"] is None
            else "rejected"
            if "domain_violation" in row["flags"]
            else "warning"
            if row["flags"]
            else "pass"
        )
        row["flags"] = json.dumps(row["flags"])
    return rows
