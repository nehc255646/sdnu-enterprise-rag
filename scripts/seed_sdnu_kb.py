"""Idempotent seed of knowledge/sdnu into tenant sdnu-demo via ingest API."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
from jose import jwt

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "knowledge" / "sdnu"
TENANT = os.environ.get("SEED_TENANT_ID", "sdnu-demo")
BASE = os.environ.get("SEED_INGEST_URL", "http://127.0.0.1:8001").rstrip("/")
SECRET = os.environ.get("JWT_SECRET", "change-me-to-a-long-random-string")
ALLOWED = {".txt", ".md", ".markdown"}


def _token() -> str:
    return jwt.encode({"sub": "seed", "tenant_id": TENANT}, SECRET, algorithm="HS256")


def _headers(tok: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tok}", "X-Tenant-Id": TENANT}


def main() -> int:
    files = sorted(p for p in CORPUS.iterdir() if p.is_file() and p.suffix.lower() in ALLOWED)
    if not files:
        print(f"no corpus files in {CORPUS}", file=sys.stderr)
        return 1
    tok = _token()
    with httpx.Client(timeout=180.0) as client:
        listed = client.get(f"{BASE}/api/v1/documents", headers=_headers(tok), params={"limit": 200})
        listed.raise_for_status()
        have = {item["filename"] for item in listed.json().get("items", [])}
        pending = [p for p in files if p.name not in have]
        print(f"sdnu-demo: {len(have)} already ingested, {len(pending)} to ingest")
        for path in pending:
            with path.open("rb") as fh:
                resp = client.post(
                    f"{BASE}/api/v1/ingest",
                    headers=_headers(tok),
                    files={"file": (path.name, fh, "text/plain")},
                    data={"doc_type": "kb", "sync": "true"},
                )
            if resp.status_code >= 400:
                print(f"  FAIL {path.name}: {resp.status_code} {resp.text}", file=sys.stderr)
                return 1
            print(f"  ok {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
