"""setuptools install script"""

from pathlib import Path

from setuptools import find_packages
from setuptools import setup

MODULE_NAME = "ocs"

INIT_FILE = "__init__.py"
VERSION_INDICATOR = "__version__"  # This sets the version in INIT_FILE

MODULE_VER = ""
with (Path(MODULE_NAME) / INIT_FILE).expanduser().resolve().open(
    encoding="utf-8",
    errors="surrogateescape",
) as f:  # Look in module's __init__ for __version__
    for line in f:
        if line.startswith(VERSION_INDICATOR):
            MODULE_VER = line.split("=", 1)[1].strip()[1:-1]
            break
    if not MODULE_VER:
        raise ValueError(
            f"{VERSION_INDICATOR} is not defined in {MODULE_NAME}/{INIT_FILE}",
        )

EXTRAS = {
    "test": [
        "bandit ~= 1.7.5",
        "black ~= 23.3.0",
        "coverage[toml] ~= 7.2.3",  # [toml] not needed on Python 3.11+
        "dlint ~= 0.14.1",
        "flake8 ~= 4.0.1",
        "flake8-boolean-trap ~= 1.0.0",
        "flake8-bugbear ~= 23.3.12",
        "flake8-comprehensions ~= 3.11.1",
        "flake8-datetimez ~= 20.10.0",
        "flake8-executable ~= 2.1.1",
        "flake8-implicit-str-concat ~= 0.4.0",
        "flake8-isort ~= 6.0.0",
        "flake8-logging-format ~= 0.9.0",
        "flake8-pie ~= 0.16.0",
        "flake8-print ~= 5.0.0",
        "flake8-pytest ~= 1.3",
        "flake8-pytest-style ~= 1.7.0",
        "flake8-quotes ~= 3.3.0",
        "flake8-return ~= 1.2.0",
        "flake8-simplify ~= 0.20.0",
        "flake8-slots ~= 0.1.5",
        "flake8-type-checking ~= 2.4.0",
        "flake8-typing-imports ~= 1.12.0",
        "flake8-use-pathlib ~= 0.3.0",
        "flynt ~= 0.78",
        "isort ~= 5.11.3",
        "mypy ~= 1.2.0",
        "pep8-naming ~= 0.13.0",
        "pylint ~= 2.17.0",
        'pyright==1.1.298; platform_system == "Linux"',
        "pytest ~= 7.3.0",
        "pytest-bandit ~= 0.6.1",
        "pytest-black ~= 0.3.12",
        "pytest-cov ~= 4.0.0",
        "pytest-dependency ~= 0.5.1",
        "pytest-flake8 ~= 1.1.1",
        "pytest-mypy ~= 0.10.0",
        "pytest-pylint ~= 0.19.0",
        "pytest-ruff ~= 0.0.5",
        "pytest-randomly ~= 3.12.0",
        "pytest-xdist ~= 3.2.0",
        'pytype==2023.3.13; platform_system == "Linux"',
        "pyupgrade-directories ~= 0.3.0",
        "ruff ~= 0.0.261",
        "refurb ~= 1.15.0",
        "semgrep ~= 1.17.1",
        "sphinx ~= 6.1.2",
        "tryceratops ~= 1.1.0",
        "vulture ~= 2.7",
        "yesqa ~= 1.4.0",
    ],
}


if __name__ == "__main__":
    setup(
        name=MODULE_NAME,
        version=MODULE_VER,
        entry_points={
            "console_scripts": [
                f"{MODULE_NAME} = {MODULE_NAME}.spidermonkey.hatch:main",
            ],
        },
        package_data={
            MODULE_NAME: [
                "py.typed",
            ],
        },
        packages=find_packages(exclude=("tests",)),
        install_requires=[
            "distro ~= 1.7.0",
            "mercurial ~= 6.2.1",
            "packaging ~= 23.0",
            "setuptools >= 65.6.3",
            "types-setuptools==67.2.0.1",  # Bump types-* only with mypy
            'types-toml==0.10.8.3; python_version <= "3.10"',
            "wheel >= 0.38.4",
            "zzbase >= 0.0.1",
        ],
        extras_require=EXTRAS,
        python_requires=">= 3.10",
        zip_safe=False,
    )
