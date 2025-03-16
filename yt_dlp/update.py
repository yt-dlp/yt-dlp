from __future__ import annotations

import atexit
import contextlib
import functools
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from dataclasses import dataclass
from zipimport import zipimporter

from .networking import Request
from .networking.exceptions import HTTPError, network_exceptions
from .utils import (
    NO_DEFAULT,
    Popen,
    deprecation_warning,
    format_field,
    remove_end,
    shell_quote,
    system_identifier,
    version_tuple,
)
from .version import (
    CHANNEL,
    ORIGIN,
    RELEASE_GIT_HEAD,
    UPDATE_HINT,
    VARIANT,
    __version__,
)

UPDATE_SOURCES = {
    'stable': 'yt-dlp/yt-dlp',
    'nightly': 'yt-dlp/yt-dlp-nightly-builds',
    'master': 'yt-dlp/yt-dlp-master-builds',
}
REPOSITORY = UPDATE_SOURCES['stable']
_INVERSE_UPDATE_SOURCES = {value: key for key, value in UPDATE_SOURCES.items()}

_VERSION_RE = re.compile(r'(\d+\.)*\d+')
_HASH_PATTERN = r'[\da-f]{40}'
_COMMIT_RE = re.compile(rf'Generated from: https://(?:[^/?#]+/){{3}}commit/(?P<hash>{_HASH_PATTERN})')

API_BASE_URL = 'https://api.github.com/repos'

# Backwards compatibility variables for the current channel
API_URL = f'{API_BASE_URL}/{REPOSITORY}/releases'


@functools.cache
def _get_variant_and_executable_path():
    """@returns (variant, executable_path)"""
    if getattr(sys, 'frozen', False):
        path = sys.executable
        if not hasattr(sys, '_MEIPASS'):
            return 'py2exe', path
        elif sys._MEIPASS == os.path.dirname(path):
            return f'{sys.platform}_dir', path
        elif sys.platform == 'darwin':
            machine = '_legacy' if version_tuple(platform.mac_ver()[0]) < (10, 15) else ''
        else:
            machine = f'_{platform.machine().lower()}'
            is_64bits = sys.maxsize > 2**32
            # Ref: https://en.wikipedia.org/wiki/Uname#Examples
            if machine[1:] in ('x86', 'x86_64', 'amd64', 'i386', 'i686'):
                machine = '_x86' if not is_64bits else ''
            # platform.machine() on 32-bit raspbian OS may return 'aarch64', so check "64-bitness"
            # See: https://github.com/yt-dlp/yt-dlp/issues/11813
            elif machine[1:] == 'aarch64' and not is_64bits:
                machine = '_armv7l'
            # sys.executable returns a /tmp/ path for staticx builds (linux_static)
            # Ref: https://staticx.readthedocs.io/en/latest/usage.html#run-time-information
            if static_exe_path := os.getenv('STATICX_PROG_PATH'):
                path = static_exe_path
        return f'{remove_end(sys.platform, "32")}{machine}_exe', path

    path = os.path.dirname(__file__)
    if isinstance(__loader__, zipimporter):
        return 'zip', os.path.join(path, '..')
    elif (os.path.basename(sys.argv[0]) in ('__main__.py', '-m')
          and os.path.exists(os.path.join(path, '../.git/HEAD'))):
        return 'source', path
    return 'unknown', path


def detect_variant():
    return VARIANT or _get_variant_and_executable_path()[0]


@functools.cache
def current_git_head():
    if detect_variant() != 'source':
        return
    with contextlib.suppress(Exception):
        stdout, _, _ = Popen.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            text=True, cwd=os.path.dirname(os.path.abspath(__file__)),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if re.fullmatch('[0-9a-f]+', stdout.strip()):
            return stdout.strip()


_FILE_SUFFIXES = {
    'zip': '',
    'win_exe': '.exe',
    'win_x86_exe': '_x86.exe',
    'darwin_exe': '_macos',
    'darwin_legacy_exe': '_macos_legacy',
    'linux_exe': '_linux',
    'linux_aarch64_exe': '_linux_aarch64',
    'linux_armv7l_exe': '_linux_armv7l',
}

