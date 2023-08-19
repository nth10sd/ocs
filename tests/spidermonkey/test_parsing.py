"""Test parsing.py."""

# ruff: noqa: S101

from __future__ import annotations

import pytest

from ocs.spidermonkey.parsing import parse_args


def test_parser() -> None:
    """Test the parser."""
    args = parse_args(
        [
            '-b="--enable-debug --enable-simulator=arm64"',
            "-r",
            "a5301180315c5a152c4173e6fc741e02f271d4ed",
        ]
    )
    assert args.build_opts == "--enable-debug --enable-simulator=arm64"
    assert args.revision == "a5301180315c5a152c4173e6fc741e02f271d4ed"

    args2 = parse_args(['--build-opts="--enable-address-sanitizer"'])
    assert args2.build_opts == "--enable-address-sanitizer"
    assert not args2.revision

    args3 = parse_args([])
    assert not args3.build_opts
    assert not args3.revision


def test_parser_no_equals() -> None:
    """Test the parser with no equals sign for -b or --build-opts."""
    with pytest.raises(SystemExit):
        parse_args(
            [
                "-b",
                "--enable-debug --enable-simulator=arm64",
                "-r",
                "a5301180315c5a152c4173e6fc741e02f271d4ed",
            ]
        )
