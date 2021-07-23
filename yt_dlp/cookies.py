import ctypes
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from hashlib import pbkdf2_hmac

from yt_dlp.aes import aes_cbc_decrypt
from yt_dlp.compat import (
    compat_b64decode,
    compat_cookiejar_Cookie,
)
from yt_dlp.utils import (
    bug_reports_message,
    bytes_to_intlist,
    expand_path,
    intlist_to_bytes,
    process_communicate_or_kill,
    YoutubeDLCookieJar,
)

try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    # although sqlite3 is part of the standard library, it is possible to compile python without
    # sqlite support. See: https://github.com/yt-dlp/yt-dlp/issues/544
    SQLITE_AVAILABLE = False


try:
    from Crypto.Cipher import AES
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

try:
    import keyring
    KEYRING_AVAILABLE = True
    KEYRING_UNAVAILABLE_REASON = f'due to unknown reasons{bug_reports_message()}'
except ImportError:
    KEYRING_AVAILABLE = False
    KEYRING_UNAVAILABLE_REASON = (
        'as the `keyring` module is not installed. '
        'Please install by running `python3 -m pip install keyring`. '
        'Depending on your platform, additional packages may be required '
        'to access the keyring; see  https://pypi.org/project/keyring')
except Exception as _err:
    KEYRING_AVAILABLE = False
    KEYRING_UNAVAILABLE_REASON = 'as the `keyring` module could not be initialized: %s' % _err


CHROMIUM_BASED_BROWSERS = {'brave', 'chrome', 'chromium', 'edge', 'opera', 'vivaldi'}
SUPPORTED_BROWSERS = CHROMIUM_BASED_BROWSERS | {'firefox', 'safari'}


class YDLLogger:
    def __init__(self, ydl=None):
        self._ydl = ydl

    def debug(self, message):
        if self._ydl:
            self._ydl.write_debug(message)

    def info(self, message):
        if self._ydl:
            self._ydl.to_screen(f'[Cookies] {message}')

    def warning(self, message, only_once=False):
        if self._ydl:
            self._ydl.report_warning(message, only_once)

    def error(self, message):
        if self._ydl:
            self._ydl.report_error(message)


def load_cookies(cookie_file, browser_specification, ydl):
    cookie_jars = []
    if browser_specification is not None:
        browser_name, profile = _parse_browser_specification(*browser_specification)
        cookie_jars.append(extract_cookies_from_browser(browser_name, profile, YDLLogger(ydl)))

    if cookie_file is not None:
        cookie_file = expand_path(cookie_file)
        jar = YoutubeDLCookieJar(cookie_file)
        if os.access(cookie_file, os.R_OK):
            jar.load(ignore_discard=True, ignore_expires=True)
        cookie_jars.append(jar)

    return _merge_cookie_jars(cookie_jars)


def extract_cookies_from_browser(browser_name, profile=None, logger=YDLLogger()):
    if browser_name == 'firefox':
        return _extract_firefox_cookies(profile, logger)
    elif browser_name == 'safari':
        return _extract_safari_cookies(profile, logger)
    elif browser_name in CHROMIUM_BASED_BROWSERS:
        return _extract_chrome_cookies(browser_name, profile, logger)
    else:
        raise ValueError('unknown browser: {}'.format(browser_name))


