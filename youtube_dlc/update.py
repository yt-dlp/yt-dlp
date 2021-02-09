from __future__ import unicode_literals

import io
import json
import traceback
import hashlib
import os
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
    """Update the program file with the latest version from the repository"""

    JSON_URL = 'https://api.github.com/repos/pukkandan/yt-dlp/releases/latest'

    def sha256sum():
        h = hashlib.sha256()
        b = bytearray(128 * 1024)
        mv = memoryview(b)
        with open(os.path.realpath(sys.executable), 'rb', buffering=0) as f:
            for n in iter(lambda: f.readinto(mv), 0):
                h.update(mv[:n])
        return h.hexdigest()

    to_screen('Current Build Hash %s' % sha256sum())

    if not isinstance(globals().get('__loader__'), zipimporter) and not hasattr(sys, 'frozen'):
        to_screen('It looks like you installed youtube-dlc with a package manager, pip, setup.py or a tarball. Please use that to update.')
        return

    # Download and check versions info
    try:
        version_info = opener.open(JSON_URL).read().decode('utf-8')
        version_info = json.loads(version_info)
    except Exception:
        if verbose:
            to_screen(encode_compat_str(traceback.format_exc()))
        to_screen('ERROR: can\'t obtain versions info. Please try again later.')
        to_screen('Visit https://github.com/pukkandan/yt-dlp/releases/lastest')
        return

    version_id = version_info['tag_name']
    if version_id == __version__:
        to_screen('youtube-dlc is up-to-date (' + __version__ + ')')
        return

    def version_tuple(version_str):
        return tuple(map(int, version_str.split('.')))

    if version_tuple(__version__) >= version_tuple(version_id):
        to_screen('youtube-dlc is up to date (%s)' % __version__)
        return

    to_screen('Updating to version ' + version_id + ' ...')

    version = {
        'bin': next(i for i in version_info['assets'] if i['name'] == 'youtube-dlc'),
        'exe': next(i for i in version_info['assets'] if i['name'] == 'youtube-dlc.exe'),
        'exe_x86': next(i for i in version_info['assets'] if i['name'] == 'youtube-dlc_x86.exe'),
    }

    # sys.executable is set to the full pathname of the exe-file for py2exe
    # though symlinks are not followed so that we need to do this manually
    # with help of realpath
    filename = compat_realpath(sys.executable if hasattr(sys, 'frozen') else sys.argv[0])

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
            urlh = opener.open(version['exe']['browser_download_url'])
            newcontent = urlh.read()
            urlh.close()
        except (IOError, OSError):
            if verbose:
                to_screen(encode_compat_str(traceback.format_exc()))
            to_screen('ERROR: unable to download latest version')
            to_screen('Visit https://github.com/pukkandan/yt-dlp/releases/lastest')
            return

        try:
            with open(exe + '.new', 'wb') as outf:
                outf.write(newcontent)
        except (IOError, OSError):
            if verbose:
                to_screen(encode_compat_str(traceback.format_exc()))
            to_screen('ERROR: unable to write the new version')
            return

        try:
            bat = os.path.join(directory, 'yt-dlp-updater.cmd')
            with io.open(bat, 'w') as batfile:
                batfile.write('''
@(
    echo.Waiting for file handle to be closed ...
    ping 127.0.0.1 -n 5 -w 1000 > NUL
    move /Y "%s.new" "%s" > NUL
    echo.Updated youtube-dlc to version %s.
)
@start /b "" cmd /c del "%%~f0"&exit /b
                ''' % (exe, exe, version_id))

            subprocess.Popen([bat])  # Continues to run in the background
            return  # Do not show premature success messages
        except (IOError, OSError):
            if verbose:
                to_screen(encode_compat_str(traceback.format_exc()))
            to_screen('ERROR: unable to overwrite current version')
            return

    # Zip unix package
    elif isinstance(globals().get('__loader__'), zipimporter):
        try:
            urlh = opener.open(version['bin']['browser_download_url'])
            newcontent = urlh.read()
            urlh.close()
        except (IOError, OSError):
            if verbose:
                to_screen(encode_compat_str(traceback.format_exc()))
            to_screen('ERROR: unable to download latest version')
            to_screen('Visit https://github.com/pukkandan/yt-dlp/releases/lastest')
            return

        try:
            with open(filename, 'wb') as outf:
                outf.write(newcontent)
        except (IOError, OSError):
            if verbose:
                to_screen(encode_compat_str(traceback.format_exc()))
            to_screen('ERROR: unable to overwrite current version')
            return

    to_screen('Updated youtube-dlc. Restart youtube-dlc to use the new version.')


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
