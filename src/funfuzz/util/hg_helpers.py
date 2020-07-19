# coding=utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Helper functions involving Mercurial (hg).
"""

import configparser
import os
import subprocess
import sys

from . import utils


def get_repo_hash_and_id(repo_dir, repo_rev="parents() and default"):
    """Return the repository hash and id, and whether it is on default.

    It will also ask what the user would like to do, should the repository not be on default.

    Args:
        repo_dir (Path): Full path to the repository
        repo_rev (str): Intended Mercurial changeset details to retrieve

    Raises:
        ValueError: Raises if the input is invalid

    Returns:
        tuple: Changeset hash, local numerical ID, boolean on whether the repository is on default tip
    """
    # This returns null if the repository is not on default.
    hg_log_template_cmds = ["hg", "-R", str(repo_dir), "log", "-r", repo_rev,
                            "--template", "{node|short} {rev}"]
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
        update_default = input("Not on default tip! "
                               "Would you like to (a)bort, update to (d)efault, or (u)se this rev: ")
        update_default = update_default.strip()
        if update_default == "a":
            print("Aborting...")
            sys.exit(0)
        elif update_default == "d":
            subprocess.run(["hg", "-R", str(repo_dir), "update", "default"], check=True)
            is_on_default = True
        elif update_default == "u":
            hg_log_template_cmds = ["hg", "-R", str(repo_dir), "log", "-r", "parents()", "--template",
                                    "{node|short} {rev}"]
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
    utils.vdump("Finished getting the hash and local id number of the repository.")
    return hg_id_hash, hg_id_local_num, is_on_default


def hgrc_repo_name(repo_dir):
    """Look in the hgrc file in the .hg directory of the Mercurial repository and return the name.

    Args:
        repo_dir (Path): Mercurial repository directory

    Returns:
        str: Returns the name of the Mercurial repository as indicated in the .hgrc
    """
    hgrc_cfg = configparser.ConfigParser()
    hgrc_cfg.read(str(repo_dir / ".hg" / "hgrc"))
    # Not all default entries in [paths] end with "/".
    return [i for i in hgrc_cfg.get("paths", "default").split("/") if i][-1]
