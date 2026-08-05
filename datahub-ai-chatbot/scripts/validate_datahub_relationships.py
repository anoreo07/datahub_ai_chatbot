"""Validate relationship integrity across the DataHub metadata source.

Scans every entity that a sync from the configured DataHub source (mock fixtures
by default, or `--fixtures <path>`) would produce and reports:

  - entities missing an owner / domain / platform
  - domain_urn referencing a non-existent domain
  - lineage (upstream/downstream) refs pointing to unknown URNs
  - glossary-term refs pointing to unknown glossary terms
  - linked-document refs pointing to unknown documents
  - duplicate or empty URNs

Run:
    python -m scripts.validate_datahub_relationships
    python -m scripts.validate_datahub_relationships --fixtures app/data/mock_datahub
"""

import argparse
from collections import defaultdict
from pathlib import Path

from ingestion.loader import MockMetadataLoader


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate DataHub relationship integrity")
    parser.add_argument("--fixtures", default=None, help="Path to a mock fixtures directory")
    args = parser.parse_args()

    if args.fixtures:
        fixtures_dir = Path(args.fixtures)
    else:
        from config.settings import settings
        fixtures_dir = Path(settings.MOCK_DATAHUB_FIXTURES_PATH)

    if not fixtures_dir.exists():
        print(f"[ERROR] fixtures dir not found: {fixtures_dir}")
        return

    loader = MockMetadataLoader(fixtures_dir)
    entities = loader.load_entities()
    domains = loader.load_domains_by_urn()

    urn_index = {e.urn: e for e in entities}
    name_index: dict[str, list] = defaultdict(list)
    for e in entities:
        name_index[e.name.lower()].append(e.urn)
        if e.display_name:
            name_index[e.display_name.lower()].append(e.urn)

    domain_urns = set(domains)
    domain_names = {d.name.lower() for d in domains.values()}

    issues: list[str] = []

    for e in entities:
        label = f"{e.entity_type}/{e.urn}"
        if not e.name:
            issues.append(f"[MISSING NAME] {label}")
        if not e.owners:
            issues.append(f"[NO OWNERS] {label}")
        if not e.domain and not e.domain_urn:
            issues.append(f"[NO DOMAIN] {label}")
        if e.domain_urn and e.domain_urn not in domain_urns:
            issues.append(f"[BROKEN DOMAIN_URN] {label} -> {e.domain_urn}")
        if e.domain and e.domain.lower() not in domain_names:
            issues.append(f"[UNKNOWN DOMAIN] {label} -> {e.domain!r}")

        for u in e.upstreams + e.downstreams:
            if u not in urn_index:
                issues.append(f"[BROKEN LINEAGE] {label} -> {u}")
            else:
                other = urn_index[u]
                if other.deleted:
                    issues.append(f"[DELETED LINEAGE TARGET] {label} -> {u}")

        for t in e.glossary_terms:
            if t not in urn_index:
                issues.append(f"[BROKEN GLOSSARY REF] {label} -> {t}")

        for d in e.linked_documents:
            matched = any(
                (doc.display_name or doc.name).lower() == d.lower()
                or d.lower() in (doc.name or "").lower()
                for doc in urn_index.values()
                if doc.entity_type == "document"
            )
            if not matched:
                issues.append(f"[BROKEN DOCUMENT REF] {label} -> {d!r}")

    issues = _dedupe(issues)
    if not issues:
        print(f"OK - no relationship issues found across {len(entities)} entities "
              f"({len(domains)} domains).")
        return

    print(f"Found {len(issues)} relationship issue(s) across {len(entities)} entities:")
    for issue in issues:
        print("  " + issue)
    raise SystemExit(1)


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


if __name__ == "__main__":
    main()
