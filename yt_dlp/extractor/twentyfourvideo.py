from .common import InfoExtractor
from ..utils import (
    parse_iso8601,
    int_or_none,
    xpath_attr,
    xpath_element,
)


class TwentyFourVideoIE(InfoExtractor):
    IE_NAME = '24video'
    _VALID_URL = r'''(?x)
                    https?://
                        (?P<host>
                            (?:(?:www|porno?)\.)?24video\.
                            (?:net|me|xxx|sexy?|tube|adult|site|vip)
                        )/
                        (?:
                            video/(?:(?:view|xml)/)?|
                            player/new24_play\.swf\?id=
                        )
                        (?P<id>\d+)
                    '''

    _TESTS = [{
        'url': 'http://www.24video.net/video/view/1044982',
        'md5': 'e09fc0901d9eaeedac872f154931deeb',
        'info_dict': {
            'id': '1044982',
            'ext': 'mp4',
            'title': 'Эротика каменного века',
            'description': 'Как смотрели порно в каменном веке.',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'SUPERTELO',
            'duration': 31,
            'timestamp': 1275937857,
            'upload_date': '20100607',
            'age_limit': 18,
            'like_count': int,
            'dislike_count': int,
        },
    }, {
        'url': 'http://www.24video.net/player/new24_play.swf?id=1044982',
        'only_matching': True,
    }, {
        'url': 'http://www.24video.me/video/view/1044982',
        'only_matching': True,
    }, {
        'url': 'http://www.24video.tube/video/view/2363750',
        'only_matching': True,
    }, {
        'url': 'https://www.24video.site/video/view/2640421',
        'only_matching': True,
    }, {
        'url': 'https://porno.24video.net/video/2640421-vsya-takaya-gibkaya-i-v-masle',
        'only_matching': True,
    }, {
        'url': 'https://www.24video.vip/video/view/1044982',
        'only_matching': True,
    }, {
        'url': 'https://porn.24video.net/video/2640421-vsya-takay',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        host = mobj.group('host')

        webpage = self._download_webpage(
            'http://%s/video/view/%s' % (host, video_id), video_id)

        title = self._og_search_title(webpage)
        description = self._html_search_regex(
            r'<(p|span)[^>]+itemprop="description"[^>]*>(?P<description>[^<]+)</\1>',
            webpage, 'description', fatal=False, group='description')
        thumbnail = self._og_search_thumbnail(webpage)
        duration = int_or_none(self._og_search_property(
            'duration', webpage, 'duration', fatal=False))
        timestamp = parse_iso8601(self._search_regex(
            r'<time[^>]+\bdatetime="([^"]+)"[^>]+itemprop="uploadDate"',
            webpage, 'upload date', fatal=False))

        uploader = self._html_search_regex(
            r'class="video-uploaded"[^>]*>\s*<a href="/jsecUser/movies/[^"]+"[^>]*>([^<]+)</a>',
            webpage, 'uploader', fatal=False)

        view_count = int_or_none(self._html_search_regex(
            r'<span class="video-views">(\d+) просмотр',
            webpage, 'view count', fatal=False))
        comment_count = int_or_none(self._html_search_regex(
            r'<a[^>]+href="#tab-comments"[^>]*>(\d+) комментари',
            webpage, 'comment count', default=None))

        # Sets some cookies
        self._download_xml(
            r'http://%s/video/xml/%s?mode=init' % (host, video_id),
            video_id, 'Downloading init XML')

        video_xml = self._download_xml(
            'http://%s/video/xml/%s?mode=play' % (host, video_id),
            video_id, 'Downloading video XML')

        video = xpath_element(video_xml, './/video', 'video', fatal=True)

        formats = [{
            'url': xpath_attr(video, '', 'url', 'video URL', fatal=True),
        }]

        like_count = int_or_none(video.get('ratingPlus'))
        dislike_count = int_or_none(video.get('ratingMinus'))
        age_limit = 18 if video.get('adult') == 'true' else 0

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'duration': duration,
            'timestamp': timestamp,
            'view_count': view_count,
            'comment_count': comment_count,
            'like_count': like_count,
            'dislike_count': dislike_count,
            'age_limit': age_limit,
            'formats': formats,
        }
