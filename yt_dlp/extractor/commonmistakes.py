from .common import InfoExtractor
from ..utils import ExtractorError


class CommonMistakesIE(InfoExtractor):
    IE_DESC = False  # Do not list
    _VALID_URL = r'(?:url|URL|yt-dlp)$'

    _TESTS = [{
        'url': 'url',
        'only_matching': True,
    }, {
        'url': 'URL',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        msg = (
            f'You\'ve asked yt-dlp to download the URL "{url}". '
            'That doesn\'t make any sense. '
            'Simply remove the parameter in your command or configuration.'
        )
        if not self.get_param('verbose'):
            msg += ' Add -v to the command line to see what arguments and configuration yt-dlp has'
        raise ExtractorError(msg, expected=True)


class UnicodeBOMIE(InfoExtractor):
    IE_DESC = False
    _VALID_URL = r'(?P<bom>\ufeff)(?P<id>.*)$'

    _TESTS = [{
        'url': '\ufeffhttp://www.youtube.com/watch?v=BaW_jenozKc',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        real_url = self._match_id(url)
        self.report_warning(
            'Your URL starts with a Byte Order Mark (BOM). '
            f'Removing the BOM and looking for "{real_url}" ...')
        return self.url_result(real_url)


class BlobIE(InfoExtractor):
    IE_DESC = False
    _VALID_URL = r'blob:'

    _TESTS = [{
        'url': 'blob:https://www.youtube.com/4eb3d090-a761-46e6-8083-c32016a36e3b',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        raise ExtractorError(
            'You\'ve asked yt-dlp to download a blob URL. '
            'A blob URL exists only locally in your browser. '
            'It is not possible for yt-dlp to access it.', expected=True)