def _extract_firefox_cookies(profile, logger):
    logger.info('Extracting cookies from firefox')
    if not SQLITE_AVAILABLE:
        logger.warning('Cannot extract cookies from firefox without sqlite3 support. '
                       'Please use a python interpreter compiled with sqlite3 support')
        return YoutubeDLCookieJar()

    if profile is None:
        search_root = _firefox_browser_dir()
    elif _is_path(profile):
        search_root = profile
    else:
        search_root = os.path.join(_firefox_browser_dir(), profile)

    cookie_database_path = _find_most_recently_used_file(search_root, 'cookies.sqlite')
    if cookie_database_path is None:
        raise FileNotFoundError('could not find firefox cookies database in {}'.format(search_root))
    logger.debug('extracting from: "{}"'.format(cookie_database_path))

    with tempfile.TemporaryDirectory(prefix='youtube_dl') as tmpdir:
        cursor = None
        try:
            cursor = _open_database_copy(cookie_database_path, tmpdir)
            cursor.execute('SELECT host, name, value, path, expiry, isSecure FROM moz_cookies')
            jar = YoutubeDLCookieJar()
            for host, name, value, path, expiry, is_secure in cursor.fetchall():
                cookie = compat_cookiejar_Cookie(
                    version=0, name=name, value=value, port=None, port_specified=False,
                    domain=host, domain_specified=bool(host), domain_initial_dot=host.startswith('.'),
                    path=path, path_specified=bool(path), secure=is_secure, expires=expiry, discard=False,
                    comment=None, comment_url=None, rest={})
                jar.set_cookie(cookie)
            logger.info('Extracted {} cookies from firefox'.format(len(jar)))
            return jar
        finally:
            if cursor is not None:
                cursor.connection.close()


def _firefox_browser_dir():
    if sys.platform in ('linux', 'linux2'):
        return os.path.expanduser('~/.mozilla/firefox')
    elif sys.platform == 'win32':
        return os.path.expandvars(r'%APPDATA%\Mozilla\Firefox\Profiles')
    elif sys.platform == 'darwin':
        return os.path.expanduser('~/Library/Application Support/Firefox')
    else:
        raise ValueError('unsupported platform: {}'.format(sys.platform))


def _get_chromium_based_browser_settings(browser_name):
    # https://chromium.googlesource.com/chromium/src/+/HEAD/docs/user_data_dir.md
    if sys.platform in ('linux', 'linux2'):
        config = _config_home()
        browser_dir = {
            'brave': os.path.join(config, 'BraveSoftware/Brave-Browser'),
            'chrome': os.path.join(config, 'google-chrome'),
            'chromium': os.path.join(config, 'chromium'),
            'edge': os.path.join(config, 'microsoft-edge'),
            'opera': os.path.join(config, 'opera'),
            'vivaldi': os.path.join(config, 'vivaldi'),
        }[browser_name]

    elif sys.platform == 'win32':
        appdata_local = os.path.expandvars('%LOCALAPPDATA%')
        appdata_roaming = os.path.expandvars('%APPDATA%')
        browser_dir = {
            'brave': os.path.join(appdata_local, r'BraveSoftware\Brave-Browser\User Data'),
            'chrome': os.path.join(appdata_local, r'Google\Chrome\User Data'),
            'chromium': os.path.join(appdata_local, r'Chromium\User Data'),
            'edge': os.path.join(appdata_local, r'Microsoft\Edge\User Data'),
            'opera': os.path.join(appdata_roaming, r'Opera Software\Opera Stable'),
            'vivaldi': os.path.join(appdata_local, r'Vivaldi\User Data'),
        }[browser_name]

    elif sys.platform == 'darwin':
        appdata = os.path.expanduser('~/Library/Application Support')
        browser_dir = {
            'brave': os.path.join(appdata, 'BraveSoftware/Brave-Browser'),
            'chrome': os.path.join(appdata, 'Google/Chrome'),
            'chromium': os.path.join(appdata, 'Chromium'),
            'edge': os.path.join(appdata, 'Microsoft Edge'),
            'opera': os.path.join(appdata, 'com.operasoftware.Opera'),
            'vivaldi': os.path.join(appdata, 'Vivaldi'),
        }[browser_name]

    else:
        raise ValueError('unsupported platform: {}'.format(sys.platform))

    # Linux keyring names can be determined by snooping on dbus while opening the browser in KDE:
    # dbus-monitor "interface='org.kde.KWallet'" "type=method_return"
    keyring_name = {
        'brave': 'Brave',
        'chrome': 'Chrome',
        'chromium': 'Chromium',
        'edge': 'Microsoft Edge' if sys.platform == 'darwin' else 'Chromium',
        'opera': 'Opera' if sys.platform == 'darwin' else 'Chromium',
        'vivaldi': 'Vivaldi' if sys.platform == 'darwin' else 'Chrome',
    }[browser_name]

    browsers_without_profiles = {'opera'}

    return {
        'browser_dir': browser_dir,
        'keyring_name': keyring_name,
        'supports_profiles': browser_name not in browsers_without_profiles
    }


