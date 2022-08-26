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
    _TESTS = [
        {    # video
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
        }
    ]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, None, 'Downloading webpage')
        m = re.match(self._VALID_URL, url)
        if m.group('type') == 'brand':
            video_id = self._search_regex(r'"https://player.smotrim.ru/iframe/video/id/(?P<video_id>[0-9]+)/', webpage, 'video_id', default=None)
            if video_id is None:
                raise ExtractorError('This page doesn\'t contain video.', expected=True)
            webpage = self._download_webpage('https://smotrim.ru/video/' + video_id, None, 'Redirect to video')

        # Example: https://player.smotrim.ru/iframe/video/id/1539617/start_zoom/true/showZoomBtn/false/sid/smotrim/isPlay/true/mute/true/?acc_video_id=1488382"
        m = re.search(
            r'"https://player.smotrim.ru/iframe/video/id/(?P<video_id>[0-9]+)/[^"]*?/?acc_video_id=(?P<player_id>[0-9]+)"',
            webpage)
        if m is None:
            raise ExtractorError('This page doesn\'t contain video.', expected=True)
        video_id = m.group('video_id')
        player_id = m.group('player_id')
        player_id_split = '/'.join(re.findall('...', player_id.zfill(9)))  # 2624356 > 002/624/356

        meta = self._download_json(f'https://player.smotrim.ru/iframe/datavideo/id/{video_id}/sid/smotrim', None,)
        meta = traverse_obj(meta, ('data', 'playlist', 'medialist'))[0]

        video_quality = {
            '234': 'low-wide',
            '336': 'low',
            '360': 'medium-wide',
            '528': 'high',
            '540': 'high-wide',
            '720': 'hd-wide',
            '1080': 'fhd-wide',
        }
        video_template = 'https://cdn-v.rtr-vesti.ru/_cdn_auth/secure/v/vh/mp4/{quality}/{id_split}.mp4?auth=mh&vid={id}'

        formats = []
        if meta.get('errors') == '':
            for key in traverse_obj(meta, ('sources', 'http')):
                if key in video_quality:
                    formats.append({
                        'format': video_quality[key],
                        'resolution': key,
                        'ext': 'mp4',
                        'acodec': 'AAC',
                        'vcodec': 'H264',
                        'url': video_template.format(quality=video_quality[key], id_split=player_id_split, id=player_id)
                    })
                else:
                    print(f'\nWARNING: unknown resolution "{key}p".')
                    print('Please, inform the developers. Open a ticket here:')
                    print('https://github.com/yt-dlp/yt-dlp/issues')
                    print('Title: [Smotrim] enhance')
                    print(f'Text: New resolution "{key}" in the video {url}.\n')
                    formats.append({
                        'format': 'unknown',
                        'resolution': key,
                        'ext': 'mp4',
                        'acodec': 'AAC',
                        'vcodec': 'H264',
                        'url': traverse_obj(meta, ('sources', 'http', key))
                    })
        elif meta.get('errors') == 'Просмотр видео ограничен в вашем регионе':  # geo-restricted
            print('Video isn\'t available in your region. Trying to identify accessible formats...')
            for key in video_quality:
                video_url = video_template.format(quality=video_quality[key], id_split=player_id_split, id=player_id)
                try:
                    print(f'   checking {key}p... ', end='')
                    urllib.request.urlopen(video_url)
                except urllib.error.HTTPError:
                    print('fail')
                    continue
                print("success")
                formats.append({
                    'format': video_quality[key],
                    'resolution': key,
                    'ext': 'mp4',
                    'acodec': 'AAC',
                    'vcodec': 'H264',
                    'url': video_url
                })
        else:
            raise ExtractorError('Unknown error: ' + meta.get('errors'), expected=False)

        # sort formats
        formats = sorted(formats, key=lambda item: int(item['resolution']))
        for i in range(len(formats)):
            formats[i]['format_id'] = str(i + 1)
            formats[i]['resolution'] += 'p'

        # import hashlib
        # print('md5:' + hashlib.md5(meta.get('anons').encode('utf-8')).hexdigest())

        return {
            'id': video_id,
            'title': meta.get('title'),
            'description': meta.get('anons'),
            'formats': formats,
        }
