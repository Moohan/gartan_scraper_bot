#!/usr/bin/env python3
"""Tests for CLI argument parsing and validation."""

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
        assert cli_args.cache_mode == "cache-preferred"
        assert cli_args.force_scrape is False

    def test_from_args_basic(self):
        """Test creating CliArgs from basic arguments."""
        # Mock argparse Namespace
        class MockArgs:
            max_days = 5
            cache_only = False
            cache_off = False
            force_scrape = False

        args = MockArgs()
        cli_args = CliArgs.from_args(args)

        assert cli_args.max_days == 5
        assert cli_args.cache_mode == "cache-preferred"
        assert cli_args.force_scrape is False

    def test_from_args_cache_only(self):
        """Test CliArgs with cache-only flag."""
        class MockArgs:
            max_days = 3
            cache_only = True
            cache_off = False
            force_scrape = False

        args = MockArgs()
        cli_args = CliArgs.from_args(args)

        assert cli_args.cache_mode == "cache-only"

    def test_from_args_cache_off(self):
        """Test CliArgs with cache-off flag."""
        class MockArgs:
            max_days = 3
            cache_only = False
            cache_off = True
            force_scrape = False

        args = MockArgs()
        cli_args = CliArgs.from_args(args)

        assert cli_args.cache_mode == "cache-off"

    def test_from_args_cache_mode_explicit(self):
        """Test CliArgs with explicit cache_mode."""
        class MockArgs:
            max_days = 3
            cache_mode = "cache-only"
            force_scrape = False

        args = MockArgs()
        cli_args = CliArgs.from_args(args)

        assert cli_args.cache_mode == "cache-only"

    def test_from_args_force_scrape(self):
        """Test CliArgs with force_scrape flag."""
        class MockArgs:
            max_days = 3
            cache_only = False
            cache_off = False
            force_scrape = True

        args = MockArgs()
        cli_args = CliArgs.from_args(args)

        assert cli_args.force_scrape is True

    def test_from_args_missing_attributes(self):
        """Test CliArgs with missing optional attributes."""
        class MockArgs:
            max_days = 7

        args = MockArgs()
        cli_args = CliArgs.from_args(args)

        assert cli_args.max_days == 7
        assert cli_args.cache_mode == "cache-preferred"  # Default
        assert cli_args.force_scrape is False  # Default


class TestArgumentParser:
    """Test argument parser creation and configuration."""

    def test_parser_creation(self):
        """Test that parser is created successfully."""
        parser = create_argument_parser()

        assert isinstance(parser, argparse.ArgumentParser)
        assert parser.description == "Gartan Scraper Bot"

    def test_max_days_argument(self):
        """Test --max-days argument parsing."""
        parser = create_argument_parser()

        # Test default value
        args = parser.parse_args([])
        assert args.max_days == 3

        # Test custom value
        args = parser.parse_args(["--max-days", "7"])
        assert args.max_days == 7

    def test_cache_only_argument(self):
        """Test --cache-only argument."""
        parser = create_argument_parser()

        # Test default (should be False)
        args = parser.parse_args([])
        assert args.cache_only is False

        # Test with flag
        args = parser.parse_args(["--cache-only"])
        assert args.cache_only is True

    def test_cache_off_argument(self):
        """Test --cache-off argument."""
        parser = create_argument_parser()

        # Test default (should be False)
        args = parser.parse_args([])
        assert args.cache_off is False

        # Test with flag
        args = parser.parse_args(["--cache-off"])
        assert args.cache_off is True

    def test_cache_mode_argument(self):
        """Test --cache-mode argument with choices."""
        parser = create_argument_parser()

        # Test default
        args = parser.parse_args([])
        assert args.cache_mode == "cache-preferred"

        # Test valid choices
        for mode in ["cache-only", "cache-preferred", "cache-off"]:
            args = parser.parse_args(["--cache-mode", mode])
            assert args.cache_mode == mode

    def test_cache_mode_invalid_choice(self):
        """Test --cache-mode with invalid choice."""
        parser = create_argument_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["--cache-mode", "invalid-mode"])

    def test_force_scrape_argument(self):
        """Test --force-scrape argument."""
        parser = create_argument_parser()

        # Test default (should be False)
        args = parser.parse_args([])
        assert args.force_scrape is False

        # Test with flag
        args = parser.parse_args(["--force-scrape"])
        assert args.force_scrape is True

    def test_mutually_exclusive_cache_flags(self):
        """Test that cache flags are mutually exclusive."""
        parser = create_argument_parser()

        # These should fail with SystemExit
        with pytest.raises(SystemExit):
            parser.parse_args(["--cache-only", "--cache-off"])

        with pytest.raises(SystemExit):
            parser.parse_args(["--cache-only", "--cache-mode", "cache-off"])

        with pytest.raises(SystemExit):
            parser.parse_args(["--cache-off", "--cache-mode", "cache-preferred"])

    def test_max_days_type_validation(self):
        """Test that --max-days requires integer values."""
        parser = create_argument_parser()

        # Valid integer
        args = parser.parse_args(["--max-days", "10"])
        assert args.max_days == 10

        # Invalid non-integer should raise SystemExit
        with pytest.raises(SystemExit):
            parser.parse_args(["--max-days", "not-a-number"])

        with pytest.raises(SystemExit):
            parser.parse_args(["--max-days", "3.5"])

    def test_max_days_boundary_values(self):
        """Test --max-days with boundary values."""
        parser = create_argument_parser()

        # Test zero
        args = parser.parse_args(["--max-days", "0"])
        assert args.max_days == 0

        # Test negative values (should be accepted by argparse)
        args = parser.parse_args(["--max-days", "-1"])
        assert args.max_days == -1

        # Test large values
        args = parser.parse_args(["--max-days", "365"])
        assert args.max_days == 365

    def test_help_option(self):
        """Test that help option works."""
        parser = create_argument_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--help"])

        # Help should exit with code 0
        assert exc_info.value.code == 0

    def test_unknown_arguments(self):
        """Test handling of unknown arguments."""
        parser = create_argument_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["--unknown-flag"])

        with pytest.raises(SystemExit):
            parser.parse_args(["--max-days", "3", "--invalid"])


