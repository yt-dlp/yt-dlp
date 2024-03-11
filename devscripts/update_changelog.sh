#!/usr/bin/env bash

[[ -f './Changelog.md' ]] || { echo 'This script must be executed from the project root directory' >&2; exit 1; }
[[ -n "${1}" ]]           || { echo 'Release version must be passed as an argument to this script' >&2; exit 1; }

set -e -o pipefail

{
  sed '/### /Q' ./Changelog.md
  echo "### ${1}"
  python ./devscripts/make_changelog.py -vv -c
  echo
  grep -Poz '(?s)### \d+\.\d+\.\d+.+' ./Changelog.md | head -n -1
} > ./Changelog.md.new

mv -f ./Changelog.md.new ./Changelog.md