def _extract_chrome_cookies(browser_name, profile, logger):
    logger.info('Extracting cookies from {}'.format(browser_name))

    if not SQLITE_AVAILABLE:
        logger.warning(('Cannot extract cookies from {} without sqlite3 support. '
                        'Please use a python interpreter compiled with sqlite3 support').format(browser_name))
        return YoutubeDLCookieJar()

    config = _get_chromium_based_browser_settings(browser_name)

    if profile is None:
        search_root = config['browser_dir']
    elif _is_path(profile):
        search_root = profile
        config['browser_dir'] = os.path.dirname(profile) if config['supports_profiles'] else profile
    else:
        if config['supports_profiles']:
            search_root = os.path.join(config['browser_dir'], profile)
        else:
            logger.error('{} does not support profiles'.format(browser_name))
            search_root = config['browser_dir']

    cookie_database_path = _find_most_recently_used_file(search_root, 'Cookies')
    if cookie_database_path is None:
        raise FileNotFoundError('could not find {} cookies database in "{}"'.format(browser_name, search_root))
    logger.debug('extracting from: "{}"'.format(cookie_database_path))

    decryptor = get_cookie_decryptor(config['browser_dir'], config['keyring_name'], logger)

    with tempfile.TemporaryDirectory(prefix='youtube_dl') as tmpdir:
        cursor = None
        try:
            cursor = _open_database_copy(cookie_database_path, tmpdir)
            cursor.connection.text_factory = bytes
            column_names = _get_column_names(cursor, 'cookies')
            secure_column = 'is_secure' if 'is_secure' in column_names else 'secure'
            cursor.execute('SELECT host_key, name, value, encrypted_value, path, '
                           'expires_utc, {} FROM cookies'.format(secure_column))
            jar = YoutubeDLCookieJar()
            failed_cookies = 0
            for host_key, name, value, encrypted_value, path, expires_utc, is_secure in cursor.fetchall():
                host_key = host_key.decode('utf-8')
                name = name.decode('utf-8')
                value = value.decode('utf-8')
                path = path.decode('utf-8')

                if not value and encrypted_value:
                    value = decryptor.decrypt(encrypted_value)
                    if value is None:
                        failed_cookies += 1
                        continue

                cookie = compat_cookiejar_Cookie(
                    version=0, name=name, value=value, port=None, port_specified=False,
                    domain=host_key, domain_specified=bool(host_key), domain_initial_dot=host_key.startswith('.'),
                    path=path, path_specified=bool(path), secure=is_secure, expires=expires_utc, discard=False,
                    comment=None, comment_url=None, rest={})
                jar.set_cookie(cookie)
            if failed_cookies > 0:
                failed_message = ' ({} could not be decrypted)'.format(failed_cookies)
            else:
                failed_message = ''
            logger.info('Extracted {} cookies from {}{}'.format(len(jar), browser_name, failed_message))
            return jar
        finally:
            if cursor is not None:
                cursor.connection.close()


class ChromeCookieDecryptor:
    """
    Overview:

        Linux:
        - cookies are either v10 or v11
            - v10: AES-CBC encrypted with a fixed key
            - v11: AES-CBC encrypted with an OS protected key (keyring)
            - v11 keys can be stored in various places depending on the activate desktop environment [2]

        Mac:
        - cookies are either v10 or not v10
            - v10: AES-CBC encrypted with an OS protected key (keyring) and more key derivation iterations than linux
            - not v10: 'old data' stored as plaintext

        Windows:
        - cookies are either v10 or not v10
            - v10: AES-GCM encrypted with a key which is encrypted with DPAPI
            - not v10: encrypted with DPAPI

    Sources:
    - [1] https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/os_crypt/
    - [2] https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/os_crypt/key_storage_linux.cc
        - KeyStorageLinux::CreateService
    """

    def decrypt(self, encrypted_value):
        raise NotImplementedError


