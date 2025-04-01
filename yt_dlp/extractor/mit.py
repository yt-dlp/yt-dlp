import json
import re

from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import (
    ExtractorError,
    clean_html,
    get_element_by_id,
)


class TechTVMITIE(InfoExtractor):
    IE_NAME = 'techtv.mit.edu'
    _VALID_URL = r'https?://techtv\.mit\.edu/(?:videos|embeds)/(?P<id>\d+)'

    _TEST = {
        'url': 'http://techtv.mit.edu/videos/25418-mit-dna-learning-center-set',
        'md5': '00a3a27ee20d44bcaa0933ccec4a2cf7',
        'info_dict': {
            'id': '25418',
            'ext': 'mp4',
            'title': 'MIT DNA and Protein Sets',
            'description': 'md5:46f5c69ce434f0a97e7c628cc142802d',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        raw_page = self._download_webpage(
            f'http://techtv.mit.edu/videos/{video_id}', video_id)
        clean_page = re.compile(r'<!--.*?-->', re.S).sub('', raw_page)

        base_url = self._proto_relative_url(self._search_regex(
            r'ipadUrl: \'(.+?cloudfront.net/)', raw_page, 'base url'), 'http:')
        formats_json = self._search_regex(
            r'bitrates: (\[.+?\])', raw_page, 'video formats')
        formats_mit = json.loads(formats_json)
        formats = [
            {
                'format_id': f['label'],
                'url': base_url + f['url'].partition(':')[2],
                'ext': f['url'].partition(':')[0],
                'format': f['label'],
                'width': f['width'],
                'vbr': f['bitrate'],
            }
            for f in formats_mit
        ]

        title = get_element_by_id('edit-title', clean_page)
        description = clean_html(get_element_by_id('edit-description', clean_page))
        thumbnail = self._search_regex(
            r'playlist:.*?url: \'(.+?)\'',
            raw_page, 'thumbnail', flags=re.DOTALL)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': description,
            'thumbnail': thumbnail,
        }


class OCWMITIE(InfoExtractor):
    IE_NAME = 'ocw.mit.edu'
    _VALID_URL = r'https?://ocw\.mit\.edu/courses/(?P<topic>[a-z0-9\-]+)'
    _BASE_URL = 'http://ocw.mit.edu/'

    _TESTS = [
        {
            'url': 'http://ocw.mit.edu/courses/electrical-engineering-and-computer-science/6-041-probabilistic-systems-analysis-and-applied-probability-fall-2010/video-lectures/lecture-7-multiple-variables-expectations-independence/',
            'info_dict': {
                'id': 'EObHWIEKGjA',
                'ext': 'webm',
                'title': 'Lecture 7: Multiple Discrete Random Variables: Expectations, Conditioning, Independence',
                'description': 'In this lecture, the professor discussed multiple random variables, expectations, and binomial distribution.',
                'upload_date': '20121109',
                'uploader_id': 'MIT',
                'uploader': 'MIT OpenCourseWare',
            },
        },
        {
            'url': 'http://ocw.mit.edu/courses/mathematics/18-01sc-single-variable-calculus-fall-2010/1.-differentiation/part-a-definition-and-basic-rules/session-1-introduction-to-derivatives/',
            'info_dict': {
                'id': '7K1sB05pE0A',
                'ext': 'mp4',
                'title': 'Session 1: Introduction to Derivatives',
                'upload_date': '20090818',
                'uploader_id': 'MIT',
                'uploader': 'MIT OpenCourseWare',
                'description': 'This section contains lecture video excerpts, lecture notes, an interactive mathlet with supporting documents, and problem solving videos.',
            },
        },
    ]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        topic = mobj.group('topic')

        webpage = self._download_webpage(url, topic)
        title = self._html_search_meta('WT.cg_s', webpage)
        description = self._html_search_meta('Description', webpage)

        # search for call to ocw_embed_chapter_media(container_id, media_url, provider, page_url, image_url, start, stop, captions_file)
        embed_chapter_media = re.search(r'ocw_embed_chapter_media\((.+?)\)', webpage)
        if embed_chapter_media:
            metadata = re.sub(r'[\'"]', '', embed_chapter_media.group(1))
            metadata = re.split(r', ?', metadata)
            yt = metadata[1]
        else:
            # search for call to ocw_embed_chapter_media(container_id, media_url, provider, page_url, image_url, captions_file)
            embed_media = re.search(r'ocw_embed_media\((.+?)\)', webpage)
            if embed_media:
                metadata = re.sub(r'[\'"]', '', embed_media.group(1))
                metadata = re.split(r', ?', metadata)
                yt = metadata[1]
            else:
                raise ExtractorError('Unable to find embedded YouTube video.')
        video_id = YoutubeIE.extract_id(yt)

        return {
            '_type': 'url_transparent',
            'id': video_id,
            'title': title,
            'description': description,
            'url': yt,
            'ie_key': 'Youtube',
        }
