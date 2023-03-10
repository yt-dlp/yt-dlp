from .common import InfoExtractor
from ..utils import ExtractorError


class Sport5IE(InfoExtractor):
    _VALID_URL = r'https?://(?:www|vod)?\.sport5\.co\.il/.*\b(?:Vi|docID)=(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'http://vod.sport5.co.il/?Vc=147&Vi=176331&Page=1',
            'info_dict': {
                'id': 's5-Y59xx1-GUh2',
                'ext': 'mp4',
                'title': 'ולנסיה-קורדובה 0:3',
                'description': 'אלקאסר, גאייה ופגולי סידרו לקבוצה של נונו ניצחון על קורדובה ואת המקום הראשון בליגה',
                'duration': 228,
                'categories': list,
            },
            'skip': 'Blocked outside of Israel',
        }, {
            'url': 'http://www.sport5.co.il/articles.aspx?FolderID=3075&docID=176372&lang=HE',
            'info_dict': {
                'id': 's5-SiXxx1-hKh2',
                'ext': 'mp4',
                'title': 'GOALS_CELTIC_270914.mp4',
                'description': '',
                'duration': 87,
                'categories': list,
            },
            'skip': 'Blocked outside of Israel',
        }
    ]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        media_id = mobj.group('id')

        webpage = self._download_webpage(url, media_id)

        video_id = self._html_search_regex(r'clipId=([\w-]+)', webpage, 'video id')

        metadata = self._download_xml(
            'http://sport5-metadata-rr-d.nsacdn.com/vod/vod/%s/HDS/metadata.xml' % video_id,
            video_id)

        error = metadata.find('./Error')
        if error is not None:
            raise ExtractorError(
                '%s returned error: %s - %s' % (
                    self.IE_NAME,
                    error.find('./Name').text,
                    error.find('./Description').text),
                expected=True)

        title = metadata.find('./Title').text
        description = metadata.find('./Description').text
        duration = int(metadata.find('./Duration').text)

        posters_el = metadata.find('./PosterLinks')
        thumbnails = [{
            'url': thumbnail.text,
            'width': int(thumbnail.get('width')),
            'height': int(thumbnail.get('height')),
        } for thumbnail in posters_el.findall('./PosterIMG')] if posters_el is not None else []

        categories_el = metadata.find('./Categories')
        categories = [
            cat.get('name') for cat in categories_el.findall('./Category')
        ] if categories_el is not None else []

        formats = [{
            'url': fmt.text,
            'ext': 'mp4',
            'vbr': int(fmt.get('bitrate')),
            'width': int(fmt.get('width')),
            'height': int(fmt.get('height')),
        } for fmt in metadata.findall('./PlaybackLinks/FileURL')]

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnails': thumbnails,
            'duration': duration,
            'categories': categories,
            'formats': formats,
        }
