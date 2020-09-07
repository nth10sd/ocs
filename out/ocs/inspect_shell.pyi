from ocs.util import utils as utils
from pathlib import Path
from typing import Any, Tuple

ASAN_ERROR_EXIT_CODE: int
RUN_MOZGLUE_LIB: str
RUN_NSPR_LIB: str
RUN_PLDS_LIB: str
RUN_PLC_LIB: str
RUN_TESTPLUG_LIB: str
ALL_RUN_LIBS: Any
WIN_ICU_VERS: Any
RUN_ICUUC_LIB_EXCL_EXT: str
RUN_ICUIN_LIB_EXCL_EXT: str
RUN_ICUIO_LIB_EXCL_EXT: str
RUN_ICUDT_LIB_EXCL_EXT: str
RUN_ICUTEST_LIB_EXCL_EXT: str
RUN_ICUTU_LIB_EXCL_EXT: str

def arch_of_binary(binary: Path) -> str: ...
def test_binary(shell_path: Path, args: Any, _use_vg: Any, stderr: Any=...) -> Tuple[str, int]: ...
def query_build_cfg(shell_path: Path, parameter: str) -> Any: ...
def verify_binary(shell: Any) -> None: ...
