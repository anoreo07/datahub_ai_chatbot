#!/usr/bin/env python3
"""CLI tool for importing documents into the chatbot."""
import argparse
import sys

import structlog

log = structlog.get_logger()


async def _import_document(args: argparse.Namespace) -> None:
    from app.dependencies import get_db_session
    from ingestion.document_ingestion import DocumentIngestionService

    async for session in get_db_session():
        service = DocumentIngestionService(session)
        try:
            if args.url:
                result = await service.ingest_from_url(args.url, title=args.title)
            elif args.file:
                with open(args.file, "rb") as f:
                    content = f.read()
                filename = args.name or args.file.rsplit("/", 1)[-1]
                result = await service.ingest_from_file(content, filename, title=args.title)
            else:
                print("Error: specify --url or --file")
                sys.exit(1)

            if result.success:
                print(f"OK  urn={result.entity_urn} chunks={result.chunks_count} title={result.title}")
            else:
                print(f"ERR {result.error}")
                sys.exit(1)
        finally:
            await service.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import documents into the chatbot knowledge base")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="Import document from URL")
    group.add_argument("--file", help="Import document from local file")
    parser.add_argument("--name", help="Explicit filename (for --file mode when original name differs)")
    parser.add_argument("--title", help="Document title (defaults to filename without extension)")
    args = parser.parse_args()

    import asyncio
    asyncio.run(_import_document(args))


if __name__ == "__main__":
    main()
