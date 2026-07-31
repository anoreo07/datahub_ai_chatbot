"""Seed script: run bootstrap."""
import asyncio

import structlog

from scripts.bootstrap import bootstrap

log = structlog.get_logger()

if __name__ == "__main__":
    asyncio.run(bootstrap())
