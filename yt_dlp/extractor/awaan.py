import base64

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urllib_parse_urlencode,
)
from ..utils import (
    format_field,
    int_or_none,
    parse_iso8601,
    smuggle_url,
    unsmuggle_url,
    urlencode_postdata,
)


class AWAANIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:awaan|dcndigital)\.ae/(?:#/)?show/(?P<show_id>\d+)/[^/]+(?:/(?P<id>\d+)/(?P<season_id>\d+))?'

    def _real_extract(self, url):
        show_id, video_id, season_id = self._match_valid_url(url).groups()
        if video_id and int(video_id) > 0:
            return self.url_result(
                'http://awaan.ae/media/%s' % video_id, 'AWAANVideo')
        elif season_id and int(season_id) > 0:
            return self.url_result(smuggle_url(
                'http://awaan.ae/program/season/%s' % season_id,
                {'show_id': show_id}), 'AWAANSeason')
        else:
            return self.url_result(
                'http://awaan.ae/program/%s' % show_id, 'AWAANSeason')


class AWAANBaseIE(InfoExtractor):
    def _parse_video_data(self, video_data, video_id, is_live):
        title = video_data.get('title_en') or video_data['title_ar']
        img = video_data.get('img')

        return {
            'id': video_id,
            'title': title,
            'description': video_data.get('description_en') or video_data.get('description_ar'),
            'thumbnail': format_field(img, None, 'http://admin.mangomolo.com/analytics/%s'),
            'duration': int_or_none(video_data.get('duration')),
            'timestamp': parse_iso8601(video_data.get('create_time'), ' '),
            'is_live': is_live,
            'uploader_id': video_data.get('user_id'),
        }


class AWAANVideoIE(AWAANBaseIE):
    IE_NAME = 'awaan:video'
    _VALID_URL = r'https?://(?:www\.)?(?:awaan|dcndigital)\.ae/(?:#/)?(?:video(?:/[^/]+)?|media|catchup/[^/]+/[^/]+)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.dcndigital.ae/#/video/%D8%B1%D8%AD%D9%84%D8%A9-%D8%A7%D9%84%D8%B9%D9%85%D8%B1-%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-1/17375',
        'md5': '5f61c33bfc7794315c671a62d43116aa',
        'info_dict':
        {
            'id': '17375',
            'ext': 'mp4',
            'title': 'رحلة العمر : الحلقة 1',
            'description': 'md5:0156e935d870acb8ef0a66d24070c6d6',
            'duration': 2041,
            'timestamp': 1227504126,
            'upload_date': '20081124',
            'uploader_id': '71',
        },
    }, {
        'url': 'http://awaan.ae/video/26723981/%D8%AF%D8%A7%D8%B1-%D8%A7%D9%84%D8%B3%D9%84%D8%A7%D9%85:-%D8%AE%D9%8A%D8%B1-%D8%AF%D9%88%D8%B1-%D8%A7%D9%84%D8%A3%D9%86%D8%B5%D8%A7%D8%B1',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video_data = self._download_json(
            'http://admin.mangomolo.com/analytics/index.php/plus/video?id=%s' % video_id,
            video_id, headers={'Origin': 'http://awaan.ae'})
        info = self._parse_video_data(video_data, video_id, False)

        embed_url = 'http://admin.mangomolo.com/analytics/index.php/customers/embed/video?' + compat_urllib_parse_urlencode({
            'id': video_data['id'],
            'user_id': video_data['user_id'],
            'signature': video_data['signature'],
            'countries': 'Q0M=',
            'filter': 'DENY',
        })
        info.update({
            '_type': 'url_transparent',
            'url': embed_url,
            'ie_key': 'MangomoloVideo',
        })
        return info


class AWAANLiveIE(AWAANBaseIE):
    IE_NAME = 'awaan:live'
    _VALID_URL = r'https?://(?:www\.)?(?:awaan|dcndigital)\.ae/(?:#/)?live/(?P<id>\d+)'
    _TEST = {
        'url': 'http://awaan.ae/live/6/dubai-tv',
        'info_dict': {
            'id': '6',
            'ext': 'mp4',
            'title': 're:Dubai Al Oula [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'upload_date': '20150107',
            'timestamp': 1420588800,
            'uploader_id': '71',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        channel_data = self._download_json(
            'http://admin.mangomolo.com/analytics/index.php/plus/getchanneldetails?channel_id=%s' % channel_id,
            channel_id, headers={'Origin': 'http://awaan.ae'})
        info = self._parse_video_data(channel_data, channel_id, True)

        embed_url = 'http://admin.mangomolo.com/analytics/index.php/customers/embed/index?' + compat_urllib_parse_urlencode({
            'id': base64.b64encode(channel_data['user_id'].encode()).decode(),
            'channelid': base64.b64encode(channel_data['id'].encode()).decode(),
            'signature': channel_data['signature'],
            'countries': 'Q0M=',
            'filter': 'DENY',
        })
        info.update({
            '_type': 'url_transparent',
            'url': embed_url,
            'ie_key': 'MangomoloLive',
        })
        return info


class AWAANSeasonIE(InfoExtractor):
    IE_NAME = 'awaan:season'
    _VALID_URL = r'https?://(?:www\.)?(?:awaan|dcndigital)\.ae/(?:#/)?program/(?:(?P<show_id>\d+)|season/(?P<season_id>\d+))'
    _TEST = {
        'url': 'http://dcndigital.ae/#/program/205024/%D9%85%D8%AD%D8%A7%D8%B6%D8%B1%D8%A7%D8%AA-%D8%A7%D9%84%D8%B4%D9%8A%D8%AE-%D8%A7%D9%84%D8%B4%D8%B9%D8%B1%D8%A7%D9%88%D9%8A',
        'info_dict':
        {
            'id': '7910',
            'title': 'محاضرات الشيخ الشعراوي',
        },
        'playlist_mincount': 27,
    }

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        show_id, season_id = self._match_valid_url(url).groups()

        data = {}
        if season_id:
            data['season'] = season_id
            show_id = smuggled_data.get('show_id')
            if show_id is None:
                season = self._download_json(
                    'http://admin.mangomolo.com/analytics/index.php/plus/season_info?id=%s' % season_id,
                    season_id, headers={'Origin': 'http://awaan.ae'})
                show_id = season['id']
        data['show_id'] = show_id
        show = self._download_json(
            'http://admin.mangomolo.com/analytics/index.php/plus/show',
            show_id, data=urlencode_postdata(data), headers={
                'Origin': 'http://awaan.ae',
                'Content-Type': 'application/x-www-form-urlencoded'
            })
        if not season_id:
            season_id = show['default_season']
        for season in show['seasons']:
            if season['id'] == season_id:
                title = season.get('title_en') or season['title_ar']

                entries = []
                for video in show['videos']:
                    video_id = compat_str(video['id'])
                    entries.append(self.url_result(
                        'http://awaan.ae/media/%s' % video_id, 'AWAANVideo', video_id))

                return self.playlist_result(entries, season_id, title)