def get_cookie_decryptor(browser_root, browser_keyring_name, logger):
    if sys.platform in ('linux', 'linux2'):
        return LinuxChromeCookieDecryptor(browser_keyring_name, logger)
    elif sys.platform == 'darwin':
        return MacChromeCookieDecryptor(browser_keyring_name, logger)
    elif sys.platform == 'win32':
        return WindowsChromeCookieDecryptor(browser_root, logger)
    else:
        raise NotImplementedError('Chrome cookie decryption is not supported '
                                  'on this platform: {}'.format(sys.platform))


class LinuxChromeCookieDecryptor(ChromeCookieDecryptor):
    def __init__(self, browser_keyring_name, logger):
        self._logger = logger
        self._v10_key = self.derive_key(b'peanuts')
        if KEYRING_AVAILABLE:
            self._v11_key = self.derive_key(_get_linux_keyring_password(browser_keyring_name))
        else:
            self._v11_key = None

    @staticmethod
    def derive_key(password):
        # values from
        # https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/os_crypt/os_crypt_linux.cc
        return pbkdf2_sha1(password, salt=b'saltysalt', iterations=1, key_length=16)

    def decrypt(self, encrypted_value):
        version = encrypted_value[:3]
        ciphertext = encrypted_value[3:]

        if version == b'v10':
            return _decrypt_aes_cbc(ciphertext, self._v10_key, self._logger)

        elif version == b'v11':
            if self._v11_key is None:
                self._logger.warning(f'cannot decrypt cookie {KEYRING_UNAVAILABLE_REASON}', only_once=True)
                return None
            return _decrypt_aes_cbc(ciphertext, self._v11_key, self._logger)

        else:
            return None


class MacChromeCookieDecryptor(ChromeCookieDecryptor):
    def __init__(self, browser_keyring_name, logger):
        self._logger = logger
        password = _get_mac_keyring_password(browser_keyring_name)
        self._v10_key = None if password is None else self.derive_key(password)

    @staticmethod
    def derive_key(password):
        # values from
        # https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/os_crypt/os_crypt_mac.mm
        return pbkdf2_sha1(password, salt=b'saltysalt', iterations=1003, key_length=16)

    def decrypt(self, encrypted_value):
        version = encrypted_value[:3]
        ciphertext = encrypted_value[3:]

        if version == b'v10':
            if self._v10_key is None:
                self._logger.warning('cannot decrypt v10 cookies: no key found', only_once=True)
                return None

            return _decrypt_aes_cbc(ciphertext, self._v10_key, self._logger)

        else:
            # other prefixes are considered 'old data' which were stored as plaintext
            # https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/os_crypt/os_crypt_mac.mm
            return encrypted_value


class WindowsChromeCookieDecryptor(ChromeCookieDecryptor):
    def __init__(self, browser_root, logger):
        self._logger = logger
        self._v10_key = _get_windows_v10_key(browser_root, logger)

    def decrypt(self, encrypted_value):
        version = encrypted_value[:3]
        ciphertext = encrypted_value[3:]

        if version == b'v10':
            if self._v10_key is None:
                self._logger.warning('cannot decrypt v10 cookies: no key found', only_once=True)
                return None
            elif not CRYPTO_AVAILABLE:
                self._logger.warning('cannot decrypt cookie as the `pycryptodome` module is not installed. '
                                     'Please install by running `python3 -m pip install pycryptodome`',
                                     only_once=True)
                return None

            # https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/os_crypt/os_crypt_win.cc
            #   kNonceLength
            nonce_length = 96 // 8
            # boringssl
            #   EVP_AEAD_AES_GCM_TAG_LEN
            authentication_tag_length = 16

            raw_ciphertext = ciphertext
            nonce = raw_ciphertext[:nonce_length]
            ciphertext = raw_ciphertext[nonce_length:-authentication_tag_length]
            authentication_tag = raw_ciphertext[-authentication_tag_length:]

            return _decrypt_aes_gcm(ciphertext, self._v10_key, nonce, authentication_tag, self._logger)

        else:
            # any other prefix means the data is DPAPI encrypted
            # https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/os_crypt/os_crypt_win.cc
            return _decrypt_windows_dpapi(encrypted_value, self._logger).decode('utf-8')


