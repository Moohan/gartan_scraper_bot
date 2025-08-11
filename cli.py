"""Minimal CLI interface for run_bot.py."""

import argparse
from typing import Optional


class CliArgs:
    """Simple CLI arguments container."""
    def __init__(self):
        self.max_days: int = 3
        self.cache_mode: str = "cache-preferred"
        self.force_scrape: bool = False

    @classmethod
    def from_args(cls, args):
        """Create CliArgs from parsed arguments."""
        cli_args = cls()
        cli_args.max_days = args.max_days

        # Set cache mode based on flags
        if hasattr(args, 'cache_only') and args.cache_only:
            cli_args.cache_mode = "cache-only"
        elif hasattr(args, 'cache_off') and args.cache_off:
            cli_args.cache_mode = "cache-off"
        elif hasattr(args, 'cache_mode'):
            cli_args.cache_mode = args.cache_mode
        else:
            cli_args.cache_mode = "cache-preferred"

        cli_args.force_scrape = getattr(args, 'force_scrape', False)
        return cli_args


def create_argument_parser() -> argparse.ArgumentParser:
    """Create argument parser for the scraper bot."""
    parser = argparse.ArgumentParser(description="Gartan Scraper Bot")

    parser.add_argument(
        "--max-days",
        type=int,
        default=3,
        help="Days to fetch forward from today (default: 3). "
             "Note: Always starts from Monday of current week for weekly availability tracking."
    )

    # Cache mode options
    cache_group = parser.add_mutually_exclusive_group()
    cache_group.add_argument(
        "--cache-only",
        action="store_true",
        help="Use cache only, don't fetch new data"
    )
    cache_group.add_argument(
        "--cache-off",
        action="store_true",
        help="Don't use cache, always fetch fresh data"
    )
    cache_group.add_argument(
        "--cache-mode",
        choices=["cache-only", "cache-preferred", "cache-off"],
        default="cache-preferred",
        help="Cache behavior mode"
    )

    parser.add_argument(
        "--force-scrape",
        action="store_true",
        help="Force scrape even if cache is fresh"
    )

    return parser


def parse_args() -> CliArgs:
    """Parse command line arguments into CliArgs object."""
    parser = create_argument_parser()
    args = parser.parse_args()
    return CliArgs.from_args(args)
