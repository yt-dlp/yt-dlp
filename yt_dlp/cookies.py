import base64
import collections
import contextlib
import datetime as dt
import functools
import glob
import hashlib
import http.cookiejar
import http.cookies
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from enum import Enum, auto

from .aes import (
    aes_cbc_decrypt_bytes,
    aes_gcm_decrypt_and_verify_bytes,
    unpad_pkcs7,
)
from .compat import compat_os_name
from .dependencies import (
    _SECRETSTORAGE_UNAVAILABLE_REASON,
    secretstorage,
    sqlite3,
)
from .minicurses import MultilinePrinter, QuietMultilinePrinter
from .utils import (
    DownloadError,
    Popen,
    error_to_str,
    expand_path,
    is_path_like,
    sanitize_url,
    str_or_none,
    try_call,
    write_string,
)
from .utils._utils import _YDLLogger
from .utils.networking import normalize_url

CHROMIUM_BASED_BROWSERS = {'brave', 'chrome', 'chromium', 'edge', 'opera', 'vivaldi', 'whale'}
SUPPORTED_BROWSERS = CHROMIUM_BASED_BROWSERS | {'firefox', 'safari'}


class YDLLogger(_YDLLogger):
    def warning(self, message, only_once=False):  # compat
        return super().warning(message, once=only_once)

    class ProgressBar(MultilinePrinter):
        _DELAY, _timer = 0.1, 0

        def print(self, message):
            if time.time() - self._timer > self._DELAY:
                self.print_at_line(f'[Cookies] {message}', 0)
                self._timer = time.time()

    def progress_bar(self):
        """Return a context manager with a print method. (Optional)"""
        # Do not print to files/pipes, loggers, or when --no-progress is used
        if not self._ydl or self._ydl.params.get('noprogress') or self._ydl.params.get('logger'):
            return
        file = self._ydl._out_files.error
        try:
            if not file.isatty():
                return
        except BaseException:
            return
        return self.ProgressBar(file, preserve_output=False)


def _create_progress_bar(logger):
    if hasattr(logger, 'progress_bar'):
        printer = logger.progress_bar()
        if printer:
            return printer
    printer = QuietMultilinePrinter()
    printer.print = lambda _: None
    return printer


def load_cookies(cookie_file, browser_specification, ydl):
    cookie_jars = []
    if browser_specification is not None:
        browser_name, profile, keyring, container = _parse_browser_specification(*browser_specification)
        cookie_jars.append(
            extract_cookies_from_browser(browser_name, profile, YDLLogger(ydl), keyring=keyring, container=container))

    if cookie_file is not None:
        is_filename = is_path_like(cookie_file)
        if is_filename:
            cookie_file = expand_path(cookie_file)

        jar = YoutubeDLCookieJar(cookie_file)
        if not is_filename or os.access(cookie_file, os.R_OK):
            jar.load()
        cookie_jars.append(jar)

    return _merge_cookie_jars(cookie_jars)


def extract_cookies_from_browser(browser_name, profile=None, logger=YDLLogger(), *, keyring=None, container=None):
    if browser_name == 'firefox':
        return _extract_firefox_cookies(profile, container, logger)
    elif browser_name == 'safari':
        return _extract_safari_cookies(profile, logger)
    elif browser_name in CHROMIUM_BASED_BROWSERS:
        return _extract_chrome_cookies(browser_name, profile, keyring, logger)
    else:
        raise ValueError(f'unknown browser: {browser_name}')


def _extract_firefox_cookies(profile, container, logger):
    logger.info('Extracting cookies from firefox')
    if not sqlite3:
        logger.warning('Cannot extract cookies from firefox without sqlite3 support. '
                       'Please use a Python interpreter compiled with sqlite3 support')
        return YoutubeDLCookieJar()

    if profile is None:
        search_roots = list(_firefox_browser_dirs())
    elif _is_path(profile):
        search_roots = [profile]
    else:
        search_roots = [os.path.join(path, profile) for path in _firefox_browser_dirs()]
    search_root = ', '.join(map(repr, search_roots))

    cookie_database_path = _newest(_firefox_cookie_dbs(search_roots))
    if cookie_database_path is None:
        raise FileNotFoundError(f'could not find firefox cookies database in {search_root}')
    logger.debug(f'Extracting cookies from: "{cookie_database_path}"')

    container_id = None
    if container not in (None, 'none'):
        containers_path = os.path.join(os.path.dirname(cookie_database_path), 'containers.json')
        if not os.path.isfile(containers_path) or not os.access(containers_path, os.R_OK):
            raise FileNotFoundError(f'could not read containers.json in {search_root}')
        with open(containers_path, encoding='utf8') as containers:
            identities = json.load(containers).get('identities', [])
        container_id = next((context.get('userContextId') for context in identities if container in (
            context.get('name'),
            try_call(lambda: re.fullmatch(r'userContext([^\.]+)\.label', context['l10nID']).group()),
        )), None)
        if not isinstance(container_id, int):
            raise ValueError(f'could not find firefox container "{container}" in containers.json')

    with tempfile.TemporaryDirectory(prefix='yt_dlp') as tmpdir:
        cursor = None
        try:
            cursor = _open_database_copy(cookie_database_path, tmpdir)
            if isinstance(container_id, int):
                logger.debug(
                    f'Only loading cookies from firefox container "{container}", ID {container_id}')
                cursor.execute(
                    'SELECT host, name, value, path, expiry, isSecure FROM moz_cookies WHERE originAttributes LIKE ? OR originAttributes LIKE ?',
                    (f'%userContextId={container_id}', f'%userContextId={container_id}&%'))
            elif container == 'none':
                logger.debug('Only loading cookies not belonging to any container')
                cursor.execute(
                    'SELECT host, name, value, path, expiry, isSecure FROM moz_cookies WHERE NOT INSTR(originAttributes,"userContextId=")')
            else:
                cursor.execute('SELECT host, name, value, path, expiry, isSecure FROM moz_cookies')
            jar = YoutubeDLCookieJar()
            with _create_progress_bar(logger) as progress_bar:
                table = cursor.fetchall()
                total_cookie_count = len(table)
                for i, (host, name, value, path, expiry, is_secure) in enumerate(table):
                    progress_bar.print(f'Loading cookie {i: 6d}/{total_cookie_count: 6d}')
                    cookie = http.cookiejar.Cookie(
                        version=0, name=name, value=value, port=None, port_specified=False,
                        domain=host, domain_specified=bool(host), domain_initial_dot=host.startswith('.'),
                        path=path, path_specified=bool(path), secure=is_secure, expires=expiry, discard=False,
                        comment=None, comment_url=None, rest={})
                    jar.set_cookie(cookie)
            logger.info(f'Extracted {len(jar)} cookies from firefox')
            return jar
        finally:
            if cursor is not None:
                cursor.connection.close()