def _extract_safari_cookies(profile, logger):
    if profile is not None:
        logger.error('safari does not support profiles')
    if sys.platform != 'darwin':
        raise ValueError('unsupported platform: {}'.format(sys.platform))

    cookies_path = os.path.expanduser('~/Library/Cookies/Cookies.binarycookies')

    if not os.path.isfile(cookies_path):
        raise FileNotFoundError('could not find safari cookies database')

    with open(cookies_path, 'rb') as f:
        cookies_data = f.read()

    jar = parse_safari_cookies(cookies_data, logger=logger)
    logger.info('Extracted {} cookies from safari'.format(len(jar)))
    return jar


class ParserError(Exception):
    pass


class DataParser:
    def __init__(self, data, logger):
        self._data = data
        self.cursor = 0
        self._logger = logger

    def read_bytes(self, num_bytes):
        if num_bytes < 0:
            raise ParserError('invalid read of {} bytes'.format(num_bytes))
        end = self.cursor + num_bytes
        if end > len(self._data):
            raise ParserError('reached end of input')
        data = self._data[self.cursor:end]
        self.cursor = end
        return data

    def expect_bytes(self, expected_value, message):
        value = self.read_bytes(len(expected_value))
        if value != expected_value:
            raise ParserError('unexpected value: {} != {} ({})'.format(value, expected_value, message))

    def read_uint(self, big_endian=False):
        data_format = '>I' if big_endian else '<I'
        return struct.unpack(data_format, self.read_bytes(4))[0]

    def read_double(self, big_endian=False):
        data_format = '>d' if big_endian else '<d'
        return struct.unpack(data_format, self.read_bytes(8))[0]

    def read_cstring(self):
        buffer = []
        while True:
            c = self.read_bytes(1)
            if c == b'\x00':
                return b''.join(buffer).decode('utf-8')
            else:
                buffer.append(c)

    def skip(self, num_bytes, description='unknown'):
        if num_bytes > 0:
            self._logger.debug('skipping {} bytes ({}): {}'.format(
                num_bytes, description, self.read_bytes(num_bytes)))
        elif num_bytes < 0:
            raise ParserError('invalid skip of {} bytes'.format(num_bytes))

    def skip_to(self, offset, description='unknown'):
        self.skip(offset - self.cursor, description)

    def skip_to_end(self, description='unknown'):
        self.skip_to(len(self._data), description)


def _mac_absolute_time_to_posix(timestamp):
    return int((datetime(2001, 1, 1, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=timestamp)).timestamp())


def _parse_safari_cookies_header(data, logger):
    p = DataParser(data, logger)
    p.expect_bytes(b'cook', 'database signature')
    number_of_pages = p.read_uint(big_endian=True)
    page_sizes = [p.read_uint(big_endian=True) for _ in range(number_of_pages)]
    return page_sizes, p.cursor


def _parse_safari_cookies_page(data, jar, logger):
    p = DataParser(data, logger)
    p.expect_bytes(b'\x00\x00\x01\x00', 'page signature')
    number_of_cookies = p.read_uint()
    record_offsets = [p.read_uint() for _ in range(number_of_cookies)]
    if number_of_cookies == 0:
        logger.debug('a cookies page of size {} has no cookies'.format(len(data)))
        return

    p.skip_to(record_offsets[0], 'unknown page header field')

    for record_offset in record_offsets:
        p.skip_to(record_offset, 'space between records')
        record_length = _parse_safari_cookies_record(data[record_offset:], jar, logger)
        p.read_bytes(record_length)
    p.skip_to_end('space in between pages')


