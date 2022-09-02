"""Logging code."""

from __future__ import annotations

import logging
from pathlib import Path
import subprocess
import sys


def get_logger(
    name: str,
    fmt: str = (
        "%(asctime)s %(name)-8s %(levelname)-8s {%(module)s} [%(funcName)s] %(message)s"
    ),
    filename: str = "",
    terminator: str = "\n",
) -> logging.Logger:
    """Create a logger, allowing setting filenames, output formats and line terminators.

    :param name: Name of logger
    :param fmt: Format of output message
    :param filename: Name of file to output the logs
    :param terminator: Line terminator (Use an empty string "" to log w/o line endings)
    :return: Desired logger object
    """
    logger = logging.getLogger(name)
    # If we use StreamHandler() without specifying sys.stdout, it defaults to sys.stderr
    # By using sys.stdout, stdout on console output should have both stdout & stderr
    c_handle = logging.StreamHandler(sys.stdout)
    c_handle.terminator = terminator
    c_handle.setFormatter(logging.Formatter(fmt=fmt, datefmt="%b %d %H:%M:%S"))
    logger.addHandler(c_handle)

    if filename:
        file_handler = logging.FileHandler(filename)
        file_handler.terminator = terminator
        file_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt="%b %d %H:%M:%S"))
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def println(cmd: list[Path | str], cwd: Path, logger: logging.Logger) -> None:
    """Print each line in the logger without any buffering.

    :param cmd: Command to be run
    :param cwd: Current working directory of command
    :param logger: Name of logger to be used
    :raise RuntimeError: If process stdout is empty
    """
    with subprocess.Popen(
        cmd,
        bufsize=0,
        cwd=cwd,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
        text=True,
    ) as ps_:
        if not (ps_stdout := ps_.stdout):
            # Ignored (code coverage), as mypy is unable to examine ps_.stdout
            raise RuntimeError("Process stdout is empty")  # pragma: no cover
        while line := ps_stdout.readline():  # pylint: disable=while-used
            logger.info(line.rstrip())
