import atexit
import contextlib
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import urllib.error
from zipimport import zipimporter

from .compat import functools  # isort: split
from .compat import compat_realpath, compat_shlex_quote
from .utils import (
    Popen,
    cached_method,
    deprecation_warning,
    network_exceptions,
    remove_end,
    remove_start,
    sanitized_Request,
    shell_quote,
    system_identifier,
    version_tuple,
)
from .version import CHANNEL, UPDATE_HINT, VARIANT, __version__

UPDATE_SOURCES = {
    'stable': 'yt-dlp/yt-dlp',
    'nightly': 'yt-dlp/yt-dlp-nightly-builds',
}
REPOSITORY = UPDATE_SOURCES['stable']

_VERSION_RE = re.compile(r'(\d+\.)*\d+')

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
            # Ref: https://en.wikipedia.org/wiki/Uname#Examples
            if machine[1:] in ('x86', 'x86_64', 'amd64', 'i386', 'i686'):
                machine = '_x86' if platform.architecture()[0][:2] == '32' else ''
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
    'py2exe': '_min.exe',
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
    'source': 'You cannot update when running from source code; Use git to pull the latest changes',
    'unknown': 'You installed yt-dlp with a package manager or setup.py; Use that to update',
    'other': 'You are using an unofficial build of yt-dlp; Build the executable again',
}


def is_non_updateable():
    if UPDATE_HINT:
        return UPDATE_HINT
    return _NON_UPDATEABLE_REASONS.get(
        detect_variant(), _NON_UPDATEABLE_REASONS['unknown' if VARIANT else 'other'])