def _parse_safari_cookies_record(data, jar, logger):
    p = DataParser(data, logger)
    record_size = p.read_uint()
    p.skip(4, 'unknown record field 1')
    flags = p.read_uint()
    is_secure = bool(flags & 0x0001)
    p.skip(4, 'unknown record field 2')
    domain_offset = p.read_uint()
    name_offset = p.read_uint()
    path_offset = p.read_uint()
    value_offset = p.read_uint()
    p.skip(8, 'unknown record field 3')
    expiration_date = _mac_absolute_time_to_posix(p.read_double())
    _creation_date = _mac_absolute_time_to_posix(p.read_double())  # noqa: F841

    try:
        p.skip_to(domain_offset)
        domain = p.read_cstring()

        p.skip_to(name_offset)
        name = p.read_cstring()

        p.skip_to(path_offset)
        path = p.read_cstring()

        p.skip_to(value_offset)
        value = p.read_cstring()
    except UnicodeDecodeError:
        logger.warning('failed to parse cookie because UTF-8 decoding failed')
        return record_size

    p.skip_to(record_size, 'space at the end of the record')

    cookie = compat_cookiejar_Cookie(
        version=0, name=name, value=value, port=None, port_specified=False,
        domain=domain, domain_specified=bool(domain), domain_initial_dot=domain.startswith('.'),
        path=path, path_specified=bool(path), secure=is_secure, expires=expiration_date, discard=False,
        comment=None, comment_url=None, rest={})
    jar.set_cookie(cookie)
    return record_size


def parse_safari_cookies(data, jar=None, logger=YDLLogger()):
    """
    References:
        - https://github.com/libyal/dtformats/blob/main/documentation/Safari%20Cookies.asciidoc
            - this data appears to be out of date but the important parts of the database structure is the same
            - there are a few bytes here and there which are skipped during parsing
    """
    if jar is None:
        jar = YoutubeDLCookieJar()
    page_sizes, body_start = _parse_safari_cookies_header(data, logger)
    p = DataParser(data[body_start:], logger)
    for page_size in page_sizes:
        _parse_safari_cookies_page(p.read_bytes(page_size), jar, logger)
    p.skip_to_end('footer')
    return jar


def _get_linux_keyring_password(browser_keyring_name):
    password = keyring.get_password('{} Keys'.format(browser_keyring_name),
                                    '{} Safe Storage'.format(browser_keyring_name))
    if password is None:
        # this sometimes occurs in KDE because chrome does not check hasEntry and instead
        # just tries to read the value (which kwallet returns "") whereas keyring checks hasEntry
        # to verify this:
        # dbus-monitor "interface='org.kde.KWallet'" "type=method_return"
        # while starting chrome.
        # this may be a bug as the intended behaviour is to generate a random password and store
        # it, but that doesn't matter here.
        password = ''
    return password.encode('utf-8')


def _get_mac_keyring_password(browser_keyring_name):
    if KEYRING_AVAILABLE:
        password = keyring.get_password('{} Safe Storage'.format(browser_keyring_name), browser_keyring_name)
        return password.encode('utf-8')
    else:
        proc = subprocess.Popen(['security', 'find-generic-password',
                                 '-w',  # write password to stdout
                                 '-a', browser_keyring_name,  # match 'account'
                                 '-s', '{} Safe Storage'.format(browser_keyring_name)],  # match 'service'
                                stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)
        try:
            stdout, stderr = process_communicate_or_kill(proc)
            return stdout
        except BaseException:
            return None


def _get_windows_v10_key(browser_root, logger):
    path = _find_most_recently_used_file(browser_root, 'Local State')
    if path is None:
        logger.error('could not find local state file')
        return None
    with open(path, 'r') as f:
        data = json.load(f)
    try:
        base64_key = data['os_crypt']['encrypted_key']
    except KeyError:
        logger.error('no encrypted key in Local State')
        return None
    encrypted_key = compat_b64decode(base64_key)
    prefix = b'DPAPI'
    if not encrypted_key.startswith(prefix):
        logger.error('invalid key')
        return None
    return _decrypt_windows_dpapi(encrypted_key[len(prefix):], logger)


