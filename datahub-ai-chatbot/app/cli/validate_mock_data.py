#!/usr/bin/env python3
"""CLI to validate mock DataHub fixture data."""
import sys
from collections import Counter
from pathlib import Path

from config.settings import settings
from ingestion.loader import MockMetadataLoader, MockValidationError


def main() -> None:
    fixtures_dir = Path(settings.MOCK_DATAHUB_FIXTURES_PATH)
    if not fixtures_dir.is_dir():
        print(f"Fixtures directory not found: {fixtures_dir}", file=sys.stderr)
        sys.exit(1)

    loader = MockMetadataLoader(fixtures_dir)

    try:
        domains = loader.load_domains()
        entities = loader.load_entities()
    except MockValidationError as e:
        print(f"Validation failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Domains ({len(domains)}):")
    for d in domains:
        print(f"  {d.urn} — {d.name}")
    print()

    type_counts = Counter(e.entity_type for e in entities)
    print(f"Entities ({len(entities)} total):")
    for etype, count in sorted(type_counts.items()):
        print(f"  {etype}: {count}")
    print()

    print("Validation passed — all fixtures are valid.")


if __name__ == "__main__":
    main()
