# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""setuptools install script"""

from setuptools import find_packages
from setuptools import setup

EXTRAS = {
    "test": [
        "coverage ~= 5.2.1",
        "flake8 == 3.8.3",
        "flake8-commas ~= 2.0.0",
        "flake8-isort ~= 4.0.0",
        "flake8-quotes ~= 3.2.0",
        "isort ~= 5.5.1",
        "mypy == 0.782",
        "pylint ~= 2.6.0",
        "pytest ~= 6.0.1",
        "pytest-cov ~= 2.10.1",
        "pytest-flake8 ~= 1.0.6",
        "pytest-pylint ~= 0.17.0",
        "sphinx ~= 3.2.1",
    ]}


if __name__ == "__main__":
    setup(name="ocs",
          version="0.8.0a1",
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
          zip_safe=False)