def _firefox_browser_dirs():
    if sys.platform in ('cygwin', 'win32'):
        yield os.path.expandvars(R'%APPDATA%\Mozilla\Firefox\Profiles')

    elif sys.platform == 'darwin':
        yield os.path.expanduser('~/Library/Application Support/Firefox/Profiles')

    else:
        yield from map(os.path.expanduser, (
            '~/.mozilla/firefox',
            '~/snap/firefox/common/.mozilla/firefox',
            '~/.var/app/org.mozilla.firefox/.mozilla/firefox',
        ))


def _firefox_cookie_dbs(roots):
    for root in map(os.path.abspath, roots):
        for pattern in ('', '*/', 'Profiles/*/'):
            yield from glob.iglob(os.path.join(root, pattern, 'cookies.sqlite'))


def _get_chromium_based_browser_settings(browser_name):
    # https://chromium.googlesource.com/chromium/src/+/HEAD/docs/user_data_dir.md
    if sys.platform in ('cygwin', 'win32'):
        appdata_local = os.path.expandvars('%LOCALAPPDATA%')
        appdata_roaming = os.path.expandvars('%APPDATA%')
        browser_dir = {
            'brave': os.path.join(appdata_local, R'BraveSoftware\Brave-Browser\User Data'),
            'chrome': os.path.join(appdata_local, R'Google\Chrome\User Data'),
            'chromium': os.path.join(appdata_local, R'Chromium\User Data'),
            'edge': os.path.join(appdata_local, R'Microsoft\Edge\User Data'),
            'opera': os.path.join(appdata_roaming, R'Opera Software\Opera Stable'),
            'vivaldi': os.path.join(appdata_local, R'Vivaldi\User Data'),
            'whale': os.path.join(appdata_local, R'Naver\Naver Whale\User Data'),
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
            'whale': os.path.join(appdata, 'Naver/Whale'),
        }[browser_name]

    else:
        config = _config_home()
        browser_dir = {
            'brave': os.path.join(config, 'BraveSoftware/Brave-Browser'),
            'chrome': os.path.join(config, 'google-chrome'),
            'chromium': os.path.join(config, 'chromium'),
            'edge': os.path.join(config, 'microsoft-edge'),
            'opera': os.path.join(config, 'opera'),
            'vivaldi': os.path.join(config, 'vivaldi'),
            'whale': os.path.join(config, 'naver-whale'),
        }[browser_name]

    # Linux keyring names can be determined by snooping on dbus while opening the browser in KDE:
    # dbus-monitor "interface='org.kde.KWallet'" "type=method_return"
    keyring_name = {
        'brave': 'Brave',
        'chrome': 'Chrome',
        'chromium': 'Chromium',
        'edge': 'Microsoft Edge' if sys.platform == 'darwin' else 'Chromium',
        'opera': 'Opera' if sys.platform == 'darwin' else 'Chromium',
        'vivaldi': 'Vivaldi' if sys.platform == 'darwin' else 'Chrome',
        'whale': 'Whale',
    }[browser_name]

    browsers_without_profiles = {'opera'}

    return {
        'browser_dir': browser_dir,
        'keyring_name': keyring_name,
        'supports_profiles': browser_name not in browsers_without_profiles,
    }


