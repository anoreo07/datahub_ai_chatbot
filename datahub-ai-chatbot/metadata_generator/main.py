import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.tags import TAGS
from data.domains import DOMAINS
from data.glossary import ALL_DOMAIN_GLOSSARY
from data.datasets import DATASETS
from data.dashboards import DASHBOARDS
from data.lineage import LINEAGE

from generators.tag import emit_tags
from generators.domain import emit_domains
from generators.glossary import emit_glossary_terms
from generators.dataset import emit_datasets
from generators.dashboard import emit_dashboards
from generators.lineage import emit_lineage

log = logging.getLogger(__name__)


def main():
    log.info("=" * 60)
    log.info("Starting DataHub metadata generation")
    log.info("=" * 60)

    log.info("\n[1/6] Emitting tags...")
    emit_tags(TAGS)

    log.info("\n[2/6] Emitting domains...")
    emit_domains(DOMAINS)

    log.info("\n[3/6] Emitting glossary terms...")
    emit_glossary_terms(ALL_DOMAIN_GLOSSARY)

    log.info("\n[4/6] Emitting datasets...")
    emit_datasets(DATASETS)

    log.info("\n[5/6] Emitting dashboards...")
    emit_dashboards(DASHBOARDS)

    log.info("\n[6/6] Emitting lineage...")
    emit_lineage(LINEAGE)

    log.info("=" * 60)
    log.info("Metadata generation complete!")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
