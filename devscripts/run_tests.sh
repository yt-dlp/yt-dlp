#!/usr/bin/env sh

>&2 echo 'run_tests.sh is deprecated. Please use `devscripts/run_tests.py` instead'
python3 devscripts/run_tests.py "$1"
