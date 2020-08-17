#! /bin/bash

# Boostrap Sphinx
sphinx-quickstart --sep -p "ocs" -a "FOO" -r "BAR" -l "en" --ext-autodoc --no-makefile --no-batchfile --no-use-make-mode;

# Copy over the intended copy of conf.py
cp source/conf_correct.py source/conf.py;

# Generate Sphinx documentation
sphinx-apidoc -o source/ ../ocs/;

# Add "modules" to one of the sections in index.rst in the middle of several empty lines
cat source/index.rst | tr '\n' '\f' | sed 's/\f\f\f\f/\f\f   modules\f\f/' | tr '\f' '\n' > source/index_new.rst;
mv source/index_new.rst source/index.rst;

# Generate Sphinx HTML documentation
sphinx-build -b html source/ build/html/;
