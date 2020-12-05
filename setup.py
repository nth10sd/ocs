# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""setuptools install script"""

from setuptools import find_packages
from setuptools import setup

EXTRAS = {
    "test": [
        "coverage ~= 5.3",
        "flake8==3.8.4",
        "flake8-commas ~= 2.0.0",
        "flake8-isort ~= 4.0.0",
        "flake8-quotes ~= 3.2.0",
        "isort ~= 5.6.4",
        "mypy==0.790",
        "pylint ~= 2.6.0",
        "pytest ~= 6.1.2",
        "pytest-cov ~= 2.10.1",
        "pytest-flake8 ~= 1.0.6",
        "pytest-mypy ~= 0.8.0",
        "pytest-pylint ~= 0.18.0",
        "sphinx ~= 3.3.1",
    ]}


if __name__ == "__main__":
    setup(
        name="ocs",
        version="0.9.0a1",
        entry_points={
            "console_scripts": ["ocs = ocs.compile_shell:main"],
        },
        package_data={"ocs": [
            "py.typed",
        ]},
        packages=find_packages(exclude=("tests",)),
        install_requires=[
            "distro ~= 1.5.0",
        ],
        extras_require=EXTRAS,
        python_requires=">= 3.7",
        zip_safe=False,
    )
