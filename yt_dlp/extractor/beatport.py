from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    determine_ext,
    int_or_none,
    join_nonempty,
    merge_dicts,
    parse_iso8601,
    T,
    traverse_obj,
    txt_or_none,
    unified_strdate,
    url_or_none,
    variadic,
)


class BeatportIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.|pro\.)?beatport\.com/track/(?P<display_id>[^/]+)/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://beatport.com/track/synesthesia-original-mix/5379371',
        'md5': 'cfcc245aafcad52a837b2c5a60a472c9',
        'info_dict': {
            'id': '5379371',
            'display_id': 'synesthesia-original-mix',
            'ext': 'mp3',
            'title': 'Froxic - Synesthesia (Original Mix)',
            'timestamp': 1397854513,
            'upload_date': '20140428',
        },
    }, {
        'url': 'https://beatport.com/track/love-and-war-original-mix/3756896',
        'md5': 'e44c3025dfa38c6577fbaeb43da43514',
        'info_dict': {
            'id': '3756896',
            'display_id': 'love-and-war-original-mix',
            'ext': 'mp3',
            'title': 'Wolfgang Gartner - Love & War (Original Mix)',
            'timestamp': 1346195831,
            'upload_date': '20120917',
        },
    }, {
        'url': 'https://beatport.com/track/birds-original-mix/4991738',
        'md5': '2dff00955b13c182931a708d979801b6',
        'info_dict': {
            'id': '4991738',
            'display_id': 'birds-original-mix',
            'ext': 'mp3',
            'title': "Tos, Middle Milk, Mumblin' Johnsson - Birds (Original Mix)",
            'timestamp': 1386121876,
            'upload_date': '20131209',
        }
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        track_id, display_id = mobj.group('id', 'display_id')

        webpage = self._download_webpage(url, display_id)

        next_data = self._search_nextjs_data(webpage, display_id, fatal=False)
        if not next_data:
            return self._old_real_extract(url)

        track = traverse_obj(
            next_data,
            ('props', 'pageProps', lambda k, v: k == 'track' and v['id'] == int(track_id)),
            get_all=False)

        title = track['name']
        artists = ', '.join(traverse_obj(track, ('artists', Ellipsis, 'name', T(txt_or_none)))) or None
        title = join_nonempty(artists, title, delim=' - ')
        title = join_nonempty(
            title, traverse_obj(track, ('mix_name', T(lambda s: '(' + s + ')'))),
            delim=' ')

        formats = []
        # next.js page has <= 1 sample URL
        f_url = traverse_obj(track, ('sample_url', T(url_or_none)))
        if f_url:
            ext = determine_ext(f_url)
            fmt = {
                'url': f_url,
                'ext': ext,
                'format_id': ext,
                'vcodec': 'none',
            }
            if ext == 'mp3':
                fmt['preference'] = 0
                fmt['acodec'] = 'mp3'
                fmt['abr'] = 96
                fmt['asr'] = 44100
            elif ext == 'mp4':
                fmt['preference'] = 1
                fmt['acodec'] = 'aac'
                fmt['abr'] = 96
                fmt['asr'] = 44100
            formats.append(fmt)
        self._sort_formats(formats)

        return merge_dicts({
            'id': track_id,
            'display_id': display_id,
            'title': title,
            'formats': formats,
            'artists': artists,
        }, traverse_obj(track, {
            'disc_number': ('catalog_number', T(int_or_none)),
            'timestamp': ('encoded_date', T(parse_iso8601)),
            'categories': ('genre', 'name', T(txt_or_none), T(variadic)),
            'thumbnail': ('image', 'uri', T(url_or_none)),
            'upload_date': (('new_release_date', 'publish_date'), T(unified_strdate)),
            'track_number': ('number', T(int_or_none)),
            'album': ('release', 'name', T(txt_or_none)),
        }, get_all=False))

    def _old_real_extract(self, url):
        mobj = self._match_valid_url(url)
        track_id = mobj.group('id')
        display_id = mobj.group('display_id')

        webpage = self._download_webpage(url, display_id)

        playables = self._parse_json(
            self._search_regex(
#                r'window\.Playables\s*=\s*({.+?});', webpage,
#                'playables info', flags=re.DOTALL),
                r'(?s)window\.Playables\s*=\s*({.+?});', webpage,
                'playables info'),
            track_id)

        track = next(t for t in playables['tracks'] if t['id'] == int(track_id))

        title = ', '.join((a['name'] for a in track['artists'])) + ' - ' + track['name']
        if track['mix']:
            title += ' (' + track['mix'] + ')'

        formats = []
        for ext, info in track['preview'].items():
            if not info['url']:
                continue
            fmt = {
                'url': info['url'],
                'ext': ext,
                'format_id': ext,
                'vcodec': 'none',
            }
            if ext == 'mp3':
                fmt['acodec'] = 'mp3'
                fmt['abr'] = 96
                fmt['asr'] = 44100
            elif ext == 'mp4':
                fmt['acodec'] = 'aac'
                fmt['abr'] = 96
                fmt['asr'] = 44100
            formats.append(fmt)

        images = []
        for name, info in track['images'].items():
            image_url = info.get('url')
            if name == 'dynamic' or not image_url:
                continue
            image = {
                'id': name,
                'url': image_url,
                'height': int_or_none(info.get('height')),
                'width': int_or_none(info.get('width')),
            }
            images.append(image)

        return {
            'id': compat_str(track.get('id')) or track_id,
            'display_id': track.get('slug') or display_id,
            'title': title,
            'formats': formats,
            'thumbnails': images,
        }
