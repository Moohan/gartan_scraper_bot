"""CLI argument validation for Gartan Scraper Bot."""

from typing import Optional
from dataclasses import dataclass
import argparse
from logging_config import get_logger

logger = get_logger()


@dataclass
class CliArgs:
    """Validated command line arguments."""

    max_days: int
    cache_mode: Optional[str] = None

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "CliArgs":
        """Create validated CliArgs from parsed arguments."""
        # Validate max_days
        if args.max_days < 1:
            raise ValueError("max_days must be at least 1")
        if args.max_days > 365:
            logger.warning("Fetching more than 365 days of data may be slow")

        # Determine cache mode
        cache_mode = None
        if args.no_cache:
            cache_mode = "no-cache"
        elif args.cache_first:
            cache_mode = "cache-first"
        elif args.cache_only:
            cache_mode = "cache-only"

        # Validate cache mode combinations
        cache_flags = [args.no_cache, args.cache_first, args.cache_only]
        if sum(cache_flags) > 1:
            raise ValueError("Only one cache mode flag can be specified")

        return cls(max_days=args.max_days, cache_mode=cache_mode)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create the argument parser with validation."""
    parser = argparse.ArgumentParser(
        description="Gartan Scraper Bot",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--no-cache", action="store_true", help="Always download, ignore cache"
    )
    parser.add_argument(
        "--cache-first", action="store_true", help="Use cache if exists, even if stale"
    )
    parser.add_argument(
        "--cache-only", action="store_true", help="Only use cache, never download"
    )
    parser.add_argument(
        "--max-days", type=int, default=28, help="Number of days to fetch (1-365)"
    )

    return parser
