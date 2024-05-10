import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    ExtractorError,
    qualities,
)


class TeacherTubeIE(InfoExtractor):
    _WORKING = False
    IE_NAME = 'teachertube'
    IE_DESC = 'teachertube.com videos'

    _VALID_URL = r'https?://(?:www\.)?teachertube\.com/(viewVideo\.php\?video_id=|music\.php\?music_id=|video/(?:[\da-z-]+-)?|audio/)(?P<id>\d+)'

    _TESTS = [{
        # flowplayer
        'url': 'http://www.teachertube.com/viewVideo.php?video_id=339997',
        'md5': 'f9434ef992fd65936d72999951ee254c',
        'info_dict': {
            'id': '339997',
            'ext': 'mp4',
            'title': 'Measures of dispersion from a frequency table',
            'description': 'Measures of dispersion from a frequency table',
            'thumbnail': r're:https?://.*\.(?:jpg|png)',
        },
    }, {
        # jwplayer
        'url': 'http://www.teachertube.com/music.php?music_id=8805',
        'md5': '01e8352006c65757caf7b961f6050e21',
        'info_dict': {
            'id': '8805',
            'ext': 'mp3',
            'title': 'PER ASPERA AD ASTRA',
            'description': 'RADIJSKA EMISIJA ZRAKOPLOVNE TEHNI?KE ?KOLE P',
        },
    }, {
        # unavailable video
        'url': 'http://www.teachertube.com/video/intro-video-schleicher-297790',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        error = self._search_regex(
            r'<div\b[^>]+\bclass=["\']msgBox error[^>]+>([^<]+)', webpage,
            'error', default=None)
        if error:
            raise ExtractorError('%s said: %s' % (self.IE_NAME, error), expected=True)

        title = self._html_search_meta('title', webpage, 'title', fatal=True)
        TITLE_SUFFIX = ' - TeacherTube'
        if title.endswith(TITLE_SUFFIX):
            title = title[:-len(TITLE_SUFFIX)].strip()

        description = self._html_search_meta('description', webpage, 'description')
        if description:
            description = description.strip()

        quality = qualities(['mp3', 'flv', 'mp4'])

        media_urls = re.findall(r'data-contenturl="([^"]+)"', webpage)
        media_urls.extend(re.findall(r'var\s+filePath\s*=\s*"([^"]+)"', webpage))
        media_urls.extend(re.findall(r'\'file\'\s*:\s*["\']([^"\']+)["\'],', webpage))

        formats = [
            {
                'url': media_url,
                'quality': quality(determine_ext(media_url))
            } for media_url in set(media_urls)
        ]

        thumbnail = self._og_search_thumbnail(
            webpage, default=None) or self._html_search_meta(
            'thumbnail', webpage)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
        }


class TeacherTubeUserIE(InfoExtractor):
    _WORKING = False
    IE_NAME = 'teachertube:user:collection'
    IE_DESC = 'teachertube.com user and collection videos'

    _VALID_URL = r'https?://(?:www\.)?teachertube\.com/(user/profile|collection)/(?P<user>[0-9a-zA-Z]+)/?'

    _MEDIA_RE = r'''(?sx)
        class="?sidebar_thumb_time"?>[0-9:]+</div>
        \s*
        <a\s+href="(https?://(?:www\.)?teachertube\.com/(?:video|audio)/[^"]+)"
    '''
    _TEST = {
        'url': 'http://www.teachertube.com/user/profile/rbhagwati2',
        'info_dict': {
            'id': 'rbhagwati2'
        },
        'playlist_mincount': 179,
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        user_id = mobj.group('user')

        urls = []
        webpage = self._download_webpage(url, user_id)
        urls.extend(re.findall(self._MEDIA_RE, webpage))

        pages = re.findall(r'/ajax-user/user-videos/%s\?page=([0-9]+)' % user_id, webpage)[:-1]
        for p in pages:
            more = 'http://www.teachertube.com/ajax-user/user-videos/%s?page=%s' % (user_id, p)
            webpage = self._download_webpage(more, user_id, 'Downloading page %s/%s' % (p, len(pages)))
            video_urls = re.findall(self._MEDIA_RE, webpage)
            urls.extend(video_urls)

        entries = [self.url_result(vurl, 'TeacherTube') for vurl in urls]
        return self.playlist_result(entries, user_id)
