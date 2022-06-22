import atexit
import hashlib
import json
import os
import platform
import subprocess
import sys
from zipimport import zipimporter

from .compat import functools  # isort: split
from .compat import compat_realpath
from .utils import Popen, shell_quote, traverse_obj, version_tuple
from .version import __version__

REPOSITORY = 'yt-dlp/yt-dlp'
API_URL = f'https://api.github.com/repos/{REPOSITORY}/releases/latest'


@functools.cache
def _get_variant_and_executable_path():
    """@returns (variant, executable_path)"""
    if hasattr(sys, 'frozen'):
        path = sys.executable
        if not hasattr(sys, '_MEIPASS'):
            return 'py2exe', path
        if sys._MEIPASS == os.path.dirname(path):
            return f'{sys.platform}_dir', path
        return f'{sys.platform}_exe', path

    path = os.path.dirname(__file__)
    if isinstance(__loader__, zipimporter):
        return 'zip', os.path.join(path, '..')
    elif (os.path.basename(sys.argv[0]) in ('__main__.py', '-m')
          and os.path.exists(os.path.join(path, '../.git/HEAD'))):
        return 'source', path
    return 'unknown', path


def detect_variant():
    return _get_variant_and_executable_path()[0]


_FILE_SUFFIXES = {
    'zip': '',
    'py2exe': '_min.exe',
    'win32_exe': '.exe',
    'darwin_exe': '_macos',
    'linux_exe': '_linux',
}

_NON_UPDATEABLE_REASONS = {
    **{variant: None for variant in _FILE_SUFFIXES},  # Updatable
    **{variant: f'Auto-update is not supported for unpackaged {name} executable; Re-download the latest release'
       for variant, name in {'win32_dir': 'Windows', 'darwin_dir': 'MacOS', 'linux_dir': 'Linux'}.items()},
    'source': 'You cannot update when running from source code; Use git to pull the latest changes',
    'unknown': 'It looks like you installed yt-dlp with a package manager, pip or setup.py; Use that to update',
    'other': 'It looks like you are using an unofficial build of yt-dlp; Build the executable again',
}


def is_non_updateable():
    return _NON_UPDATEABLE_REASONS.get(detect_variant(), _NON_UPDATEABLE_REASONS['other'])


def _sha256_file(path):
    h = hashlib.sha256()
    mv = memoryview(bytearray(128 * 1024))
    with open(os.path.realpath(path), 'rb', buffering=0) as f:
        for n in iter(lambda: f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()


class Updater:
    def __init__(self, ydl):
        self.ydl = ydl

    @functools.cached_property
    def _new_version_info(self):
        self.ydl.write_debug(f'Fetching release info: {API_URL}')
        return json.loads(self.ydl.urlopen(API_URL).read().decode())

    @property
    def current_version(self):
        """Current version"""
        return __version__

    @property
    def new_version(self):
        """Version of the latest release"""
        return self._new_version_info['tag_name']

    @property
    def has_update(self):
        """Whether there is an update available"""
        return version_tuple(__version__) < version_tuple(self.new_version)

    @functools.cached_property
    def filename(self):
        """Filename of the executable"""
        return compat_realpath(_get_variant_and_executable_path()[1])

    def _download(self, name=None):
        name = name or self.release_name
        url = traverse_obj(self._new_version_info, (
            'assets', lambda _, v: v['name'] == name, 'browser_download_url'), get_all=False)
        if not url:
            raise Exception('Unable to find download URL')
        self.ydl.write_debug(f'Downloading {name} from {url}')
        return self.ydl.urlopen(url).read()

    @functools.cached_property
    def release_name(self):
        """The release filename"""
        label = _FILE_SUFFIXES[detect_variant()]
        if label and platform.architecture()[0][:2] == '32':
            label = f'_x86{label}'
        return f'yt-dlp{label}'

    @functools.cached_property
    def release_hash(self):
        """Hash of the latest release"""
        hash_data = dict(ln.split()[::-1] for ln in self._download('SHA2-256SUMS').decode().splitlines())
        return hash_data[self.release_name]

    def _report_error(self, msg, expected=False):
        self.ydl.report_error(msg, tb=False if expected else None)

    def _report_permission_error(self, file):
        self._report_error(f'Unable to write to {file}; Try running as administrator', True)

    def _report_network_error(self, action, delim=';'):
        self._report_error(f'Unable to {action}{delim} Visit  https://github.com/{REPOSITORY}/releases/latest', True)

    def check_update(self):
        """Report whether there is an update available"""
        try:
            self.ydl.to_screen(
                f'Latest version: {self.new_version}, Current version: {self.current_version}')
        except Exception:
            return self._report_network_error('obtain version info', delim='; Please try again later or')

        if not self.has_update:
            return self.ydl.to_screen(f'yt-dlp is up to date ({__version__})')

        if not is_non_updateable():
            self.ydl.to_screen(f'Current Build Hash {_sha256_file(self.filename)}')
        return True

    def update(self):
        """Update yt-dlp executable to the latest version"""
        if not self.check_update():
            return
        err = is_non_updateable()
        if err:
            return self._report_error(err, True)
        self.ydl.to_screen(f'Updating to version {self.new_version} ...')

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
            newcontent = self._download()
        except OSError:
            return self._report_network_error('download latest version')
        except Exception:
            return self._report_network_error('fetch updates')

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

        try:
            if old_filename:
                os.rename(self.filename, old_filename)
        except OSError:
            return self._report_error('Unable to move current version')
        try:
            if old_filename:
                os.rename(new_filename, self.filename)
        except OSError:
            self._report_error('Unable to overwrite current version')
            return os.rename(old_filename, self.filename)

        if detect_variant() not in ('win32_exe', 'py2exe'):
            if old_filename:
                os.remove(old_filename)
        else:
            atexit.register(Popen, f'ping 127.0.0.1 -n 5 -w 1000 & del /F "{old_filename}"',
                            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        self.ydl.to_screen(f'Updated yt-dlp to version {self.new_version}')
        return True

    @functools.cached_property
    def cmd(self):
        """The command-line to run the executable, if known"""
        # There is no sys.orig_argv in py < 3.10. Also, it can be [] when frozen
        if getattr(sys, 'orig_argv', None):
            return sys.orig_argv
        elif hasattr(sys, 'frozen'):
            return sys.argv

    def restart(self):
        """Restart the executable"""
        assert self.cmd, 'Must be frozen or Py >= 3.10'
        self.ydl.write_debug(f'Restarting: {shell_quote(self.cmd)}')
        _, _, returncode = Popen.run(self.cmd)
        return returncode


def run_update(ydl):
    """Update the program file with the latest version from the repository
    @returns    Whether there was a successfull update (No update = False)
    """
    return Updater(ydl).update()


# Deprecated
def update_self(to_screen, verbose, opener):
    import traceback

    from .utils import write_string

    write_string(
        'DeprecationWarning: "yt_dlp.update.update_self" is deprecated and may be removed in a future version. '
        'Use "yt_dlp.update.run_update(ydl)" instead\n')

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
