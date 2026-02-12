import json
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    js_to_json,
    make_archive_id,
    parse_iso8601,
    str_or_none,
    traverse_obj,
    url_or_none,
    urljoin,
)


class KhanAcademyBaseIE(InfoExtractor):
    _RUNTIME_JS_URL = None
    _MAIN_JS_URL = None
    _VALID_URL_TEMPL = r'https?://(?:www\.)?khanacademy\.org/(?P<id>(?:[^/]+/){%s}%s[^?#/&]+)'

    def _load_script_src_urls(self, webpage):
        search = lambda name: self._search_regex(
            rf'<script src="(https://cdn\.kastatic\.org/khanacademy/{name}\.[0-9a-f]+\.js)">', webpage, name)
        self._RUNTIME_JS_URL = search('runtime')
        self._MAIN_JS_URL = search('khanacademy')

    def _extract_graphql(self, query_name):
        main_js = self._download_webpage(self._MAIN_JS_URL, None, 'Downloading khanacademy.js')
        if f'query {query_name}' in main_js:
            return self._parse_graphql_js(main_js)

        # runtime.js contains hash version for each js file, which is needed for building js src url
        runtime_js = self._download_webpage(self._RUNTIME_JS_URL, None, 'Downloading runtime.js')
        version_hashes = self._search_json(
            r'""\+e\+"\."\+\(', runtime_js, 'js resources', None, end_pattern=r'\)\[e\]\+"\.js"',
            transform_source=lambda s: re.sub(r'([\da-f]+):', r'"\1":', s))  # cannot use js_to_json, due to #13621

        # iterate all lazy-loaded js to find query-containing js file
        for lazy_load in re.finditer(r'lazy\(function\(\)\{return Promise\.all\(\[(.+?)\]\)\.then', main_js):
            for js_name in re.finditer(r'X.e\("([0-9a-f]+)"\)', lazy_load[1]):
                if not (js_hash := version_hashes.get(js_name[1])):
                    self.report_warning(f'{js_name[1]} has no hash record for it, skip')
                    continue
                url = f'https://cdn.kastatic.org/khanacademy/{js_name[1]}.{js_hash}.js'
                js_src = self._download_webpage(url, None, f'Downloading {js_name[1]}.js')
                if f'query {query_name}' in js_src:
                    return self._parse_graphql_js(js_src)
        raise ExtractorError('Failed to find query js')

    def _parse_graphql_js(self, src):
        # extract gql strings for each object
        queries = [self._sanitize_query(''.join(json.loads(js_to_json(match['body'])))) for match in re.finditer(
            r'function (?P<obj_id>_templateObject\d*).*?\((?P<body>\[.+?\])\);return', src)]
        return {self._search_regex(r'^(?:fragment|query|mutation) (\w+)', query,
                                   'query name', default=None): query for query in queries}

    def _sanitize_query(self, query: str):
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

    def _compose_query(self, query_objs, name):
        fragments = {}

        def _add_fragment(parent_name):
            for frag_name in re.findall(r'\.\.\.(\w+)', query_objs[parent_name]):
                if frag_name not in fragments:
                    fragments[frag_name] = query_objs[frag_name]
                    _add_fragment(frag_name)
        try:
            _add_fragment(name)
            return '\n\n'.join([query_objs[name], *(fragments[name] for name in sorted(fragments))])
        except KeyError as e:
            raise ExtractorError(f'Failed to find query object for {name}->{e.args}')

    def _string_hash(self, input_str):
        str_hash = 5381
        for char in input_str[::-1]:
            str_hash = ((str_hash * 33) ^ ord(char)) & 0xFFFFFFFF
        return str_hash

    def _get_query_hash(self, query_name):
        # change in version hash may indicate change of graphql schema
        #   consider cached hash as invalidated upon such change
        js_version = f'{self._RUNTIME_JS_URL}{self._MAIN_JS_URL}'
        if cache := self.cache.load('khanacademy', f'{query_name}-hash'):
            if cache['js_version'] == js_version:
                return cache['hash']

        query_hash = self._string_hash(self._compose_query(self._extract_graphql(query_name), query_name))
        self.cache.store('khanacademy', f'{query_name}-hash', {'hash': query_hash, 'js_version': js_version})
        return query_hash

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

        ka_data = self._search_json(r'__KA_DATA__ \s*=', webpage, 'initial state', display_id)
        data = self._download_json(
            'https://www.khanacademy.org/api/internal/graphql/ContentForPath', display_id,
            query={
                'fastly_cacheable': 'persist_until_publish',
                'pcv': ka_data['KA-published-content-version'],
                'hash': self._get_query_hash('ContentForPath'),
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
