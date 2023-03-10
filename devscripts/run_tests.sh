#!/usr/bin/env sh

if [ -z "$1" ]; then
    test_set='test'
elif [ "$1" = 'core' ]; then
    test_set="-m not download"
elif [ "$1" = 'download' ]; then
    test_set="-m download"
else
    echo 'Invalid test type "'"$1"'". Use "core" | "download"'
    exit 1
fi

python3 -bb -Werror -m pytest "$test_set"
