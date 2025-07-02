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

    def _parse_js_urls(self, webpage):
        search = lambda name: self._search_regex(
            rf'<script src="(https://cdn\.kastatic\.org/khanacademy/{name}\.[0-9a-f]+\.js)">', webpage, name)
        self._RUNTIME_JS_URL = search('runtime')
        self._MAIN_JS_URL = search('khanacademy')

    def _search_query_js(self, query_name):
        # runtime.js contains hash version for each js file, which is needed for building js src url
        runtime_js = self._download_webpage(self._RUNTIME_JS_URL, None, 'Downloading runtime.js')
        js_hashes = self._search_json(
            r'return\s*""\+e\+"\."\+\(', runtime_js, 'js resources', None, end_pattern=r'\)\[e\]\+"\.js"',
            transform_source=lambda s: re.sub(r'([\da-f]+):', r'"\1":', s))

        # traverse all lazy-loaded js to find query-containing js file
        main_js = self._download_webpage(self._MAIN_JS_URL, None, 'Downloading khanacademy.js')
        for lazy_load in re.finditer(r'lazy\(function\(\)\{return Promise\.all\(\[(.+?)\]\)\.then', main_js):
            for js_name in re.finditer(r'X.e\("([0-9a-f]+)"\)', lazy_load[1]):
                if not (js_hash := js_hashes.get(js_name[1])):
                    self.report_warning(f'{js_name[1]} has no hash record for it, skip')
                    continue
                url = f'https://cdn.kastatic.org/khanacademy/{js_name[1]}.{js_hash}.js'
                js_src = self._download_webpage(url, None, f'Downloading {js_name[1]}.js')
                if f'query {query_name}' in js_src:
                    return js_src
        raise ExtractorError('Failed to find query js')

    def _parse_query_src(self, src):
        # extract gql strings for each object
        queries = {match['obj_id']: json.loads(js_to_json(match['body'])) for match in re.finditer(
            r'function (?P<obj_id>_templateObject\d*)\(\)\{var n=\(0,r\._\)\((?P<body>\[.+?\])\);return', src)}
        # extract variable name to object query map at end: `x=o()(_templateObject00(), m, n, k)`
        return {
            match['name']: {
                'sort': match['sort'] is not None,
                'query': queries[match['obj_id']][0],
                'embeds': match['embeds'].strip(',').split(',') if match['embeds'] else [],
            } for match in re.finditer(
                r'(?:var |,)(?P<name>[A-Za-z$_]+)=(?P<sort>\(0,s\.Fv\)\()?'
                r'o\(\)\((?P<obj_id>_templateObject\d*)\(\)(?P<embeds>(?:,[A-Za-z$_]+)*)\)', src)}

    def _sanitize_query(self, query: str):
        outlines = []
        indent = 0
        for line in query.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line == '}':
                if indent > 2 or outlines[0].startswith('fragment'):
                    outlines.append(f'{" " * indent}__typename')
                indent -= 2
            outlines.append(f'{" " * indent}{line}')
            if line[-1] == '{':
                indent += 2
        return '\n'.join(outlines)

    def _compose_query(self, queries, key):
        def _get_fragments(key):
            fragments = [self._sanitize_query(queries[key]['query'])]
            for key in queries[key]['embeds']:
                fragments.extend(_get_fragments(key))
            return fragments

        # recursively find all fragments then sort them
        queries = _get_fragments(key)
        if not (query := next((q for q in queries if q.startswith('query ')), None)):
            raise ExtractorError(f'Failed to get query for {key}')
        fragments = sorted(set(q for q in queries if q.startswith('fragment ')))
        return '\n\n'.join([query, *fragments])

    def _string_hash(self, input):
        hash = 5381
        for char in input[::-1]:
            hash = ((hash * 33) ^ ord(char)) & 0xFFFFFFFF
        return hash

    def _get_query_hash(self, query_name):
        if cache := self.cache.load('khanacademy', f'{query_name}-hash'):
            # change in hash of runtime.js may indicate change of website version
            if cache['runtime_js'] == self._RUNTIME_JS_URL:
                return cache['hash']

        queries = self._parse_query_src(self._search_query_js(query_name))
        for key, query_obj in queries.items():
            if f'query {query_name}' in query_obj['query']:
                query_hash = self._string_hash(self._compose_query(queries, key))
                self.cache.store('khanacademy', f'{query_name}-hash', {
                    'hash': query_hash, 'runtime_js': self._RUNTIME_JS_URL})
                return query_hash

        raise ExtractorError(f'Failed to find query object for {query_name}')

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
        self._parse_js_urls(webpage)

        ka_data = self._search_json(r'__KA_DATA__ \s*=', webpage, 'initial state', display_id)
        content = self._download_json(
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
            })['data']['contentRoute']['listedPathData']
        return self._parse_component_props(content, display_id)


class KhanAcademyIE(KhanAcademyBaseIE):
    IE_NAME = 'khanacademy'
    _VALID_URL = KhanAcademyBaseIE._VALID_URL_TEMPL % ('4', 'v/')
    _TEST = {
        'url': 'https://www.khanacademy.org/computing/computer-science/cryptography/crypt/v/one-time-pad',
        'md5': '1d5c2e70fa6aa29c38eca419f12515ce',
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
            'categories': ['Education'],
            'creators': ['Brit Cruise'],
            'tags': [],
            'age_limit': 0,
            'availability': 'public',
            'comment_count': int,
            'channel_follower_count': int,
            'thumbnail': str,
            'view_count': int,
            'like_count': int,
            'heatmap': list,
        },
        'add_ie': ['Youtube'],
    }

    def _parse_component_props(self, component_props, display_id):
        video = component_props['content']
        return {
            **self._parse_video(video),
            **traverse_obj(video, {
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
    }, {
        'url': 'https://www.khanacademy.org/computing/computer-science',
        'info_dict': {
            'id': 'x301707a0',
            'title': 'Computer science theory',
            'description': 'md5:4b472a4646e6cf6ec4ccb52c4062f8ba',
            'display_id': 'computing/computer-science',
            '_old_archive_ids': ['khanacademyunit computer-science'],
        },
        'playlist_mincount': 50,
    }]

    def _parse_component_props(self, component_props, display_id):
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
