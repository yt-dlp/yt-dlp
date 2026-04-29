import requests
from dataclasses import dataclass
from pathlib import Path
import hashlib

DEFAULT_OUTPUT = 'THIRD_PARTY_LICENSES.txt'
CACHE_LOCATION = '.license_cache'
HEADER = '''THIRD-PARTY LICENSES

This file aggregates license texts of third-party components included with the yt-dlp PyInstaller-bundled executables.
yt-dlp itself is licensed under the Unlicense (see LICENSE file).
Source code for bundled third-party components is available from the original projects.
If you cannot obtain it, the maintainers will provide it as per license obligation; maintainer emails are listed in pyproject.toml.'''


@dataclass(frozen=True)
class Dependency:
    name: str
    license_url: str
    project_url: str = ''
    license: str = ''
    comment: str = ''


DEPENDENCIES: list[Dependency] = [
    # Core runtime environment components
    Dependency(
        name='Python',
        license='PSF-2.0',
        license_url='https://raw.githubusercontent.com/python/cpython/refs/heads/main/LICENSE',
        project_url='https://www.python.org/',
    ),
    Dependency(
        name='Microsoft Distributable Code',
        license_url='https://raw.githubusercontent.com/python/cpython/refs/heads/main/PC/crtlicense.txt',
        comment='Only included in Windows builds',
    ),
    Dependency(
        name='bzip2',
        license='bzip2-1.0.6',
        license_url='https://gitlab.com/federicomenaquintero/bzip2/-/raw/master/COPYING',
        project_url='https://sourceware.org/bzip2/',
    ),
    Dependency(
        name='libffi',
        license='MIT',
        license_url='https://raw.githubusercontent.com/libffi/libffi/refs/heads/master/LICENSE',
        project_url='https://sourceware.org/libffi/',
    ),
    Dependency(
        name='OpenSSL 3.0+',
        license='Apache-2.0',
        license_url='https://raw.githubusercontent.com/openssl/openssl/refs/heads/master/LICENSE.txt',
        project_url='https://www.openssl.org/',
    ),
    Dependency(
        name='SQLite',
        license='Public Domain',  # Technically does not need to be included
        license_url='https://sqlite.org/src/raw/e108e1e69ae8e8a59e93c455654b8ac9356a11720d3345df2a4743e9590fb20d?at=LICENSE.md',
        project_url='https://www.sqlite.org/',
    ),
    Dependency(
        name='liblzma',
        license='0BSD',  # Technically does not need to be included
        license_url='https://raw.githubusercontent.com/tukaani-project/xz/refs/heads/master/COPYING',
        project_url='https://tukaani.org/xz/',
    ),
    Dependency(
        name='mpdecimal',
        license='BSD-2-Clause',
        # No official repo URL
        license_url='https://gist.githubusercontent.com/seproDev/9e5dbfc08af35c3f2463e64eb9b27161/raw/61f5a98bc1a4ad7d48b1c793fc3314d4d43c2ab1/mpdecimal_COPYRIGHT.txt',
        project_url='https://www.bytereef.org/mpdecimal/',
    ),
    Dependency(
        name='zlib',
        license='zlib',
        license_url='https://raw.githubusercontent.com/madler/zlib/refs/heads/develop/LICENSE',
        project_url='https://zlib.net/',
    ),
    Dependency(
        name='Expat',
        license='MIT',
        license_url='https://raw.githubusercontent.com/libexpat/libexpat/refs/heads/master/COPYING',
        project_url='https://libexpat.github.io/',
    ),
    Dependency(
        name='ncurses',
        license='X11-distribute-modifications-variant',
        license_url='https://raw.githubusercontent.com/mirror/ncurses/refs/heads/master/COPYING',
        comment='Only included in Linux/macOS builds',
        project_url='https://invisible-island.net/ncurses/',
    ),
    Dependency(
        name='GNU Readline',
        license='GPL-3.0-or-later',
        license_url='https://tiswww.case.edu/php/chet/readline/COPYING',
        comment='Only included in Linux builds',
        project_url='https://www.gnu.org/software/readline/',
    ),
    Dependency(
        name='libstdc++',
        license='GPL-3.0-with-GCC-exception',
        license_url='https://raw.githubusercontent.com/gcc-mirror/gcc/refs/heads/master/COPYING.RUNTIME',
        comment='Only included in Linux builds',
        project_url='https://gcc.gnu.org/onlinedocs/libstdc++/',
    ),
    Dependency(
        name='libgcc',
        license='GPL-3.0-with-GCC-exception',
        license_url='https://raw.githubusercontent.com/gcc-mirror/gcc/refs/heads/master/COPYING.RUNTIME',
        comment='Only included in Linux builds',
        project_url='https://gcc.gnu.org/',
    ),
    Dependency(
        name='libuuid',
        license='BSD-3-Clause',
        license_url='https://git.kernel.org/pub/scm/fs/ext2/e2fsprogs.git/plain/lib/uuid/COPYING',
        comment='Only included in Linux builds',
        project_url='https://git.kernel.org/pub/scm/fs/ext2/e2fsprogs.git/tree/lib/uuid',
    ),
    Dependency(
        name='libintl',
        license='LGPL-2.1-or-later',
        license_url='https://raw.githubusercontent.com/autotools-mirror/gettext/refs/heads/master/gettext-runtime/intl/COPYING.LIB',
        comment='Only included in macOS builds',
        project_url='https://www.gnu.org/software/gettext/',
    ),
    Dependency(
        name='libidn2',
        license='LGPL-3.0-or-later',
        license_url='https://gitlab.com/libidn/libidn2/-/raw/master/COPYING.LESSERv3',
        comment='Only included in macOS builds',
        project_url='https://www.gnu.org/software/libidn/',
    ),
    Dependency(
        name='libidn2 (Unicode character data files)',
        license='Unicode-TOU AND Unicode-DFS-2016',
        license_url='https://gitlab.com/libidn/libidn2/-/raw/master/COPYING.unicode',
        comment='Only included in macOS builds',
        project_url='https://www.gnu.org/software/libidn/',
    ),
    Dependency(
        name='libunistring',
        license='LGPL-3.0-or-later',
        license_url='https://gitweb.git.savannah.gnu.org/gitweb/?p=libunistring.git;a=blob_plain;f=COPYING.LIB;hb=HEAD',
        comment='Only included in macOS builds',
        project_url='https://www.gnu.org/software/libunistring/',
    ),
    Dependency(
        name='librtmp',
        license='LGPL-2.1-or-later',
        # No official repo URL
        license_url='https://gist.githubusercontent.com/seproDev/31d8c691ccddebe37b8b379307cb232d/raw/053408e98547ea8c7d9ba3a80c965f33e163b881/librtmp_COPYING.txt',
        comment='Only included in macOS builds',
        project_url='https://rtmpdump.mplayerhq.hu/',
    ),
    Dependency(
        name='zstd',
        license='BSD-3-Clause',
        license_url='https://raw.githubusercontent.com/facebook/zstd/refs/heads/dev/LICENSE',
        comment='Only included in macOS builds',
        project_url='https://facebook.github.io/zstd/',
    ),

    # Python packages
    Dependency(
        name='brotli',
        license='MIT',
        license_url='https://raw.githubusercontent.com/google/brotli/refs/heads/master/LICENSE',
        project_url='https://brotli.org/',
    ),
    Dependency(
        name='curl_cffi',
        license='MIT',
        license_url='https://raw.githubusercontent.com/lexiforest/curl_cffi/refs/heads/main/LICENSE',
        comment='Not included in `yt-dlp_x86` and `yt-dlp_musllinux_aarch64` builds',
        project_url='https://curl-cffi.readthedocs.io/',
    ),
    # Dependency of curl_cffi
    Dependency(
        name='curl-impersonate',
        license='MIT',
        license_url='https://raw.githubusercontent.com/lexiforest/curl-impersonate/refs/heads/main/LICENSE',
        comment='Not included in `yt-dlp_x86` and `yt-dlp_musllinux_aarch64` builds',
        project_url='https://github.com/lexiforest/curl-impersonate',
    ),
    Dependency(
        name='cffi',
        license='MIT-0',  # Technically does not need to be included
        license_url='https://raw.githubusercontent.com/python-cffi/cffi/refs/heads/main/LICENSE',
        project_url='https://cffi.readthedocs.io/',
    ),
    # Dependecy of cffi
    Dependency(
        name='pycparser',
        license='BSD-3-Clause',
        license_url='https://raw.githubusercontent.com/eliben/pycparser/refs/heads/main/LICENSE',
        project_url='https://github.com/eliben/pycparser',
    ),
    Dependency(
        name='mutagen',
        license='GPL-2.0-or-later',
        license_url='https://raw.githubusercontent.com/quodlibet/mutagen/refs/heads/main/COPYING',
        project_url='https://mutagen.readthedocs.io/',
    ),
    Dependency(
        name='PyCryptodome',
        license='Public Domain and BSD-2-Clause',
        license_url='https://raw.githubusercontent.com/Legrandin/pycryptodome/refs/heads/master/LICENSE.rst',
        project_url='https://www.pycryptodome.org/',
    ),
    Dependency(
        name='certifi',
        license='MPL-2.0',
        license_url='https://raw.githubusercontent.com/certifi/python-certifi/refs/heads/master/LICENSE',
        project_url='https://github.com/certifi/python-certifi',
    ),
    Dependency(
        name='requests',
        license='Apache-2.0',
        license_url='https://raw.githubusercontent.com/psf/requests/refs/heads/main/LICENSE',
        project_url='https://requests.readthedocs.io/',
    ),
    # Dependency of requests
    Dependency(
        name='charset-normalizer',
        license='MIT',
        license_url='https://raw.githubusercontent.com/jawah/charset_normalizer/refs/heads/master/LICENSE',
        project_url='https://charset-normalizer.readthedocs.io/',
    ),
    # Dependency of requests
    Dependency(
        name='idna',
        license='BSD-3-Clause',
        license_url='https://raw.githubusercontent.com/kjd/idna/refs/heads/master/LICENSE.md',
        project_url='https://github.com/kjd/idna',
    ),
    Dependency(
        name='urllib3',
        license='MIT',
        license_url='https://raw.githubusercontent.com/urllib3/urllib3/refs/heads/main/LICENSE.txt',
        project_url='https://urllib3.readthedocs.io/',
    ),
    Dependency(
        name='SecretStorage',
        license='BSD-3-Clause',
        license_url='https://raw.githubusercontent.com/mitya57/secretstorage/refs/heads/master/LICENSE',
        comment='Only included in Linux builds',
        project_url='https://secretstorage.readthedocs.io/',
    ),
    # Dependency of SecretStorage
    Dependency(
        name='cryptography',
        license='Apache-2.0',  # Also available as BSD-3-Clause
        license_url='https://raw.githubusercontent.com/pyca/cryptography/refs/heads/main/LICENSE.APACHE',
        comment='Only included in Linux builds',
        project_url='https://cryptography.io/',
    ),
    # Dependency of SecretStorage
    Dependency(
        name='Jeepney',
        license='MIT',
        license_url='https://gitlab.com/takluyver/jeepney/-/raw/master/LICENSE',
        comment='Only included in Linux builds',
        project_url='https://jeepney.readthedocs.io/',
    ),
    Dependency(
        name='websockets',
        license='BSD-3-Clause',
        license_url='https://raw.githubusercontent.com/python-websockets/websockets/refs/heads/main/LICENSE',
        project_url='https://websockets.readthedocs.io/',
    ),
    # Dependencies of yt-dlp-ejs
    Dependency(
        name='Meriyah',
        license='ISC',
        license_url='https://raw.githubusercontent.com/meriyah/meriyah/refs/heads/main/LICENSE.md',
        project_url='https://github.com/meriyah/meriyah',
    ),
    Dependency(
        name='Astring',
        license='MIT',
        license_url='https://raw.githubusercontent.com/davidbonnet/astring/refs/heads/main/LICENSE',
        project_url='https://github.com/davidbonnet/astring/',
    ),
]


def fetch_text(dep: Dependency) -> str:
    cache_dir = Path(CACHE_LOCATION)
    cache_dir.mkdir(exist_ok=True)
    url_hash = hashlib.sha256(dep.license_url.encode('utf-8')).hexdigest()
    cache_file = cache_dir / f'{url_hash}.txt'

    if cache_file.exists():
        return cache_file.read_text()

    # UA needed since some domains block requests default UA
    req = requests.get(dep.license_url, headers={'User-Agent': 'yt-dlp license fetcher'})
    req.raise_for_status()
    text = req.text
    cache_file.write_text(text)
    return text


def build_output() -> str:
    lines = [HEADER]
    for d in DEPENDENCIES:
        lines.append('\n')
        lines.append('-' * 80)
        header = f'{d.name}'
        if d.license:
            header += f' | {d.license}'
        if d.comment:
            header += f'\nNote: {d.comment}'
        if d.project_url:
            header += f'\nURL: {d.project_url}'
        lines.append(header)
        lines.append('-' * 80)

        text = fetch_text(d)
        lines.append(text.strip('\n') + '\n')
    return '\n'.join(lines)


if __name__ == '__main__':
    content = build_output()
    Path(DEFAULT_OUTPUT).write_text(content)
