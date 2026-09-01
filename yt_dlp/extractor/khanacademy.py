import json
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    make_archive_id,
    parse_iso8601,
    str_or_none,
    traverse_obj,
    url_or_none,
    urljoin,
)


class KhanAcademyBaseIE(InfoExtractor):
    _MAIN_JS_HASH = None
    _RUNTIME_JS_HASH = None
    _PCV = None
    _CACHED_JS = {}
    _QUERY_HASH = {}
    _VALID_URL_TEMPL = r'https?://(?:www\.)?khanacademy\.org/(?P<id>(?:[^/]+/){%s}%s[^?#/&]+)'
    _QUERY_NAME: str

    def _load_script_src_urls(self, webpage):
        search_hash = lambda name: self._search_regex(
            rf'https://cdn\.kastatic\.org/khanacademy/{name}\.([0-9a-f]+)\.js', webpage, f'{name}-hash')
        self._MAIN_JS_HASH = search_hash('khanacademy')
        self._RUNTIME_JS_HASH = search_hash('runtime')
        self._PCV = self._search_json(
            r'__KA_DATA__ \s*=', webpage, 'initial state', None)['KA-published-content-version']

    def _get_js(self, js_name, js_hash, disk_cache=False):
        if disk_cache and (cache := self.cache.load('khanacademy', f'{js_name}.js')):
            if cache['js_hash'] == js_hash:
                return cache['content']

        filename = f'{js_name}.{js_hash}.js'
        if filename not in self._CACHED_JS:
            self._CACHED_JS[filename] = self._download_webpage(
                f'https://cdn.kastatic.org/khanacademy/{filename}', None, f'Downloading {filename}')
        if disk_cache:
            self.cache.store('khanacademy', f'{js_name}.js', {'js_hash': js_hash, 'content': self._CACHED_JS[filename]})
        return self._CACHED_JS[filename]

    def _extract_query(self, query_name):
        main_js = self._get_js('khanacademy', self._MAIN_JS_HASH, disk_cache=True)
        if f'query {query_name}' in main_js:
            return self._parse_graphql_js(main_js, query_name)

        # runtime.js contains hash version for each js file, which is needed for building js src url
        runtime_js = self._get_js('runtime', self._RUNTIME_JS_HASH)
        version_hashes = self._search_json(
            r'""\+e\+"\."\+\(', runtime_js, 'js resources', None, end_pattern=r'\)\[e\]\+"\.js"',
            transform_source=lambda s: re.sub(r'([\da-f]+):', r'"\1":', s))  # cannot use js_to_json, due to #13621

        for js_name, js_hash in version_hashes.items():
            js_src = self._get_js(js_name, js_hash)
            if f'query {query_name}' in js_src:
                return self._parse_graphql_js(js_src, query_name)
        raise ExtractorError(f'Failed to find query js for "{query_name}"')

    def _parse_graphql_js(self, src, query_name):
        # recursively extract gql strings
        query = self._search_definition(src, query_name)
        fragments = {}
        def _search_fragments(definition):
            for frag_name in re.findall(r'\.\.\.(\w+)', definition):
                if frag_name not in fragments:
                    fragments[frag_name] = self._search_definition(src, frag_name)
                    _search_fragments(fragments[frag_name])
        _search_fragments(query)

        return '\n\n'.join([query, *(fragments[name] for name in sorted(fragments))])

    def _search_definition(self, src: str, name):
        m = re.search(rf'(?:query {name}\s*\([^\)]*\)|fragment {name} on \w+)', src)
        if not m:
            raise ExtractorError(f'Failed to find {name}')
        lines = []
        depth = 0
        for line in src[m.end(0):].splitlines():
            lines.append(line)
            depth += line.count('{') - line.count('}')
            if depth == 0:
                return self._sanitize_query(m[0] + '\n'.join(lines))
        raise ExtractorError(f'Failed to extract definition for {name}')

    def _sanitize_query(self, query: str):
        for inner in re.findall(r'\(([^\)]+)\)', query):
            if '\n' in inner:  # convert params from newline-split to comma-split
                new = ', '.join(l.strip() for l in inner.splitlines() if l.strip())
                query = query.replace(inner, new)
        outlines = []
        indent = 0
        for line in query.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line == '}':
                # unlike fragment, query has no __typename at its very end
                # only object inside query has tailing __typename
                if indent > 2 or outlines[0].startswith('fragment'):
                    outlines.append(f'{" " * indent}__typename')
                indent -= 2
            outlines.append(f'{" " * indent}{line}')
            if line[-1] == '{':
                indent += 2
        return '\n'.join(outlines)

    def _string_hash(self, input_str):
        str_hash = 5381
        for char in input_str[::-1]:
            str_hash = ((str_hash * 33) ^ ord(char)) & 0xFFFFFFFF
        return str_hash

    def _get_query_hash(self, query_name):
        if query_name not in self._QUERY_HASH:
            self._QUERY_HASH[query_name] = self._string_hash(self._extract_query(query_name))
        return self._QUERY_HASH[query_name]

    def _parse_video(self, video):
        return {
            '_type': 'url_transparent',
            'url': video['youtubeId'],
            'id': video['youtubeId'],
            'ie_key': 'Youtube',
            **traverse_obj(video, {
                'display_id': ('id', {str_or_none}),
                'title': ('translatedTitle', {str}),
                'thumbnail': ('thumbnailUrls', ..., 'url', {url_or_none}),
                'duration': ('duration', {int_or_none}),
                'description': ('description', {str}),
            }, get_all=False),
        }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        self._load_script_src_urls(webpage)

        data = self._download_json(
            f'https://www.khanacademy.org/api/internal/graphql/{self._QUERY_NAME}', display_id,
            query={
                'fastly_cacheable': 'persist_until_publish',
                'pcv': self._PCV,
                'hash': self._get_query_hash(self._QUERY_NAME),
                'variables': json.dumps({
                    'path': display_id,
                    'countryCode': 'US',
                }),
                'lang': 'en',
                'app': 'khanacademy',
            })['data']['contentRoute']

        if data.get('listedPathData'):
            return self._parse_component_props(data['listedPathData'], display_id, listed=True)
        else:
            return self._parse_component_props(data['unlistedPathData'], display_id, listed=False)


