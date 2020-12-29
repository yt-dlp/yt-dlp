@echo off

rem Keep this list in sync with the `offlinetest` target in Makefile
set DOWNLOAD_TESTS="age_restriction^|download^|iqiyi_sdk_interpreter^|socks^|subtitles^|write_annotations^|youtube_lists^|youtube_signature^|post_hooks"

if "%YTDL_TEST_SET%" == "core" (
    set test_set="-I test_("%DOWNLOAD_TESTS%")\.py"
    set multiprocess_args=""
) else if "%YTDL_TEST_SET%" == "download" (
    set test_set="-I test_(?!"%DOWNLOAD_TESTS%").+\.py"
    set multiprocess_args="--processes=4 --process-timeout=540"
) else (
    echo YTDL_TEST_SET is not set or invalid
    exit /b 1
)

nosetests test --verbose %test_set:"=% %multiprocess_args:"=%