_NON_UPDATEABLE_REASONS = {
    **{variant: None for variant in _FILE_SUFFIXES},  # Updatable
    **{variant: f'Auto-update is not supported for unpackaged {name} executable; Re-download the latest release'
       for variant, name in {'win32_dir': 'Windows', 'darwin_dir': 'MacOS', 'linux_dir': 'Linux'}.items()},
    'py2exe': 'py2exe is no longer supported by yt-dlp; This executable cannot be updated',
    'source': 'You cannot update when running from source code; Use git to pull the latest changes',
    'unknown': 'You installed yt-dlp from a manual build or with a package manager; Use that to update',
    'other': 'You are using an unofficial build of yt-dlp; Build the executable again',
}


def is_non_updateable():
    if UPDATE_HINT:
        return UPDATE_HINT
    return _NON_UPDATEABLE_REASONS.get(
        detect_variant(), _NON_UPDATEABLE_REASONS['unknown' if VARIANT else 'other'])


def _get_binary_name():
    return format_field(_FILE_SUFFIXES, detect_variant(), template='yt-dlp%s', ignore=None, default=None)


def _get_system_deprecation():
    MIN_SUPPORTED, MIN_RECOMMENDED = (3, 9), (3, 9)

    if sys.version_info > MIN_RECOMMENDED:
        return None

    major, minor = sys.version_info[:2]
    PYTHON_MSG = f'Please update to Python {".".join(map(str, MIN_RECOMMENDED))} or above'

    if sys.version_info < MIN_SUPPORTED:
        return f'Python version {major}.{minor} is no longer supported! {PYTHON_MSG}'

    return f'Support for Python version {major}.{minor} has been deprecated. {PYTHON_MSG}'