def _extract_chrome_cookies(browser_name, profile, keyring, logger):
    logger.info(f'Extracting cookies from {browser_name}')

    if not sqlite3:
        logger.warning(f'Cannot extract cookies from {browser_name} without sqlite3 support. '
                       'Please use a Python interpreter compiled with sqlite3 support')
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
            logger.error(f'{browser_name} does not support profiles')
            search_root = config['browser_dir']

    cookie_database_path = _newest(_find_files(search_root, 'Cookies', logger))
    if cookie_database_path is None:
        raise FileNotFoundError(f'could not find {browser_name} cookies database in "{search_root}"')
    logger.debug(f'Extracting cookies from: "{cookie_database_path}"')

    decryptor = get_cookie_decryptor(config['browser_dir'], config['keyring_name'], logger, keyring=keyring)

    with tempfile.TemporaryDirectory(prefix='yt_dlp') as tmpdir:
        cursor = None
        try:
            cursor = _open_database_copy(cookie_database_path, tmpdir)
            cursor.connection.text_factory = bytes
            column_names = _get_column_names(cursor, 'cookies')
            secure_column = 'is_secure' if 'is_secure' in column_names else 'secure'
            cursor.execute(f'SELECT host_key, name, value, encrypted_value, path, expires_utc, {secure_column} FROM cookies')
            jar = YoutubeDLCookieJar()
            failed_cookies = 0
            unencrypted_cookies = 0
            with _create_progress_bar(logger) as progress_bar:
                table = cursor.fetchall()
                total_cookie_count = len(table)
                for i, line in enumerate(table):
                    progress_bar.print(f'Loading cookie {i: 6d}/{total_cookie_count: 6d}')
                    is_encrypted, cookie = _process_chrome_cookie(decryptor, *line)
                    if not cookie:
                        failed_cookies += 1
                        continue
                    elif not is_encrypted:
                        unencrypted_cookies += 1
                    jar.set_cookie(cookie)
            if failed_cookies > 0:
                failed_message = f' ({failed_cookies} could not be decrypted)'
            else:
                failed_message = ''
            logger.info(f'Extracted {len(jar)} cookies from {browser_name}{failed_message}')
            counts = decryptor._cookie_counts.copy()
            counts['unencrypted'] = unencrypted_cookies
            logger.debug(f'cookie version breakdown: {counts}')
            return jar
        except PermissionError as error:
            if compat_os_name == 'nt' and error.errno == 13:
                message = 'Could not copy Chrome cookie database. See  https://github.com/yt-dlp/yt-dlp/issues/7271  for more info'
                logger.error(message)
                raise DownloadError(message)  # force exit
            raise
        finally:
            if cursor is not None:
                cursor.connection.close()


def _process_chrome_cookie(decryptor, host_key, name, value, encrypted_value, path, expires_utc, is_secure):
    host_key = host_key.decode()
    name = name.decode()
    value = value.decode()
    path = path.decode()
    is_encrypted = not value and encrypted_value

    if is_encrypted:
        value = decryptor.decrypt(encrypted_value)
        if value is None:
            return is_encrypted, None

    # In chrome, session cookies have expires_utc set to 0
    # In our cookie-store, cookies that do not expire should have expires set to None
    if not expires_utc:
        expires_utc = None

    return is_encrypted, http.cookiejar.Cookie(
        version=0, name=name, value=value, port=None, port_specified=False,
        domain=host_key, domain_specified=bool(host_key), domain_initial_dot=host_key.startswith('.'),
        path=path, path_specified=bool(path), secure=is_secure, expires=expires_utc, discard=False,
        comment=None, comment_url=None, rest={})


class ChromeCookieDecryptor:
    """
    Overview:

        Linux:
        - cookies are either v10 or v11
            - v10: AES-CBC encrypted with a fixed key
                - also attempts empty password if decryption fails
            - v11: AES-CBC encrypted with an OS protected key (keyring)
                - also attempts empty password if decryption fails
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
    - [2] https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/os_crypt/sync/key_storage_linux.cc
        - KeyStorageLinux::CreateService
    """

    _cookie_counts = {}

    def decrypt(self, encrypted_value):
        raise NotImplementedError('Must be implemented by sub classes')


def get_cookie_decryptor(browser_root, browser_keyring_name, logger, *, keyring=None):
    if sys.platform == 'darwin':
        return MacChromeCookieDecryptor(browser_keyring_name, logger)
    elif sys.platform in ('win32', 'cygwin'):
        return WindowsChromeCookieDecryptor(browser_root, logger)
    return LinuxChromeCookieDecryptor(browser_keyring_name, logger, keyring=keyring)


class LinuxChromeCookieDecryptor(ChromeCookieDecryptor):
    def __init__(self, browser_keyring_name, logger, *, keyring=None):
        self._logger = logger
        self._v10_key = self.derive_key(b'peanuts')
        self._empty_key = self.derive_key(b'')
        self._cookie_counts = {'v10': 0, 'v11': 0, 'other': 0}
        self._browser_keyring_name = browser_keyring_name
        self._keyring = keyring

    @functools.cached_property
    def _v11_key(self):
        password = _get_linux_keyring_password(self._browser_keyring_name, self._keyring, self._logger)
        return None if password is None else self.derive_key(password)

    @staticmethod
    def derive_key(password):
        # values from
        # https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/os_crypt/sync/os_crypt_linux.cc
        return pbkdf2_sha1(password, salt=b'saltysalt', iterations=1, key_length=16)

    def decrypt(self, encrypted_value):
        """

        following the same approach as the fix in [1]: if cookies fail to decrypt then attempt to decrypt
        with an empty password. The failure detection is not the same as what chromium uses so the
        results won't be perfect

        References:
            - [1] https://chromium.googlesource.com/chromium/src/+/bbd54702284caca1f92d656fdcadf2ccca6f4165%5E%21/
                - a bugfix to try an empty password as a fallback
        """
        version = encrypted_value[:3]
        ciphertext = encrypted_value[3:]

        if version == b'v10':
            self._cookie_counts['v10'] += 1
            return _decrypt_aes_cbc_multi(ciphertext, (self._v10_key, self._empty_key), self._logger)

        elif version == b'v11':
            self._cookie_counts['v11'] += 1
            if self._v11_key is None:
                self._logger.warning('cannot decrypt v11 cookies: no key found', only_once=True)
                return None
            return _decrypt_aes_cbc_multi(ciphertext, (self._v11_key, self._empty_key), self._logger)

        else:
            self._logger.warning(f'unknown cookie version: "{version}"', only_once=True)
            self._cookie_counts['other'] += 1
            return None


