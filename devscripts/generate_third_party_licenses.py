import requests
from dataclasses import dataclass
from pathlib import Path
import hashlib

DEFAULT_OUTPUT = 'THIRD_PARTY_LICENSES.txt'

@dataclass(frozen=True)
class Dependency:
    name: str
    source_url: str
    license: str = ''
    comment: str = ''


DEPENDENCIES: list[Dependency] = [
    # Core runtime environment components
    Dependency(
        name='Python',
        license='PSF-2.0',
        source_url='https://raw.githubusercontent.com/python/cpython/refs/heads/main/LICENSE',
    ),
    Dependency(
        name='Microsoft Distributable Code',
        source_url='https://raw.githubusercontent.com/python/cpython/refs/heads/main/PC/crtlicense.txt',
        comment='Only included in Windows builds',
    ),
    Dependency(
        name='bzip2',
        license='bzip2-1.0.6',
        source_url='https://gitlab.com/federicomenaquintero/bzip2/-/raw/master/COPYING',
    ),
    Dependency(
        name='libffi',
        license='MIT',
        source_url='https://raw.githubusercontent.com/libffi/libffi/refs/heads/master/LICENSE',
    ),
    Dependency(
        name='OpenSSL 3.0+',
        license='Apache-2.0',
        source_url='https://raw.githubusercontent.com/openssl/openssl/refs/heads/master/LICENSE.txt',
    ),
    Dependency(
        name='SQLite',
        license='Public Domain', # Technically does not need to be included
        source_url='https://sqlite.org/src/raw/e108e1e69ae8e8a59e93c455654b8ac9356a11720d3345df2a4743e9590fb20d?at=LICENSE.md',
    ),
    Dependency(
        name='liblzma',
        license='0BSD', # Technically does not need to be included
        source_url='https://raw.githubusercontent.com/tukaani-project/xz/refs/heads/master/COPYING',
    ),
    Dependency(
        name='mpdecimal',
        license='BSD-2-Clause',
        source_url='https://gist.githubusercontent.com/seproDev/9e5dbfc08af35c3f2463e64eb9b27161/raw/61f5a98bc1a4ad7d48b1c793fc3314d4d43c2ab1/mpdecimal_COPYRIGHT.txt', # No official repo URL
    ),
    Dependency(
        name='zlib',
        license='zlib',
        source_url='https://raw.githubusercontent.com/madler/zlib/refs/heads/develop/LICENSE',
    ),
    Dependency(
        name='ncurses',
        license='X11-distribute-modifications-variant',
        source_url='https://raw.githubusercontent.com/mirror/ncurses/refs/heads/master/COPYING',
        comment='Only included in Linux/macOS builds',
    ),
    Dependency(
        name='GNU Readline',
        license='GPL-3.0-or-later',
        source_url='https://tiswww.case.edu/php/chet/readline/COPYING',
        comment='Only included in Linux builds',
    ),
    Dependency(
        name='libstdc++',
        license='GPL-3.0-with-GCC-exception',
        source_url='https://raw.githubusercontent.com/gcc-mirror/gcc/refs/heads/master/COPYING.RUNTIME',
        comment='Only included in Linux builds',
    ),
    Dependency(
        name='libgcc',
        license='GPL-3.0-with-GCC-exception',
        source_url='https://raw.githubusercontent.com/gcc-mirror/gcc/refs/heads/master/COPYING.RUNTIME',
        comment='Only included in Linux builds',
    ),
    Dependency(
        name='libuuid',
        license='BSD-3-Clause',
        source_url='https://git.kernel.org/pub/scm/fs/ext2/e2fsprogs.git/plain/lib/uuid/COPYING',
        comment='Only included in Linux builds',
    ),
    Dependency(
        name='libintl',
        license='LGPL-2.1-or-later',
        source_url='https://raw.githubusercontent.com/autotools-mirror/gettext/refs/heads/master/gettext-runtime/intl/COPYING.LIB',
        comment='Only included in macOS builds',
    ),
    Dependency(
        name='libidn2',
        license='LGPL-3.0-or-later',
        source_url='https://gitlab.com/libidn/libidn2/-/raw/master/COPYING.LESSERv3',
        comment='Only included in macOS builds',
    ),
    Dependency(
        name='libidn2 (Unicode character data files)',
        license='Unicode-TOU AND Unicode-DFS-2016',
        source_url='https://gitlab.com/libidn/libidn2/-/raw/master/COPYING.unicode',
        comment='Only included in macOS builds',
    ),
    Dependency(
        name='libunistring',
        license='LGPL-3.0-or-later',
        source_url='https://gitweb.git.savannah.gnu.org/gitweb/?p=libunistring.git;a=blob_plain;f=COPYING.LIB;hb=HEAD',
        comment='Only included in macOS builds',
    ),
    Dependency(
        name='librtmp',
        license='LGPL-2.1-or-later',
        source_url='https://gist.githubusercontent.com/seproDev/31d8c691ccddebe37b8b379307cb232d/raw/053408e98547ea8c7d9ba3a80c965f33e163b881/librtmp_COPYING.txt', # No official repo URL
        comment='Only included in macOS builds',
    ),
    Dependency(
        name='zstd',
        license='BSD-3-Clause',
        source_url='https://raw.githubusercontent.com/facebook/zstd/refs/heads/dev/LICENSE',
        comment='Only included in macOS builds',
    ),

    # Python packages
    Dependency(
        name='brotli',
        license='MIT',
        source_url='https://raw.githubusercontent.com/google/brotli/refs/heads/master/LICENSE',
    ),
    Dependency(
        name='curl_cffi',
        license='MIT',
        source_url='https://raw.githubusercontent.com/lexiforest/curl_cffi/refs/heads/main/LICENSE',
        comment='Not included in `yt-dlp_x86` and `yt-dlp_musllinux_aarch64` builds',
    ),
    # Dependency of curl_cffi
    Dependency(
        name='curl-impersonate',
        license='MIT',
        source_url='https://raw.githubusercontent.com/lexiforest/curl-impersonate/refs/heads/main/LICENSE',
        comment='Not included in `yt-dlp_x86` and `yt-dlp_musllinux_aarch64` builds',
    ),
    Dependency(
        name='cffi',
        license='MIT-0', # Technically does not need to be included
        source_url='https://raw.githubusercontent.com/python-cffi/cffi/refs/heads/main/LICENSE',
    ),
    # Dependecy of cffi
    Dependency(
        name='pycparser',
        license='BSD-3-Clause',
        source_url='https://raw.githubusercontent.com/eliben/pycparser/refs/heads/main/LICENSE',
    ),
    Dependency(
        name='mutagen',
        license='GPL-2.0-or-later',
        source_url='https://raw.githubusercontent.com/quodlibet/mutagen/refs/heads/main/COPYING',
    ),
    Dependency(
        name='PyCryptodome',
        license='Public Domain and BSD-2-Clause',
        source_url='https://raw.githubusercontent.com/Legrandin/pycryptodome/refs/heads/master/LICENSE.rst',
    ),
    Dependency(
        name='certifi',
        license='MPL-2.0',
        source_url='https://raw.githubusercontent.com/certifi/python-certifi/refs/heads/master/LICENSE',
    ),
    Dependency(
        name='requests',
        license='Apache-2.0',
        source_url='https://raw.githubusercontent.com/psf/requests/refs/heads/main/LICENSE',
    ),
    # Dependencies of requests
    Dependency(
        name='charset-normalizer',
        license='MIT',
        source_url='https://raw.githubusercontent.com/jawah/charset_normalizer/refs/heads/master/LICENSE',
    ),
    # Dependencies of requests
    Dependency(
        name='idna',
        license='BSD-3-Clause',
        source_url='https://raw.githubusercontent.com/kjd/idna/refs/heads/master/LICENSE.md',
    ),
    Dependency(
        name='urllib3',
        license='MIT',
        source_url='https://raw.githubusercontent.com/urllib3/urllib3/refs/heads/main/LICENSE.txt',
    ),
    Dependency(
        name='SecretStorage',
        license='BSD-3-Clause',
        source_url='https://raw.githubusercontent.com/mitya57/secretstorage/refs/heads/master/LICENSE',
        comment='Only included in Linux builds',
    ),
    # Dependencies of SecretStorage
    Dependency(
        name='cryptography',
        license='Apache-2.0', # Also available as BSD-3-Clause
        source_url='https://raw.githubusercontent.com/pyca/cryptography/refs/heads/main/LICENSE.APACHE',
        comment='Only included in Linux builds',
    ),
    # Dependencies of SecretStorage
    Dependency(
        name='Jeepney',
        license='MIT',
        source_url='https://gitlab.com/takluyver/jeepney/-/raw/master/LICENSE',
        comment='Only included in Linux builds',
    ),
    Dependency(
        name='websockets',
        license='BSD-3-Clause',
        source_url='https://raw.githubusercontent.com/python-websockets/websockets/refs/heads/main/LICENSE',
    ),
]


