import hashlib
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import httpx

BASE = "https://api.worldbank.org/v2"


class WorldBank:
    def __init__(self, raw_dir="data/raw", client=None, delay=1.0, attempts=4):
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.client = client or httpx.Client(
            timeout=45,
            follow_redirects=True,
            headers={"User-Agent": "OpenBIL/0.2.0 public-research"},
        )
        self.delay = delay
        self.attempts = attempts
        self.manifest = []

    def close(self):
        self.client.close()

    def page(self, path, params):
        url = f"{BASE}/{path}"
        for attempt in range(self.attempts):
            try:
                time.sleep(self.delay)
                r = self.client.get(url, params=params)
                if r.status_code == 429 or r.status_code >= 500:
                    if attempt == self.attempts - 1:
                        r.raise_for_status()
                    retry = r.headers.get("Retry-After", "")
                    try:
                        wait = float(retry)
                    except ValueError:
                        try:
                            wait = (
                                parsedate_to_datetime(retry)
                                - datetime.now(timezone.utc)
                            ).total_seconds()
                        except (ValueError, TypeError):
                            wait = 2**attempt
                    if wait > 300:
                        raise RuntimeError(
                            "Retry-After >300s: deferred to next scheduled run"
                        )
                    time.sleep(max(0, wait))
                    continue
                r.raise_for_status()
                body = r.content
                digest = hashlib.sha256(body).hexdigest()
                path_raw = self.raw_dir / f"{digest}.json"
                path_raw.write_bytes(body)
                payload = r.json()
                if (
                    not isinstance(payload, list)
                    or len(payload) != 2
                    or not isinstance(payload[0], dict)
                    or "pages" not in payload[0]
                ):
                    raise ValueError("Invalid World Bank envelope or API error")
                if payload[1] is not None and not isinstance(payload[1], list):
                    raise ValueError("Expected records list")
                self.manifest.append(
                    {
                        "url": str(r.url),
                        "sha256": digest,
                        "file": str(path_raw),
                        "retrieved_at": datetime.now(timezone.utc).isoformat(),
                        "http_status": r.status_code,
                    }
                )
                return payload, str(r.url)
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == self.attempts - 1:
                    raise
                time.sleep(2**attempt)
        raise RuntimeError("Retry limit reached")

    def pages(self, path, params=None):
        params = {"format": "json", "per_page": 1000, **(params or {})}
        first, url = self.page(path, {**params, "page": 1})
        total = int(first[0]["total"])
        pages = int(first[0]["pages"])
        records = []
        if pages > 10000:
            raise ValueError("Unexpected page count")
        for p in range(1, max(pages, 1) + 1):
            data, u = (first, url) if p == 1 else self.page(path, {**params, "page": p})
            if int(data[0]["total"]) != total or data[0].get("lastupdated") != first[
                0
            ].get("lastupdated"):
                raise ValueError(
                    "Source changed during pagination; retry entire dataset"
                )
            records.extend((row, u) for row in (data[1] or []))
        if len(records) != total:
            raise ValueError(f"Incomplete pagination: {len(records)} / {total}")
        return first[0], records

    def indicator(self, code):
        _, rows = self.pages(f"indicator/{code}", {"source": 2})
        matches = [
            r
            for r, _ in rows
            if r["id"] == code and r.get("source", {}).get("id") == "2"
        ]
        if len(matches) != 1:
            raise ValueError("WDI indicator metadata missing or ambiguous")
        return matches[0]

    def collect(self, code, countries, start, end):
        self.manifest = []
        meta = self.indicator(code)
        header, records = self.pages(
            f"country/{';'.join(sorted(countries))}/indicator/{code}",
            {"source": 2, "date": f"{start}:{end}", "footnote": "y", "scale": "n"},
        )
        return meta, header, records, list(self.manifest)

    def discover(self):
        _, rows = self.pages("indicator", {"source": 2})
        return [r for r, _ in rows]
