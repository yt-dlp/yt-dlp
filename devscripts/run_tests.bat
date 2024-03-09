@echo off

>&2 echo run_tests.bat is deprecated. Please use `devscripts/run_tests.py` instead
python %~dp0run_tests.py %~1
