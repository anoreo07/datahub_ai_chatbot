#!/usr/bin/env python3
"""Test kết nối + auth tới DataHub corporate qua GraphQL.

Dùng để xác nhận endpoint + token hoạt động (vd sau khi đổi mạng/VPN).
Chạy:
    python scripts/test_datahub_conn.py
    python scripts/test_datahub_conn.py --url https://.../api/graphql --token eyJ...
    DATAHUB_GMS_URL=... DATAHUB_TOKEN=... python scripts/test_datahub_conn.py

Kết quả: in từng test với PASS/FAIL + thời gian. Exit code 0 nếu tất cả PASS.
Phát hiện WAF block (403 / ::IM_UNDER_ATTACK_BOX::) và báo rõ.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

WAF_MARKERS = ("im_under_attack_box", "loading-page")


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


def post(session: requests.Session, url: str, query: str, variables: dict | None = None):
    return session.post(
        url,
        json={"query": query, "variables": variables or {}},
        timeout=90,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Test DataHub GraphQL connectivity + auth")
    parser.add_argument("--url", default=os.environ.get("DATAHUB_GMS_URL", ""))
    parser.add_argument("--token", default=os.environ.get("DATAHUB_TOKEN", ""))
    parser.add_argument("--no-env", action="store_true", help="không đọc .env")
    args = parser.parse_args()

    if not args.no_env:
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    url = args.url or os.environ.get("DATAHUB_GMS_URL", "")
    token = args.token or os.environ.get("DATAHUB_TOKEN", "")

    if not url:
        print("ERROR: thiếu --url (hoặc DATAHUB_GMS_URL).")
        return 2
    if not token:
        print("ERROR: thiếu --token (hoặc DATAHUB_TOKEN).")
        return 2

    print("=" * 70)
    print("DATAHUB GRAPHQL CONNECTIVITY TEST")
    print("=" * 70)
    print(f"URL   : {url}")
    print(f"Token : {'set' if token else 'missing'} (len={len(token)})")
    print()

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "DataAtlas-MetadataSync/1.0 (internal; contact: dataatlas team)",
    })

    results = []

    def run(name: str, query: str, variables: dict | None = None, expect_path: str | None = None):
        t0 = time.time()
        try:
            resp = post(session, url, query, variables)
            dt = time.time() - t0
            if resp.status_code == 403 or any(m in resp.text.lower() for m in WAF_MARKERS):
                results.append((name, False, f"WAF/403 BLOCKED ({dt:.1f}s)"))
                print(f"[FAIL] {name} -> WAF/403 BLOCKED ({dt:.1f}s)")
                print(f"       body[:160]: {resp.text[:160]!r}")
                return None
            if resp.status_code != 200:
                results.append((name, False, f"HTTP {resp.status_code} ({dt:.1f}s)"))
                print(f"[FAIL] {name} -> HTTP {resp.status_code} ({dt:.1f}s)")
                print(f"       body[:160]: {resp.text[:160]!r}")
                return None
            data = resp.json()
            if "errors" in data:
                errs = [e.get("message", "") for e in data["errors"]][:3]
                results.append((name, False, f"GraphQL errors ({dt:.1f}s)"))
                print(f"[FAIL] {name} -> GraphQL errors ({dt:.1f}s)")
                for e in errs:
                    print(f"       err: {e}")
                return None
            if expect_path:
                node = data
                for part in expect_path.split("."):
                    node = (node or {}).get(part)
                if node is None:
                    results.append((name, False, f"path '{expect_path}' = null ({dt:.1f}s)"))
                    print(f"[FAIL] {name} -> path '{expect_path}' = null ({dt:.1f}s)")
                    return None
            results.append((name, True, f"{dt:.1f}s"))
            print(f"[PASS] {name} ({dt:.1f}s)")
            return data
        except requests.exceptions.SSLError as exc:
            results.append((name, False, "SSL/TLS error"))
            print(f"[FAIL] {name} -> SSL/TLS error: {exc}")
            return None
        except requests.exceptions.Timeout as exc:
            results.append((name, False, "timeout 90s"))
            print(f"[FAIL] {name} -> timeout: {exc}")
            return None
        except Exception as exc:
            results.append((name, False, str(exc)[:120]))
            print(f"[FAIL] {name} -> {exc}")
            return None

    print("--- 1. Authentication (me) ---")
    me = run("auth.me", "query { me { corpUser { username properties { displayName email } } } }", expect_path="data.me")

    print()
    print("--- 2. Search 5 datasets ---")
    search_data = run(
        "search.datasets",
        """query searchDatasets($query: String!, $count: Int) {
  search(input: { type: DATASET, query: $query, count: $count }) {
    total
    searchResults { entity { urn type ... on Dataset { name } } }
  }
}""",
        variables={"query": "*", "count": 5},
        expect_path="data.search.total",
    )

    print()
    print("--- 3. Dataset detail (schema/domain/ownership/glossary) ---")
    urn = None
    if search_data:
        results_list = (search_data.get("data", {}).get("search", {}).get("searchResults") or [])
        if results_list:
            urn = results_list[0].get("entity", {}).get("urn")
    if urn:
        detail = run(
            "dataset.detail",
            """query getDataset($urn: String!) {
  entity(urn: $urn) {
    urn
    type
    ... on Dataset {
      name
      properties { description }
      platform { name }
      ownership { owners { owner { ... on CorpUser { username } } } }
      domain { domain { properties { name } } }
      glossaryTerms { terms { term { name } } }
      schemaMetadata { fields { fieldPath nativeDataType } }
    }
  }
}""",
            variables={"urn": urn},
            expect_path="data.entity",
        )
        if detail:
            ent = detail.get("data", {}).get("entity") or {}
            print(f"       urn        : {ent.get('urn')}")
            print(f"       name       : {ent.get('name')}")
            print(f"       platform   : {ent.get('platform')}")
            domain = ((ent.get("domain") or {}).get("domain") or {}).get("properties") or {}
            print(f"       domain     : {domain.get('name')}")
            schema = ent.get("schemaMetadata") or {}
            fields = schema.get("fields") or []
            print(f"       schema     : {len(fields)} fields"
                  + (f" (vd: {fields[0].get('fieldPath')} : {fields[0].get('nativeDataType')})" if fields else ""))
            owners = (ent.get("ownership") or {}).get("owners") or []
            print(f"       owners     : {len(owners)}")
            terms = ((ent.get("glossaryTerms") or {}).get("terms") or [])
            print(f"       glossary   : {len(terms)} terms")
    else:
        print("[SKIP] dataset.detail -> không có kết quả search để lấy urn")

    print()
    print("--- 4. Domain list ---")
    run(
        "list.domains",
        """query domains($count: Int) {
  search(input: { type: DOMAIN, query: "*", count: $count }) {
    total
    searchResults { entity { urn type ... on Domain { properties { name } } } }
  }
}""",
        variables={"count": 10},
        expect_path="data.search.total",
    )

    print()
    print("=" * 70)
    n_pass = sum(1 for _, ok, _ in results if ok)
    n_fail = sum(1 for _, ok, _ in results if not ok)
    print(f"RESULT: {n_pass} PASS / {n_fail} FAIL / {len(results)} total")
    if n_fail:
        print("Chi tiết fail:")
        for name, ok, note in results:
            if not ok:
                print(f"  - {name}: {note}")
    print("=" * 70)
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
