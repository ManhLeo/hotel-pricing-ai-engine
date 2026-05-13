"""
Main Entry Point - Phase 2 LLM Engine

Usage:
    python main.py --input <csv_path> [--output <json_path>]

Example:
    python main.py --input ../room_recommendation_actions_updated.csv
    python main.py --input data/input/sample.csv --output data/output/advice.json
"""

import argparse
import logging
import sys
from pathlib import Path

from config.settings import DATA_OUTPUT_DIR, LOG_DATE_FORMAT, LOG_FORMAT, LOG_LEVEL
from src.advice_generator import AdviceGenerator

# ============================================================
# Logging setup
# ============================================================
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("engine.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Phase 2 LLM Engine - Generate Expert Advice"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to CSV file from Phase 1",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save JSON output (default: data/output/advice_<timestamp>.json)",
    )
    parser.add_argument(
        "--actions",
        type=str,
        default=None,
        help="Path to Actions CSV file (optional, used for recommendation_label)",
    )
    parser.add_argument(
        "--scores",
        type=str,
        default=None,
        help="Path to Risk Scores CSV file (optional, used for fee_structure)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build contexts only, do NOT call LLM API",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point."""
    args = parse_args()
    logger.info("=" * 60)
    logger.info("Phase 2 LLM Engine - Starting")
    logger.info("=" * 60)
    logger.info("Input: %s", args.input)

    # Validate input
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        sys.exit(1)

    # Output path
    if args.output:
        output_path = args.output
    else:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(DATA_OUTPUT_DIR / f"advice_{timestamp}.json")

    logger.info("Output: %s", output_path)

    if args.dry_run:
        logger.info("DRY RUN MODE - No API calls will be made")
        from src.context_builder import ContextBuilder
        contexts = ContextBuilder.build_from_csv(str(input_path), args.actions, args.scores)
        for ctx in contexts[:10]:
            print("\n" + ctx.to_prompt_text())
        logger.info("Dry run complete. %d contexts built.", len(contexts))
        return

    # Run
    generator = AdviceGenerator()
    results = generator.generate_batch(
        csv_path=str(input_path),
        actions_path=args.actions,
        scores_path=args.scores,
        output_path=output_path,
    )

    # Final report
    success = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - success
    logger.info("=" * 60)
    logger.info("FINAL REPORT")
    logger.info("  Total:   %d", len(results))
    logger.info("  Success: %d", success)
    logger.info("  Failed:  %d", failed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
