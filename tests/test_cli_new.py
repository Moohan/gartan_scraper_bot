#!/usr/bin/env python3
"""Tests for CLI argument parsing and validation - Updated for new CLI interface."""

import argparse
import sys
from unittest.mock import patch

import pytest

from cli import CliArgs, create_argument_parser, parse_args


class TestCliArgs:
    """Test CliArgs dataclass functionality."""

    def test_default_values(self):
        """Test default CliArgs values."""
        cli_args = CliArgs()

        assert cli_args.max_days == 3
        assert cli_args.cache_mode is None  # Default is intelligent caching
        assert cli_args.fresh_start is False

    def test_from_args_basic(self):
        """Test creating CliArgs from basic arguments."""

        # Mock argparse Namespace
        class MockArgs:
            max_days = 5
            cache_only = False
            no_cache = False
            cache_first = False
            cache_mode = None
            fresh_start = False

        args = MockArgs()
        cli_args = CliArgs.from_args(args)

        assert cli_args.max_days == 5
        assert cli_args.cache_mode is None  # Default intelligent caching
        assert cli_args.fresh_start is False

    def test_from_args_cache_only(self):
        """Test CliArgs with cache-only flag."""

        class MockArgs:
            max_days = 3
            cache_only = True
            no_cache = False
            cache_first = False
            cache_mode = None
            fresh_start = False

        args = MockArgs()
        cli_args = CliArgs.from_args(args)

        assert cli_args.max_days == 3
        assert cli_args.cache_mode == "cache-only"
        assert cli_args.fresh_start is False

    def test_from_args_no_cache(self):
        """Test CliArgs with no-cache flag."""

        class MockArgs:
            max_days = 7
            cache_only = False
            no_cache = True
            cache_first = False
            cache_mode = None
            fresh_start = False

        args = MockArgs()
        cli_args = CliArgs.from_args(args)

        assert cli_args.max_days == 7
        assert cli_args.cache_mode == "no-cache"
        assert cli_args.fresh_start is False

    def test_from_args_cache_first(self):
        """Test CliArgs with cache-first flag."""

        class MockArgs:
            max_days = 2
            cache_only = False
            no_cache = False
            cache_first = True
            cache_mode = None
            fresh_start = False

        args = MockArgs()
        cli_args = CliArgs.from_args(args)

        assert cli_args.max_days == 2
        assert cli_args.cache_mode == "cache-first"
        assert cli_args.fresh_start is False

    def test_from_args_fresh_start(self):
        """Test CliArgs with fresh-start flag."""

        class MockArgs:
            max_days = 3
            cache_only = False
            no_cache = False
            cache_first = False
            cache_mode = None
            fresh_start = True

        args = MockArgs()
        cli_args = CliArgs.from_args(args)

        assert cli_args.max_days == 3
        assert cli_args.cache_mode is None
        assert cli_args.fresh_start is True

    def test_from_args_explicit_cache_mode(self):
        """Test CliArgs with explicit cache mode."""

        class MockArgs:
            max_days = 4
            cache_only = False
            no_cache = False
            cache_first = False
            cache_mode = "cache-only"
            fresh_start = False

        args = MockArgs()
        cli_args = CliArgs.from_args(args)

        assert cli_args.max_days == 4
        assert cli_args.cache_mode == "cache-only"
        assert cli_args.fresh_start is False

    def test_from_args_missing_attributes(self):
        """Test CliArgs with missing optional attributes."""

        class MockArgs:
            max_days = 7

        args = MockArgs()
        cli_args = CliArgs.from_args(args)

        assert cli_args.max_days == 7
        assert cli_args.cache_mode is None  # Default
        assert cli_args.fresh_start is False  # Default


class TestArgumentParser:
    """Test argument parser creation and configuration."""

    def test_parser_creation(self):
        """Test that parser is created successfully."""
        parser = create_argument_parser()

        assert isinstance(parser, argparse.ArgumentParser)
        assert parser.description == "Gartan Scraper Bot"

    def test_max_days_argument(self):
        """Test max-days argument parsing."""
        parser = create_argument_parser()
        args = parser.parse_args(["--max-days", "5"])

        assert args.max_days == 5

    def test_cache_only_argument(self):
        """Test cache-only argument parsing."""
        parser = create_argument_parser()
        args = parser.parse_args(["--cache-only"])

        assert args.cache_only is True
        assert args.no_cache is False
        assert args.cache_first is False

    def test_no_cache_argument(self):
        """Test no-cache argument parsing."""
        parser = create_argument_parser()
        args = parser.parse_args(["--no-cache"])

        assert args.no_cache is True
        assert args.cache_only is False
        assert args.cache_first is False

    def test_cache_first_argument(self):
        """Test cache-first argument parsing."""
        parser = create_argument_parser()
        args = parser.parse_args(["--cache-first"])

        assert args.cache_first is True
        assert args.cache_only is False
        assert args.no_cache is False

    def test_cache_mode_argument(self):
        """Test cache-mode argument parsing."""
        parser = create_argument_parser()
        args = parser.parse_args(["--cache-mode", "cache-only"])

        assert args.cache_mode == "cache-only"

    def test_fresh_start_argument(self):
        """Test fresh-start argument parsing."""
        parser = create_argument_parser()
        args = parser.parse_args(["--fresh-start"])

        assert args.fresh_start is True

    def test_default_arguments(self):
        """Test default argument values."""
        parser = create_argument_parser()
        args = parser.parse_args([])

        assert args.max_days == 3
        assert args.cache_only is False
        assert args.no_cache is False
        assert args.cache_first is False
        assert args.cache_mode is None
        assert args.fresh_start is False

    def test_mutually_exclusive_cache_arguments(self):
        """Test that cache arguments are mutually exclusive."""
        parser = create_argument_parser()

        # Should raise SystemExit due to mutually exclusive arguments
        with pytest.raises(SystemExit):
            parser.parse_args(["--cache-only", "--no-cache"])


