"""Fetch and snapshot Supabase PostgREST OpenAPI schema.

This does NOT require direct Postgres credentials.
It queries the Supabase PostgREST OpenAPI endpoint and writes:
- supabase_openapi.json
- supabase_schema_summary.md

Usage (PowerShell):
  Set-Location .
  $env:PYTHONPATH = "$PWD\src"
  "C:/Users/Daksh Thakur/Desktop/ZeroDay/.venv/Scripts/python.exe" scripts/snapshot_supabase_schema.py

Requires:
- SUPABASE_URL
- SUPABASE_KEY (anon key is enough to fetch OpenAPI for exposed schemas)

Note:
- OpenAPI does not contain every DB constraint (e.g., RLS policies, indexes).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    from junior.core import settings

    supabase_url = (settings.supabase_url or "").strip().rstrip("/")
    supabase_key = (settings.supabase_key or "").strip()

    if not supabase_url or not supabase_key:
        print("Missing SUPABASE_URL and/or SUPABASE_KEY in .env")
        return 2

    openapi_url = f"{supabase_url}/rest/v1/"

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept": "application/openapi+json",
    }

    print(f"Fetching OpenAPI schema from: {openapi_url}")

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        resp = client.get(openapi_url, headers=headers)
        resp.raise_for_status()
        openapi = resp.json()

    root = Path(__file__).resolve().parents[1]
    out_json = root / "supabase_openapi.json"
    out_md = root / "supabase_schema_summary.md"

    _write_json(out_json, openapi)

    # Extract tables from paths
    paths = openapi.get("paths") or {}
    tables = sorted({p.strip("/").split("/")[0] for p in paths.keys() if isinstance(p, str) and p.startswith("/")})

    lines: list[str] = []
    lines.append("# Supabase schema snapshot")
    lines.append("")
    lines.append(f"Source: `{openapi_url}`")
    lines.append(f"Tables exposed via PostgREST: {len(tables)}")
    lines.append("")

    for t in tables:
        if not t:
            continue
        lines.append(f"- {t}")

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print(f"Tables: {', '.join(tables) if tables else '(none detected)'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