def pbkdf2_sha1(password, salt, iterations, key_length):
    return pbkdf2_hmac('sha1', password, salt, iterations, key_length)


def _decrypt_aes_cbc(ciphertext, key, logger, initialization_vector=b' ' * 16):
    plaintext = aes_cbc_decrypt(bytes_to_intlist(ciphertext),
                                bytes_to_intlist(key),
                                bytes_to_intlist(initialization_vector))
    padding_length = plaintext[-1]
    try:
        return intlist_to_bytes(plaintext[:-padding_length]).decode('utf-8')
    except UnicodeDecodeError:
        logger.warning('failed to decrypt cookie because UTF-8 decoding failed. Possibly the key is wrong?')
        return None


def _decrypt_aes_gcm(ciphertext, key, nonce, authentication_tag, logger):
    cipher = AES.new(key, AES.MODE_GCM, nonce)
    try:
        plaintext = cipher.decrypt_and_verify(ciphertext, authentication_tag)
    except ValueError:
        logger.warning('failed to decrypt cookie because the MAC check failed. Possibly the key is wrong?')
        return None

    try:
        return plaintext.decode('utf-8')
    except UnicodeDecodeError:
        logger.warning('failed to decrypt cookie because UTF-8 decoding failed. Possibly the key is wrong?')
        return None


def _decrypt_windows_dpapi(ciphertext, logger):
    """
    References:
        - https://docs.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata
    """
    from ctypes.wintypes import DWORD

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [('cbData', DWORD),
                    ('pbData', ctypes.POINTER(ctypes.c_char))]

    buffer = ctypes.create_string_buffer(ciphertext)
    blob_in = DATA_BLOB(ctypes.sizeof(buffer), buffer)
    blob_out = DATA_BLOB()
    ret = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),  # pDataIn
        None,  # ppszDataDescr: human readable description of pDataIn
        None,  # pOptionalEntropy: salt?
        None,  # pvReserved: must be NULL
        None,  # pPromptStruct: information about prompts to display
        0,  # dwFlags
        ctypes.byref(blob_out)  # pDataOut
    )
    if not ret:
        logger.warning('failed to decrypt with DPAPI')
        return None

    result = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return result


def _config_home():
    return os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))


def _open_database_copy(database_path, tmpdir):
    # cannot open sqlite databases if they are already in use (e.g. by the browser)
    database_copy_path = os.path.join(tmpdir, 'temporary.sqlite')
    shutil.copy(database_path, database_copy_path)
    conn = sqlite3.connect(database_copy_path)
    return conn.cursor()


def _get_column_names(cursor, table_name):
    table_info = cursor.execute('PRAGMA table_info({})'.format(table_name)).fetchall()
    return [row[1].decode('utf-8') for row in table_info]


def _find_most_recently_used_file(root, filename):
    # if there are multiple browser profiles, take the most recently used one
    paths = []
    for root, dirs, files in os.walk(root):
        for file in files:
            if file == filename:
                paths.append(os.path.join(root, file))
    return None if not paths else max(paths, key=lambda path: os.lstat(path).st_mtime)


def _merge_cookie_jars(jars):
    output_jar = YoutubeDLCookieJar()
    for jar in jars:
        for cookie in jar:
            output_jar.set_cookie(cookie)
        if jar.filename is not None:
            output_jar.filename = jar.filename
    return output_jar


def _is_path(value):
    return os.path.sep in value


def _parse_browser_specification(browser_name, profile=None):
    if browser_name not in SUPPORTED_BROWSERS:
        raise ValueError(f'unsupported browser: "{browser_name}"')
    if profile is not None and _is_path(profile):
        profile = os.path.expanduser(profile)
    return browser_name, profile