def fetch_text(dep: Dependency) -> str:
    cache_dir = Path('_cache')
    cache_dir.mkdir(exist_ok=True)
    url_hash = hashlib.sha256(dep.source_url.encode('utf-8')).hexdigest()
    cache_file = cache_dir / f'{url_hash}.txt'

    if cache_file.exists():
        return cache_file.read_text()

    req = requests.get(dep.source_url, headers={'User-Agent': 'yt-dlp license fetcher'}) # needed since some domains block requests UA
    req.raise_for_status()
    text = req.text
    cache_file.write_text(text)
    return text


def build_output() -> str:
    lines = []
    lines.append('THIRD-PARTY LICENSES')
    lines.append('')
    lines.append('This file aggregates license texts of third-party components bundled with the yt-dlp executables.')
    lines.append('yt-dlp itself is licensed under the Unlicense (see LICENSE file).')

    for d in DEPENDENCIES:
        lines.append('\n')
        lines.append('-' * 80)
        header = f'{d.name}'
        if d.license:
            header += f' | {d.license}'
        if d.comment:
            header += f' | Note: {d.comment}'
        lines.append(header)
        lines.append('-' * 80)

        text = fetch_text(d)
        lines.append(text.strip('\n') + '\n')
    return '\n'.join(lines)

if __name__ == '__main__':
    content = build_output()
    Path(DEFAULT_OUTPUT).write_text(content)
