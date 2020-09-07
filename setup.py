# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""setuptools install script"""

from setuptools import find_packages
from setuptools import setup

EXTRAS = {
    "test": [
        "coverage>=5.2.1,<5.3",
        "flake8==3.8.3",
        "flake8-commas>=2.0.0,<2.1",
        "flake8-isort>=3.0.0,<3.1",
        "flake8-quotes>=3.2.0,<3.3",
        "isort==4.3.21",
        "mypy==0.782",
        "pylint>=2.5.3,<2.6",
        "pytest>=5.4.3,<5.5",
        "pytest-cov>=2.10.0,<2.11",
        "pytest-flake8>=1.0.6,<1.1",
        "pytest-mypy>=0.6.2,<0.7",
        "pytest-pylint>=0.17.0,<0.18",
        "sphinx==3.2.1",
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
              "distro>=1.3.0",
          ],
          extras_require=EXTRAS,
          python_requires=">=3.6",
          zip_safe=False)
