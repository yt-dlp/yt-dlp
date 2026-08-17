from .common import InfoExtractor


class DBTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?dagbladet\.no/video/(?:(?:embed|(?P<display_id>[^/]+))/)?(?P<id>[0-9A-Za-z_-]{11}|[a-zA-Z0-9]{8})'
    _EMBED_REGEX = [r'<iframe[^>]+src=(["\'])(?P<url>(?:https?:)?//(?:www\.)?dagbladet\.no/video/embed/(?:[0-9A-Za-z_-]{11}|[a-zA-Z0-9]{8}).*?)\1']
    _TESTS = [{
        'url': 'https://www.dagbladet.no/video/PynxJnNWChE/',
        'md5': 'b8f850ba1860adbda668d367f9b77699',
        'info_dict': {
            'id': 'PynxJnNWChE',
            'ext': 'mp4',
            'title': 'Skulle teste ut fornøyelsespark, men kollegaen var bare opptatt av bikinikroppen',
            'description': 'md5:49cc8370e7d66e8a2ef15c3b4631fd3f',
            'thumbnail': r're:https?://.+\.jpg',
            'upload_date': '20160916',
            'duration': 69,
            'uploader_id': 'UCk5pvsyZJoYJBd7_oFPTlRQ',
            'uploader': 'Dagbladet',
        },
        'skip': 'Invalid URL',
    }, {
        'url': 'https://www.dagbladet.no/video/embed/xlGmyIeN9Jo/?autoplay=false',
        'only_matching': True,
    }, {
        'url': 'https://www.dagbladet.no/video/truer-iran-bor-passe-dere/PalfB2Cw',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        # FIXME: Embed detection
        'url': 'https://www.dagbladet.no/nyheter/rekordstort-russisk-angrep/83325693',
        'info_dict': {
            'id': '1HW7fYry',
            'ext': 'mp4',
            'title': 'Putin taler - så skjer dette',
            'description': 'md5:3e8bacee33de861a9663d9a3fcc54e5e',
            'display_id': 'putin-taler-sa-skjer-dette',
            'thumbnail': r're:https?://cdn\.jwplayer\.com/v2/media/.+',
            'timestamp': 1751043600,
            'upload_date': '20250627',
        },
    }]

    def _real_extract(self, url):
        display_id, video_id = self._match_valid_url(url).groups()
        info = {
            '_type': 'url_transparent',
            'id': video_id,
            'display_id': display_id,
        }
        if len(video_id) == 11:
            info.update({
                'url': video_id,
                'ie_key': 'Youtube',
            })
        else:
            info.update({
                'url': 'jwplatform:' + video_id,
                'ie_key': 'JWPlatform',
            })
        return info
