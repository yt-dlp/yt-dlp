#!/bin/bash

# Keep this list in sync with the `offlinetest` target in Makefile
DOWNLOAD_TESTS="age_restriction|download|iqiyi_sdk_interpreter|socks|subtitles|write_annotations|youtube_lists|youtube_signature|post_hooks"

test_set=""
multiprocess_args=""

case "$YTDL_TEST_SET" in
    core)
        test_set="-I test_($DOWNLOAD_TESTS)\.py"
    ;;
    download)
        test_set="-I test_(?!$DOWNLOAD_TESTS).+\.py"
        multiprocess_args="--processes=4 --process-timeout=540"
    ;;
    *)
        break
    ;;
esac

nosetests test --verbose $test_set $multiprocess_args
