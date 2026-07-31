#!/usr/bin/env python3
"""CLI runner for RAG quality evaluation."""
import argparse
import json

import structlog

log = structlog.get_logger()


async def _run_evaluation(args: argparse.Namespace) -> None:
    from app.dependencies import get_db_session
    from app.services.chat_service import ChatService
    from evaluation.evaluator import Evaluator
    from evaluation.golden_dataset import load_golden_dataset

    dataset = load_golden_dataset(args.dataset if args.dataset else None)
    log.info("evaluation_started", dataset=dataset.name, samples=len(dataset.samples))

    async for session in get_db_session():
        chat_service = ChatService(session)
        evaluator = Evaluator(chat_service)
        report = await evaluator.evaluate(dataset)
        break

    report.print_summary()

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        log.info("evaluation_report_saved", path=args.output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RAG quality evaluation")
    parser.add_argument("--dataset", help="Path to golden dataset JSON file (optional, uses built-in)")
    parser.add_argument("--output", "-o", help="Path to save evaluation report JSON")
    args = parser.parse_args()

    import asyncio
    asyncio.run(_run_evaluation(args))


if __name__ == "__main__":
    main()