def _sha256_file(path):
    h = hashlib.sha256()
    mv = memoryview(bytearray(128 * 1024))
    with open(os.path.realpath(path), 'rb', buffering=0) as f:
        for n in iter(lambda: f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()


class Updater:
    _exact = True

    def __init__(self, ydl, target=None):
        self.ydl = ydl

        self.target_channel, sep, self.target_tag = (target or CHANNEL).rpartition('@')
        # stable => stable@latest
        if not sep and ('/' in self.target_tag or self.target_tag in UPDATE_SOURCES):
            self.target_channel = self.target_tag
            self.target_tag = None
        elif not self.target_channel:
            self.target_channel = CHANNEL.partition('@')[0]

        if not self.target_tag:
            self.target_tag = 'latest'
            self._exact = False
        elif self.target_tag != 'latest':
            self.target_tag = f'tags/{self.target_tag}'

        if '/' in self.target_channel:
            self._target_repo = self.target_channel
            if self.target_channel not in (CHANNEL, *UPDATE_SOURCES.values()):
                self.ydl.report_warning(
                    f'You are switching to an {self.ydl._format_err("unofficial", "red")} executable '
                    f'from {self.ydl._format_err(self._target_repo, self.ydl.Styles.EMPHASIS)}. '
                    f'Run {self.ydl._format_err("at your own risk", "light red")}')
                self._block_restart('Automatically restarting into custom builds is disabled for security reasons')
        else:
            self._target_repo = UPDATE_SOURCES.get(self.target_channel)
            if not self._target_repo:
                self._report_error(
                    f'Invalid update channel {self.target_channel!r} requested. '
                    f'Valid channels are {", ".join(UPDATE_SOURCES)}', True)

    def _version_compare(self, a, b, channel=CHANNEL):
        if self._exact and channel != self.target_channel:
            return False

        if _VERSION_RE.fullmatch(f'{a}.{b}'):
            a, b = version_tuple(a), version_tuple(b)
            return a == b if self._exact else a >= b
        return a == b

    @functools.cached_property
    def _tag(self):
        if self._version_compare(self.current_version, self.latest_version):
            return self.target_tag

        identifier = f'{detect_variant()} {self.target_channel} {system_identifier()}'
        for line in self._download('_update_spec', 'latest').decode().splitlines():
            if not line.startswith('lock '):
                continue
            _, tag, pattern = line.split(' ', 2)
            if re.match(pattern, identifier):
                if not self._exact:
                    return f'tags/{tag}'
                elif self.target_tag == 'latest' or not self._version_compare(
                        tag, self.target_tag[5:], channel=self.target_channel):
                    self._report_error(
                        f'yt-dlp cannot be updated above {tag} since you are on an older Python version', True)
                    return f'tags/{self.current_version}'
        return self.target_tag

    @cached_method
    def _get_version_info(self, tag):
        url = f'{API_BASE_URL}/{self._target_repo}/releases/{tag}'
        self.ydl.write_debug(f'Fetching release info: {url}')
        return json.loads(self.ydl.urlopen(sanitized_Request(url, headers={
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'yt-dlp',
            'X-GitHub-Api-Version': '2022-11-28',
        })).read().decode())

    @property
    def current_version(self):
        """Current version"""
        return __version__

    @staticmethod
    def _label(channel, tag):
        """Label for a given channel and tag"""
        return f'{channel}@{remove_start(tag, "tags/")}'

    def _get_actual_tag(self, tag):
        if tag.startswith('tags/'):
            return tag[5:]
        return self._get_version_info(tag)['tag_name']

    @property
    def new_version(self):
        """Version of the latest release we can update to"""
        return self._get_actual_tag(self._tag)

    @property
    def latest_version(self):
        """Version of the target release"""
        return self._get_actual_tag(self.target_tag)

    @property
    def has_update(self):
        """Whether there is an update available"""
        return not self._version_compare(self.current_version, self.new_version)

    @functools.cached_property
    def filename(self):
        """Filename of the executable"""
        return compat_realpath(_get_variant_and_executable_path()[1])

    def _download(self, name, tag):
        slug = 'latest/download' if tag == 'latest' else f'download/{tag[5:]}'
        url = f'https://github.com/{self._target_repo}/releases/{slug}/{name}'
        self.ydl.write_debug(f'Downloading {name} from {url}')
        return self.ydl.urlopen(url).read()

    @functools.cached_property
    def release_name(self):
        """The release filename"""
        return f'yt-dlp{_FILE_SUFFIXES[detect_variant()]}'

    @functools.cached_property
    def release_hash(self):
        """Hash of the latest release"""
        hash_data = dict(ln.split()[::-1] for ln in self._download('SHA2-256SUMS', self._tag).decode().splitlines())
        return hash_data[self.release_name]

    def _report_error(self, msg, expected=False):
        self.ydl.report_error(msg, tb=False if expected else None)
        self.ydl._download_retcode = 100

    def _report_permission_error(self, file):
        self._report_error(f'Unable to write to {file}; Try running as administrator', True)

    def _report_network_error(self, action, delim=';'):
        self._report_error(
            f'Unable to {action}{delim} visit  '
            f'https://github.com/{self._target_repo}/releases/{self.target_tag.replace("tags/", "tag/")}', True)

    def check_update(self):
        """Report whether there is an update available"""
        if not self._target_repo:
            return False
        try:
            self.ydl.to_screen((
                f'Available version: {self._label(self.target_channel, self.latest_version)}, ' if self.target_tag == 'latest' else ''
            ) + f'Current version: {self._label(CHANNEL, self.current_version)}')
        except network_exceptions as e:
            return self._report_network_error(f'obtain version info ({e})', delim='; Please try again later or')

        if not is_non_updateable():
            self.ydl.to_screen(f'Current Build Hash: {_sha256_file(self.filename)}')

        if self.has_update:
            return True

        if self.target_tag == self._tag:
            self.ydl.to_screen(f'yt-dlp is up to date ({self._label(CHANNEL, self.current_version)})')
        elif not self._exact:
            self.ydl.report_warning('yt-dlp cannot be updated any further since you are on an older Python version')
        return False

    def update(self):
        """Update yt-dlp executable to the latest version"""
        if not self.check_update():
            return
        err = is_non_updateable()
        if err:
            return self._report_error(err, True)
        self.ydl.to_screen(f'Updating to {self._label(self.target_channel, self.new_version)} ...')
        if (_VERSION_RE.fullmatch(self.target_tag[5:])
                and version_tuple(self.target_tag[5:]) < (2023, 3, 2)):
            self.ydl.report_warning('You are downgrading to a version without --update-to')
            self._block_restart('Cannot automatically restart to a version without --update-to')

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
            newcontent = self._download(self.release_name, self._tag)
        except network_exceptions as e:
            if isinstance(e, urllib.error.HTTPError) and e.code == 404:
                return self._report_error(
                    f'The requested tag {self._label(self.target_channel, self.target_tag)} does not exist', True)
            return self._report_network_error(f'fetch updates: {e}')

        try:
            expected_hash = self.release_hash
        except Exception:
            self.ydl.report_warning('no hash information found for the release')
        else:
            if hashlib.sha256(newcontent).hexdigest() != expected_hash:
                return self._report_network_error('verify the new executable')

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
        if variant.startswith('win') or variant == 'py2exe':
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
                    f'Unable to set permissions. Run: sudo chmod a+rx {compat_shlex_quote(self.filename)}')

        self.ydl.to_screen(f'Updated yt-dlp to {self._label(self.target_channel, self.new_version)}')
        return True

    @functools.cached_property
    def cmd(self):
        """The command-line to run the executable, if known"""
        # There is no sys.orig_argv in py < 3.10. Also, it can be [] when frozen
        if getattr(sys, 'orig_argv', None):
            return sys.orig_argv
        elif getattr(sys, 'frozen', False):
            return sys.argv

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


def run_update(ydl):
    """Update the program file with the latest version from the repository
    @returns    Whether there was a successful update (No update = False)
    """
    return Updater(ydl).update()


# Deprecated
def update_self(to_screen, verbose, opener):
    import traceback

    deprecation_warning(f'"{__name__}.update_self" is deprecated and may be removed '
                        f'in a future version. Use "{__name__}.run_update(ydl)" instead')

    printfn = to_screen

    class FakeYDL():
        to_screen = printfn

        def report_warning(self, msg, *args, **kwargs):
            return printfn(f'WARNING: {msg}', *args, **kwargs)

        def report_error(self, msg, tb=None):
            printfn(f'ERROR: {msg}')
            if not verbose:
                return
            if tb is None:
                # Copied from YoutubeDL.trouble
                if sys.exc_info()[0]:
                    tb = ''
                    if hasattr(sys.exc_info()[1], 'exc_info') and sys.exc_info()[1].exc_info[0]:
                        tb += ''.join(traceback.format_exception(*sys.exc_info()[1].exc_info))
                    tb += traceback.format_exc()
                else:
                    tb_data = traceback.format_list(traceback.extract_stack())
                    tb = ''.join(tb_data)
            if tb:
                printfn(tb)

        def write_debug(self, msg, *args, **kwargs):
            printfn(f'[debug] {msg}', *args, **kwargs)

        def urlopen(self, url):
            return opener.open(url)

    return run_update(FakeYDL())


__all__ = ['Updater']
