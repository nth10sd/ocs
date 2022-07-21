"""Test logging.py."""

from __future__ import annotations

import filecmp
from logging import INFO
from pathlib import Path
from shutil import which

from ocs.util.logging import get_logger
from ocs.util.logging import println


def test_get_logger(tmp_path: Path) -> None:
    """Test the get_logger function.

    :param tmp_path: Temp dir to test creation of a log file
    """
    log_name = "test_log"
    log_path = tmp_path / f"{log_name}.txt"
    logger = get_logger(
        log_name,
        fmt="%(name)-8s %(levelname)-8s {%(module)s} [%(funcName)s] %(message)s",
        filename=str(log_path),
        terminator=" different_terminator\n",
    )
    logger.setLevel(INFO)
    logger.error("This is a test error message")
    logger.info("This is a test info message")

    assert filecmp.cmp(
        log_path, Path(__file__).parents[1] / "data" / "log-sample.txt"
    ), "generated and expected output are not identical"


def test_println(tmp_path: Path) -> None:
    """Test the println function.

    :param tmp_path: Temp dir for log file creation
    :raise FileNotFoundError: If the cat utility is not found
    """
    if not (which_cat := which("cat")):
        # Ignored (code coverage), as cat utility is often available
        raise FileNotFoundError("The cat utility is not found")  # pragma: no cover

    log_name = "test_log"
    log_path = tmp_path / f"{log_name}.txt"
    logger = get_logger(
        log_name,
        fmt="%(name)-8s %(levelname)-8s {%(module)s} [%(funcName)s] %(message)s",
        filename=str(log_path),
        terminator=" separate_terminator\n",
    )
    logger.setLevel(INFO)

    println(
        [which_cat, Path(__file__).parents[1] / "data" / "log-sample.txt"],
        Path(__file__).parents[1] / "data",
        logger,
    )

    assert filecmp.cmp(
        log_path, Path(__file__).parents[1] / "data" / "unbuffered-log.txt"
    ), "generated and expected output are not identical"
