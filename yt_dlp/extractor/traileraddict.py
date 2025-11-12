import re

from .common import InfoExtractor


class TrailerAddictIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'(?:https?://)?(?:www\.)?traileraddict\.com/(?:trailer|clip)/(?P<movie>.+?)/(?P<trailer_name>.+)'
    _TEST = {
        'url': 'http://www.traileraddict.com/trailer/prince-avalanche/trailer',
        'md5': '41365557f3c8c397d091da510e73ceb4',
        'info_dict': {
            'id': '76184',
            'ext': 'mp4',
            'title': 'Prince Avalanche Trailer',
            'description': 'Trailer for Prince Avalanche.\n\nTwo highway road workers spend the summer of 1988 away from their city lives. The isolated landscape becomes a place of misadventure as the men find themselves at odds with each other and the women they left behind.',
        },
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        name = mobj.group('movie') + '/' + mobj.group('trailer_name')
        webpage = self._download_webpage(url, name)

        title = self._html_extract_title(webpage, 'video title').replace(' - Trailer Addict', '')
        view_count_str = self._search_regex(
            r'<span class="views_n">([0-9,.]+)</span>',
            webpage, 'view count', fatal=False)
        view_count = (
            None if view_count_str is None
            else int(view_count_str.replace(',', '')))
        video_id = self._search_regex(
            r'<param\s+name="movie"\s+value="/emb/([0-9]+)"\s*/>',
            webpage, 'video id')

        # Presence of (no)watchplus function indicates HD quality is available
        if re.search(r'function (no)?watchplus()', webpage):
            fvar = 'fvarhd'
        else:
            fvar = 'fvar'

        info_url = f'http://www.traileraddict.com/{fvar}.php?tid={video_id!s}'
        info_webpage = self._download_webpage(info_url, video_id, 'Downloading the info webpage')

        final_url = self._search_regex(r'&fileurl=(.+)',
                                       info_webpage, 'Download url').replace('%3F', '?')
        thumbnail_url = self._search_regex(r'&image=(.+?)&',
                                           info_webpage, 'thumbnail url')

        description = self._html_search_regex(
            r'(?s)<div class="synopsis">.*?<div class="movie_label_info"[^>]*>(.*?)</div>',
            webpage, 'description', fatal=False)

        return {
            'id': video_id,
            'url': final_url,
            'title': title,
            'thumbnail': thumbnail_url,
            'description': description,
            'view_count': view_count,
        }
