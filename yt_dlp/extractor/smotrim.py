import re
import urllib.request

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    traverse_obj
)

# ToDo:
# 1. Download audio (radio)
#    Example: https://smotrim.ru/audio/2649922
# 2. Website vgtrk.ru embeds video from smotrim.ru
#    Example: https://vgtrk.ru/tvkultura
# 3. Live video, probably the same as #2
#    Example: https://smotrim.ru/live/19201
# 4. Treat 'brand' as a playlist and download all video?
#    Example: https://smotrim.ru/brand/66035


class SmotrimIE(InfoExtractor):
    _VALID_URL = r'https?://smotrim\.ru/(?P<type>brand|video|article)/[0-9]+'
    _TESTS = [{    # video
        'url': 'https://smotrim.ru/video/1539617',
        'md5': 'b1923a533c8cab09679789d720d0b1c5',
        'info_dict': {
            'id': '1539617',
            'ext': 'mp4',
            'title': 'Полиглот. Китайский с нуля за 16 часов! Урок №16',
            'description': '',
        }
    }, {  # article (geo-restricted)
        'only_matching': True,
        'url': 'https://smotrim.ru/article/2813445',
        'md5': 'e0ac453952afbc6a2742e850b4dc8e77',
        'info_dict': {
            'id': '2431846',
            'ext': 'mp4',
            'title': 'Новости культуры. Съёмки первой программы "Большие и маленькие"',
            'description': 'md5:94a4a22472da4252bf5587a4ee441b99',
        }
    }, {  # brand, redirect
        'only_matching': True,
        'url': 'https://smotrim.ru/brand/64356',
        'md5': '740472999ccff81d7f6df79cecd91c18',
        'info_dict': {
            'id': '2354523',
            'ext': 'mp4',
            'title': 'Большие и маленькие. Лучшее. 4-й выпуск',
            'description': 'md5:84089e834429008371ea41ea3507b989',
        }
    }, {  # w/o video
        'only_matching': True,
        'url': 'https://smotrim.ru/article/2909569',
    }]


    QUALITIES = {
        '234': 'low-wide',
        '336': 'low',
        '360': 'medium-wide',
        '528': 'high',
        '540': 'high-wide',
        '720': 'hd-wide',
        '1080': 'fhd-wide',
    }
    URL_TMPL = 'https://cdn-v.rtr-vesti.ru/_cdn_auth/secure/v/vh/mp4/{quality}/{id_split}.mp4?auth=mh&vid={id}'

    def _real_extract(self, url):
        video_id, typ = self._match_valid_url(url).group('id', 'type')
        webpage = self._download_webpage(url, video_id, 'Downloading webpage')
        if typ == 'brand':
            video_id = self._search_regex(
                r'"https://player.smotrim.ru/iframe/video/id/(?P<video_id>\d+)/',
                webpage, 'video_id', default=None)
            if video_id is None:
                raise ExtractorError('There are no video in this page.', expected=True)
            webpage = self._download_webpage(f'https://smotrim.ru/video/{video_id}', video_id, 'Redirect to video')



        player_id = self._search_regex(
            rf'"https://player.smotrim.ru/iframe/video/id/{re.escape(video_id)}/[^"]*?/\?acc_video_id=(?P<player_id>\d+)"',
            webpage, 'player id', default=None)
        if not player_id:
            raise ExtractorError('There are no video in this page.', expected=True)
        player_id_split = '/'.join(re.findall('...', player_id.zfill(9)))  # 2624356 > 002/624/356

        meta = self._download_json(f'https://player.smotrim.ru/iframe/datavideo/id/{video_id}/sid/smotrim', video_id)
        medialist = traverse_obj(meta, ('data', 'playlist', 'medialist'), get_all=False)

        formats = []

        def add_format(key, format_id=None, url=None, check=False, preference=-1):
            fmt = {
                'format_id': format_id or self.QUALITIES[key],
                'resolution': key,
                'ext': 'mp4',
                'acodec': 'aac',
                'vcodec': 'h264',
                'preference': preference,
                'url': url or self.URL_TMPL.format(quality=self.QUALITIES[key], id_split=player_id_split, id=player_id)
            }
            if check and not self._check_formats([fmt], video_id):
                return
            formats.append(fmt)

        if not medialist.get('errors'):
            for key in traverse_obj(medialist, ('sources', 'http')):
                if key in self.QUALITIES:
                    add_format(key)
                else:
                    self.report_warning(f'Unknown resolution "{key}p". Continuing anyway')
                    add_format(key, url=traverse_obj(medialist, ('sources', 'http', key)), format_id=key, preference=-2)

        elif medialist.get('errors') == 'Просмотр видео ограничен в вашем регионе':  # geo-restricted
            self.to_screen('Video is not available in your region. Trying to identify accessible formats...')
            for key, value in self.QUALITIES.items():
                add_format(key, format_id=value, check=True)
        else:
            raise ExtractorError(f'Smotrim says: {medialist.get("errors")}', expected=False)

        return {
            'id': video_id,
            'title': medialist.get('title'),
            'description': medialist.get('anons'),
            'formats': formats,
        }
