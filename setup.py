# coding=utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""setuptools install script"""

from setuptools import find_packages
from setuptools import setup

EXTRAS = {
    "test": [
        # "codecov==2.0.15",
        "coverage>=4.5.4,<4.6",
        "flake8==3.8.3",
        "flake8-commas>=2.0.0,<2.1",
        "flake8-isort>=3.0.0,<3.1",
        "flake8-quotes>=3.2.0,<3.3",
        "isort==4.3.21",
        "pylint>=2.5.3,<2.6",
        "pytest>=5.4.3,<5.5",
        "pytest-cov>=2.10.0,<2.11",
        "pytest-flake8>=1.0.6,<1.1",
        "pytest-pylint>=0.17.0,<0.18",
    ]}


if __name__ == "__main__":
    setup(name="funfuzz",
          version="0.7.0a1",
          entry_points={
              "console_scripts": ["funfuzz = funfuzz.js.compile_shell:main"],
          },
          package_data={"funfuzz": [
          ]},
          package_dir={"": "src"},
          packages=find_packages(where="src"),
          install_requires=[
          ],
          extras_require=EXTRAS,
          python_requires=">=3.6",
          zip_safe=False)
