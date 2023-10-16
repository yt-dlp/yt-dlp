from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    unified_strdate
)


class JoveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?jove\.com/video/(?P<id>[0-9]+)'
    _CHAPTERS_URL = 'http://www.jove.com/video-chapters?videoid={video_id:}'
    _TESTS = [
        {
            'url': 'http://www.jove.com/video/2744/electrode-positioning-montage-transcranial-direct-current',
            'md5': '93723888d82dbd6ba8b3d7d0cd65dd2b',
            'info_dict': {
                'id': '2744',
                'ext': 'mp4',
                'title': 'Electrode Positioning and Montage in Transcranial Direct Current Stimulation',
                'description': 'md5:015dd4509649c0908bc27f049e0262c6',
                'thumbnail': r're:^https?://.*\.png$',
                'upload_date': '20110523',
            }
        },
        {
            'url': 'http://www.jove.com/video/51796/culturing-caenorhabditis-elegans-axenic-liquid-media-creation',
            'md5': '914aeb356f416811d911996434811beb',
            'info_dict': {
                'id': '51796',
                'ext': 'mp4',
                'title': 'Culturing Caenorhabditis elegans in Axenic Liquid Media and Creation of Transgenic Worms by Microparticle Bombardment',
                'description': 'md5:35ff029261900583970c4023b70f1dc9',
                'thumbnail': r're:^https?://.*\.png$',
                'upload_date': '20140802',
            }
        },

    ]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')

        webpage = self._download_webpage(url, video_id)

        chapters_id = self._html_search_regex(
            r'/video-chapters\?videoid=([0-9]+)', webpage, 'chapters id')

        chapters_xml = self._download_xml(
            self._CHAPTERS_URL.format(video_id=chapters_id),
            video_id, note='Downloading chapters XML',
            errnote='Failed to download chapters XML')

        video_url = chapters_xml.attrib.get('video')
        if not video_url:
            raise ExtractorError('Failed to get the video URL')

        title = self._html_search_meta('citation_title', webpage, 'title')
        thumbnail = self._og_search_thumbnail(webpage)
        description = self._html_search_regex(
            r'<div id="section_body_summary"><p class="jove_content">(.+?)</p>',
            webpage, 'description', fatal=False)
        publish_date = unified_strdate(self._html_search_meta(
            'citation_publication_date', webpage, 'publish date', fatal=False))
        comment_count = int(self._html_search_regex(
            r'<meta name="num_comments" content="(\d+) Comments?"',
            webpage, 'comment count', fatal=False))

        return {
            'id': video_id,
            'title': title,
            'url': video_url,
            'thumbnail': thumbnail,
            'description': description,
            'upload_date': publish_date,
            'comment_count': comment_count,
        }
