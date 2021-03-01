# Unused
#!/bin/bash

# IMPORTANT: the following assumptions are made
# * the GH repo is on the origin remote
# * the gh-pages branch is named so locally
# * the git config user.signingkey is properly set

# You will need
# pip install coverage nose rsa wheel

# TODO
# release notes
# make hash on local files

set -e

skip_tests=true
gpg_sign_commits=""
buildserver='localhost:8142'

while true
do
case "$1" in
    --run-tests)
        skip_tests=false
        shift
    ;;
    --gpg-sign-commits|-S)
        gpg_sign_commits="-S"
        shift
    ;;
    --buildserver)
        buildserver="$2"
        shift 2
    ;;
    --*)
        echo "ERROR: unknown option $1"
        exit 1
    ;;
    *)
        break
    ;;
esac
done

if [ -z "$1" ]; then echo "ERROR: specify version number like this: $0 1994.09.06"; exit 1; fi
version="$1"
major_version=$(echo "$version" | sed -n 's#^\([0-9]*\.[0-9]*\.[0-9]*\).*#\1#p')
if test "$major_version" '!=' "$(date '+%Y.%m.%d')"; then
    echo "$version does not start with today's date!"
    exit 1
fi

if [ ! -z "`git tag | grep "$version"`" ]; then echo 'ERROR: version already present'; exit 1; fi
if [ ! -z "`git status --porcelain | grep -v CHANGELOG`" ]; then echo 'ERROR: the working directory is not clean; commit or stash changes'; exit 1; fi
useless_files=$(find yt_dlp -type f -not -name '*.py')
if [ ! -z "$useless_files" ]; then echo "ERROR: Non-.py files in yt_dlp: $useless_files"; exit 1; fi
if [ ! -f "updates_key.pem" ]; then echo 'ERROR: updates_key.pem missing'; exit 1; fi
if ! type pandoc >/dev/null 2>/dev/null; then echo 'ERROR: pandoc is missing'; exit 1; fi
if ! python3 -c 'import rsa' 2>/dev/null; then echo 'ERROR: python3-rsa is missing'; exit 1; fi
if ! python3 -c 'import wheel' 2>/dev/null; then echo 'ERROR: wheel is missing'; exit 1; fi

read -p "Is Changelog up to date? (y/n) " -n 1
if [[ ! $REPLY =~ ^[Yy]$ ]]; then exit 1; fi

/bin/echo -e "\n### First of all, testing..."
make clean
if $skip_tests ; then
    echo 'SKIPPING TESTS'
else
    nosetests --verbose --with-coverage --cover-package=yt_dlp --cover-html test --stop || exit 1
fi

/bin/echo -e "\n### Changing version in version.py..."
sed -i "s/__version__ = '.*'/__version__ = '$version'/" yt_dlp/version.py

/bin/echo -e "\n### Changing version in Changelog..."
sed -i "s/<unreleased>/$version/" Changelog.md

/bin/echo -e "\n### Committing documentation, templates and yt_dlp/version.py..."
make README.md CONTRIBUTING.md issuetemplates supportedsites
git add README.md CONTRIBUTING.md .github/ISSUE_TEMPLATE/1_broken_site.md .github/ISSUE_TEMPLATE/2_site_support_request.md .github/ISSUE_TEMPLATE/3_site_feature_request.md .github/ISSUE_TEMPLATE/4_bug_report.md .github/ISSUE_TEMPLATE/5_feature_request.md .github/ISSUE_TEMPLATE/6_question.md docs/supportedsites.md yt_dlp/version.py Changelog.md
git commit $gpg_sign_commits -m "release $version"

/bin/echo -e "\n### Now tagging, signing and pushing..."
git tag -s -m "Release $version" "$version"
git show "$version"
read -p "Is it good, can I push? (y/n) " -n 1
if [[ ! $REPLY =~ ^[Yy]$ ]]; then exit 1; fi
echo
MASTER=$(git rev-parse --abbrev-ref HEAD)
git push origin $MASTER:master
git push origin "$version"

/bin/echo -e "\n### OK, now it is time to build the binaries..."
REV=$(git rev-parse HEAD)
make yt-dlp yt-dlp.tar.gz
read -p "VM running? (y/n) " -n 1
wget "http://$buildserver/build/ytdl-org/youtube-dl/yt-dlp.exe?rev=$REV" -O yt-dlp.exe
mkdir -p "build/$version"
mv yt-dlp yt-dlp.exe "build/$version"
mv yt-dlp.tar.gz "build/$version/yt-dlp-$version.tar.gz"
RELEASE_FILES="yt-dlp yt-dlp.exe yt-dlp-$version.tar.gz"
(cd build/$version/ && md5sum $RELEASE_FILES > MD5SUMS)
(cd build/$version/ && sha1sum $RELEASE_FILES > SHA1SUMS)
(cd build/$version/ && sha256sum $RELEASE_FILES > SHA2-256SUMS)
(cd build/$version/ && sha512sum $RELEASE_FILES > SHA2-512SUMS)

/bin/echo -e "\n### Signing and uploading the new binaries to GitHub..."
for f in $RELEASE_FILES; do gpg --passphrase-repeat 5 --detach-sig "build/$version/$f"; done

ROOT=$(pwd)
python devscripts/create-github-release.py Changelog.md $version "$ROOT/build/$version"

ssh ytdl@yt-dl.org "sh html/update_latest.sh $version"

/bin/echo -e "\n### Now switching to gh-pages..."
git clone --branch gh-pages --single-branch . build/gh-pages
(
    set -e
    ORIGIN_URL=$(git config --get remote.origin.url)
    cd build/gh-pages
    "$ROOT/devscripts/gh-pages/add-version.py" $version
    "$ROOT/devscripts/gh-pages/update-feed.py"
    "$ROOT/devscripts/gh-pages/sign-versions.py" < "$ROOT/updates_key.pem"
    "$ROOT/devscripts/gh-pages/generate-download.py"
    "$ROOT/devscripts/gh-pages/update-copyright.py"
    "$ROOT/devscripts/gh-pages/update-sites.py"
    git add *.html *.html.in update
    git commit $gpg_sign_commits -m "release $version"
    git push "$ROOT" gh-pages
    git push "$ORIGIN_URL" gh-pages
)
rm -rf build

make pypi-files
echo "Uploading to PyPi ..."
python setup.py sdist bdist_wheel upload
make clean

/bin/echo -e "\n### DONE!"