class TestParseArgs:
    """Test the main parse_args function."""

    def test_parse_args_no_arguments(self):
        """Test parse_args with no command line arguments."""
        with patch.object(sys, "argv", ["run_bot.py"]):
            cli_args = parse_args()

            assert isinstance(cli_args, CliArgs)
            assert cli_args.max_days == 3
            assert cli_args.cache_mode == "cache-preferred"
            assert cli_args.force_scrape is False

    def test_parse_args_with_arguments(self):
        """Test parse_args with command line arguments."""
        with patch.object(sys, "argv", ["run_bot.py", "--max-days", "5", "--cache-only"]):
            cli_args = parse_args()

            assert cli_args.max_days == 5
            assert cli_args.cache_mode == "cache-only"

    def test_parse_args_force_scrape(self):
        """Test parse_args with force scrape flag."""
        with patch.object(sys, "argv", ["run_bot.py", "--force-scrape"]):
            cli_args = parse_args()

            assert cli_args.force_scrape is True

    def test_parse_args_cache_modes(self):
        """Test all cache mode variations through parse_args."""
        # Test cache-only flag
        with patch.object(sys, "argv", ["run_bot.py", "--cache-only"]):
            cli_args = parse_args()
            assert cli_args.cache_mode == "cache-only"

        # Test cache-off flag
        with patch.object(sys, "argv", ["run_bot.py", "--cache-off"]):
            cli_args = parse_args()
            assert cli_args.cache_mode == "cache-off"

        # Test explicit cache-mode
        with patch.object(sys, "argv", ["run_bot.py", "--cache-mode", "cache-preferred"]):
            cli_args = parse_args()
            assert cli_args.cache_mode == "cache-preferred"

    def test_parse_args_complex_combination(self):
        """Test parse_args with complex argument combinations."""
        with patch.object(sys, "argv", ["run_bot.py", "--max-days", "10", "--force-scrape", "--cache-mode", "cache-off"]):
            cli_args = parse_args()

            assert cli_args.max_days == 10
            assert cli_args.force_scrape is True
            assert cli_args.cache_mode == "cache-off"

    def test_parse_args_invalid_arguments(self):
        """Test parse_args with invalid arguments."""
        with patch.object(sys, "argv", ["run_bot.py", "--max-days", "invalid"]):
            with pytest.raises(SystemExit):
                parse_args()

    def test_parse_args_help_exit(self):
        """Test that parse_args exits appropriately for help."""
        with patch.object(sys, "argv", ["run_bot.py", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                parse_args()

            assert exc_info.value.code == 0


class TestCliIntegration:
    """Test CLI components working together."""

    def test_full_cli_pipeline(self):
        """Test complete CLI argument processing pipeline."""
        # Mock command line arguments
        test_args = ["run_bot.py", "--max-days", "7", "--cache-only", "--force-scrape"]

        with patch.object(sys, "argv", test_args):
            cli_args = parse_args()

            # Verify all arguments were processed correctly
            assert cli_args.max_days == 7
            assert cli_args.cache_mode == "cache-only"
            assert cli_args.force_scrape is True

    def test_argument_precedence(self):
        """Test argument precedence when multiple cache options could apply."""
        # When using explicit --cache-mode, it should override flag-based settings
        parser = create_argument_parser()

        # Test that explicit cache-mode works
        args = parser.parse_args(["--cache-mode", "cache-preferred"])
        cli_args = CliArgs.from_args(args)
        assert cli_args.cache_mode == "cache-preferred"

    def test_edge_case_combinations(self):
        """Test edge cases in argument combinations."""
        # Zero max-days with force scrape
        with patch.object(sys, "argv", ["run_bot.py", "--max-days", "0", "--force-scrape"]):
            cli_args = parse_args()
            assert cli_args.max_days == 0
            assert cli_args.force_scrape is True

    def test_cli_args_immutability_concept(self):
        """Test that CliArgs behaves predictably after creation."""
        cli_args = CliArgs()
        original_max_days = cli_args.max_days

        # Modify and ensure it's actually changed
        cli_args.max_days = 10
        assert cli_args.max_days == 10
        assert cli_args.max_days != original_max_days

    def test_argument_help_text_content(self):
        """Test that help text contains expected information."""
        parser = create_argument_parser()
        help_text = parser.format_help()

        # Check for key argument descriptions
        assert "--max-days" in help_text
        assert "--cache-only" in help_text
        assert "--cache-off" in help_text
        assert "--cache-mode" in help_text
        assert "--force-scrape" in help_text
        assert "Gartan Scraper Bot" in help_text


if __name__ == "__main__":
    pytest.main([__file__])
