import base64
import re

from .common import InfoExtractor


class CloudflareStreamIE(InfoExtractor):
    _DOMAIN_RE = r'(?:cloudflarestream\.com|(?:videodelivery|bytehighway)\.net)'
    _EMBED_RE = r'embed\.%s/embed/[^/]+\.js\?.*?\bvideo=' % _DOMAIN_RE
    _ID_RE = r'[\da-f]{32}|[\w-]+\.[\w-]+\.[\w-]+'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:watch\.)?%s/|
                            %s
                        )
                        (?P<id>%s)
                    ''' % (_DOMAIN_RE, _EMBED_RE, _ID_RE)
    _TESTS = [{
        'url': 'https://embed.cloudflarestream.com/embed/we4g.fla9.latest.js?video=31c9291ab41fac05471db4e73aa11717',
        'info_dict': {
            'id': '31c9291ab41fac05471db4e73aa11717',
            'ext': 'mp4',
            'title': '31c9291ab41fac05471db4e73aa11717',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://watch.cloudflarestream.com/9df17203414fd1db3e3ed74abbe936c1',
        'only_matching': True,
    }, {
        'url': 'https://cloudflarestream.com/31c9291ab41fac05471db4e73aa11717/manifest/video.mpd',
        'only_matching': True,
    }, {
        'url': 'https://embed.videodelivery.net/embed/r4xu.fla9.latest.js?video=81d80727f3022488598f68d323c1ad5e',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_urls(webpage):
        return [
            mobj.group('url')
            for mobj in re.finditer(
                r'<script[^>]+\bsrc=(["\'])(?P<url>(?:https?:)?//%s(?:%s).*?)\1' % (CloudflareStreamIE._EMBED_RE, CloudflareStreamIE._ID_RE),
                webpage)]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        domain = 'bytehighway.net' if 'bytehighway.net/' in url else 'videodelivery.net'
        base_url = 'https://%s/%s/' % (domain, video_id)
        if '.' in video_id:
            video_id = self._parse_json(base64.urlsafe_b64decode(
                video_id.split('.')[1]), video_id)['sub']
        manifest_base_url = base_url + 'manifest/video.'

        formats = self._extract_m3u8_formats(
            manifest_base_url + 'm3u8', video_id, 'mp4',
            'm3u8_native', m3u8_id='hls', fatal=False)
        formats.extend(self._extract_mpd_formats(
            manifest_base_url + 'mpd', video_id, mpd_id='dash', fatal=False))
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video_id,
            'thumbnail': base_url + 'thumbnails/thumbnail.jpg',
            'formats': formats,
        }