class MacChromeCookieDecryptor(ChromeCookieDecryptor):
    def __init__(self, browser_keyring_name, logger):
        self._logger = logger
        password = _get_mac_keyring_password(browser_keyring_name, logger)
        self._v10_key = None if password is None else self.derive_key(password)
        self._cookie_counts = {'v10': 0, 'other': 0}

    @staticmethod
    def derive_key(password):
        # values from
        # https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/os_crypt/sync/os_crypt_mac.mm
        return pbkdf2_sha1(password, salt=b'saltysalt', iterations=1003, key_length=16)

    def decrypt(self, encrypted_value):
        version = encrypted_value[:3]
        ciphertext = encrypted_value[3:]

        if version == b'v10':
            self._cookie_counts['v10'] += 1
            if self._v10_key is None:
                self._logger.warning('cannot decrypt v10 cookies: no key found', only_once=True)
                return None

            return _decrypt_aes_cbc_multi(ciphertext, (self._v10_key,), self._logger)

        else:
            self._cookie_counts['other'] += 1
            # other prefixes are considered 'old data' which were stored as plaintext
            # https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/os_crypt/sync/os_crypt_mac.mm
            return encrypted_value


class WindowsChromeCookieDecryptor(ChromeCookieDecryptor):
    def __init__(self, browser_root, logger):
        self._logger = logger
        self._v10_key = _get_windows_v10_key(browser_root, logger)
        self._cookie_counts = {'v10': 0, 'other': 0}

    def decrypt(self, encrypted_value):
        version = encrypted_value[:3]
        ciphertext = encrypted_value[3:]

        if version == b'v10':
            self._cookie_counts['v10'] += 1
            if self._v10_key is None:
                self._logger.warning('cannot decrypt v10 cookies: no key found', only_once=True)
                return None

            # https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/os_crypt/sync/os_crypt_win.cc
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
            self._cookie_counts['other'] += 1
            # any other prefix means the data is DPAPI encrypted
            # https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/os_crypt/sync/os_crypt_win.cc
            return _decrypt_windows_dpapi(encrypted_value, self._logger).decode()


def _extract_safari_cookies(profile, logger):
    if sys.platform != 'darwin':
        raise ValueError(f'unsupported platform: {sys.platform}')

    if profile:
        cookies_path = os.path.expanduser(profile)
        if not os.path.isfile(cookies_path):
            raise FileNotFoundError('custom safari cookies database not found')

    else:
        cookies_path = os.path.expanduser('~/Library/Cookies/Cookies.binarycookies')

        if not os.path.isfile(cookies_path):
            logger.debug('Trying secondary cookie location')
            cookies_path = os.path.expanduser('~/Library/Containers/com.apple.Safari/Data/Library/Cookies/Cookies.binarycookies')
            if not os.path.isfile(cookies_path):
                raise FileNotFoundError('could not find safari cookies database')

    with open(cookies_path, 'rb') as f:
        cookies_data = f.read()

    jar = parse_safari_cookies(cookies_data, logger=logger)
    logger.info(f'Extracted {len(jar)} cookies from safari')
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
            raise ParserError(f'invalid read of {num_bytes} bytes')
        end = self.cursor + num_bytes
        if end > len(self._data):
            raise ParserError('reached end of input')
        data = self._data[self.cursor:end]
        self.cursor = end
        return data

    def expect_bytes(self, expected_value, message):
        value = self.read_bytes(len(expected_value))
        if value != expected_value:
            raise ParserError(f'unexpected value: {value} != {expected_value} ({message})')

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
                return b''.join(buffer).decode()
            else:
                buffer.append(c)

    def skip(self, num_bytes, description='unknown'):
        if num_bytes > 0:
            self._logger.debug(f'skipping {num_bytes} bytes ({description}): {self.read_bytes(num_bytes)!r}')
        elif num_bytes < 0:
            raise ParserError(f'invalid skip of {num_bytes} bytes')

    def skip_to(self, offset, description='unknown'):
        self.skip(offset - self.cursor, description)

    def skip_to_end(self, description='unknown'):
        self.skip_to(len(self._data), description)


