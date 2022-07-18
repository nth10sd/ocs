"""Test parsing.py."""

from __future__ import annotations

import pytest

from ocs.spidermonkey.parsing import parse_args


def test_parser() -> None:
    """Test the parser."""
    parser = parse_args(
        [
            '-b="--enable-debug --enable-simulator=arm64"',
            "-r",
            "a5301180315c5a152c4173e6fc741e02f271d4ed",
        ]
    )
    assert parser.build_opts == "--enable-debug --enable-simulator=arm64"
    assert parser.revision == "a5301180315c5a152c4173e6fc741e02f271d4ed"

    parser2 = parse_args(['--build-opts="--enable-address-sanitizer"'])
    assert parser2.build_opts == "--enable-address-sanitizer"
    assert not parser2.revision

    parser3 = parse_args([])
    assert not parser3.build_opts
    assert not parser3.revision


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
