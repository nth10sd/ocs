"""Module details."""

from pathlib import Path

# \with contextlib.suppress(ModuleNotFoundError):  # Bypass package install issues on CI
# \    from beartype import BeartypeConf
# \    from beartype.claw import beartype_this_package

__title__ = "ocs"
__version__ = (Path(__file__).parent / "_version.txt").read_text(encoding="utf-8")

# If reactivation of beartype is desired, disable ruff TC001, TC002 and TC003 errors
# "TC001",   # TYPE_CHECKING seems incompatible with beartype
# Beartype does not support dataclasses well yet, see:
# https://github.com/beartype/beartype/issues/119
# \with contextlib.suppress(NameError):
# \    beartype_this_package(
# \        conf=BeartypeConf(
# \            violation_type=UserWarning
# \        )
# \    )
