"""Tests for CLI argument handling."""

import pytest
from cli import create_argument_parser, CliArgs


def test_valid_max_days():
    """Test valid max_days values."""
    parser = create_argument_parser()
    args = parser.parse_args(["--max-days", "14"])
    cli_args = CliArgs.from_args(args)
    assert cli_args.max_days == 14
    assert cli_args.cache_mode is None


def test_invalid_max_days():
    """Test invalid max_days values."""
    parser = create_argument_parser()
    args = parser.parse_args(["--max-days", "0"])
    with pytest.raises(ValueError, match="max_days must be at least 1"):
        CliArgs.from_args(args)


def test_cache_modes():
    """Test various cache mode combinations."""
    parser = create_argument_parser()

    # Test no-cache
    args = parser.parse_args(["--no-cache"])
    cli_args = CliArgs.from_args(args)
    assert cli_args.cache_mode == "no-cache"

    # Test cache-first
    args = parser.parse_args(["--cache-first"])
    cli_args = CliArgs.from_args(args)
    assert cli_args.cache_mode == "cache-first"

    # Test cache-only
    args = parser.parse_args(["--cache-only"])
    cli_args = CliArgs.from_args(args)
    assert cli_args.cache_mode == "cache-only"


def test_multiple_cache_modes():
    """Test that multiple cache modes raise an error."""
    parser = create_argument_parser()
    args = parser.parse_args(["--no-cache", "--cache-first"])
    with pytest.raises(ValueError, match="Only one cache mode flag can be specified"):
        CliArgs.from_args(args)


def test_default_values():
    """Test default argument values."""
    parser = create_argument_parser()
    args = parser.parse_args([])
    cli_args = CliArgs.from_args(args)
    assert cli_args.max_days == 28  # Default value
    assert cli_args.cache_mode is None
