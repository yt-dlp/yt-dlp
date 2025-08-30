import re

from .common import InfoExtractor
from ..utils import ExtractorError, int_or_none, str_to_int


class RUTVIE(InfoExtractor):
    IE_DESC = 'RUTV.RU'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:test)?player\.(?:rutv\.ru|vgtrk\.com)/
                        (?P<path>
                            flash\d+v/container\.swf\?id=|
                            iframe/(?P<type>swf|video|live)/id/|
                            index/iframe/cast_id/
                        )
                        (?P<id>\d+)
                    '''
    _EMBED_REGEX = [
        r'<iframe[^>]+?src=(["\'])(?P<url>https?://(?:test)?player\.(?:rutv\.ru|vgtrk\.com)/(?:iframe/(?:swf|video|live)/id|index/iframe/cast_id)/.+?)\1',
        r'<meta[^>]+?property=(["\'])og:video\1[^>]+?content=(["\'])(?P<url>https?://(?:test)?player\.(?:rutv\.ru|vgtrk\.com)/flash\d+v/container\.swf\?id=.+?\2)',
    ]

    _TESTS = [{
        'url': 'http://player.rutv.ru/flash2v/container.swf?id=774471&sid=kultura&fbv=true&isPlay=true&ssl=false&i=560&acc_video_id=episode_id/972347/video_id/978186/brand_id/31724',
        'info_dict': {
            'id': '774471',
            'ext': 'mp4',
            'title': 'Монологи на все времена. Концерт',
            'description': 'md5:18d8b5e6a41fb1faa53819471852d5d5',
            'duration': 2906,
            'thumbnail': r're:https?://cdn-st2\.smotrim\.ru/.+\.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://player.vgtrk.com/flash2v/container.swf?id=774016&sid=russiatv&fbv=true&isPlay=true&ssl=false&i=560&acc_video_id=episode_id/972098/video_id/977760/brand_id/57638',
        'info_dict': {
            'id': '774016',
            'ext': 'mp4',
            'title': 'Чужой в семье Сталина',
            'description': '',
            'duration': 2539,
        },
        'skip': 'Invalid URL',
    }, {
        'url': 'http://player.rutv.ru/iframe/swf/id/766888/sid/hitech/?acc_video_id=4000',
        'info_dict': {
            'id': '766888',
            'ext': 'mp4',
            'title': 'Вести.net: интернет-гиганты начали перетягивание программных "одеял"',
            'description': 'md5:65ddd47f9830c4f42ed6475f8730c995',
            'duration': 279,
            'thumbnail': r're:https?://cdn-st2\.smotrim\.ru/.+\.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'http://player.rutv.ru/iframe/video/id/771852/start_zoom/true/showZoomBtn/false/sid/russiatv/?acc_video_id=episode_id/970443/video_id/975648/brand_id/5169',
        'info_dict': {
            'id': '771852',
            'ext': 'mp4',
            'title': 'Прямой эфир. Жертвы загадочной болезни: смерть от старости в 17 лет',
            'description': 'md5:b81c8c55247a4bd996b43ce17395b2d8',
            'duration': 3096,
            'thumbnail': r're:https?://cdn-st2\.smotrim\.ru/.+\.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'http://player.rutv.ru/iframe/live/id/51499/showZoomBtn/false/isPlay/true/sid/sochi2014',
        'info_dict': {
            'id': '51499',
            'ext': 'flv',
            'title': 'Сочи-2014. Биатлон. Индивидуальная гонка. Мужчины ',
            'description': 'md5:9e0ed5c9d2fa1efbfdfed90c9a6d179c',
        },
        'skip': 'Invalid URL',
    }, {
        'url': 'http://player.rutv.ru/iframe/live/id/21/showZoomBtn/false/isPlay/true/',
        'info_dict': {
            'id': '21',
            'ext': 'mp4',
            'title': str,
            'is_live': True,
        },
        'skip': 'Invalid URL',
    }, {
        'url': 'https://testplayer.vgtrk.com/iframe/live/id/19201/showZoomBtn/false/isPlay/true/',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'http://istoriya-teatra.ru/news/item/f00/s05/n0000545/index.shtml',
        'info_dict': {
            'id': '1952012',
            'ext': 'mp4',
            'title': 'Новости культуры. Эфир от 10.10.2019 (23:30). Театр Сатиры отмечает день рождения премьерой',
            'description': 'md5:fced27112ff01ff8fc4a452fc088bad6',
            'duration': 191,
            'thumbnail': r're:https?://cdn-st2\.smotrim\.ru/.+\.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        video_path = mobj.group('path')

        if re.match(r'flash\d+v', video_path):
            video_type = 'video'
        elif video_path.startswith('iframe'):
            video_type = mobj.group('type')
            if video_type == 'swf':
                video_type = 'video'
        elif video_path.startswith('index/iframe/cast_id'):
            video_type = 'live'

        is_live = video_type == 'live'

        json_data = self._download_json(
            'http://player.vgtrk.com/iframe/data{}/id/{}'.format('live' if is_live else 'video', video_id),
            video_id, 'Downloading JSON')

        if json_data['errors']:
            raise ExtractorError('{} said: {}'.format(self.IE_NAME, json_data['errors']), expected=True)

        playlist = json_data['data']['playlist']
        medialist = playlist['medialist']
        media = medialist[0]

        if media['errors']:
            raise ExtractorError('{} said: {}'.format(self.IE_NAME, media['errors']), expected=True)

        view_count = int_or_none(playlist.get('count_views'))
        priority_transport = playlist['priority_transport']

        thumbnail = media['picture']
        width = int_or_none(media['width'])
        height = int_or_none(media['height'])
        description = media['anons']
        title = media['title']
        duration = int_or_none(media.get('duration'))

        formats = []
        subtitles = {}

        for transport, links in media['sources'].items():
            for quality, url in links.items():
                preference = -1 if priority_transport == transport else -2
                if transport == 'rtmp':
                    mobj = re.search(r'^(?P<url>rtmp://[^/]+/(?P<app>.+))/(?P<playpath>.+)$', url)
                    if not mobj:
                        continue
                    fmt = {
                        'url': mobj.group('url'),
                        'play_path': mobj.group('playpath'),
                        'app': mobj.group('app'),
                        'page_url': 'http://player.rutv.ru',
                        'player_url': 'http://player.rutv.ru/flash3v/osmf.swf?i=22',
                        'rtmp_live': True,
                        'ext': 'flv',
                        'vbr': str_to_int(quality),
                    }
                elif transport == 'm3u8':
                    fmt, subs = self._extract_m3u8_formats_and_subtitles(
                        url, video_id, 'mp4', quality=preference, m3u8_id='hls')
                    formats.extend(fmt)
                    self._merge_subtitles(subs, target=subtitles)
                    continue
                else:
                    fmt = {
                        'url': url,
                    }
                fmt.update({
                    'width': int_or_none(quality, default=height, invscale=width, scale=height),
                    'height': int_or_none(quality, default=height),
                    'format_id': f'{transport}-{quality}',
                    'source_preference': preference,
                })
                formats.append(fmt)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'view_count': view_count,
            'duration': duration,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': is_live,
            '_format_sort_fields': ('source', ),
        }
