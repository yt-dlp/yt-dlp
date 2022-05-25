import hashlib
import json
import os
import platform
import subprocess
import sys
from zipimport import zipimporter

from .compat import functools  # isort: split
from .compat import compat_realpath
from .utils import Popen, traverse_obj, version_tuple
from .version import __version__


RELEASE_JSON_URL = 'https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest'


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
    elif os.path.basename(sys.argv[0]) == '__main__.py':
        return 'source', path
    return 'unknown', path


def detect_variant():
    return _get_variant_and_executable_path()[0]


_FILE_SUFFIXES = {
    'zip': '',
    'py2exe': '_min.exe',
    'win32_exe': '.exe',
    'darwin_exe': '_macos',
}

_NON_UPDATEABLE_REASONS = {
    **{variant: None for variant in _FILE_SUFFIXES},  # Updatable
    **{variant: f'Auto-update is not supported for unpackaged {name} executable; Re-download the latest release'
       for variant, name in {'win32_dir': 'Windows', 'darwin_dir': 'MacOS'}.items()},
    'source': 'You cannot update when running from source code; Use git to pull the latest changes',
    'unknown': 'It looks like you installed yt-dlp with a package manager, pip or setup.py; Use that to update',
    'other': 'It looks like you are using an unofficial build of yt-dlp; Build the executable again',
}


def is_non_updateable():
    return _NON_UPDATEABLE_REASONS.get(detect_variant(), _NON_UPDATEABLE_REASONS['other'])


def run_update(ydl):
    """
    Update the program file with the latest version from the repository
    Returns whether the program should terminate
    """

    def report_error(msg, expected=False):
        ydl.report_error(msg, tb=False if expected else None)

    def report_unable(action, expected=False):
        report_error(f'Unable to {action}', expected)

    def report_permission_error(file):
        report_unable(f'write to {file}; Try running as administrator', True)

    def report_network_error(action, delim=';'):
        report_unable(f'{action}{delim} Visit  https://github.com/yt-dlp/yt-dlp/releases/latest', True)

    def calc_sha256sum(path):
        h = hashlib.sha256()
        mv = memoryview(bytearray(128 * 1024))
        with open(os.path.realpath(path), 'rb', buffering=0) as f:
            for n in iter(lambda: f.readinto(mv), 0):
                h.update(mv[:n])
        return h.hexdigest()

    try:
        version_info = json.loads(ydl.urlopen(RELEASE_JSON_URL).read().decode())
    except Exception:
        return report_network_error('obtain version info', delim='; Please try again later or')

    version_id = version_info['tag_name']
    ydl.to_screen(f'Latest version: {version_id}, Current version: {__version__}')
    if version_tuple(__version__) >= version_tuple(version_id):
        ydl.to_screen(f'yt-dlp is up to date ({__version__})')
        return

    err = is_non_updateable()
    if err:
        return report_error(err, True)

    variant, filename = _get_variant_and_executable_path()
    filename = compat_realpath(filename)  # Absolute path, following symlinks

    label = _FILE_SUFFIXES[variant]
    if label and platform.architecture()[0][:2] == '32':
        label = f'_x86{label}'
    release_name = f'yt-dlp{label}'

    ydl.to_screen(f'Current Build Hash {calc_sha256sum(filename)}')
    ydl.to_screen(f'Updating to version {version_id} ...')

    def get_file(name, fatal=True):
        error = report_network_error if fatal else lambda _: None
        url = traverse_obj(
            version_info, ('assets', lambda _, v: v['name'] == name, 'browser_download_url'), get_all=False)
        if not url:
            return error('fetch updates')
        try:
            return ydl.urlopen(url).read()
        except OSError:
            return error('download latest version')

    def verify(content):
        if not content:
            return False
        hash_data = get_file('SHA2-256SUMS', fatal=False) or b''
        expected = dict(ln.split()[::-1] for ln in hash_data.decode().splitlines()).get(release_name)
        if not expected:
            ydl.report_warning('no hash information found for the release')
        elif hashlib.sha256(content).hexdigest() != expected:
            return report_network_error('verify the new executable')
        return True

    directory = os.path.dirname(filename)
    if not os.access(filename, os.W_OK):
        return report_permission_error(filename)
    elif not os.access(directory, os.W_OK):
        return report_permission_error(directory)

    new_filename, old_filename = f'{filename}.new', f'{filename}.old'
    if variant == 'zip':  # Can be replaced in-place
        new_filename, old_filename = filename, None

    try:
        if os.path.exists(old_filename or ''):
            os.remove(old_filename)
    except OSError:
        return report_unable('remove the old version')

    newcontent = get_file(release_name)
    if not verify(newcontent):
        return
    try:
        with open(new_filename, 'wb') as outf:
            outf.write(newcontent)
    except OSError:
        return report_permission_error(new_filename)

    try:
        if old_filename:
            os.rename(filename, old_filename)
    except OSError:
        return report_unable('move current version')
    try:
        if old_filename:
            os.rename(new_filename, filename)
    except OSError:
        report_unable('overwrite current version')
        os.rename(old_filename, filename)
        return

    if variant not in ('win32_exe', 'py2exe'):
        if old_filename:
            os.remove(old_filename)
        ydl.to_screen(f'Updated yt-dlp to version {version_id}; Restart yt-dlp to use the new version')
        return

    try:
        # Continues to run in the background
        Popen(f'ping 127.0.0.1 -n 5 -w 1000 & del /F "{old_filename}"',
              shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ydl.to_screen(f'Updated yt-dlp to version {version_id}')
        return True  # Exit app
    except OSError:
        report_unable('delete the old version')


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

        @staticmethod
        def report_warning(msg, *args, **kwargs):
            return printfn(f'WARNING: {msg}', *args, **kwargs)

        @staticmethod
        def report_error(msg, tb=None):
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

        def urlopen(self, url):
            return opener.open(url)

    return run_update(FakeYDL())
