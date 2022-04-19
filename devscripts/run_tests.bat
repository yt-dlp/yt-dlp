@setlocal
@echo off
cd /d %~dp0..

if ["%~1"]==[""] (
    set "test_set="test""
) else if ["%~1"]==["core"] (
    set "test_set="-m not download""
) else if ["%~1"]==["download"] (
    set "test_set="-m "download""
) else (
    echo.Invalid test type "%~1". Use "core" ^| "download"
    exit /b 1
)

set PYTHONWARNINGS=error
pytest %test_set%
