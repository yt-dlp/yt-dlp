import base64
import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    get_elements_html_by_attribute,
    traverse_obj,
    unescapeHTML,
)


class StatsNZGenericPassthroughIE(InfoExtractor):
    _VALID_URL = False

    def _extract_from_webpage(self, url, webpage):
        if not re.compile(r'https?://www\.stats\.govt\.nz').match(url):
            return
        combined_html = ''
        for html in get_elements_html_by_attribute('id', 'pageViewData', webpage):
            data = self._parse_json(unescapeHTML(extract_attributes(html).get('data-value')), self._generic_id(url))
            for inner_html in traverse_obj(data, ('PageBlocks', ..., 'Content')):
                yield from self._extract_generic_embeds(url, inner_html)
                #combined_html += f'\n{inner_html}'
      #  if combined_html:

