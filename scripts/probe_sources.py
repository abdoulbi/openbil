"""Official endpoint probes; HTTP 200 is not proof of data integration."""

import concurrent.futures
import datetime
import json
import time
from pathlib import Path
import urllib.request

TARGETS = {
    "worldbank": (
        "api",
        "https://api.worldbank.org/v2/country/BFA/indicator/NY.GDP.MKTP.CD?format=json&per_page=1",
    ),
    "imf": ("documentation", "https://data.imf.org/en/Resource-Pages/IMF-API"),
    "afdb": ("documentation", "https://www.afdb.org/en/knowledge/statistics"),
    "unctad": ("portal", "https://unctadstat.unctad.org/datacentre/"),
    "comtrade": (
        "api_releases",
        "https://comtradeapi.un.org/public/v1/getComtradeReleases",
    ),
    "faostat": ("portal", "https://www.fao.org/faostat/"),
    "ilostat": ("documentation", "https://ilostat.ilo.org/data/bulk/"),
}


def probe(item):
    name, (kind, url) = item
    start = time.monotonic()
    row = {
        "source": name,
        "kind": kind,
        "url": url,
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "OpenBIL/0.2.0 access-check"}
        )
        with urllib.request.urlopen(req, timeout=25) as r:
            sample = r.read(4096)
            row.update(
                status=r.status,
                content_type=r.headers.get("Content-Type"),
                sample_bytes=len(sample),
                final_url=r.url,
            )
    except Exception as e:
        row.update(
            status=getattr(e, "code", None), error=type(e).__name__ + ": " + str(e)
        )
    row["seconds"] = round(time.monotonic() - start, 2)
    return row


if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(probe, TARGETS.items()))
    path = Path("docs/access-probes.json")
    path.write_text(json.dumps(results, indent=2))
    print(path)