def _mac_absolute_time_to_posix(timestamp):
    return int((dt.datetime(2001, 1, 1, 0, 0, tzinfo=dt.timezone.utc) + dt.timedelta(seconds=timestamp)).timestamp())


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
        logger.debug(f'a cookies page of size {len(data)} has no cookies')
        return

    p.skip_to(record_offsets[0], 'unknown page header field')

    with _create_progress_bar(logger) as progress_bar:
        for i, record_offset in enumerate(record_offsets):
            progress_bar.print(f'Loading cookie {i: 6d}/{number_of_cookies: 6d}')
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
        logger.warning('failed to parse Safari cookie because UTF-8 decoding failed', only_once=True)
        return record_size

    p.skip_to(record_size, 'space at the end of the record')

    cookie = http.cookiejar.Cookie(
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


class _LinuxDesktopEnvironment(Enum):
    """
    https://chromium.googlesource.com/chromium/src/+/refs/heads/main/base/nix/xdg_util.h
    DesktopEnvironment
    """
    OTHER = auto()
    CINNAMON = auto()
    DEEPIN = auto()
    GNOME = auto()
    KDE3 = auto()
    KDE4 = auto()
    KDE5 = auto()
    KDE6 = auto()
    PANTHEON = auto()
    UKUI = auto()
    UNITY = auto()
    XFCE = auto()
    LXQT = auto()


class _LinuxKeyring(Enum):
    """
    https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/os_crypt/sync/key_storage_util_linux.h
    SelectedLinuxBackend
    """
    KWALLET = auto()  # KDE4
    KWALLET5 = auto()
    KWALLET6 = auto()
    GNOMEKEYRING = auto()
    BASICTEXT = auto()


SUPPORTED_KEYRINGS = _LinuxKeyring.__members__.keys()


def _get_linux_desktop_environment(env, logger):
    """
    https://chromium.googlesource.com/chromium/src/+/refs/heads/main/base/nix/xdg_util.cc
    GetDesktopEnvironment
    """
    xdg_current_desktop = env.get('XDG_CURRENT_DESKTOP', None)
    desktop_session = env.get('DESKTOP_SESSION', None)
    if xdg_current_desktop is not None:
        for part in map(str.strip, xdg_current_desktop.split(':')):
            if part == 'Unity':
                if desktop_session is not None and 'gnome-fallback' in desktop_session:
                    return _LinuxDesktopEnvironment.GNOME
                else:
                    return _LinuxDesktopEnvironment.UNITY
            elif part == 'Deepin':
                return _LinuxDesktopEnvironment.DEEPIN
            elif part == 'GNOME':
                return _LinuxDesktopEnvironment.GNOME
            elif part == 'X-Cinnamon':
                return _LinuxDesktopEnvironment.CINNAMON
            elif part == 'KDE':
                kde_version = env.get('KDE_SESSION_VERSION', None)
                if kde_version == '5':
                    return _LinuxDesktopEnvironment.KDE5
                elif kde_version == '6':
                    return _LinuxDesktopEnvironment.KDE6
                elif kde_version == '4':
                    return _LinuxDesktopEnvironment.KDE4
                else:
                    logger.info(f'unknown KDE version: "{kde_version}". Assuming KDE4')
                    return _LinuxDesktopEnvironment.KDE4
            elif part == 'Pantheon':
                return _LinuxDesktopEnvironment.PANTHEON
            elif part == 'XFCE':
                return _LinuxDesktopEnvironment.XFCE
            elif part == 'UKUI':
                return _LinuxDesktopEnvironment.UKUI
            elif part == 'LXQt':
                return _LinuxDesktopEnvironment.LXQT
        logger.info(f'XDG_CURRENT_DESKTOP is set to an unknown value: "{xdg_current_desktop}"')

    elif desktop_session is not None:
        if desktop_session == 'deepin':
            return _LinuxDesktopEnvironment.DEEPIN
        elif desktop_session in ('mate', 'gnome'):
            return _LinuxDesktopEnvironment.GNOME
        elif desktop_session in ('kde4', 'kde-plasma'):
            return _LinuxDesktopEnvironment.KDE4
        elif desktop_session == 'kde':
            if 'KDE_SESSION_VERSION' in env:
                return _LinuxDesktopEnvironment.KDE4
            else:
                return _LinuxDesktopEnvironment.KDE3
        elif 'xfce' in desktop_session or desktop_session == 'xubuntu':
            return _LinuxDesktopEnvironment.XFCE
        elif desktop_session == 'ukui':
            return _LinuxDesktopEnvironment.UKUI
        else:
            logger.info(f'DESKTOP_SESSION is set to an unknown value: "{desktop_session}"')

    else:
        if 'GNOME_DESKTOP_SESSION_ID' in env:
            return _LinuxDesktopEnvironment.GNOME
        elif 'KDE_FULL_SESSION' in env:
            if 'KDE_SESSION_VERSION' in env:
                return _LinuxDesktopEnvironment.KDE4
            else:
                return _LinuxDesktopEnvironment.KDE3
    return _LinuxDesktopEnvironment.OTHER


def _choose_linux_keyring(logger):
    """
    SelectBackend in [1]

    There is currently support for forcing chromium to use BASIC_TEXT by creating a file called
    `Disable Local Encryption` [1] in the user data dir. The function to write this file (`WriteBackendUse()` [1])
    does not appear to be called anywhere other than in tests, so the user would have to create this file manually
    and so would be aware enough to tell yt-dlp to use the BASIC_TEXT keyring.

    References:
        - [1] https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/os_crypt/sync/key_storage_util_linux.cc
    """
    desktop_environment = _get_linux_desktop_environment(os.environ, logger)
    logger.debug(f'detected desktop environment: {desktop_environment.name}')
    if desktop_environment == _LinuxDesktopEnvironment.KDE4:
        linux_keyring = _LinuxKeyring.KWALLET
    elif desktop_environment == _LinuxDesktopEnvironment.KDE5:
        linux_keyring = _LinuxKeyring.KWALLET5
    elif desktop_environment == _LinuxDesktopEnvironment.KDE6:
        linux_keyring = _LinuxKeyring.KWALLET6
    elif desktop_environment in (
        _LinuxDesktopEnvironment.KDE3, _LinuxDesktopEnvironment.LXQT, _LinuxDesktopEnvironment.OTHER,
    ):
        linux_keyring = _LinuxKeyring.BASICTEXT
    else:
        linux_keyring = _LinuxKeyring.GNOMEKEYRING
    return linux_keyring


def _get_kwallet_network_wallet(keyring, logger):
    """ The name of the wallet used to store network passwords.

    https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/os_crypt/sync/kwallet_dbus.cc
    KWalletDBus::NetworkWallet
    which does a dbus call to the following function:
    https://api.kde.org/frameworks/kwallet/html/classKWallet_1_1Wallet.html
    Wallet::NetworkWallet
    """
    default_wallet = 'kdewallet'
    try:
        if keyring == _LinuxKeyring.KWALLET:
            service_name = 'org.kde.kwalletd'
            wallet_path = '/modules/kwalletd'
        elif keyring == _LinuxKeyring.KWALLET5:
            service_name = 'org.kde.kwalletd5'
            wallet_path = '/modules/kwalletd5'
        elif keyring == _LinuxKeyring.KWALLET6:
            service_name = 'org.kde.kwalletd6'
            wallet_path = '/modules/kwalletd6'
        else:
            raise ValueError(keyring)

        stdout, _, returncode = Popen.run([
            'dbus-send', '--session', '--print-reply=literal',
            f'--dest={service_name}',
            wallet_path,
            'org.kde.KWallet.networkWallet',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        if returncode:
            logger.warning('failed to read NetworkWallet')
            return default_wallet
        else:
            logger.debug(f'NetworkWallet = "{stdout.strip()}"')
            return stdout.strip()
    except Exception as e:
        logger.warning(f'exception while obtaining NetworkWallet: {e}')
        return default_wallet


def _get_kwallet_password(browser_keyring_name, keyring, logger):
    logger.debug(f'using kwallet-query to obtain password from {keyring.name}')

    if shutil.which('kwallet-query') is None:
        logger.error('kwallet-query command not found. KWallet and kwallet-query '
                     'must be installed to read from KWallet. kwallet-query should be'
                     'included in the kwallet package for your distribution')
        return b''

    network_wallet = _get_kwallet_network_wallet(keyring, logger)

    try:
        stdout, _, returncode = Popen.run([
            'kwallet-query',
            '--read-password', f'{browser_keyring_name} Safe Storage',
            '--folder', f'{browser_keyring_name} Keys',
            network_wallet,
        ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        if returncode:
            logger.error(f'kwallet-query failed with return code {returncode}. '
                         'Please consult the kwallet-query man page for details')
            return b''
        else:
            if stdout.lower().startswith(b'failed to read'):
                logger.debug('failed to read password from kwallet. Using empty string instead')
                # this sometimes occurs in KDE because chrome does not check hasEntry and instead
                # just tries to read the value (which kwallet returns "") whereas kwallet-query
                # checks hasEntry. To verify this:
                # dbus-monitor "interface='org.kde.KWallet'" "type=method_return"
                # while starting chrome.
                # this was identified as a bug later and fixed in
                # https://chromium.googlesource.com/chromium/src/+/bbd54702284caca1f92d656fdcadf2ccca6f4165%5E%21/#F0
                # https://chromium.googlesource.com/chromium/src/+/5463af3c39d7f5b6d11db7fbd51e38cc1974d764
                return b''
            else:
                logger.debug('password found')
                return stdout.rstrip(b'\n')
    except Exception as e:
        logger.warning(f'exception running kwallet-query: {error_to_str(e)}')
        return b''


def _get_gnome_keyring_password(browser_keyring_name, logger):
    if not secretstorage:
        logger.error(f'secretstorage not available {_SECRETSTORAGE_UNAVAILABLE_REASON}')
        return b''
    # the Gnome keyring does not seem to organise keys in the same way as KWallet,
    # using `dbus-monitor` during startup, it can be observed that chromium lists all keys
    # and presumably searches for its key in the list. It appears that we must do the same.
    # https://github.com/jaraco/keyring/issues/556
    with contextlib.closing(secretstorage.dbus_init()) as con:
        col = secretstorage.get_default_collection(con)
        for item in col.get_all_items():
            if item.get_label() == f'{browser_keyring_name} Safe Storage':
                return item.get_secret()
        logger.error('failed to read from keyring')
        return b''


def _get_linux_keyring_password(browser_keyring_name, keyring, logger):
    # note: chrome/chromium can be run with the following flags to determine which keyring backend
    # it has chosen to use
    # chromium --enable-logging=stderr --v=1 2>&1 | grep key_storage_
    # Chromium supports a flag: --password-store=<basic|gnome|kwallet> so the automatic detection
    # will not be sufficient in all cases.

    keyring = _LinuxKeyring[keyring] if keyring else _choose_linux_keyring(logger)
    logger.debug(f'Chosen keyring: {keyring.name}')

    if keyring in (_LinuxKeyring.KWALLET, _LinuxKeyring.KWALLET5, _LinuxKeyring.KWALLET6):
        return _get_kwallet_password(browser_keyring_name, keyring, logger)
    elif keyring == _LinuxKeyring.GNOMEKEYRING:
        return _get_gnome_keyring_password(browser_keyring_name, logger)
    elif keyring == _LinuxKeyring.BASICTEXT:
        # when basic text is chosen, all cookies are stored as v10 (so no keyring password is required)
        return None
    assert False, f'Unknown keyring {keyring}'


def _get_mac_keyring_password(browser_keyring_name, logger):
    logger.debug('using find-generic-password to obtain password from OSX keychain')
    try:
        stdout, _, returncode = Popen.run(
            ['security', 'find-generic-password',
             '-w',  # write password to stdout
             '-a', browser_keyring_name,  # match 'account'
             '-s', f'{browser_keyring_name} Safe Storage'],  # match 'service'
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if returncode:
            logger.warning('find-generic-password failed')
            return None
        return stdout.rstrip(b'\n')
    except Exception as e:
        logger.warning(f'exception running find-generic-password: {error_to_str(e)}')
        return None


def _get_windows_v10_key(browser_root, logger):
    """
    References:
        - [1] https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/os_crypt/sync/os_crypt_win.cc
    """
    path = _newest(_find_files(browser_root, 'Local State', logger))
    if path is None:
        logger.error('could not find local state file')
        return None
    logger.debug(f'Found local state file at "{path}"')
    with open(path, encoding='utf8') as f:
        data = json.load(f)
    try:
        # kOsCryptEncryptedKeyPrefName in [1]
        base64_key = data['os_crypt']['encrypted_key']
    except KeyError:
        logger.error('no encrypted key in Local State')
        return None
    encrypted_key = base64.b64decode(base64_key)
    # kDPAPIKeyPrefix in [1]
    prefix = b'DPAPI'
    if not encrypted_key.startswith(prefix):
        logger.error('invalid key')
        return None
    return _decrypt_windows_dpapi(encrypted_key[len(prefix):], logger)


def pbkdf2_sha1(password, salt, iterations, key_length):
    return hashlib.pbkdf2_hmac('sha1', password, salt, iterations, key_length)


def _decrypt_aes_cbc_multi(ciphertext, keys, logger, initialization_vector=b' ' * 16):
    for key in keys:
        plaintext = unpad_pkcs7(aes_cbc_decrypt_bytes(ciphertext, key, initialization_vector))
        try:
            return plaintext.decode()
        except UnicodeDecodeError:
            pass
    logger.warning('failed to decrypt cookie (AES-CBC) because UTF-8 decoding failed. Possibly the key is wrong?', only_once=True)
    return None


def _decrypt_aes_gcm(ciphertext, key, nonce, authentication_tag, logger):
    try:
        plaintext = aes_gcm_decrypt_and_verify_bytes(ciphertext, key, authentication_tag, nonce)
    except ValueError:
        logger.warning('failed to decrypt cookie (AES-GCM) because the MAC check failed. Possibly the key is wrong?', only_once=True)
        return None

    try:
        return plaintext.decode()
    except UnicodeDecodeError:
        logger.warning('failed to decrypt cookie (AES-GCM) because UTF-8 decoding failed. Possibly the key is wrong?', only_once=True)
        return None


def _decrypt_windows_dpapi(ciphertext, logger):
    """
    References:
        - https://docs.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata
    """

    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [('cbData', ctypes.wintypes.DWORD),
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
        ctypes.byref(blob_out),  # pDataOut
    )
    if not ret:
        logger.warning('failed to decrypt with DPAPI', only_once=True)
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
    table_info = cursor.execute(f'PRAGMA table_info({table_name})').fetchall()
    return [row[1].decode() for row in table_info]


def _newest(files):
    return max(files, key=lambda path: os.lstat(path).st_mtime, default=None)


def _find_files(root, filename, logger):
    # if there are multiple browser profiles, take the most recently used one
    i = 0
    with _create_progress_bar(logger) as progress_bar:
        for curr_root, _, files in os.walk(root):
            for file in files:
                i += 1
                progress_bar.print(f'Searching for "{filename}": {i: 6d} files searched')
                if file == filename:
                    yield os.path.join(curr_root, file)


def _merge_cookie_jars(jars):
    output_jar = YoutubeDLCookieJar()
    for jar in jars:
        for cookie in jar:
            output_jar.set_cookie(cookie)
        if jar.filename is not None:
            output_jar.filename = jar.filename
    return output_jar


def _is_path(value):
    return any(sep in value for sep in (os.path.sep, os.path.altsep) if sep)


def _parse_browser_specification(browser_name, profile=None, keyring=None, container=None):
    if browser_name not in SUPPORTED_BROWSERS:
        raise ValueError(f'unsupported browser: "{browser_name}"')
    if keyring not in (None, *SUPPORTED_KEYRINGS):
        raise ValueError(f'unsupported keyring: "{keyring}"')
    if profile is not None and _is_path(expand_path(profile)):
        profile = expand_path(profile)
    return browser_name, profile, keyring, container


class LenientSimpleCookie(http.cookies.SimpleCookie):
    """More lenient version of http.cookies.SimpleCookie"""
    # From https://github.com/python/cpython/blob/v3.10.7/Lib/http/cookies.py
    # We use Morsel's legal key chars to avoid errors on setting values
    _LEGAL_KEY_CHARS = r'\w\d' + re.escape('!#$%&\'*+-.:^_`|~')
    _LEGAL_VALUE_CHARS = _LEGAL_KEY_CHARS + re.escape('(),/<=>?@[]{}')

    _RESERVED = {
        'expires',
        'path',
        'comment',
        'domain',
        'max-age',
        'secure',
        'httponly',
        'version',
        'samesite',
    }

    _FLAGS = {'secure', 'httponly'}

    # Added 'bad' group to catch the remaining value
    _COOKIE_PATTERN = re.compile(r'''
        \s*                            # Optional whitespace at start of cookie
        (?P<key>                       # Start of group 'key'
        [''' + _LEGAL_KEY_CHARS + r''']+?# Any word of at least one letter
        )                              # End of group 'key'
        (                              # Optional group: there may not be a value.
        \s*=\s*                          # Equal Sign
        (                                # Start of potential value
        (?P<val>                           # Start of group 'val'
        "(?:[^\\"]|\\.)*"                    # Any doublequoted string
        |                                    # or
        \w{3},\s[\w\d\s-]{9,11}\s[\d:]{8}\sGMT # Special case for "expires" attr
        |                                    # or
        [''' + _LEGAL_VALUE_CHARS + r''']*     # Any word or empty string
        )                                  # End of group 'val'
        |                                  # or
        (?P<bad>(?:\\;|[^;])*?)            # 'bad' group fallback for invalid values
        )                                # End of potential value
        )?                             # End of optional value group
        \s*                            # Any number of spaces.
        (\s+|;|$)                      # Ending either at space, semicolon, or EOS.
        ''', re.ASCII | re.VERBOSE)

    def load(self, data):
        # Workaround for https://github.com/yt-dlp/yt-dlp/issues/4776
        if not isinstance(data, str):
            return super().load(data)

        morsel = None
        for match in self._COOKIE_PATTERN.finditer(data):
            if match.group('bad'):
                morsel = None
                continue

            key, value = match.group('key', 'val')

            is_attribute = False
            if key.startswith('$'):
                key = key[1:]
                is_attribute = True

            lower_key = key.lower()
            if lower_key in self._RESERVED:
                if morsel is None:
                    continue

                if value is None:
                    if lower_key not in self._FLAGS:
                        morsel = None
                        continue
                    value = True
                else:
                    value, _ = self.value_decode(value)

                morsel[key] = value

            elif is_attribute:
                morsel = None

            elif value is not None:
                morsel = self.get(key, http.cookies.Morsel())
                real_value, coded_value = self.value_decode(value)
                morsel.set(key, real_value, coded_value)
                self[key] = morsel

            else:
                morsel = None


class YoutubeDLCookieJar(http.cookiejar.MozillaCookieJar):
    """
    See [1] for cookie file format.

    1. https://curl.haxx.se/docs/http-cookies.html
    """
    _HTTPONLY_PREFIX = '#HttpOnly_'
    _ENTRY_LEN = 7
    _HEADER = '''# Netscape HTTP Cookie File
# This file is generated by yt-dlp.  Do not edit.

'''
    _CookieFileEntry = collections.namedtuple(
        'CookieFileEntry',
        ('domain_name', 'include_subdomains', 'path', 'https_only', 'expires_at', 'name', 'value'))

    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(None, *args, **kwargs)
        if is_path_like(filename):
            filename = os.fspath(filename)
        self.filename = filename

    @staticmethod
    def _true_or_false(cndn):
        return 'TRUE' if cndn else 'FALSE'

    @contextlib.contextmanager
    def open(self, file, *, write=False):
        if is_path_like(file):
            with open(file, 'w' if write else 'r', encoding='utf-8') as f:
                yield f
        else:
            if write:
                file.truncate(0)
            yield file

    def _really_save(self, f, ignore_discard, ignore_expires):
        now = time.time()
        for cookie in self:
            if (not ignore_discard and cookie.discard
                    or not ignore_expires and cookie.is_expired(now)):
                continue
            name, value = cookie.name, cookie.value
            if value is None:
                # cookies.txt regards 'Set-Cookie: foo' as a cookie
                # with no name, whereas http.cookiejar regards it as a
                # cookie with no value.
                name, value = '', name
            f.write('{}\n'.format('\t'.join((
                cookie.domain,
                self._true_or_false(cookie.domain.startswith('.')),
                cookie.path,
                self._true_or_false(cookie.secure),
                str_or_none(cookie.expires, default=''),
                name, value,
            ))))

    def save(self, filename=None, ignore_discard=True, ignore_expires=True):
        """
        Save cookies to a file.
        Code is taken from CPython 3.6
        https://github.com/python/cpython/blob/8d999cbf4adea053be6dbb612b9844635c4dfb8e/Lib/http/cookiejar.py#L2091-L2117 """

        if filename is None:
            if self.filename is not None:
                filename = self.filename
            else:
                raise ValueError(http.cookiejar.MISSING_FILENAME_TEXT)

        # Store session cookies with `expires` set to 0 instead of an empty string
        for cookie in self:
            if cookie.expires is None:
                cookie.expires = 0

        with self.open(filename, write=True) as f:
            f.write(self._HEADER)
            self._really_save(f, ignore_discard, ignore_expires)

    def load(self, filename=None, ignore_discard=True, ignore_expires=True):
        """Load cookies from a file."""
        if filename is None:
            if self.filename is not None:
                filename = self.filename
            else:
                raise ValueError(http.cookiejar.MISSING_FILENAME_TEXT)

        def prepare_line(line):
            if line.startswith(self._HTTPONLY_PREFIX):
                line = line[len(self._HTTPONLY_PREFIX):]
            # comments and empty lines are fine
            if line.startswith('#') or not line.strip():
                return line
            cookie_list = line.split('\t')
            if len(cookie_list) != self._ENTRY_LEN:
                raise http.cookiejar.LoadError(f'invalid length {len(cookie_list)}')
            cookie = self._CookieFileEntry(*cookie_list)
            if cookie.expires_at and not cookie.expires_at.isdigit():
                raise http.cookiejar.LoadError(f'invalid expires at {cookie.expires_at}')
            return line

        cf = io.StringIO()
        with self.open(filename) as f:
            for line in f:
                try:
                    cf.write(prepare_line(line))
                except http.cookiejar.LoadError as e:
                    if f'{line.strip()} '[0] in '[{"':
                        raise http.cookiejar.LoadError(
                            'Cookies file must be Netscape formatted, not JSON. See  '
                            'https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp')
                    write_string(f'WARNING: skipping cookie file entry due to {e}: {line!r}\n')
                    continue
        cf.seek(0)
        self._really_load(cf, filename, ignore_discard, ignore_expires)
        # Session cookies are denoted by either `expires` field set to
        # an empty string or 0. MozillaCookieJar only recognizes the former
        # (see [1]). So we need force the latter to be recognized as session
        # cookies on our own.
        # Session cookies may be important for cookies-based authentication,
        # e.g. usually, when user does not check 'Remember me' check box while
        # logging in on a site, some important cookies are stored as session
        # cookies so that not recognizing them will result in failed login.
        # 1. https://bugs.python.org/issue17164
        for cookie in self:
            # Treat `expires=0` cookies as session cookies
            if cookie.expires == 0:
                cookie.expires = None
                cookie.discard = True

    def get_cookie_header(self, url):
        """Generate a Cookie HTTP header for a given url"""
        cookie_req = urllib.request.Request(normalize_url(sanitize_url(url)))
        self.add_cookie_header(cookie_req)
        return cookie_req.get_header('Cookie')

    def get_cookies_for_url(self, url):
        """Generate a list of Cookie objects for a given url"""
        # Policy `_now` attribute must be set before calling `_cookies_for_request`
        # Ref: https://github.com/python/cpython/blob/3.7/Lib/http/cookiejar.py#L1360
        self._policy._now = self._now = int(time.time())
        return self._cookies_for_request(urllib.request.Request(normalize_url(sanitize_url(url))))

    def clear(self, *args, **kwargs):
        with contextlib.suppress(KeyError):
            return super().clear(*args, **kwargs)
