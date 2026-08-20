#!/usr/bin/env python3
"""Phân tích chất lượng data thật trên DataHub corporate.

Đếm tỉ lệ dataset có schema fields / domain / ownership / glossaryTerms
trên mẫu N dataset, đồng thời kiểm tra query nào bị WAF chặn (scroll vs search).

Chạy (khi đã vào mạng corporate):
    .venv/bin/python scripts/analyze_datahub_quality.py            # mẫu 200, an toàn (có delay)
    .venv/bin/python scripts/analyze_datahub_quality.py --count 500 --no-wait

Kết quả in ra + lưu file JSON báo cáo.
Exit code: 0 = chạy xong (kể cả nếu scroll bị WAF mà đã fallback search),
           1 = mọi đường đều bị chặn/không kết nối được.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections import Counter
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


class WAFBlocked(RuntimeError):
    pass


def gql(session: requests.Session, url: str, query: str, variables: dict | None = None) -> dict:
    try:
        r = session.post(url, json={"query": query, "variables": variables or {}}, timeout=120)
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"network error: {exc}") from exc
    if r.status_code == 403 or any(m in r.text.lower() for m in WAF_MARKERS):
        raise WAFBlocked(f"HTTP 403 (WAF). body[:150]={r.text[:150]!r}")
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    data = r.json()
    if "errors" in data:
        msgs = [e.get("message", "")[:150] for e in data["errors"]][:3]
        raise RuntimeError(f"GraphQL errors: {msgs}")
    return data


def jittered_sleep(base: float):
    time.sleep(base + random.uniform(0.2, 0.8))


OWNER_SELECTION = """ownership {
  owners {
    owner {
      corpUser { urn username properties { displayName email } }
      corpGroup { urn name properties { displayName email } }
    }
  }
}"""


def build_scroll_query(with_owner: bool = True) -> str:
    owner_block = OWNER_SELECTION if with_owner else ""
    return f"""query scroll($input: ScrollAcrossEntitiesInput!) {{
  scrollAcrossEntities(input: $input) {{
    total
    nextScrollId
    searchResults {{
      entity {{
        urn
        type
        ... on Dataset {{
          platform {{ name }}
          {owner_block}
          domain {{ domain {{ properties {{ name }} }} }}
          glossaryTerms {{ terms {{ term {{ name }} }} }}
          schemaMetadata {{ fields {{ fieldPath nativeDataType }} }}
        }}
      }}
    }}
  }}
}}"""


SCROLL_QUERY = build_scroll_query(with_owner=True)

SEARCH_QUERY = """query search($query: String!, $count: Int, $start: Int) {
  search(input: { type: DATASET, query: $query, count: $count, start: $start }) {
    total
    searchResults { entity { urn type } }
  }
}"""


def build_detail_query(with_owner: bool = True) -> str:
    owner_block = OWNER_SELECTION if with_owner else ""
    return f"""query detail($urn: String!) {{
  entity(urn: $urn) {{
    urn
    ... on Dataset {{
      platform {{ name }}
      {owner_block}
      domain {{ domain {{ properties {{ name }} }} }}
      glossaryTerms {{ terms {{ term {{ name }} }} }}
      schemaMetadata {{ fields {{ fieldPath nativeDataType }} }}
    }}
  }}
}}"""


DETAIL_QUERY = build_detail_query(with_owner=True)


def is_owner_validation_error(exc: Exception) -> bool:
    text = str(exc)
    low = text.lower()
    return "ownership" in low or "ownertype" in low or "corpuser" in low or "corpgroup" in low


def count_fields(entity: dict) -> int:
    return len((entity.get("schemaMetadata") or {}).get("fields") or [])


def has_owner(entity: dict) -> bool:
    for owner in ((entity.get("ownership") or {}).get("owners") or []):
        o = owner.get("owner") or {}
        if o.get("corpUser") or o.get("corpGroup"):
            return True
    return False


def extract(entity: dict) -> dict:
    domain = ((entity.get("domain") or {}).get("domain") or {}).get("properties") or {}
    return {
        "urn": entity.get("urn"),
        "platform": ((entity.get("platform") or {}).get("name")) or "?",
        "n_fields": count_fields(entity),
        "has_domain": bool(domain),
        "domain_name": domain.get("name"),
        "has_owner": has_owner(entity),
        "has_glossary": bool((entity.get("glossaryTerms") or {}).get("terms")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phân tích chất lượng data DataHub corporate")
    parser.add_argument("--count", type=int, default=200, help="số dataset tối đa cần phân tích")
    parser.add_argument("--no-wait", action="store_true", help="bỏ delay giữa các request (nhanh hơn, dễ bị WAF)")
    parser.add_argument("--scroll", action="store_true", help="chỉ dùng scroll; nếu bị WAF sẽ dừng ngay (không fallback)")
    parser.add_argument("--out", default="", help="đường dẫn file báo cáo JSON (mặc định: /tmp/datahub_quality_report.json)")
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    url = os.environ.get("DATAHUB_GMS_URL", "")
    token = os.environ.get("DATAHUB_TOKEN", "")
    if not url or not token:
        print("ERROR: thiếu DATAHUB_GMS_URL / DATAHUB_TOKEN trong .env")
        return 1

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "DataAtlas-MetadataSync/1.0 (internal; contact: dataatlas team)",
    })

    delay = 0.0 if args.no_wait else 1.5
    print("=" * 70)
    print("DATAHUB DATA QUALITY ANALYSIS")
    print("=" * 70)
    print(f"URL   : {url}")
    print(f"Count : {args.count} datasets")
    print()

    stats = Counter()
    platforms = Counter()
    domain_names = Counter()
    samples: list[dict] = []
    errors: list[str] = []
    used_scroll = False
    n_total = 0

    # ---------------- Phase 1: scrollAcrossEntities ----------------
    if delay:
        jittered_sleep(1.0)
    scroll_id = None
    seen: set[str] = set()
    try:
        while n_total < args.count:
            inp = {"types": ["DATASET"], "query": "*", "count": 100}
            if scroll_id:
                inp["scrollId"] = scroll_id
            data = gql(session, url, SCROLL_QUERY, {"input": inp})
            sc = data["data"]["scrollAcrossEntities"]
            results = sc.get("searchResults") or []
            for item in results:
                ent = item.get("entity") or {}
                urn = ent.get("urn")
                if urn in seen:
                    continue
                seen.add(urn)
                stats["scanned"] += 1
                info = extract(ent)
                samples.append(info)
                stats["with_schema"] += bool(info["n_fields"])
                stats["with_domain"] += bool(info["has_domain"])
                stats["with_owner"] += bool(info["has_owner"])
                stats["with_glossary"] += bool(info["has_glossary"])
                if info["n_fields"] and info["has_domain"]:
                    stats["with_schema_and_domain"] += 1
                platforms[info["platform"]] += 1
                if info["domain_name"]:
                    domain_names[info["domain_name"]] += 1
                n_total += 1
                if n_total >= args.count:
                    break
            scroll_id = sc.get("nextScrollId")
            if not results or not scroll_id:
                break
            if delay:
                jittered_sleep(delay)
        used_scroll = True
        print(f"[PASS] scrollAcrossEntities: lấy được {n_total} dataset")
    except WAFBlocked as exc:
        errors.append(f"scroll: WAF blocked -> {exc}")
        print(f"[FAIL] scrollAcrossEntities: WAF/403 blocked")
        if args.scroll:
            print("       (--scroll được đặt, dừng tại đây)")
            _report(stats, platforms, domain_names, samples, errors, used_scroll, args.out)
            return 1
        print("       -> fallback sang search + detail theo từng urn")
    except Exception as exc:
        errors.append(f"scroll: {exc}")
        print(f"[FAIL] scrollAcrossEntities: {exc}")
        if args.scroll:
            _report(stats, platforms, domain_names, samples, errors, used_scroll, args.out)
            return 1
        print("       -> fallback sang search + detail theo từng urn")

    # ---------------- Phase 2 (fallback): search + detail ----------------
    if not used_scroll and n_total < args.count:
        try:
            start = 0
            while n_total < args.count:
                if delay:
                    jittered_sleep(delay)
                data = gql(session, url, SEARCH_QUERY, {"query": "*", "count": 100, "start": start})
                results = data["data"]["search"]["searchResults"]
                if not results:
                    break
                for item in results:
                    if n_total >= args.count:
                        break
                    urn = (item.get("entity") or {}).get("urn")
                    if not urn or urn in seen:
                        continue
                    seen.add(urn)
                    if delay:
                        jittered_sleep(delay)
                    try:
                        detail = gql(session, url, DETAIL_QUERY, {"urn": urn})
                    except Exception as exc:
                        errors.append(f"detail {urn[:80]}: {exc}")
                        continue
                    ent = detail["data"]["entity"] or {}
                    info = extract(ent)
                    samples.append(info)
                    stats["scanned"] += 1
                    stats["with_schema"] += bool(info["n_fields"])
                    stats["with_domain"] += bool(info["has_domain"])
                    stats["with_owner"] += bool(info["has_owner"])
                    stats["with_glossary"] += bool(info["has_glossary"])
                    if info["n_fields"] and info["has_domain"]:
                        stats["with_schema_and_domain"] += 1
                    platforms[info["platform"]] += 1
                    if info["domain_name"]:
                        domain_names[info["domain_name"]] += 1
                    n_total += 1
                start += len(results)
                if start >= data["data"]["search"]["total"]:
                    break
            print(f"[PASS] search+detail: lấy được {n_total} dataset")
        except WAFBlocked as exc:
            errors.append(f"search: WAF blocked -> {exc}")
            print(f"[FAIL] search+detail: WAF/403 blocked")
        except Exception as exc:
            errors.append(f"search: {exc}")
            print(f"[FAIL] search+detail: {exc}")

    return _report(stats, platforms, domain_names, samples, errors, used_scroll, args.out)


def _report(stats, platforms, domain_names, samples, errors, used_scroll, out) -> int:
    n = stats.get("scanned", 0)
    print()
    print("=" * 70)
    print("KẾT QUẢ")
    print("=" * 70)
    if n == 0:
        print("Không lấy được dataset nào (xem errors).")
    else:
        print(f"Datasets quét được : {n}")
        for key in ("with_schema", "with_domain", "with_owner", "with_glossary", "with_schema_and_domain"):
            v = stats.get(key, 0)
            print(f"  {key:<24}: {v:5d}  ({100 * v / n:5.1f}%)")
        print()
        print("Top platforms:")
        for p, c in platforms.most_common(8):
            print(f"  {p:<24}: {c}")
        print()
        print("Top domains:")
        for d, c in domain_names.most_common(12):
            print(f"  {d:<30}: {c}")
    if errors:
        print()
        print("Errors:")
        for e in errors[:10]:
            print(f"  - {e}")
    report = {
        "used_scroll": used_scroll,
        "scanned": n,
        "stats": {k: v for k, v in stats.items() if k != "scanned"},
        "platforms": dict(platforms.most_common()),
        "domains": dict(domain_names.most_common()),
        "errors": errors,
        "samples": samples[:50],
    }
    out_path = out or "/tmp/datahub_quality_report.json"
    Path(out_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"Báo cáo chi tiết: {out_path}")
    print("=" * 70)
    return 0 if n else 1


if __name__ == "__main__":
    sys.exit(main())
