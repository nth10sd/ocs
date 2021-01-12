# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Logging code."""

from __future__ import annotations

import logging


def get_logger(name: str, fmt: str = "%(asctime)s %(name)-8s %(levelname)-8s {%(module)s} [%(funcName)s] %(message)s",
               terminator: str = "\n") -> logging.Logger:
    """Create a logger allow setting output formats and line terminators.

    :param name: Name of logger
    :param fmt: Format of output message
    :param terminator: Line terminator (Set to empty string "" for logging without line endings)
    :return: Desired logger object
    """
    handler = logging.StreamHandler()
    handler.terminator = terminator
    handler.setFormatter(logging.Formatter(fmt=fmt, datefmt="%b %d %H:%M:%S"))

    logger = logging.getLogger(name)
    logger.addHandler(handler)
    return logger
