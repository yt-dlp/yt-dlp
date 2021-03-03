from __future__ import unicode_literals

import io
import json
import traceback
import hashlib
import os
import platform
import subprocess
import sys
from zipimport import zipimporter

from .compat import compat_realpath
from .utils import encode_compat_str

from .version import __version__


'''  # Not signed
def rsa_verify(message, signature, key):
    from hashlib import sha256
    assert isinstance(message, bytes)
    byte_size = (len(bin(key[0])) - 2 + 8 - 1) // 8
    signature = ('%x' % pow(int(signature, 16), key[1], key[0])).encode()
    signature = (byte_size * 2 - len(signature)) * b'0' + signature
    asn1 = b'3031300d060960864801650304020105000420'
    asn1 += sha256(message).hexdigest().encode()
    if byte_size < len(asn1) // 2 + 11:
        return False
    expected = b'0001' + (byte_size - len(asn1) // 2 - 3) * b'ff' + b'00' + asn1
    return expected == signature
'''


def update_self(to_screen, verbose, opener):
    """
    Update the program file with the latest version from the repository
    Returns whether the program should terminate
    """

    JSON_URL = 'https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest'

    def calc_sha256sum(path):
        h = hashlib.sha256()
        b = bytearray(128 * 1024)
        mv = memoryview(b)
        with open(os.path.realpath(path), 'rb', buffering=0) as f:
            for n in iter(lambda: f.readinto(mv), 0):
                h.update(mv[:n])
        return h.hexdigest()

    if not isinstance(globals().get('__loader__'), zipimporter) and not hasattr(sys, 'frozen'):
        to_screen('It looks like you installed yt-dlp with a package manager, pip, setup.py or a tarball. Please use that to update.')
        return

    # sys.executable is set to the full pathname of the exe-file for py2exe
    # though symlinks are not followed so that we need to do this manually
    # with help of realpath
    filename = compat_realpath(sys.executable if hasattr(sys, 'frozen') else sys.argv[0])
    to_screen('Current Build Hash %s' % calc_sha256sum(filename))

    # Download and check versions info
    try:
        version_info = opener.open(JSON_URL).read().decode('utf-8')
        version_info = json.loads(version_info)
    except Exception:
        if verbose:
            to_screen(encode_compat_str(traceback.format_exc()))
        to_screen('ERROR: can\'t obtain versions info. Please try again later.')
        to_screen('Visit https://github.com/yt-dlp/yt-dlp/releases/latest')
        return

    def version_tuple(version_str):
        return tuple(map(int, version_str.split('.')))

    version_id = version_info['tag_name']
    if version_tuple(__version__) >= version_tuple(version_id):
        to_screen('yt-dlp is up to date (%s)' % __version__)
        return

    to_screen('Updating to version ' + version_id + ' ...')

    version_labels = {
        'zip_3': '',
        'zip_2': '',
        # 'zip_2': '_py2',
        'exe_64': '.exe',
        'exe_32': '_x86.exe',
    }

    def get_bin_info(bin_or_exe, version):
        label = version_labels['%s_%s' % (bin_or_exe, version)]
        return next(
            (i for i in version_info['assets'] if i['name'] == 'yt-dlp%s' % label),
            {})

    def get_sha256sum(bin_or_exe, version):
        label = version_labels['%s_%s' % (bin_or_exe, version)]
        urlh = next(
            (i for i in version_info['assets']
                if i['name'] in ('SHA2-256SUMS')), {}).get('browser_download_url')
        if not urlh:
            return None
        hash_data = opener.open(urlh).read().decode('utf-8')
        hashes = list(map(lambda x: x.split(':'), hash_data.splitlines()))
        return next(
            (i[1] for i in hashes if i[0] == 'yt-dlp%s' % label),
            None)

    if not os.access(filename, os.W_OK):
        to_screen('ERROR: no write permissions on %s' % filename)
        return

    # PyInstaller
    if hasattr(sys, 'frozen'):
        exe = filename
        directory = os.path.dirname(exe)
        if not os.access(directory, os.W_OK):
            to_screen('ERROR: no write permissions on %s' % directory)
            return

        try:
            arch = platform.architecture()[0][:2]
            url = get_bin_info('exe', arch).get('browser_download_url')
            if not url:
                to_screen('ERROR: unable to fetch updates')
                to_screen('Visit https://github.com/yt-dlp/yt-dlp/releases/latest')
                return
            urlh = opener.open(url)
            newcontent = urlh.read()
            urlh.close()
        except (IOError, OSError, StopIteration):
            if verbose:
                to_screen(encode_compat_str(traceback.format_exc()))
            to_screen('ERROR: unable to download latest version')
            to_screen('Visit https://github.com/yt-dlp/yt-dlp/releases/latest')
            return

        try:
            with open(exe + '.new', 'wb') as outf:
                outf.write(newcontent)
        except (IOError, OSError):
            if verbose:
                to_screen(encode_compat_str(traceback.format_exc()))
            to_screen('ERROR: unable to write the new version')
            return

        expected_sum = get_sha256sum('exe', arch)
        if not expected_sum:
            to_screen('WARNING: no hash information found for the release')
        elif calc_sha256sum(exe + '.new') != expected_sum:
            to_screen('ERROR: unable to verify the new executable')
            to_screen('Visit https://github.com/yt-dlp/yt-dlp/releases/latest')
            try:
                os.remove(exe + '.new')
            except OSError:
                to_screen('ERROR: unable to remove corrupt download')
            return

        try:
            bat = os.path.join(directory, 'yt-dlp-updater.cmd')
            with io.open(bat, 'w') as batfile:
                batfile.write('''
@(
    echo.Waiting for file handle to be closed ...
    ping 127.0.0.1 -n 5 -w 1000 > NUL
    move /Y "%s.new" "%s" > NUL
    echo.Updated yt-dlp to version %s.
)
@start /b "" cmd /c del "%%~f0"&exit /b
                ''' % (exe, exe, version_id))

            subprocess.Popen([bat])  # Continues to run in the background
            return True  # Exit app
        except (IOError, OSError):
            if verbose:
                to_screen(encode_compat_str(traceback.format_exc()))
            to_screen('ERROR: unable to overwrite current version')
            return

    # Zip unix package
    elif isinstance(globals().get('__loader__'), zipimporter):
        try:
            py_ver = platform.python_version()[0]
            url = get_bin_info('zip', py_ver).get('browser_download_url')
            if not url:
                to_screen('ERROR: unable to fetch updates')
                to_screen('Visit https://github.com/yt-dlp/yt-dlp/releases/latest')
                return
            urlh = opener.open(url)
            newcontent = urlh.read()
            urlh.close()
        except (IOError, OSError, StopIteration):
            if verbose:
                to_screen(encode_compat_str(traceback.format_exc()))
            to_screen('ERROR: unable to download latest version')
            to_screen('Visit https://github.com/yt-dlp/yt-dlp/releases/latest')
            return

        expected_sum = get_sha256sum('zip', py_ver)
        if expected_sum and hashlib.sha256(newcontent).hexdigest() != expected_sum:
            to_screen('ERROR: unable to verify the new zip')
            to_screen('Visit https://github.com/yt-dlp/yt-dlp/releases/latest')
            return

        try:
            with open(filename, 'wb') as outf:
                outf.write(newcontent)
        except (IOError, OSError):
            if verbose:
                to_screen(encode_compat_str(traceback.format_exc()))
            to_screen('ERROR: unable to overwrite current version')
            return

    to_screen('Updated yt-dlp. Restart yt-dlp to use the new version.')


'''  # UNUSED
def get_notes(versions, fromVersion):
    notes = []
    for v, vdata in sorted(versions.items()):
        if v > fromVersion:
            notes.extend(vdata.get('notes', []))
    return notes


def print_notes(to_screen, versions, fromVersion=__version__):
    notes = get_notes(versions, fromVersion)
    if notes:
        to_screen('PLEASE NOTE:')
        for note in notes:
            to_screen(note)
'''
