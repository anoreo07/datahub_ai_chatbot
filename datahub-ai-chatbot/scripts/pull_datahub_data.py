#!/usr/bin/env python3
"""Kéo toàn bộ metadata từ DataHub corporate về JSONL (mỗi dòng 1 JSON).

- Scroll query có inline fragments đủ: schema fields, domain, ownership, glossaryTerms, tags, platform.
- Owner selection TỰ INTROSPECT schema `OwnerType` (vì corporate không có `urn`/`corpUser` như
  các phiên bản khác nhau); nếu introspect fail thì tự bỏ ownership (không làm hỏng toàn bộ pull).
- Nếu scroll bị WAF/validation-error -> tự fallback search theo từng loại entity.
- Delay + jitter + retry + circuit breaker để không bị WAF chặn.
- Checkpoint: ghi dần từng entity, resume không kéo lại trùng.

Chạy (khi đã vào mạng corporate):
    .venv/bin/python scripts/pull_datahub_data.py
    .venv/bin/python scripts/pull_datahub_data.py --out /home/annh45/Desktop/datahub_pull
    .venv/bin/python scripts/pull_datahub_data.py --types DATASET,DOMAIN,GLOSSARY_TERM

Output: <out>/<entity_type>.txt (JSONL) + <out>/state/<entity_type>_urns.txt (checkpoint)
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
REQUEST_TIMEOUT = 90

BASE_DELAY = float(os.getenv("PULL_DELAY", "1.2"))
RETRIES = 3
RETRY_BACKOFF = 3.0
RETRY_BACKOFF_MAX = 30.0


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


class SchemaValidationError(RuntimeError):
    pass


def jittered_sleep(base: float):
    time.sleep(base + random.uniform(0.0, base * 0.5))


def classify_gql_errors(errors: list[dict]) -> str:
    for err in errors:
        ext = err.get("extensions") or {}
        c = ext.get("classification", "")
        if c == "ValidationError":
            return "validation"
        if c == "DataFetchingException":
            return "data_fetching"
    return "other"


def graphql(session, url, query, variables=None, retries=RETRIES) -> dict:
    last = None
    for attempt in range(1, retries + 1):
        try:
            r = session.post(url, json={"query": query, "variables": variables or {}}, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as exc:
            last = exc
            if attempt < retries:
                jittered_sleep(min(RETRY_BACKOFF * 2 ** (attempt - 1), RETRY_BACKOFF_MAX))
                continue
            raise
        if r.status_code == 403 or any(m in r.text.lower() for m in WAF_MARKERS):
            raise WAFBlocked(f"HTTP 403 WAF: {r.text[:150]!r}")
        if r.status_code == 429:
            last = RuntimeError(f"HTTP 429: {r.text[:150]}")
            if attempt < retries:
                jittered_sleep(min(RETRY_BACKOFF * 2 ** (attempt - 1), RETRY_BACKOFF_MAX))
                continue
            raise last
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
        data = r.json()
        if "errors" in data:
            cls = classify_gql_errors(data["errors"])
            if cls == "validation":
                raise SchemaValidationError(json.dumps(data["errors"], ensure_ascii=False)[:2000])
            if attempt < retries:
                jittered_sleep(min(RETRY_BACKOFF * 2 ** (attempt - 1), RETRY_BACKOFF_MAX))
                continue
            raise RuntimeError(json.dumps(data["errors"], ensure_ascii=False)[:2000])
        return data
    raise last


# ----------------------------------------------------------------
# Introspection OwnerType -> chọn selection phù hợp
# ----------------------------------------------------------------

OWNER_INTROSPECTION = """query {
  ownerRef: __type(name: "OwnerRef") { kind name fields { name } }
  ownerType: __type(name: "OwnerType") { kind name fields { name } }
}"""

# Ưu tiên theo thứ tự field thấy được trên OwnerType
def build_owner_selection(owner_fields: set[str]) -> str:
    if not owner_fields:
        return ""
    if "corpUser" in owner_fields and "corpGroup" in owner_fields:
        return (
            "ownership { owners { owner { "
            "corpUser { urn username properties { displayName email } } "
            "corpGroup { urn name properties { displayName email } } } } }"
        )
    if "urn" in owner_fields:
        return "ownership { owners { owner { urn } } }"
    if "ownerUrn" in owner_fields:
        return "ownership { owners { owner { ownerUrn } } }"
    return ""


def discover_owner_selection(session, url) -> tuple[str, str]:
    """Trả về (owner_selection, note). note rỗng nếu introspect OK."""
    try:
        data = graphql(session, url, OWNER_INTROSPECTION, retries=1)
    except Exception as exc:
        return "", f"introspect OwnerType failed: {str(exc)[:150]}"
    owner_type = (data.get("data") or {}).get("ownerType") or {}
    fields = {(f or {}).get("name") for f in (owner_type.get("fields") or [])}
    sel = build_owner_selection(fields)
    note = f"OwnerType fields={sorted(fields)} -> selection={'co owner' if sel else 'bo owner'}"
    return sel, note


# ----------------------------------------------------------------
# Query builders
# ----------------------------------------------------------------

def build_fragment(type_name: str, owner_selection: str) -> str:
    if type_name == "DATASET":
        return f"""... on Dataset {{
        properties {{ name qualifiedName origin description }}
        editableProperties {{ description }}
        platform {{ name urn }}
        {owner_selection}
        domain {{ domain {{ urn properties {{ name description }} }} }}
        glossaryTerms {{ terms {{ term {{ urn name properties {{ name description }} }} }} }}
        tags {{ tags {{ tag {{ urn name }} }} }}
        schemaMetadata {{ fields {{ fieldPath description nativeDataType type nullable isPartOfKey }} }}
    }}"""
    if type_name == "DASHBOARD":
        return f"""... on Dashboard {{
        tool dashboardId properties {{ name description }} platform {{ name urn }}
        {owner_selection}
        domain {{ domain {{ urn properties {{ name description }} }} }}
    }}"""
    if type_name == "CHART":
        return f"""... on Chart {{
        tool chartId properties {{ name description }} platform {{ name urn }}
        {owner_selection}
    }}"""
    if type_name == "CONTAINER":
        return f"""... on Container {{
        properties {{ name description }} platform {{ name urn }}
        {owner_selection}
        domain {{ domain {{ urn properties {{ name description }} }} }}
    }}"""
    if type_name == "DATA_FLOW":
        return f"""... on DataFlow {{
        orchestrator flowId cluster properties {{ name description externalUrl }} platform {{ name urn }}
        {owner_selection}
        domain {{ domain {{ urn properties {{ name description }} }} }}
    }}"""
    if type_name == "DATA_JOB":
        return f"""... on DataJob {{
        jobId dataFlow {{ flowId }} properties {{ name description externalUrl }}
        {owner_selection}
        domain {{ domain {{ urn properties {{ name description }} }} }}
    }}"""
    if type_name == "GLOSSARY_TERM":
        return f"""... on GlossaryTerm {{
        properties {{ name description }}
        {owner_selection}
    }}"""
    if type_name == "GLOSSARY_NODE":
        return """... on GlossaryNode { properties { name description } }"""
    if type_name == "CORP_USER":
        return """... on CorpUser { username properties { displayName email title departmentName } }"""
    if type_name == "CORP_GROUP":
        return """... on CorpGroup { name properties { displayName description } }"""
    if type_name == "DATA_PLATFORM":
        return """... on DataPlatform { name properties { type displayName } }"""
    if type_name == "DOMAIN":
        return """... on Domain { properties { name description } parentDomains { domains { urn ... on Domain { properties { name } } } } }"""
    if type_name == "TAG":
        return """... on Tag { name properties { name description } }"""
    if type_name == "ML_MODEL":
        return f"""... on MLModel {{
        properties {{ name description }} platform {{ name urn }}
        {owner_selection}
    }}"""
    if type_name == "ML_MODEL_GROUP":
        return f"""... on MLModelGroup {{
        properties {{ name description }} platform {{ name urn }}
        {owner_selection}
    }}"""
    raise KeyError(type_name)


def build_scroll_query(types: list[str], owner_selection: str) -> str:
    frags = "\n".join(build_fragment(t, owner_selection) for t in types)
    return f"""query scroll($input: ScrollAcrossEntitiesInput!) {{
  scrollAcrossEntities(input: $input) {{
    total
    nextScrollId
    searchResults {{
      entity {{
        urn
        type
        {frags}
      }}
    }}
  }}
}}"""


def build_search_query(entity_type: str, owner_selection: str) -> str:
    frags = build_fragment(entity_type, owner_selection)
    return f"""query search($query: String!, $count: Int, $start: Int) {{
  search(input: {{ type: {entity_type}, query: $query, count: $count, start: $start }}) {{
    total
    searchResults {{
      entity {{
        urn
        type
        {frags}
      }}
    }}
  }}
}}"""


def is_owner_error(exc: Exception) -> bool:
    low = str(exc).lower()
    return any(k in low for k in ("ownertype", "ownership", "corpuser", "corpgroup"))


def dedup_outputs(out_dir: Path, state_dir: Path) -> int:
    """Dedup các file output theo urn + rebuild checkpoint. Trả về số dòng xóa."""
    print("=" * 70)
    print("DEDUP + REBUILD CHECKPOINT")
    print("=" * 70)
    state_dir.mkdir(parents=True, exist_ok=True)
    removed_total = 0
    for path in sorted(out_dir.glob("*.txt")):
        etype = path.stem.upper()
        seen: dict[str, str] = {}
        lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        kept: list[str] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                urn = json.loads(line).get("urn")
            except Exception:
                urn = None
            if not urn:
                kept.append(line)
                continue
            if urn in seen:
                continue
            seen[urn] = line
            kept.append(line)
        removed = len(lines) - len(kept)
        if removed:
            path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
            removed_total += removed
        (state_dir / f"{etype.lower()}_urns.txt").write_text("\n".join(sorted(seen)), encoding="utf-8")
        (state_dir / f"{etype.lower()}_progress.json").write_text(
            json.dumps({"start": len(seen), "total": len(seen), "done": True}), encoding="utf-8"
        )
        print(f"  {etype:<16}: {len(lines):>6} dòng -> {len(kept):>6} (xóa {removed})")
    print(f"Tổng dòng trùng đã xóa: {removed_total}")
    print("=" * 70)
    return 0


# ----------------------------------------------------------------
# Main
# ----------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Kéo metadata DataHub corporate về JSONL")
    parser.add_argument("--out", default="", help="thư mục output (mặc định: <project>/datahub_pull)")
    parser.add_argument("--types", default="DATASET,DOMAIN,GLOSSARY_TERM,CORP_USER,CORP_GROUP,DATA_PLATFORM,TAG,DASHBOARD,CHART,CONTAINER,DATA_FLOW,DATA_JOB,GLOSSARY_NODE",
                        help="danh sách entity type, phân cách bằng dấu phẩy")
    parser.add_argument("--limit", type=int, default=0, help="giới hạn tổng entity (0 = không giới hạn)")
    parser.add_argument("--no-wait", action="store_true", help="bỏ delay (nhanh, dễ bị WAF)")
    parser.add_argument("--scroll", action="store_true", help="dùng scroll trước (mặc định: search, vì scroll hay fail do merge fragment)")
    parser.add_argument("--force-scroll", action="store_true", help="không fallback search nếu scroll fail")
    parser.add_argument("--no-owner", action="store_true", help="không kéo ownership (bỏ qua introspect)")
    parser.add_argument("--dedup", action="store_true", help="dedup các file output theo urn + rebuild checkpoint, rồi thoát")
    parser.add_argument("--rebuild-index", action="store_true", help="alias --dedup (dedup + rebuild checkpoint)")
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    url = os.environ.get("DATAHUB_GMS_URL", "")
    token = os.environ.get("DATAHUB_TOKEN", "")
    if not url or not token:
        print("ERROR: thiếu DATAHUB_GMS_URL / DATAHUB_TOKEN trong .env")
        return 2

    out_dir = Path(args.out) if args.out else Path(__file__).resolve().parent.parent / "datahub_pull"
    state_dir = out_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    types = [t.strip() for t in args.types.split(",") if t.strip()]

    if args.dedup or args.rebuild_index:
        return dedup_outputs(out_dir, state_dir)

    for t in types:
        try:
            build_fragment(t, "")
        except KeyError:
            print(f"ERROR: type không hỗ trợ: {t}")
            return 2
    delay = 0.0 if args.no_wait else BASE_DELAY

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "DataAtlas-MetadataSync/2.0 (internal metadata mirror; contact: dataatlas team)",
    })

    print("=" * 70)
    print("DATAHUB DATA PULL")
    print("=" * 70)
    print(f"URL   : {url}")
    print(f"Types : {', '.join(types)}")
    print(f"Out   : {out_dir}")
    print(f"Delay : {delay or '0'}s/request")
    print()

    # ---------------- Owner selection (introspect) ----------------
    cfg = {"owner_selection": ""}
    if not args.no_owner:
        if delay:
            jittered_sleep(1.0)
        cfg["owner_selection"], note = discover_owner_selection(session, url)
        print(f"[INFO] owner: {note}")
    else:
        print("[INFO] owner: bị tắt (--no-owner)")

    total_saved = 0
    errors: list[str] = []
    per_type = Counter()
    circuit_breaker = False

    def load_existing(entity_type: str) -> set:
        p = state_dir / f"{entity_type.lower()}_urns.txt"
        if not p.exists():
            return set()
        return {ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()}

    def save_existing(entity_type: str, urns: set) -> None:
        (state_dir / f"{entity_type.lower()}_urns.txt").write_text("\n".join(sorted(urns)), encoding="utf-8")

    def write_entity(entity_type: str, entity: dict) -> None:
        (out_dir / f"{entity_type.lower()}.txt").open("a", encoding="utf-8").write(
            json.dumps(entity, ensure_ascii=False) + "\n"
        )

    def _save_progress(etype: str, start: int, total: int | None, done: bool) -> None:
        (state_dir / f"{etype.lower()}_progress.json").write_text(
            json.dumps({"start": start, "total": total, "done": done}), encoding="utf-8"
        )

    def handle_results(results: list[dict], existing_by_type: dict) -> int:
        saved = 0
        for item in results:
            ent = item.get("entity") or {}
            urn = ent.get("urn")
            etype = ent.get("type")
            if not urn or not etype or etype not in existing_by_type:
                continue
            if urn in existing_by_type[etype]:
                continue
            existing_by_type[etype].add(urn)
            write_entity(etype, ent)
            per_type[etype] += 1
            saved += 1
        return saved

    def flush_checkpoints(existing_by_type: dict) -> None:
        for t, urns in existing_by_type.items():
            save_existing(t, urns)

    def enumerate_scroll() -> tuple[int, str | None]:
        nonlocal circuit_breaker, total_saved
        q = build_scroll_query(types, cfg["owner_selection"])
        existing_by_type = {t: load_existing(t) for t in types}
        scroll_id = None
        saved_total = 0
        while True:
            inp = {"types": types, "query": "*", "count": 100}
            if scroll_id:
                inp["scrollId"] = scroll_id
            try:
                data = graphql(session, url, q, {"input": inp})
            except WAFBlocked as exc:
                circuit_breaker = True
                flush_checkpoints(existing_by_type)
                return saved_total, f"WAF blocked: {exc}"
            except SchemaValidationError as exc:
                flush_checkpoints(existing_by_type)
                return saved_total, f"validation: {exc}"
            except Exception as exc:
                flush_checkpoints(existing_by_type)
                return saved_total, f"error: {exc}"
            sc = data.get("data", {}).get("scrollAcrossEntities") or {}
            results = sc.get("searchResults") or []
            saved = handle_results(results, existing_by_type)
            saved_total += saved
            total_saved += saved
            print(f"  scroll: +{saved} (saved={total_saved}, per_type={dict(per_type)})", flush=True)
            scroll_id = sc.get("nextScrollId")
            if args.limit and total_saved >= args.limit:
                break
            if not results or not scroll_id:
                break
            if delay:
                jittered_sleep(delay)
        flush_checkpoints(existing_by_type)
        return saved_total, None

    def enumerate_search() -> tuple[int, str | None]:
        nonlocal circuit_breaker, total_saved
        saved_total = 0
        errors_local = []
        for etype in types:
            q = build_search_query(etype, cfg["owner_selection"])
            existing = load_existing(etype)

            progress_path = state_dir / f"{etype.lower()}_progress.json"
            start = 0
            total = None
            done = False
            if progress_path.exists():
                try:
                    prog = json.loads(progress_path.read_text(encoding="utf-8"))
                    start = int(prog.get("start", 0))
                    total = prog.get("total")
                    done = bool(prog.get("done"))
                except Exception:
                    pass
            if done:
                print(f"  skip {etype} (đã hoàn thành trước đó, {len(existing)} entities)", flush=True)
                continue

            page_size = 100
            n_retry_bad = 0
            n_pages = 0
            while True:
                if args.limit and total_saved >= args.limit:
                    break
                try:
                    data = graphql(session, url, q, {"query": "*", "count": page_size, "start": start}, retries=1)
                except WAFBlocked as exc:
                    circuit_breaker = True
                    save_existing(etype, existing)
                    _save_progress(etype, start, total, done=False)
                    return saved_total, f"WAF blocked at {etype}: {exc}"
                except SchemaValidationError as exc:
                    save_existing(etype, existing)
                    errors_local.append(f"validation at {etype}: {str(exc)[:150]}")
                    break
                except Exception as exc:
                    if page_size > 1:
                        page_size = max(1, page_size // 2)
                        continue
                    # count=1 vẫn lỗi -> index hỏng, skip offset này
                    n_retry_bad += 1
                    print(f"  search {etype}@bad-index {start}: skip (+1)", flush=True)
                    start += 1
                    page_size = 100
                    if n_retry_bad > 200:
                        save_existing(etype, existing)
                        _save_progress(etype, start, total, done=False)
                        errors_local.append(f"quá nhiều bad index tại {etype}")
                        break
                    continue
                search = data.get("data", {}).get("search") or {}
                if total is None:
                    total = search.get("total", 0)
                results = search.get("searchResults") or []
                saved = 0
                for item in results:
                    ent = item.get("entity") or {}
                    urn = ent.get("urn")
                    if not urn or urn in existing:
                        continue
                    existing.add(urn)
                    write_entity(etype, ent)
                    per_type[etype] += 1
                    saved += 1
                saved_total += saved
                total_saved += saved
                print(f"  search {etype}@{start}: +{saved}/{len(results)} (total={total}, saved={total_saved})", flush=True)
                if not results:
                    break
                start += len(results)
                if total is not None and start >= total:
                    break
                if page_size < 100:
                    page_size = min(100, page_size * 2)
                if delay:
                    jittered_sleep(delay)
                n_pages += 1
                _save_progress(etype, start, total, done=False)
                if n_pages % 5 == 0:
                    save_existing(etype, existing)
            save_existing(etype, existing)
            _save_progress(etype, start, total, done=True)
        if errors_local:
            return saved_total, "; ".join(errors_local)
        return saved_total, None

    # ---------------- Phase 1: scroll (chỉ khi --scroll) ----------------
    scroll_ok = True
    if args.scroll:
        print("--- Phase 1: scrollAcrossEntities ---")
        if delay:
            jittered_sleep(1.0)
        saved, err = enumerate_scroll()
        if err:
            if not circuit_breaker and cfg["owner_selection"] and is_owner_error(Exception(err)):
                print(f"  owner vẫn lỗi schema -> thử bỏ ownership: {err[:150]}")
                cfg["owner_selection"] = ""
                if delay:
                    jittered_sleep(2.0)
                saved2, err2 = enumerate_scroll()
                if err2 is None:
                    print("[INFO] kéo được sau khi bỏ ownership")
                    err = None
                else:
                    print(f"  [FAIL] kể cả bỏ ownership vẫn lỗi: {err2[:200]}")
            elif not circuit_breaker:
                print(f"  -> thử lại không có ownership (lỗi không liên quan owner: {err[:150]})")
                cfg["owner_selection"] = ""
                if delay:
                    jittered_sleep(2.0)
                saved2, err2 = enumerate_scroll()
                if err2 is None:
                    print("[INFO] kéo được sau khi bỏ ownership")
                    err = None
                else:
                    print(f"  [FAIL] kể cả bỏ ownership vẫn lỗi: {err2[:200]}")
        if err:
            print(f"[FAIL] scroll: {err[:200]}")
            if circuit_breaker or args.force_scroll:
                print("Circuit breaker / --force-scroll: dừng. Chạy lại để resume.")
                _summary(out_dir, per_type, total_saved, errors + [err])
                return 1
            print("-> fallback search")
            scroll_ok = False
        else:
            print("[PASS] scroll done")
    else:
        print("--- (dùng search, bỏ qua scroll; thêm --scroll để thử scroll) ---")

    # ---------------- Phase 2: search ----------------
    if (args.scroll and not scroll_ok and not circuit_breaker) or not args.scroll:
        if args.scroll:
            print("--- Phase 2: search fallback ---")
        else:
            print("--- Phase 1: search (per entity type) ---")
        if delay:
            jittered_sleep(1.0)
        s2, e2 = enumerate_search()
        if e2:
            errors.append(f"search: {e2[:200]}")
            print(f"[FAIL] search: {e2[:200]}")
        else:
            print("[PASS] search done")

    _summary(out_dir, per_type, total_saved, errors)
    return 0 if not errors else 1


def _summary(out_dir: Path, per_type: Counter, total_saved: int, errors: list[str]) -> None:
    print()
    print("=" * 70)
    print("KẾT QUẢ PULL")
    print("=" * 70)
    for t, c in per_type.most_common():
        print(f"  {t:<16}: {c}")
    print(f"  {'TOTAL':<16}: {total_saved}")
    if errors:
        print()
        print("Errors:")
        for e in errors[:10]:
            print(f"  - {e}")
    print(f"Output: {out_dir}")
    print("=" * 70)


if __name__ == "__main__":
    sys.exit(main())