class TestParseArgs:
    """Test the high-level parse_args function."""

    def test_parse_args_no_arguments(self):
        """Test parse_args with no arguments."""
        with patch.object(sys, "argv", ["run_bot.py"]):
            cli_args = parse_args()

            assert cli_args.max_days == 3
            assert cli_args.cache_mode is None
            assert cli_args.fresh_start is False

    def test_parse_args_max_days(self):
        """Test parse_args with max-days argument."""
        with patch.object(sys, "argv", ["run_bot.py", "--max-days", "7"]):
            cli_args = parse_args()

            assert cli_args.max_days == 7

    def test_parse_args_fresh_start(self):
        """Test parse_args with fresh-start argument."""
        with patch.object(sys, "argv", ["run_bot.py", "--fresh-start"]):
            cli_args = parse_args()

            assert cli_args.fresh_start is True

    def test_parse_args_cache_modes(self):
        """Test parse_args with various cache modes."""
        test_cases = [
            (["run_bot.py", "--cache-only"], "cache-only"),
            (["run_bot.py", "--no-cache"], "no-cache"),
            (["run_bot.py", "--cache-first"], "cache-first"),
            (["run_bot.py", "--cache-mode", "cache-only"], "cache-only"),
        ]

        for argv, expected_mode in test_cases:
            with patch.object(sys, "argv", argv):
                cli_args = parse_args()
                assert cli_args.cache_mode == expected_mode

    def test_parse_args_complex_combination(self):
        """Test parse_args with multiple arguments."""
        with patch.object(sys, "argv", ["run_bot.py", "--max-days", "5", "--fresh-start"]):
            cli_args = parse_args()

            assert cli_args.max_days == 5
            assert cli_args.fresh_start is True
            assert cli_args.cache_mode is None


class TestCliIntegration:
    """Integration tests for complete CLI functionality."""

    def test_full_cli_pipeline(self):
        """Test complete CLI argument processing pipeline."""
        test_argv = ["run_bot.py", "--max-days", "10", "--no-cache", "--fresh-start"]

        with patch.object(sys, "argv", test_argv):
            cli_args = parse_args()

            assert cli_args.max_days == 10
            assert cli_args.cache_mode == "no-cache"
            assert cli_args.fresh_start is True

    def test_argument_precedence(self):
        """Test argument precedence and mutual exclusion."""
        parser = create_argument_parser()

        # Test that explicit cache-mode takes precedence
        args = parser.parse_args(["--cache-mode", "cache-first"])
        cli_args = CliArgs.from_args(args)
        assert cli_args.cache_mode == "cache-first"

    def test_edge_case_combinations(self):
        """Test edge cases and unusual argument combinations."""
        test_cases = [
            # Maximum days with fresh start
            (["run_bot.py", "--max-days", "1", "--fresh-start"], 1, True, None),
            # Cache first with fresh start (fresh start should override cache mode)
            (["run_bot.py", "--cache-first", "--fresh-start"], 3, True, "cache-first"),
        ]

        for argv, expected_days, expected_fresh, expected_cache in test_cases:
            with patch.object(sys, "argv", argv):
                cli_args = parse_args()
                assert cli_args.max_days == expected_days
                assert cli_args.fresh_start == expected_fresh
                assert cli_args.cache_mode == expected_cache

    def test_argument_help_text_content(self):
        """Test that help text contains expected content."""
        parser = create_argument_parser()
        help_text = parser.format_help()

        # Check for key arguments
        assert "--max-days" in help_text
        assert "--cache-only" in help_text
        assert "--no-cache" in help_text
        assert "--cache-first" in help_text
        assert "--cache-mode" in help_text
        assert "--fresh-start" in help_text

        # Check for descriptions
        assert "Clear database and start fresh" in help_text
        assert "Don't use cache" in help_text
        assert "Use cache only" in help_text


if __name__ == "__main__":
    pytest.main([__file__])
