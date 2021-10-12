@setlocal
@echo off
cd /d %~dp0..

if ["%~1"]==[""] (
    set "test_set="
) else if ["%~1"]==["core"] (
    set "test_set="not download""
) else if ["%~1"]==["download"] (
    set "test_set="download"
) else (
    echo.Invalid test type "%~1". Use "core" ^| "download"
    exit /b 1
)

pytest -m %test_set%
