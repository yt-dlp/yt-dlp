import re
import urllib.parse

from .common import InfoExtractor
from .youtube import YoutubeTabIE
from ..utils import parse_qs, smuggle_url, traverse_obj


class EmbedlyIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www|cdn\.)?embedly\.com/widgets/media\.html\?(?:[^#]*?&)?(?:src|url)=(?:[^#&]+)'
    _TESTS = [{
        'url': 'https://cdn.embedly.com/widgets/media.html?src=http%3A%2F%2Fwww.youtube.com%2Fembed%2Fvideoseries%3Flist%3DUUGLim4T2loE5rwCMdpCIPVg&url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DSU4fj_aEMVw%26list%3DUUGLim4T2loE5rwCMdpCIPVg&image=http%3A%2F%2Fi.ytimg.com%2Fvi%2FSU4fj_aEMVw%2Fhqdefault.jpg&key=8ee8a2e6a8cc47aab1a5ee67f9a178e0&type=text%2Fhtml&schema=youtube&autoplay=1',
        'info_dict': {
            'id': 'UUGLim4T2loE5rwCMdpCIPVg',
            'modified_date': '20221225',
            'view_count': int,
            'uploader_url': 'https://www.youtube.com/@TraciHinesMusic',
            'channel_id': 'UCGLim4T2loE5rwCMdpCIPVg',
            'uploader': 'TraciJHines',
            'channel_url': 'https://www.youtube.com/@TraciHinesMusic',
            'channel': 'TraciJHines',
            'availability': 'public',
            'uploader_id': 'UCGLim4T2loE5rwCMdpCIPVg',
            'description': '',
            'tags': [],
            'title': 'Uploads from TraciJHines',
        },
        'playlist_mincount': 10,
    }, {
        'url': 'https://cdn.embedly.com/widgets/media.html?src=http%3A%2F%2Fwww.youtube.com%2Fembed%2Fvideoseries%3Flist%3DUUGLim4T2loE5rwCMdpCIPVg&url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DSU4fj_aEMVw%26list%3DUUGLim4T2loE5rwCMdpCIPVg&image=http%3A%2F%2Fi.ytimg.com%2Fvi%2FSU4fj_aEMVw%2Fhqdefault.jpg&key=8ee8a2e6a8cc47aab1a5ee67f9a178e0&type=text%2Fhtml&schema=youtube&autoplay=1',
        'params': {'noplaylist': True},
        'info_dict': {
            'id': 'SU4fj_aEMVw',
            'ext': 'mp4',
            'title': 'I\'m on Patreon!',
            'age_limit': 0,
            'categories': ['Entertainment'],
            'thumbnail': 'https://i.ytimg.com/vi_webp/SU4fj_aEMVw/maxresdefault.webp',
            'live_status': 'not_live',
            'playable_in_embed': True,
            'channel': 'TraciJHines',
            'uploader_id': 'TraciJHines',
            'channel_url': 'https://www.youtube.com/channel/UCGLim4T2loE5rwCMdpCIPVg',
            'uploader_url': 'http://www.youtube.com/user/TraciJHines',
            'upload_date': '20150211',
            'duration': 282,
            'availability': 'public',
            'channel_follower_count': int,
            'tags': 'count:39',
            'view_count': int,
            'comment_count': int,
            'channel_id': 'UCGLim4T2loE5rwCMdpCIPVg',
            'like_count': int,
            'uploader': 'TraciJHines',
            'description': 'md5:8af6425f50bd46fbf29f3db0fc3a8364',
            'chapters': list,

        },
    }, {
        'url': 'https://cdn.embedly.com/widgets/media.html?src=https://player.vimeo.com/video/1234567?h=abcdefgh',
        'only_matching': True,
    }]

    _WEBPAGE_TESTS = [{
        'url': 'http://www.permacultureetc.com/2022/12/comment-greffer-facilement-les-arbres-fruitiers.html',
        'info_dict': {
            'id': 'pfUK_ADTvgY',
            'ext': 'mp4',
            'title': 'Comment greffer facilement les arbres fruitiers ? (mois par mois)',
            'description': 'md5:d3a876995e522f138aabb48e040bfb4c',
            'view_count': int,
            'upload_date': '20221210',
            'comment_count': int,
            'live_status': 'not_live',
            'channel_id': 'UCsM4_jihNFYe4CtSkXvDR-Q',
            'channel_follower_count': int,
            'tags': ['permaculture', 'jardinage', 'dekarz', 'autonomie', 'greffe', 'fruitiers', 'arbres', 'jardin forêt', 'forêt comestible', 'damien'],
            'playable_in_embed': True,
            'uploader': 'permaculture agroécologie etc...',
            'channel': 'permaculture agroécologie etc...',
            'thumbnail': 'https://i.ytimg.com/vi/pfUK_ADTvgY/sddefault.jpg',
            'duration': 1526,
            'channel_url': 'https://www.youtube.com/channel/UCsM4_jihNFYe4CtSkXvDR-Q',
            'age_limit': 0,
            'uploader_id': 'permacultureetc',
            'like_count': int,
            'uploader_url': 'http://www.youtube.com/user/permacultureetc',
            'categories': ['Education'],
            'availability': 'public',
        },
    }]

    @classmethod
    def _extract_from_webpage(cls, url, webpage):
        # Bypass "ie=cls" and suitable check
        for mobj in re.finditer(r'class=["\']embedly-card["\'][^>]href=["\'](?P<url>[^"\']+)', webpage):
            yield cls.url_result(mobj.group('url'))

        for mobj in re.finditer(r'class=["\']embedly-embed["\'][^>]src=["\'][^"\']*url=(?P<url>[^&]+)', webpage):
            yield cls.url_result(urllib.parse.unquote(mobj.group('url')))

    def _real_extract(self, url):
        qs = parse_qs(url)
        src = urllib.parse.unquote(traverse_obj(qs, ('url', 0)) or '')
        if src and YoutubeTabIE.suitable(src):
            return self.url_result(src, YoutubeTabIE)
        return self.url_result(smuggle_url(
            urllib.parse.unquote(traverse_obj(qs, ('src', 0), ('url', 0))),
            {'referer': url}))
