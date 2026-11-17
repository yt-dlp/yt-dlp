import json
import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    float_or_none,
    int_or_none,
    parse_iso8601,
    strip_or_none,
)


class ToggleIE(InfoExtractor):
    IE_NAME = 'toggle'
    _VALID_URL = r'(?:https?://(?:(?:www\.)?mewatch|video\.toggle)\.sg/(?:en|zh)/(?:[^/]+/){2,}|toggle:)(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://www.mewatch.sg/en/series/lion-moms-tif/trailers/lion-moms-premier/343115',
        'info_dict': {
            'id': '343115',
            'ext': 'mp4',
            'title': 'Lion Moms Premiere',
            'description': 'md5:aea1149404bff4d7f7b6da11fafd8e6b',
            'upload_date': '20150910',
            'timestamp': 1441858274,
        },
        'params': {
            'skip_download': 'm3u8 download',
        },
    }, {
        'url': 'http://www.mewatch.sg/en/movies/dug-s-special-mission/341413',
        'only_matching': True,
    }, {
        'url': 'http://www.mewatch.sg/en/series/28th-sea-games-5-show/28th-sea-games-5-show-ep11/332861',
        'only_matching': True,
    }, {
        'url': 'http://video.toggle.sg/en/clips/seraph-sun-aloysius-will-suddenly-sing-some-old-songs-in-high-pitch-on-set/343331',
        'only_matching': True,
    }, {
        'url': 'http://www.mewatch.sg/en/clips/seraph-sun-aloysius-will-suddenly-sing-some-old-songs-in-high-pitch-on-set/343331',
        'only_matching': True,
    }, {
        'url': 'http://www.mewatch.sg/zh/series/zero-calling-s2-hd/ep13/336367',
        'only_matching': True,
    }, {
        'url': 'http://www.mewatch.sg/en/series/vetri-s2/webisodes/jeeva-is-an-orphan-vetri-s2-webisode-7/342302',
        'only_matching': True,
    }, {
        'url': 'http://www.mewatch.sg/en/movies/seven-days/321936',
        'only_matching': True,
    }, {
        'url': 'https://www.mewatch.sg/en/tv-show/news/may-2017-cna-singapore-tonight/fri-19-may-2017/512456',
        'only_matching': True,
    }, {
        'url': 'http://www.mewatch.sg/en/channels/eleven-plus/401585',
        'only_matching': True,
    }]

    _API_USER = 'tvpapi_147'
    _API_PASS = '11111'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        params = {
            'initObj': {
                'Locale': {
                    'LocaleLanguage': '',
                    'LocaleCountry': '',
                    'LocaleDevice': '',
                    'LocaleUserState': 0,
                },
                'Platform': 0,
                'SiteGuid': 0,
                'DomainID': '0',
                'UDID': '',
                'ApiUser': self._API_USER,
                'ApiPass': self._API_PASS,
            },
            'MediaID': video_id,
            'mediaType': 0,
        }

        info = self._download_json(
            'http://tvpapi.as.tvinci.com/v2_9/gateways/jsonpostgw.aspx?m=GetMediaInfo',
            video_id, 'Downloading video info json', data=json.dumps(params).encode())

        title = info['MediaName']

        formats = []
        for video_file in info.get('Files', []):
            video_url, vid_format = video_file.get('URL'), video_file.get('Format')
            if not video_url or video_url == 'NA' or not vid_format:
                continue
            ext = determine_ext(video_url)
            vid_format = vid_format.replace(' ', '')
            # if geo-restricted, m3u8 is inaccessible, but mp4 is okay
            if ext == 'm3u8':
                m3u8_formats = self._extract_m3u8_formats(
                    video_url, video_id, ext='mp4', m3u8_id=vid_format,
                    note=f'Downloading {vid_format} m3u8 information',
                    errnote=f'Failed to download {vid_format} m3u8 information',
                    fatal=False)
                for f in m3u8_formats:
                    # Apple FairPlay Streaming
                    if '/fpshls/' in f['url']:
                        continue
                    formats.append(f)
            elif ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    video_url, video_id, mpd_id=vid_format,
                    note=f'Downloading {vid_format} MPD manifest',
                    errnote=f'Failed to download {vid_format} MPD manifest',
                    fatal=False))
            elif ext == 'ism':
                formats.extend(self._extract_ism_formats(
                    video_url, video_id, ism_id=vid_format,
                    note=f'Downloading {vid_format} ISM manifest',
                    errnote=f'Failed to download {vid_format} ISM manifest',
                    fatal=False))
            elif ext == 'mp4':
                formats.append({
                    'ext': ext,
                    'url': video_url,
                    'format_id': vid_format,
                })
        if not formats:
            for meta in (info.get('Metas') or []):
                if (not self.get_param('allow_unplayable_formats')
                        and meta.get('Key') == 'Encryption' and meta.get('Value') == '1'):
                    self.report_drm(video_id)
            # Most likely because geo-blocked if no formats and no DRM

        thumbnails = []
        for picture in info.get('Pictures', []):
            if not isinstance(picture, dict):
                continue
            pic_url = picture.get('URL')
            if not pic_url:
                continue
            thumbnail = {
                'url': pic_url,
            }
            pic_size = picture.get('PicSize', '')
            m = re.search(r'(?P<width>\d+)[xX](?P<height>\d+)', pic_size)
            if m:
                thumbnail.update({
                    'width': int(m.group('width')),
                    'height': int(m.group('height')),
                })
            thumbnails.append(thumbnail)

        def counter(prefix):
            return int_or_none(
                info.get(prefix + 'Counter') or info.get(prefix.lower() + '_counter'))

        return {
            'id': video_id,
            'title': title,
            'description': strip_or_none(info.get('Description')),
            'duration': int_or_none(info.get('Duration')),
            'timestamp': parse_iso8601(info.get('CreationDate') or None),
            'average_rating': float_or_none(info.get('Rating')),
            'view_count': counter('View'),
            'like_count': counter('Like'),
            'thumbnails': thumbnails,
            'formats': formats,
        }


class MeWatchIE(InfoExtractor):
    IE_NAME = 'mewatch'
    _VALID_URL = r'https?://(?:(?:www|live)\.)?mewatch\.sg/watch/[^/?#&]+-(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.mewatch.sg/watch/Recipe-Of-Life-E1-179371',
        'info_dict': {
            'id': '1008625',
            'ext': 'mp4',
            'title': 'Recipe Of Life 味之道',
            'timestamp': 1603306526,
            'description': 'md5:6e88cde8af2068444fc8e1bc3ebf257c',
            'upload_date': '20201021',
        },
        'params': {
            'skip_download': 'm3u8 download',
        },
    }, {
        'url': 'https://www.mewatch.sg/watch/Little-Red-Dot-Detectives-S2-搜密。打卡。小红点-S2-E1-176232',
        'only_matching': True,
    }, {
        'url': 'https://www.mewatch.sg/watch/Little-Red-Dot-Detectives-S2-%E6%90%9C%E5%AF%86%E3%80%82%E6%89%93%E5%8D%A1%E3%80%82%E5%B0%8F%E7%BA%A2%E7%82%B9-S2-E1-176232',
        'only_matching': True,
    }, {
        'url': 'https://live.mewatch.sg/watch/Recipe-Of-Life-E41-189759',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        item_id = self._match_id(url)
        custom_id = self._download_json(
            'https://cdn.mewatch.sg/api/items/' + item_id,
            item_id, query={'segments': 'all'})['customId']
        return self.url_result(
            'toggle:' + custom_id, ToggleIE.ie_key(), custom_id)
