# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Helper functions involving Mercurial (hg)."""

from __future__ import annotations

import configparser
import os
from pathlib import Path
import subprocess
import sys
from typing import Tuple


def get_repo_hash_and_id(
    repo_dir: Path,
    repo_rev: str = "parents() and default",
) -> Tuple[str, str, bool]:
    """Return the repository hash and id, and whether it is on default. It will also ask
    what the user would like to do, should the repository not be on default.

    :param repo_dir: Full path to the repository
    :param repo_rev: Intended Mercurial changeset details to retrieve
    :raise ValueError: Raises if the input is invalid
    :return: Changeset hash, local numerical ID, whether repository is on default tip
    """
    # This will return null if the repository is not on default.
    hg_log_template_cmds = [
        "hg",
        "-R",
        str(repo_dir),
        "log",
        "-r",
        repo_rev,
        "--template",
        "{node|short} {rev}",
    ]
    hg_id_full = subprocess.run(
        hg_log_template_cmds,
        cwd=os.getcwd(),
        check=True,
        stdout=subprocess.PIPE,
        timeout=99,
    ).stdout.decode("utf-8", errors="replace")
    is_on_default = bool(hg_id_full)
    if not is_on_default:
        # pylint: disable=input-builtin
        update_default = input(
            "Not on default tip! "
            "Would you like to (a)bort, update to (d)efault, or (u)se this rev: ",
        )
        update_default = update_default.strip()
        if update_default == "a":
            print("Aborting...")  # noqa: T001
            sys.exit(0)
        elif update_default == "d":
            subprocess.run(["hg", "-R", str(repo_dir), "update", "default"], check=True)
            is_on_default = True
        elif update_default == "u":
            hg_log_template_cmds = [
                "hg",
                "-R",
                str(repo_dir),
                "log",
                "-r",
                "parents()",
                "--template",
                "{node|short} {rev}",
            ]
        else:
            raise ValueError("Invalid choice.")
        hg_id_full = subprocess.run(
            hg_log_template_cmds,
            cwd=os.getcwd(),
            check=True,
            stdout=subprocess.PIPE,
            timeout=99,
        ).stdout.decode("utf-8", errors="replace")
    assert hg_id_full != ""
    (hg_id_hash, hg_id_local_num) = hg_id_full.split(" ")
    # The following line interferes with __init__.py import system, needs to be
    # converted to logging:
    # utils.vdump("Finished getting the hash and local id number of the repository.")
    return hg_id_hash, hg_id_local_num, is_on_default


def hgrc_repo_name(repo_dir: Path) -> str:
    """Extract the Mercurial repo name from the hgrc file.

    :param repo_dir: Repo directory
    :return: Name of the repo in the .hgrc file
    """
    hgrc_cfg = configparser.ConfigParser()
    hgrc_cfg.read(repo_dir / ".hg" / "hgrc")
    # Not all default entries in [paths] end with "/".
    return [i for i in hgrc_cfg.get("paths", "default").split("/") if i][-1]
