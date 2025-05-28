"""Module details."""

import contextlib
from pathlib import Path

with contextlib.suppress(ModuleNotFoundError):  # Bypass package install issues on CI
    from beartype import BeartypeConf
    from beartype.claw import beartype_this_package

__title__ = "ocs"
__version__ = (Path(__file__).parent / "_version.txt").read_text(encoding="utf-8")

with contextlib.suppress(NameError):
    beartype_this_package(  # pyright: ignore[reportPossiblyUnboundVariable]
        conf=BeartypeConf(  # pyright: ignore[reportPossiblyUnboundVariable]
            violation_type=UserWarning
        )
    )