def _sha256_file(path):
    h = hashlib.sha256()
    mv = memoryview(bytearray(128 * 1024))
    with open(os.path.realpath(path), 'rb', buffering=0) as f:
        for n in iter(lambda: f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()


def _make_label(origin, tag, version=None):
    if '/' in origin:
        channel = _INVERSE_UPDATE_SOURCES.get(origin, origin)
    else:
        channel = origin
    label = f'{channel}@{tag}'
    if version and version != tag:
        label += f' build {version}'
    if channel != origin:
        label += f' from {origin}'
    return label


@dataclass
class UpdateInfo:
    """
    Update target information

    Can be created by `query_update()` or manually.

    Attributes:
        tag                 The release tag that will be updated to. If from query_update,
                            the value is after API resolution and update spec processing.
                            The only property that is required.
        version             The actual numeric version (if available) of the binary to be updated to,
                            after API resolution and update spec processing. (default: None)
        requested_version   Numeric version of the binary being requested (if available),
                            after API resolution only. (default: None)
        commit              Commit hash (if available) of the binary to be updated to,
                            after API resolution and update spec processing. (default: None)
                            This value will only match the RELEASE_GIT_HEAD of prerelease builds.
        binary_name         Filename of the binary to be updated to. (default: current binary name)
        checksum            Expected checksum (if available) of the binary to be
                            updated to. (default: None)
    """
    tag: str
    version: str | None = None
    requested_version: str | None = None
    commit: str | None = None

    binary_name: str | None = _get_binary_name()  # noqa: RUF009: Always returns the same value
    checksum: str | None = None


class Updater:
    # XXX: use class variables to simplify testing
    _channel = CHANNEL
    _origin = ORIGIN
    _update_sources = UPDATE_SOURCES

    def __init__(self, ydl, target: str | None = None):
        self.ydl = ydl
        # For backwards compat, target needs to be treated as if it could be None
        self.requested_channel, sep, self.requested_tag = (target or self._channel).rpartition('@')
        # Check if requested_tag is actually the requested repo/channel
        if not sep and ('/' in self.requested_tag or self.requested_tag in self._update_sources):
            self.requested_channel = self.requested_tag
            self.requested_tag: str = None  # type: ignore (we set it later)
        elif not self.requested_channel:
            # User did not specify a channel, so we are requesting the default channel
            self.requested_channel = self._channel.partition('@')[0]

        # --update should not be treated as an exact tag request even if CHANNEL has a @tag
        self._exact = bool(target) and target != self._channel
        if not self.requested_tag:
            # User did not specify a tag, so we request 'latest' and track that no exact tag was passed
            self.requested_tag = 'latest'
            self._exact = False

        if '/' in self.requested_channel:
            # requested_channel is actually a repository
            self.requested_repo = self.requested_channel
            if not self.requested_repo.startswith('yt-dlp/') and self.requested_repo != self._origin:
                self.ydl.report_warning(
                    f'You are switching to an {self.ydl._format_err("unofficial", "red")} executable '
                    f'from {self.ydl._format_err(self.requested_repo, self.ydl.Styles.EMPHASIS)}. '
                    f'Run {self.ydl._format_err("at your own risk", "light red")}')
                self._block_restart('Automatically restarting into custom builds is disabled for security reasons')
        else:
            # Check if requested_channel resolves to a known repository or else raise
            self.requested_repo = self._update_sources.get(self.requested_channel)
            if not self.requested_repo:
                self._report_error(
                    f'Invalid update channel {self.requested_channel!r} requested. '
                    f'Valid channels are {", ".join(self._update_sources)}', True)

        self._identifier = f'{detect_variant()} {system_identifier()}'

    @property
    def current_version(self):
        """Current version"""
        return __version__

    @property
    def current_commit(self):
        """Current commit hash"""
        return RELEASE_GIT_HEAD

    def _download_asset(self, name, tag=None):
        if not tag:
            tag = self.requested_tag

        path = 'latest/download' if tag == 'latest' else f'download/{tag}'
        url = f'https://github.com/{self.requested_repo}/releases/{path}/{name}'
        self.ydl.write_debug(f'Downloading {name} from {url}')
        return self.ydl.urlopen(url).read()

    def _call_api(self, tag):
        tag = f'tags/{tag}' if tag != 'latest' else tag
        url = f'{API_BASE_URL}/{self.requested_repo}/releases/{tag}'
        self.ydl.write_debug(f'Fetching release info: {url}')
        return json.loads(self.ydl.urlopen(Request(url, headers={
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'yt-dlp',
            'X-GitHub-Api-Version': '2022-11-28',
        })).read().decode())

    def _get_version_info(self, tag: str) -> tuple[str | None, str | None]:
        if _VERSION_RE.fullmatch(tag):
            return tag, None

        api_info = self._call_api(tag)

        if tag == 'latest':
            requested_version = api_info['tag_name']
        else:
            match = re.search(rf'\s+(?P<version>{_VERSION_RE.pattern})$', api_info.get('name', ''))
            requested_version = match.group('version') if match else None

        if re.fullmatch(_HASH_PATTERN, api_info.get('target_commitish', '')):
            target_commitish = api_info['target_commitish']
        else:
            match = _COMMIT_RE.match(api_info.get('body', ''))
            target_commitish = match.group('hash') if match else None

        if not (requested_version or target_commitish):
            self._report_error('One of either version or commit hash must be available on the release', expected=True)

        return requested_version, target_commitish

    def _download_update_spec(self, source_tags):
        for tag in source_tags:
            try:
                return self._download_asset('_update_spec', tag=tag).decode()
            except network_exceptions as error:
                if isinstance(error, HTTPError) and error.status == 404:
                    continue
                self._report_network_error(f'fetch update spec: {error}')
                return None

        self._report_error(
            f'The requested tag {self.requested_tag} does not exist for {self.requested_repo}', True)
        return None

    def _process_update_spec(self, lockfile: str, resolved_tag: str):
        lines = lockfile.splitlines()
        is_version2 = any(line.startswith('lockV2 ') for line in lines)

        for line in lines:
            if is_version2:
                if not line.startswith(f'lockV2 {self.requested_repo} '):
                    continue
                _, _, tag, pattern = line.split(' ', 3)
            else:
                if not line.startswith('lock '):
                    continue
                _, tag, pattern = line.split(' ', 2)

            if re.match(pattern, self._identifier):
                if _VERSION_RE.fullmatch(tag):
                    if not self._exact:
                        return tag
                    elif self._version_compare(tag, resolved_tag):
                        return resolved_tag
                elif tag != resolved_tag:
                    continue

                self._report_error(
                    f'yt-dlp cannot be updated to {resolved_tag} since you are on an older Python version '
                    'or your operating system is not compatible with the requested build', True)
                return None

        return resolved_tag

    def _version_compare(self, a: str, b: str):
        """
        Compare two version strings

        This function SHOULD NOT be called if self._exact == True
        """
        if _VERSION_RE.fullmatch(f'{a}.{b}'):
            return version_tuple(a) >= version_tuple(b)
        return a == b

    def query_update(self, *, _output=False) -> UpdateInfo | None:
        """Fetches info about the available update
        @returns   An `UpdateInfo` if there is an update available, else None
        """
        if not self.requested_repo:
            self._report_error('No target repository could be determined from input')
            return None

        try:
            requested_version, target_commitish = self._get_version_info(self.requested_tag)
        except network_exceptions as e:
            self._report_network_error(f'obtain version info ({e})', delim='; Please try again later or')
            return None

        if self._exact and self._origin != self.requested_repo:
            has_update = True
        elif requested_version:
            if self._exact:
                has_update = self.current_version != requested_version
            else:
                has_update = not self._version_compare(self.current_version, requested_version)
        elif target_commitish:
            has_update = target_commitish != self.current_commit
        else:
            has_update = False

        resolved_tag = requested_version if self.requested_tag == 'latest' else self.requested_tag
        current_label = _make_label(self._origin, self._channel.partition('@')[2] or self.current_version, self.current_version)
        requested_label = _make_label(self.requested_repo, resolved_tag, requested_version)
        latest_or_requested = f'{"Latest" if self.requested_tag == "latest" else "Requested"} version: {requested_label}'
        if not has_update:
            if _output:
                self.ydl.to_screen(f'{latest_or_requested}\nyt-dlp is up to date ({current_label})')
            return None

        update_spec = self._download_update_spec(('latest', None) if requested_version else (None,))
        if not update_spec:
            return None
        # `result_` prefixed vars == post-_process_update_spec() values
        result_tag = self._process_update_spec(update_spec, resolved_tag)
        if not result_tag or result_tag == self.current_version:
            return None
        elif result_tag == resolved_tag:
            result_version = requested_version
        elif _VERSION_RE.fullmatch(result_tag):
            result_version = result_tag
        else:  # actual version being updated to is unknown
            result_version = None

        checksum = None
        # Non-updateable variants can get update_info but need to skip checksum
        if not is_non_updateable():
            try:
                hashes = self._download_asset('SHA2-256SUMS', result_tag)
            except network_exceptions as error:
                if not isinstance(error, HTTPError) or error.status != 404:
                    self._report_network_error(f'fetch checksums: {error}')
                    return None
                self.ydl.report_warning('No hash information found for the release, skipping verification')
            else:
                for ln in hashes.decode().splitlines():
                    if ln.endswith(_get_binary_name()):
                        checksum = ln.split()[0]
                        break
                if not checksum:
                    self.ydl.report_warning('The hash could not be found in the checksum file, skipping verification')

        if _output:
            update_label = _make_label(self.requested_repo, result_tag, result_version)
            self.ydl.to_screen(
                f'Current version: {current_label}\n{latest_or_requested}'
                + (f'\nUpgradable to: {update_label}' if update_label != requested_label else ''))

        return UpdateInfo(
            tag=result_tag,
            version=result_version,
            requested_version=requested_version,
            commit=target_commitish if result_tag == resolved_tag else None,
            checksum=checksum)

    def update(self, update_info=NO_DEFAULT):
        """Update yt-dlp executable to the latest version
        @param update_info  `UpdateInfo | None` as returned by query_update()
        """
        if update_info is NO_DEFAULT:
            update_info = self.query_update(_output=True)
        if not update_info:
            return False

        err = is_non_updateable()
        if err:
            self._report_error(err, True)
            return False

        self.ydl.to_screen(f'Current Build Hash: {_sha256_file(self.filename)}')

        update_label = _make_label(self.requested_repo, update_info.tag, update_info.version)
        self.ydl.to_screen(f'Updating to {update_label} ...')

        directory = os.path.dirname(self.filename)
        if not os.access(self.filename, os.W_OK):
            return self._report_permission_error(self.filename)
        elif not os.access(directory, os.W_OK):
            return self._report_permission_error(directory)

        new_filename, old_filename = f'{self.filename}.new', f'{self.filename}.old'
        if detect_variant() == 'zip':  # Can be replaced in-place
            new_filename, old_filename = self.filename, None

        try:
            if os.path.exists(old_filename or ''):
                os.remove(old_filename)
        except OSError:
            return self._report_error('Unable to remove the old version')

        try:
            newcontent = self._download_asset(update_info.binary_name, update_info.tag)
        except network_exceptions as e:
            if isinstance(e, HTTPError) and e.status == 404:
                return self._report_error(
                    f'The requested tag {self.requested_repo}@{update_info.tag} does not exist', True)
            return self._report_network_error(f'fetch updates: {e}', tag=update_info.tag)

        if not update_info.checksum:
            self._block_restart('Automatically restarting into unverified builds is disabled for security reasons')
        elif hashlib.sha256(newcontent).hexdigest() != update_info.checksum:
            return self._report_network_error('verify the new executable', tag=update_info.tag)

        try:
            with open(new_filename, 'wb') as outf:
                outf.write(newcontent)
        except OSError:
            return self._report_permission_error(new_filename)

        if old_filename:
            mask = os.stat(self.filename).st_mode
            try:
                os.rename(self.filename, old_filename)
            except OSError:
                return self._report_error('Unable to move current version')

            try:
                os.rename(new_filename, self.filename)
            except OSError:
                self._report_error('Unable to overwrite current version')
                return os.rename(old_filename, self.filename)

        variant = detect_variant()
        if variant.startswith('win'):
            atexit.register(Popen, f'ping 127.0.0.1 -n 5 -w 1000 & del /F "{old_filename}"',
                            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif old_filename:
            try:
                os.remove(old_filename)
            except OSError:
                self._report_error('Unable to remove the old version')

            try:
                os.chmod(self.filename, mask)
            except OSError:
                return self._report_error(
                    f'Unable to set permissions. Run: sudo chmod a+rx {shell_quote(self.filename)}')

        self.ydl.to_screen(f'Updated yt-dlp to {update_label}')
        return True

    @functools.cached_property
    def filename(self):
        """Filename of the executable"""
        return os.path.realpath(_get_variant_and_executable_path()[1])

    @functools.cached_property
    def cmd(self):
        """The command-line to run the executable, if known"""
        argv = None
        # There is no sys.orig_argv in py < 3.10. Also, it can be [] when frozen
        if getattr(sys, 'orig_argv', None):
            argv = sys.orig_argv
        elif getattr(sys, 'frozen', False):
            argv = sys.argv
        # linux_static exe's argv[0] will be /tmp/staticx-NNNN/yt-dlp_linux if we don't fixup here
        if argv and os.getenv('STATICX_PROG_PATH'):
            argv = [self.filename, *argv[1:]]
        return argv

    def restart(self):
        """Restart the executable"""
        assert self.cmd, 'Must be frozen or Py >= 3.10'
        self.ydl.write_debug(f'Restarting: {shell_quote(self.cmd)}')
        _, _, returncode = Popen.run(self.cmd)
        return returncode

    def _block_restart(self, msg):
        def wrapper():
            self._report_error(f'{msg}. Restart yt-dlp to use the updated version', expected=True)
            return self.ydl._download_retcode
        self.restart = wrapper

    def _report_error(self, msg, expected=False):
        self.ydl.report_error(msg, tb=False if expected else None)
        self.ydl._download_retcode = 100

    def _report_permission_error(self, file):
        self._report_error(f'Unable to write to {file}; try running as administrator', True)

    def _report_network_error(self, action, delim=';', tag=None):
        if not tag:
            tag = self.requested_tag
        path = tag if tag == 'latest' else f'tag/{tag}'
        self._report_error(
            f'Unable to {action}{delim} visit  '
            f'https://github.com/{self.requested_repo}/releases/{path}', True)


def run_update(ydl):
    """Update the program file with the latest version from the repository
    @returns    Whether there was a successful update (No update = False)
    """
    deprecation_warning(
        '"yt_dlp.update.run_update(ydl)" is deprecated and may be removed in a future version. '
        'Use "yt_dlp.update.Updater(ydl).update()" instead')
    return Updater(ydl).update()


__all__ = ['Updater']