class KhanAcademyIE(KhanAcademyBaseIE):
    IE_NAME = 'khanacademy'
    _VALID_URL = KhanAcademyBaseIE._VALID_URL_TEMPL % ('4', 'v/')
    _QUERY_NAME = 'ContentRouteLessonAndContentData'

    _TESTS = [{
        'url': 'https://www.khanacademy.org/computing/computer-science/cryptography/crypt/v/one-time-pad',
        'info_dict': {
            'id': 'FlIG3TvQCBQ',
            'ext': 'mp4',
            'title': 'The one-time pad',
            'description': 'The perfect cipher',
            'display_id': '716378217',
            'duration': 176,
            'uploader': 'Khan Academy',
            'uploader_id': '@khanacademy',
            'uploader_url': 'https://www.youtube.com/@khanacademy',
            'upload_date': '20120411',
            'timestamp': 1334170113,
            'license': 'cc-by-nc-sa',
            'live_status': 'not_live',
            'channel': 'Khan Academy',
            'channel_id': 'UC4a-Gbdw7vOaccHmFo40b9g',
            'channel_url': 'https://www.youtube.com/channel/UC4a-Gbdw7vOaccHmFo40b9g',
            'channel_is_verified': True,
            'playable_in_embed': True,
            'creators': ['Brit Cruise'],
            'tags': [],
            'age_limit': 0,
            'comment_count': int,
            'channel_follower_count': int,
            'thumbnail': str,
            'view_count': int,
            'like_count': int,
            'heatmap': list,
            'media_type': 'video',
            'categories': ['Education'],
            'availability': 'public',
        },
        'expected_warnings': ['[0-9a-f]+ has no hash record for it, skip'],
        'add_ie': ['Youtube'],
    }, {
        'note': 'unlisted path video',
        'url': 'https://www.khanacademy.org/math/math-for-fun-and-glory/vi-hart/spirals-fibonacci/v/doodling-in-math-spirals-fibonacci-and-being-a-plant-1-of-3',
        'info_dict': {
            'id': '537957955',
            'ext': 'mp4',
            'title': 'Doodling in math: Spirals, Fibonacci, and being a plant [1 of 3]',
            'description': 'md5:4098102420babcf909097ec1633a52e7',
            'upload_date': '20120131',
            'timestamp': 1327972656,
            'thumbnail': r're:https://cdn.kastatic.org/.*',
            'duration': 355,
            'creators': ['Vi Hart'],
            'license': 'cc-by-nc-sa',
        },
        'expected_warnings': ['[0-9a-f]+ has no hash record for it, skip'],
    }]

    def _parse_component_props(self, component_props, display_id, listed=True):
        video = component_props['content']
        if listed:
            return {
                **self._parse_video(video),
                **traverse_obj(video, {
                    'creators': ('authorNames', ..., {str}),
                    'timestamp': ('dateAdded', {parse_iso8601}),
                    'license': ('kaUserLicense', {str}),
                }),
            }
        else:
            return {
                'id': str(video['id']),
                'formats': self._extract_m3u8_formats(json.loads(video['downloadUrls'])['m3u8'], display_id),
                **traverse_obj(video, {
                    'title': ('translatedTitle', {str}),
                    'description': ('description', {str}),
                    'thumbnail': ('thumbnailUrls', ..., 'url', {url_or_none}, any),
                    'duration': ('duration', {int}),
                    'creators': ('authorNames', ..., {str}),
                    'timestamp': ('dateAdded', {parse_iso8601}),
                    'license': ('kaUserLicense', {str}),
                }),
            }


