#!/bin/bash
set -exuo pipefail

if [[ -z "${PYTHON_VERSION:-}" ]]; then
    PYTHON_VERSION="3.13"
    echo "Defaulting to using Python ${PYTHON_VERSION}"
fi

# Set up virtual environment
rm -rf .venv
py"${PYTHON_VERSION}" -m venv .venv --without-pip
sys_pkg_path=$(py"${PYTHON_VERSION}" -c 'import sysconfig; print(sysconfig.get_path("purelib"))')
# shellcheck disable=SC1091
source .venv/bin/activate
# In the activated venv we can use python instead of py3.13 or py3.14 etc
venv_pkg_path=$(python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')
# Copy up-to-date pip+etc from system site-packages to venv site-packages
cp -ra "${sys_pkg_path}/"* "${venv_pkg_path}/"

python -m pip install -U --require-hashes -r "bundle/requirements/requirements-${REQUIREMENTS}.txt"
python -m devscripts.make_lazy_extractors
python devscripts/update-version.py -c "${CHANNEL}" -r "${ORIGIN}" "${VERSION}"

if [[ -z "${SKIP_ONEDIR_BUILD:-}" ]]; then
    mkdir -p /build
    python -m bundle.pyinstaller --onedir --distpath=/build
    pushd "/build/${EXE_NAME}"
    chmod +x "${EXE_NAME}"
    python -m zipfile -c "/yt-dlp/dist/${EXE_NAME}.zip" ./
    popd
fi

if [[ -z "${SKIP_ONEFILE_BUILD:-}" ]]; then
    python -m bundle.pyinstaller
    chmod +x "./dist/${EXE_NAME}"
fi

deactivate
