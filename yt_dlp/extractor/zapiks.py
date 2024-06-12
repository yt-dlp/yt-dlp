import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_duration,
    parse_iso8601,
    xpath_text,
    xpath_with_ns,
)


class ZapiksIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?zapiks\.(?:fr|com)/(?:(?:[a-z]{2}/)?(?P<display_id>.+?)\.html|index\.php\?.*\bmedia_id=(?P<id>\d+))'
    _EMBED_REGEX = [r'<iframe[^>]+src="(?P<url>https?://(?:www\.)?zapiks\.fr/index\.php\?.+?)"']
    _TESTS = [
        {
            'url': 'http://www.zapiks.fr/ep2s3-bon-appetit-eh-be-viva.html',
            'md5': 'aeb3c473b2d564b2d46d664d28d5f050',
            'info_dict': {
                'id': '80798',
                'ext': 'mp4',
                'title': 'EP2S3 - Bon Appétit - Eh bé viva les pyrénées con!',
                'description': 'md5:7054d6f6f620c6519be1fe710d4da847',
                'thumbnail': r're:^https?://.*\.jpg$',
                'duration': 528,
                'timestamp': 1359044972,
                'upload_date': '20130124',
                'view_count': int,
            },
        },
        {
            'url': 'http://www.zapiks.com/ep3s5-bon-appetit-baqueira-m-1.html',
            'only_matching': True,
        },
        {
            'url': 'http://www.zapiks.com/nl/ep3s5-bon-appetit-baqueira-m-1.html',
            'only_matching': True,
        },
        {
            'url': 'http://www.zapiks.fr/index.php?action=playerIframe&amp;media_id=118046&amp;width=640&amp;height=360&amp;autoStart=false&amp;language=fr',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        display_id = mobj.group('display_id') or video_id

        webpage = self._download_webpage(url, display_id)

        if not video_id:
            video_id = self._search_regex(
                r'data-media-id="(\d+)"', webpage, 'video id')

        playlist = self._download_xml(
            f'http://www.zapiks.fr/view/index.php?action=playlist&media_id={video_id}&lang=en',
            display_id)

        NS_MAP = {
            'jwplayer': 'http://rss.jwpcdn.com/',
        }

        def ns(path):
            return xpath_with_ns(path, NS_MAP)

        item = playlist.find('./channel/item')

        title = xpath_text(item, 'title', 'title') or self._og_search_title(webpage)
        description = self._og_search_description(webpage, default=None)
        thumbnail = xpath_text(
            item, ns('./jwplayer:image'), 'thumbnail') or self._og_search_thumbnail(webpage, default=None)
        duration = parse_duration(self._html_search_meta(
            'duration', webpage, 'duration', default=None))
        timestamp = parse_iso8601(self._html_search_meta(
            'uploadDate', webpage, 'upload date', default=None), ' ')

        view_count = int_or_none(self._search_regex(
            r'UserPlays:(\d+)', webpage, 'view count', default=None))
        comment_count = int_or_none(self._search_regex(
            r'UserComments:(\d+)', webpage, 'comment count', default=None))

        formats = []
        for source in item.findall(ns('./jwplayer:source')):
            format_id = source.attrib['label']
            f = {
                'url': source.attrib['file'],
                'format_id': format_id,
            }
            m = re.search(r'^(?P<height>\d+)[pP]', format_id)
            if m:
                f['height'] = int(m.group('height'))
            formats.append(f)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'timestamp': timestamp,
            'view_count': view_count,
            'comment_count': comment_count,
            'formats': formats,
        }
