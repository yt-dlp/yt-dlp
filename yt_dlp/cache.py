import contextlib
import errno
import json
import os
import re
import shutil
import traceback

from .compat import compat_getenv
from .utils import expand_path, write_json_file


class Cache:
    def __init__(self, ydl):
        self._ydl = ydl

    def _get_root_dir(self):
        res = self._ydl.params.get('cachedir')
        if res is None:
            cache_root = compat_getenv('XDG_CACHE_HOME', '~/.cache')
            res = os.path.join(cache_root, 'yt-dlp')
        return expand_path(res)

    def _get_cache_fn(self, section, key, dtype):
        assert re.match(r'^[a-zA-Z0-9_.-]+$', section), \
            'invalid section %r' % section
        assert re.match(r'^[a-zA-Z0-9_.-]+$', key), 'invalid key %r' % key
        return os.path.join(
            self._get_root_dir(), section, f'{key}.{dtype}')

    @property
    def enabled(self):
        return self._ydl.params.get('cachedir') is not False

    def store(self, section, key, data, dtype='json'):
        assert dtype in ('json',)

        if not self.enabled:
            return

        fn = self._get_cache_fn(section, key, dtype)
        try:
            try:
                os.makedirs(os.path.dirname(fn))
            except OSError as ose:
                if ose.errno != errno.EEXIST:
                    raise
            self._ydl.write_debug(f'Saving {section}.{key} to cache')
            write_json_file(data, fn)
        except Exception:
            tb = traceback.format_exc()
            self._ydl.report_warning(f'Writing cache to {fn!r} failed: {tb}')

    def load(self, section, key, dtype='json', default=None):
        assert dtype in ('json',)

        if not self.enabled:
            return default

        cache_fn = self._get_cache_fn(section, key, dtype)
        with contextlib.suppress(OSError):
            try:
                with open(cache_fn, encoding='utf-8') as cachef:
                    self._ydl.write_debug(f'Loading {section}.{key} from cache')
                    return json.load(cachef)
            except ValueError:
                try:
                    file_size = os.path.getsize(cache_fn)
                except OSError as oe:
                    file_size = str(oe)
                self._ydl.report_warning(f'Cache retrieval from {cache_fn} failed ({file_size})')

        return default

    def remove(self):
        if not self.enabled:
            self._ydl.to_screen('Cache is disabled (Did you combine --no-cache-dir and --rm-cache-dir?)')
            return

        cachedir = self._get_root_dir()
        if not any((term in cachedir) for term in ('cache', 'tmp')):
            raise Exception('Not removing directory %s - this does not look like a cache dir' % cachedir)

        self._ydl.to_screen(
            'Removing cache dir %s .' % cachedir, skip_eol=True)
        if os.path.exists(cachedir):
            self._ydl.to_screen('.', skip_eol=True)
            shutil.rmtree(cachedir)
        self._ydl.to_screen('.')
