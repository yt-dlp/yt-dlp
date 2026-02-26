from .common import InfoExtractor
from .kaltura import KalturaIE
from ..utils.traversal import require, traverse_obj


class AZMedienIE(InfoExtractor):
    IE_DESC = 'AZ Medien videos'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.|tv\.)?
                        (?:
                            telezueri\.ch|
                            telebaern\.tv|
                            telem1\.ch|
                            tvo-online\.ch
                        )/
                        [^/?#]+/
                        (?P<id>
                            [^/?#]+-\d+
                        )
                        (?:
                            \#video=
                            (?P<kaltura_id>
                                [_0-9a-z]+
                            )
                        )?
                    '''

    _TESTS = [{
        'url': 'https://tv.telezueri.ch/sonntalk/bundesrats-vakanzen-eu-rahmenabkommen-133214569',
        'info_dict': {
            'id': '1_anruz3wy',
            'ext': 'mp4',
            'title': 'Bundesrats-Vakanzen / EU-Rahmenabkommen',
            'uploader_id': 'TVOnline',
            'upload_date': '20180930',
            'timestamp': 1538328802,
            'view_count': int,
            'thumbnail': 'http://cfvod.kaltura.com/p/1719221/sp/171922100/thumbnail/entry_id/1_anruz3wy/version/100031',
            'duration': 1930,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.telebaern.tv/telebaern-news/montag-1-oktober-2018-ganze-sendung-133531189#video=0_7xjo9lf1',
        'only_matching': True,
    }]
    _PARTNER_ID = '1719221'

    def _real_extract(self, url):
        display_id, entry_id = self._match_valid_url(url).groups()

        if not entry_id:
            webpage = self._download_webpage(url, display_id)
            data = self._search_json(
                r'window\.__APOLLO_STATE__\s*=', webpage, 'video data', display_id)
            entry_id = traverse_obj(data, (
                lambda _, v: v['__typename'] == 'KalturaData', 'kalturaId', any, {require('kaltura id')}))

        return self.url_result(
            f'kaltura:{self._PARTNER_ID}:{entry_id}',
            ie=KalturaIE.ie_key(), video_id=entry_id)
