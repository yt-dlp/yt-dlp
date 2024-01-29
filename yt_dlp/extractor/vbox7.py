from .common import InfoExtractor
from ..utils import int_or_none
from ..utils.traversal import traverse_obj


class Vbox7IE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:[^/]+\.)?vbox7\.com/
                        (?:
                            play:|
                            (?:
                                emb/external\.php|
                                player/ext\.swf
                            )\?.*?\bvid=
                        )
                        (?P<id>[\da-fA-F]+)
                    '''
    _EMBED_REGEX = [r'<iframe[^>]+src=(?P<q>["\'])(?P<url>(?:https?:)?//vbox7\.com/emb/external\.php.+?)(?P=q)']
    _GEO_COUNTRIES = ['BG']
    _TESTS = [{
        'url': 'http://vbox7.com/play:0946fff23c',
        'md5': '50ca1f78345a9c15391af47d8062d074',
        'info_dict': {
            'id': '0946fff23c',
            'ext': 'mp4',
            'title': 'Борисов: Притеснен съм за бъдещето на България',
            'description': 'По думите му е опасно страната ни да бъде обявена за "сигурна"',
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1470982814,
            'upload_date': '20160812',
            'uploader': 'zdraveibulgaria',
            'view_count': int,
            'duration': 2640,
        },
    }, {
        'url': 'http://vbox7.com/play:249bb972c2',
        'md5': '99f65c0c9ef9b682b97313e052734c3f',
        'info_dict': {
            'id': '249bb972c2',
            'ext': 'mp4',
            'title': 'Смях! Чудо - чист за секунди - Скрита камера',
            'uploader': 'svideteliat_ot_varshava',
            'view_count': int,
            'timestamp': 1360215023,
            'thumbnail': 'https://i49.vbox7.com/design/iconci/png/noimg6.png',
            'description': 'Смях! Чудо - чист за секунди - Скрита камера',
            'upload_date': '20130207',
            'duration': 83,
        },
        'expected_warnings': ['Failed to download m3u8 information'],
    }, {
        'url': 'http://vbox7.com/emb/external.php?vid=a240d20f9c&autoplay=1',
        'only_matching': True,
    }, {
        'url': 'http://i49.vbox7.com/player/ext.swf?vid=0946fff23c&autoplay=1',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        data = self._download_json(
            'https://www.vbox7.com/aj/player/item/options', video_id,
            query={'vid': video_id})['options']

        if '.mp4' in data['src']:
            base_url = data['src'].rpartition('_')[0]
        else:
            base_url = data['src'].rpartition('.')[0]

        formats = self._extract_m3u8_formats(
            f'{base_url}.m3u8', video_id, m3u8_id='hls', fatal=False)
        # TODO: Add MPD formats, when dash range support is added
        for res in traverse_obj(data, ('resolutions', lambda _, v: v != 0, {int})):
            formats.append({
                'url': f'{base_url}_{res}.mp4',
                'format_id': f'http-{res}',
                'height': res,
            })

        return {
            'id': video_id,
            'formats': formats,
            **self._search_json_ld(self._download_webpage(
                f'https://www.vbox7.com/play:{video_id}', video_id, fatal=False) or '', video_id, fatal=False),
            **traverse_obj(data, {
                'title': ('title', {str}),
                'uploader': ('uploader', {str}),
                'duration': ('duration', {int_or_none}),
            }),
        }
