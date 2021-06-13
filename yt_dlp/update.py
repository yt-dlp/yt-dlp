from __future__ import unicode_literals

import hashlib
import json
import os
import platform
import subprocess
import sys
import traceback
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
    ''' Exists for backward compatibility. Use run_update(ydl) instead '''

    printfn = to_screen

    class FakeYDL():
        _opener = opener
        to_screen = printfn

        @staticmethod
        def report_warning(msg, *args, **kwargs):
            return printfn('WARNING: %s' % msg, *args, **kwargs)

        @staticmethod
        def report_error(msg, tb=None):
            printfn('ERROR: %s' % msg)
            if not verbose:
                return
            if tb is None:
                # Copied from YoutubeDl.trouble
                if sys.exc_info()[0]:
                    tb = ''
                    if hasattr(sys.exc_info()[1], 'exc_info') and sys.exc_info()[1].exc_info[0]:
                        tb += ''.join(traceback.format_exception(*sys.exc_info()[1].exc_info))
                    tb += encode_compat_str(traceback.format_exc())
                else:
                    tb_data = traceback.format_list(traceback.extract_stack())
                    tb = ''.join(tb_data)
            if tb:
                printfn(tb)

    return run_update(FakeYDL())


def run_update(ydl):
    """
    Update the program file with the latest version from the repository
    Returns whether the program should terminate
    """

    JSON_URL = 'https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest'

    def report_error(msg, network=False, expected=False, delim=';'):
        if network:
            msg += '%s Visit  https://github.com/yt-dlp/yt-dlp/releases/latest' % delim
        ydl.report_error(msg, tb='' if network or expected else None)

    def calc_sha256sum(path):
        h = hashlib.sha256()
        b = bytearray(128 * 1024)
        mv = memoryview(b)
        with open(os.path.realpath(path), 'rb', buffering=0) as f:
            for n in iter(lambda: f.readinto(mv), 0):
                h.update(mv[:n])
        return h.hexdigest()

    err = None
    if isinstance(globals().get('__loader__'), zipimporter):
        pass
    elif hasattr(sys, 'frozen'):
        pass
    else:
        err = 'It looks like you installed yt-dlp with a package manager, pip, setup.py or a tarball. Please use that to update'
    if err:
        return report_error(err, expected=True)

    # sys.executable is set to the full pathname of the exe-file for py2exe
    # though symlinks are not followed so that we need to do this manually
    # with help of realpath
    filename = compat_realpath(sys.executable if hasattr(sys, 'frozen') else sys.argv[0])
    ydl.to_screen('Current Build Hash %s' % calc_sha256sum(filename))

    # Download and check versions info
    try:
        version_info = ydl._opener.open(JSON_URL).read().decode('utf-8')
        version_info = json.loads(version_info)
    except Exception:
        return report_error('can\'t obtain versions info. Please try again later ', True, delim='or')

    def version_tuple(version_str):
        return tuple(map(int, version_str.split('.')))

    version_id = version_info['tag_name']
    if version_tuple(__version__) >= version_tuple(version_id):
        ydl.to_screen('yt-dlp is up to date (%s)' % __version__)
        return

    ydl.to_screen('Updating to version ' + version_id + ' ...')

    version_labels = {
        'zip_3': '',
        'exe_64': '.exe',
        'exe_32': '_x86.exe',
    }

    def get_bin_info(bin_or_exe, version):
        label = version_labels['%s_%s' % (bin_or_exe, version)]
        return next((i for i in version_info['assets'] if i['name'] == 'yt-dlp%s' % label), {})

    def get_sha256sum(bin_or_exe, version):
        filename = 'yt-dlp%s' % version_labels['%s_%s' % (bin_or_exe, version)]
        urlh = next(
            (i for i in version_info['assets'] if i['name'] in ('SHA2-256SUMS')),
            {}).get('browser_download_url')
        if not urlh:
            return None
        hash_data = ydl._opener.open(urlh).read().decode('utf-8')
        if hash_data.startswith('version:'):
            # Old colon-separated hash file
            return dict(ln.split(':') for ln in hash_data.splitlines()).get(filename)
        else:
            # GNU-style hash file
            return dict(ln.split()[::-1] for ln in hash_data.splitlines()).get(filename)

    if not os.access(filename, os.W_OK):
        return report_error('no write permissions on %s' % filename, expected=True)

    # PyInstaller
    if hasattr(sys, 'frozen'):
        exe = filename
        directory = os.path.dirname(exe)
        if not os.access(directory, os.W_OK):
            return report_error('no write permissions on %s' % directory, expected=True)
        try:
            if os.path.exists(filename + '.old'):
                os.remove(filename + '.old')
        except (IOError, OSError):
            return report_error('unable to remove the old version')

        try:
            arch = platform.architecture()[0][:2]
            url = get_bin_info('exe', arch).get('browser_download_url')
            if not url:
                return report_error('unable to fetch updates', True)
            urlh = ydl._opener.open(url)
            newcontent = urlh.read()
            urlh.close()
        except (IOError, OSError, StopIteration):
            return report_error('unable to download latest version', True)

        try:
            with open(exe + '.new', 'wb') as outf:
                outf.write(newcontent)
        except (IOError, OSError):
            return report_error('unable to write the new version')

        expected_sum = get_sha256sum('exe', arch)
        if not expected_sum:
            ydl.report_warning('no hash information found for the release')
        elif calc_sha256sum(exe + '.new') != expected_sum:
            report_error('unable to verify the new executable', True)
            try:
                os.remove(exe + '.new')
            except OSError:
                return report_error('unable to remove corrupt download')

        try:
            os.rename(exe, exe + '.old')
        except (IOError, OSError):
            return report_error('unable to move current version')
        try:
            os.rename(exe + '.new', exe)
        except (IOError, OSError):
            report_error('unable to overwrite current version')
            os.rename(exe + '.old', exe)
            return
        try:
            # Continues to run in the background
            subprocess.Popen(
                'ping 127.0.0.1 -n 5 -w 1000 & del /F "%s.old"' % exe,
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ydl.to_screen('Updated yt-dlp to version %s' % version_id)
            return True  # Exit app
        except OSError:
            report_error('unable to delete old version')

    # Zip unix package
    elif isinstance(globals().get('__loader__'), zipimporter):
        try:
            url = get_bin_info('zip', '3').get('browser_download_url')
            if not url:
                return report_error('unable to fetch updates', True)
            urlh = ydl._opener.open(url)
            newcontent = urlh.read()
            urlh.close()
        except (IOError, OSError, StopIteration):
            return report_error('unable to download latest version', True)

        expected_sum = get_sha256sum('zip', '3')
        if not expected_sum:
            ydl.report_warning('no hash information found for the release')
        elif hashlib.sha256(newcontent).hexdigest() != expected_sum:
            return report_error('unable to verify the new zip', True)

        try:
            with open(filename, 'wb') as outf:
                outf.write(newcontent)
        except (IOError, OSError):
            return report_error('unable to overwrite current version')

    ydl.to_screen('Updated yt-dlp to version %s; Restart yt-dlp to use the new version' % version_id)


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