class KhanAcademyUnitIE(KhanAcademyBaseIE):
    IE_NAME = 'khanacademy:unit'
    _VALID_URL = (KhanAcademyBaseIE._VALID_URL_TEMPL % ('1,2', '')) + '/?(?:[?#&]|$)'
    _QUERY_NAME = 'ContentRouteCourseData'

    _TESTS = [{
        'url': 'https://www.khanacademy.org/computing/computer-science/cryptography',
        'info_dict': {
            'id': 'x48c910b6',
            'title': 'Cryptography',
            'description': 'How have humans protected their secret messages through history? What has changed today?',
            'display_id': 'computing/computer-science/cryptography',
            '_old_archive_ids': ['khanacademyunit cryptography'],
        },
        'playlist_mincount': 31,
        'expected_warnings': ['[0-9a-f]+ has no hash record for it, skip'],
    }, {
        'url': 'https://www.khanacademy.org/computing/computer-science',
        'info_dict': {
            'id': 'x301707a0',
            'title': 'Computer science theory',
            'description': 'md5:20a0c2d331e5d0e609872629079e6ec8',
            'display_id': 'computing/computer-science',
            '_old_archive_ids': ['khanacademyunit computer-science'],
        },
        'playlist_mincount': 50,
        'expected_warnings': ['[0-9a-f]+ has no hash record for it, skip'],
    }, {
        'note': 'unlisted path unit',
        'url': 'https://www.khanacademy.org/math/math-for-fun-and-glory/vi-hart',
        'info_dict': {
            'id': 'xf48ec4ac',
            'title': 'Doodling in Math and more',
            'description': 'md5:81ca50417783334a27e48d687a346f14',
            'display_id': 'math/math-for-fun-and-glory/vi-hart',
            '_old_archive_ids': ['khanacademyunit vi-hart'],
        },
        'playlist_mincount': 50,
        'expected_warnings': ['[0-9a-f]+ has no hash record for it, skip'],
    }]

    def _parse_component_props(self, component_props, display_id, listed=True):
        course = component_props['course']
        selected_unit = traverse_obj(course, (
            'unitChildren', lambda _, v: v['relativeUrl'] == f'/{display_id}', any)) or course

        def build_entry(entry):
            return self.url_result(urljoin(
                'https://www.khanacademy.org', entry['canonicalUrl']),
                KhanAcademyIE, title=entry.get('translatedTitle'))

        entries = traverse_obj(selected_unit, (
            (('unitChildren', ...), None), 'allOrderedChildren', ..., 'curatedChildren',
            lambda _, v: v['contentKind'] == 'Video' and v['canonicalUrl'], {build_entry}))

        return self.playlist_result(
            entries,
            display_id=display_id,
            **traverse_obj(selected_unit, {
                'id': ('id', {str}),
                'title': ('translatedTitle', {str}),
                'description': ('translatedDescription', {str}),
                '_old_archive_ids': ('slug', {str}, {lambda x: [make_archive_id(self, x)] if x else None}),
            }))
