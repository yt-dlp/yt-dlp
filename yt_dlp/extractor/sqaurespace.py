import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    get_elements_html_by_class,
)


class SqaurespaceGenericPassthroughIE(InfoExtractor):
    _VALID_URL = False

    def _extract_from_webpage(self, url, webpage):
        for html in get_elements_html_by_class('sqs-video-wrapper', webpage):
            data = urllib.parse.unquote(extract_attributes(html).get('data-html'))
            yield from self._extract_generic_embeds(url, data, note=data)
