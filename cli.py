"""Minimal CLI interface for run_bot.py."""

import argparse
from typing import Optional


class CliArgs:
    """Simple CLI arguments container."""

    def __init__(self):
        self.max_days: int = 3
        self.cache_mode: Optional[str] = None  # None = auto-detect, or explicit mode
        self.fresh_start: bool = False

    @classmethod
    def from_args(cls, args):
        """Create CliArgs from parsed arguments."""
        cli_args = cls()
        cli_args.max_days = args.max_days
        cli_args.fresh_start = getattr(args, "fresh_start", False)

        # Set cache mode based on flags
        if hasattr(args, "cache_only") and args.cache_only:
            cli_args.cache_mode = "cache-only"
        elif hasattr(args, "no_cache") and args.no_cache:
            cli_args.cache_mode = "no-cache"
        elif hasattr(args, "cache_first") and args.cache_first:
            cli_args.cache_mode = "cache-first"
        elif hasattr(args, "cache_mode") and args.cache_mode:
            cli_args.cache_mode = args.cache_mode
        else:
            # Default: intelligent caching based on data age (None = auto-detect)
            cli_args.cache_mode = None

        return cli_args


def create_argument_parser() -> argparse.ArgumentParser:
    """Create argument parser for the scraper bot."""
    parser = argparse.ArgumentParser(description="Gartan Scraper Bot")

    parser.add_argument(
        "--max-days",
        type=int,
        default=3,
        help="Days to fetch forward from today (default: 3). "
        "Note: Always starts from Monday of current week for weekly availability tracking.",
    )

    # Cache mode options
    cache_group = parser.add_mutually_exclusive_group()
    cache_group.add_argument(
        "--cache-only", action="store_true", help="Use cache only, don't fetch new data"
    )
    cache_group.add_argument(
        "--no-cache",
        action="store_true",
        help="Don't use cache, always fetch fresh data",
    )
    cache_group.add_argument(
        "--cache-first",
        action="store_true",
        help="Use cache if available, even if stale",
    )
    cache_group.add_argument(
        "--cache-mode",
        choices=["cache-only", "cache-first", "no-cache"],
        help="Cache behavior mode (default: intelligent caching based on data age)",
    )

    # Database options
    parser.add_argument(
        "--fresh-start",
        action="store_true",
        help="Clear database and start fresh (forces complete rescrape)",
    )

    return parser


def parse_args() -> CliArgs:
    """Parse command line arguments into CliArgs object."""
    parser = create_argument_parser()
    args = parser.parse_args()
    return CliArgs.from_args(args)
