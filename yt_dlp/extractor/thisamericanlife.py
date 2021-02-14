from __future__ import unicode_literals

from .common import InfoExtractor


class ThisAmericanLifeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?thisamericanlife\.org/(?:radio-archives/episode/|play_full\.php\?play=)(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.thisamericanlife.org/radio-archives/episode/487/harper-high-school-part-one',
        'md5': '8f7d2da8926298fdfca2ee37764c11ce',
        'info_dict': {
            'id': '487',
            'ext': 'm4a',
            'title': '487: Harper High School, Part One',
            'description': 'md5:ee40bdf3fb96174a9027f76dbecea655',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }, {
        'url': 'http://www.thisamericanlife.org/play_full.php?play=487',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            'http://www.thisamericanlife.org/radio-archives/episode/%s' % video_id, video_id)

        return {
            'id': video_id,
            'url': 'http://stream.thisamericanlife.org/{0}/stream/{0}_64k.m3u8'.format(video_id),
            'protocol': 'm3u8_native',
            'ext': 'm4a',
            'acodec': 'aac',
            'vcodec': 'none',
            'abr': 64,
            'title': self._html_search_meta(r'twitter:title', webpage, 'title', fatal=True),
            'description': self._html_search_meta(r'description', webpage, 'description'),
            'thumbnail': self._og_search_thumbnail(webpage),
        }
