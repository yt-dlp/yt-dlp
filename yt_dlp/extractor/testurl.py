import re

from .common import InfoExtractor
from ..utils import ExtractorError


class TestURLIE(InfoExtractor):
    """ Allows addressing of the test cases as test:yout.*be_1 """

    IE_DESC = False  # Do not list
    _VALID_URL = r'test(?:url)?:(?P<extractor>.*?)(?:_(?P<num>[0-9]+))?$'

    def _real_extract(self, url):
        from . import gen_extractor_classes

        extractor_id, num = self._match_valid_url(url).group('extractor', 'num')
        if not extractor_id:
            return {'id': ':test', 'title': '', 'url': url}

        rex = re.compile(extractor_id, flags=re.IGNORECASE)
        matching_extractors = [e for e in gen_extractor_classes() if rex.search(e.IE_NAME)]

        if len(matching_extractors) == 0:
            raise ExtractorError(f'No extractors matching {extractor_id!r} found', expected=True)
        elif len(matching_extractors) > 1:
            extractor = next((  # Check for exact match
                ie for ie in matching_extractors if ie.IE_NAME.lower() == extractor_id.lower()
            ), None) or next((  # Check for exact match without plugin suffix
                ie for ie in matching_extractors if ie.IE_NAME.split('+')[0].lower() == extractor_id.lower()
            ), None)
            if not extractor:
                raise ExtractorError(
                    'Found multiple matching extractors: %s' % ' '.join(ie.IE_NAME for ie in matching_extractors),
                    expected=True)
        else:
            extractor = matching_extractors[0]

        testcases = tuple(extractor.get_testcases(True))
        try:
            tc = testcases[int(num or 0)]
        except IndexError:
            raise ExtractorError(
                f'Test case {num or 0} not found, got only {len(testcases)} tests', expected=True)

        self.to_screen(f'Test URL: {tc["url"]}')
        return self.url_result(tc['url'])
