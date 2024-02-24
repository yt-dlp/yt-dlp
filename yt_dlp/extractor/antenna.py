import urllib.parse

from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    ExtractorError,
    determine_ext,
    make_archive_id,
    scale_thumbnails_to_max_format_width,
)


class AntennaBaseIE(InfoExtractor):
    def _download_and_extract_api_data(self, video_id, netloc, cid=None):
        info = self._download_json(f'{self.http_scheme()}//{netloc}{self._API_PATH}',
                                   video_id, query={'cid': cid or video_id})
        if not info.get('url'):
            raise ExtractorError(f'No source found for {video_id}')

        ext = determine_ext(info['url'])
        if ext == 'm3u8':
            formats, subs = self._extract_m3u8_formats_and_subtitles(info['url'], video_id, 'mp4')
        else:
            formats, subs = [{'url': info['url'], 'format_id': ext}], {}

        thumbnails = scale_thumbnails_to_max_format_width(
            formats, [{'url': info['thumb']}], r'(?<=/imgHandler/)\d+') if info.get('thumb') else []
        return {
            'id': video_id,
            'title': info.get('title'),
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subs,
        }


class AntennaGrWatchIE(AntennaBaseIE):
    IE_NAME = 'antenna:watch'
    IE_DESC = 'antenna.gr and ant1news.gr videos'
    _VALID_URL = r'https?://(?P<netloc>(?:www\.)?(?:antenna|ant1news)\.gr)/watch/(?P<id>\d+)/'
    _API_PATH = '/templates/data/player'

    _TESTS = [{
        'url': 'https://www.ant1news.gr/watch/1506168/ant1-news-09112021-stis-18-45',
        'md5': 'c472d9dd7cd233c63aff2ea42201cda6',
        'info_dict': {
            'id': '1506168',
            'ext': 'mp4',
            'title': 'md5:0ad00fa66ecf8aa233d26ab0dba7514a',
            'description': 'md5:18665af715a6dcfeac1d6153a44f16b0',
            'thumbnail': r're:https://ant1media\.azureedge\.net/imgHandler/\d+/26d46bf6-8158-4f02-b197-7096c714b2de\.jpg',
        },
    }, {
        'url': 'https://www.antenna.gr/watch/1643812/oi-prodotes-epeisodio-01',
        'md5': '8f6f7dd3b1dba4d835ba990e25f31243',
        'info_dict': {
            'id': '1643812',
            'ext': 'mp4',
            'format_id': 'mp4',
            'title': 'ΟΙ ΠΡΟΔΟΤΕΣ – ΕΠΕΙΣΟΔΙΟ 01',
            'thumbnail': r're:https://ant1media\.azureedge\.net/imgHandler/\d+/b3d63096-e72d-43c4-87a0-00d4363d242f\.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id, netloc = self._match_valid_url(url).group('id', 'netloc')
        webpage = self._download_webpage(url, video_id)
        info = self._download_and_extract_api_data(video_id, netloc)
        info['description'] = self._og_search_description(webpage, default=None)
        info['_old_archive_ids'] = [make_archive_id('Ant1NewsGrWatch', video_id)],
        return info


class Ant1NewsGrArticleIE(AntennaBaseIE):
    IE_NAME = 'ant1newsgr:article'
    IE_DESC = 'ant1news.gr articles'
    _VALID_URL = r'https?://(?:www\.)?ant1news\.gr/[^/]+/article/(?P<id>\d+)/'

    _TESTS = [{
        'url': 'https://www.ant1news.gr/afieromata/article/549468/o-tzeims-mpont-sta-meteora-oi-apeiles-kai-o-xesikomos-ton-kalogeron',
        'md5': '57eb8d12181f0fa2b14b0b138e1de9b6',
        'info_dict': {
            'id': '_xvg/m_cmbatw=',
            'ext': 'mp4',
            'title': 'md5:a93e8ecf2e4073bfdffcb38f59945411',
            'timestamp': 1666166520,
            'upload_date': '20221019',
            'thumbnail': 'https://ant1media.azureedge.net/imgHandler/1920/756206d2-d640-40e2-b201-3555abdfc0db.jpg',
        },
    }, {
        'url': 'https://ant1news.gr/Society/article/620286/symmoria-anilikon-dikigoros-thymaton-ithelan-na-toys-apoteleiosoyn',
        'info_dict': {
            'id': '620286',
            'title': 'md5:91fe569e952e4d146485740ae927662b',
        },
        'playlist_mincount': 2,
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        info = self._search_json_ld(webpage, video_id, expected_type='NewsArticle')
        embed_urls = list(Ant1NewsGrEmbedIE._extract_embed_urls(url, webpage))
        if not embed_urls:
            raise ExtractorError('no videos found for %s' % video_id, expected=True)
        return self.playlist_from_matches(
            embed_urls, video_id, info.get('title'), ie=Ant1NewsGrEmbedIE.ie_key(),
            video_kwargs={'url_transparent': True, 'timestamp': info.get('timestamp')})


class Ant1NewsGrEmbedIE(AntennaBaseIE):
    IE_NAME = 'ant1newsgr:embed'
    IE_DESC = 'ant1news.gr embedded videos'
    _BASE_PLAYER_URL_RE = r'(?:https?:)?//(?:[a-zA-Z0-9\-]+\.)?(?:antenna|ant1news)\.gr/templates/pages/player'
    _VALID_URL = rf'{_BASE_PLAYER_URL_RE}\?([^#]+&)?cid=(?P<id>[^#&]+)'
    _EMBED_REGEX = [rf'<iframe[^>]+?src=(?P<_q1>["\'])(?P<url>{_BASE_PLAYER_URL_RE}\?(?:(?!(?P=_q1)).)+)(?P=_q1)']
    _API_PATH = '/templates/data/jsonPlayer'

    _TESTS = [{
        'url': 'https://www.antenna.gr/templates/pages/player?cid=3f_li_c_az_jw_y_u=&w=670&h=377',
        'md5': 'dfc58c3a11a5a9aad2ba316ed447def3',
        'info_dict': {
            'id': '3f_li_c_az_jw_y_u=',
            'ext': 'mp4',
            'title': 'md5:a30c93332455f53e1e84ae0724f0adf7',
            'thumbnail': 'https://ant1media.azureedge.net/imgHandler/640/bbe31201-3f09-4a4e-87f5-8ad2159fffe2.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        canonical_url = self._request_webpage(
            HEADRequest(url), video_id,
            note='Resolve canonical player URL',
            errnote='Could not resolve canonical player URL').url
        _, netloc, _, _, query, _ = urllib.parse.urlparse(canonical_url)
        cid = urllib.parse.parse_qs(query)['cid'][0]

        return self._download_and_extract_api_data(video_id, netloc, cid=cid)
