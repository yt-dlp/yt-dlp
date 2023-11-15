from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urllib_parse_unquote,
)
from ..utils import (
    int_or_none,
    parse_iso8601,
    strip_or_none,
    try_get,
)


class KinjaEmbedIE(InfoExtractor):
    IENAME = 'kinja:embed'
    _DOMAIN_REGEX = r'''(?:[^.]+\.)?
        (?:
            avclub|
            clickhole|
            deadspin|
            gizmodo|
            jalopnik|
            jezebel|
            kinja|
            kotaku|
            lifehacker|
            splinternews|
            the(?:inventory|onion|root|takeout)
        )\.com'''
    _COMMON_REGEX = r'''/
        (?:
            ajax/inset|
            embed/video
        )/iframe\?.*?\bid='''
    _VALID_URL = r'''(?x)https?://%s%s
        (?P<type>
            fb|
            imgur|
            instagram|
            jwp(?:layer)?-video|
            kinjavideo|
            mcp|
            megaphone|
            ooyala|
            soundcloud(?:-playlist)?|
            tumblr-post|
            twitch-stream|
            twitter|
            ustream-channel|
            vimeo|
            vine|
            youtube-(?:list|video)
        )-(?P<id>[^&]+)''' % (_DOMAIN_REGEX, _COMMON_REGEX)
    _EMBED_REGEX = [rf'(?x)<iframe[^>]+?src=(?P<q>["\'])(?P<url>(?:(?:https?:)?//{_DOMAIN_REGEX})?{_COMMON_REGEX}(?:(?!\1).)+)\1']
    _TESTS = [{
        'url': 'https://kinja.com/ajax/inset/iframe?id=fb-10103303356633621',
        'only_matching': True,
    }, {
        'url': 'https://kinja.com/ajax/inset/iframe?id=kinjavideo-100313',
        'only_matching': True,
    }, {
        'url': 'https://kinja.com/ajax/inset/iframe?id=megaphone-PPY1300931075',
        'only_matching': True,
    }, {
        'url': 'https://kinja.com/ajax/inset/iframe?id=ooyala-xzMXhleDpopuT0u1ijt_qZj3Va-34pEX%2FZTIxYmJjZDM2NWYzZDViZGRiOWJjYzc5',
        'only_matching': True,
    }, {
        'url': 'https://kinja.com/ajax/inset/iframe?id=soundcloud-128574047',
        'only_matching': True,
    }, {
        'url': 'https://kinja.com/ajax/inset/iframe?id=soundcloud-playlist-317413750',
        'only_matching': True,
    }, {
        'url': 'https://kinja.com/ajax/inset/iframe?id=tumblr-post-160130699814-daydreams-at-midnight',
        'only_matching': True,
    }, {
        'url': 'https://kinja.com/ajax/inset/iframe?id=twitch-stream-libratus_extra',
        'only_matching': True,
    }, {
        'url': 'https://kinja.com/ajax/inset/iframe?id=twitter-1068875942473404422',
        'only_matching': True,
    }, {
        'url': 'https://kinja.com/ajax/inset/iframe?id=ustream-channel-10414700',
        'only_matching': True,
    }, {
        'url': 'https://kinja.com/ajax/inset/iframe?id=vimeo-120153502',
        'only_matching': True,
    }, {
        'url': 'https://kinja.com/ajax/inset/iframe?id=vine-5BlvV5qqPrD',
        'only_matching': True,
    }, {
        'url': 'https://kinja.com/ajax/inset/iframe?id=youtube-list-BCQ3KyrPjgA/PLE6509247C270A72E',
        'only_matching': True,
    }, {
        'url': 'https://kinja.com/ajax/inset/iframe?id=youtube-video-00QyL0AgPAE',
        'only_matching': True,
    }]
    _JWPLATFORM_PROVIDER = ('cdn.jwplayer.com/v2/media/', 'JWPlatform')
    _PROVIDER_MAP = {
        'fb': ('facebook.com/video.php?v=', 'Facebook'),
        'imgur': ('imgur.com/', 'Imgur'),
        'instagram': ('instagram.com/p/', 'Instagram'),
        'jwplayer-video': _JWPLATFORM_PROVIDER,
        'jwp-video': _JWPLATFORM_PROVIDER,
        'megaphone': ('player.megaphone.fm/', 'Generic'),
        'ooyala': ('player.ooyala.com/player.js?embedCode=', 'Ooyala'),
        'soundcloud': ('api.soundcloud.com/tracks/', 'Soundcloud'),
        'soundcloud-playlist': ('api.soundcloud.com/playlists/', 'SoundcloudPlaylist'),
        'tumblr-post': ('%s.tumblr.com/post/%s', 'Tumblr'),
        'twitch-stream': ('twitch.tv/', 'TwitchStream'),
        'twitter': ('twitter.com/i/cards/tfw/v1/', 'TwitterCard'),
        'ustream-channel': ('ustream.tv/embed/', 'Ustream'),
        'vimeo': ('vimeo.com/', 'Vimeo'),
        'vine': ('vine.co/v/', 'Vine'),
        'youtube-list': ('youtube.com/embed/%s?list=%s', 'YoutubePlaylist'),
        'youtube-video': ('youtube.com/embed/', 'Youtube'),
    }

    def _real_extract(self, url):
        video_type, video_id = self._match_valid_url(url).groups()

        provider = self._PROVIDER_MAP.get(video_type)
        if provider:
            video_id = compat_urllib_parse_unquote(video_id)
            if video_type == 'tumblr-post':
                video_id, blog = video_id.split('-', 1)
                result_url = provider[0] % (blog, video_id)
            elif video_type == 'youtube-list':
                video_id, playlist_id = video_id.split('/')
                result_url = provider[0] % (video_id, playlist_id)
            else:
                if video_type == 'ooyala':
                    video_id = video_id.split('/')[0]
                result_url = provider[0] + video_id
            return self.url_result('http://' + result_url, provider[1])

        if video_type == 'kinjavideo':
            data = self._download_json(
                'https://kinja.com/api/core/video/views/videoById',
                video_id, query={'videoId': video_id})['data']
            title = data['title']

            formats = []
            for k in ('signedPlaylist', 'streaming'):
                m3u8_url = data.get(k + 'Url')
                if m3u8_url:
                    formats.extend(self._extract_m3u8_formats(
                        m3u8_url, video_id, 'mp4', 'm3u8_native',
                        m3u8_id='hls', fatal=False))

            thumbnail = None
            poster = data.get('poster') or {}
            poster_id = poster.get('id')
            if poster_id:
                thumbnail = 'https://i.kinja-img.com/gawker-media/image/upload/%s.%s' % (poster_id, poster.get('format') or 'jpg')

            return {
                'id': video_id,
                'title': title,
                'description': strip_or_none(data.get('description')),
                'formats': formats,
                'tags': data.get('tags'),
                'timestamp': int_or_none(try_get(
                    data, lambda x: x['postInfo']['publishTimeMillis']), 1000),
                'thumbnail': thumbnail,
                'uploader': data.get('network'),
            }
        else:
            video_data = self._download_json(
                'https://api.vmh.univision.com/metadata/v1/content/' + video_id,
                video_id)['videoMetadata']
            iptc = video_data['photoVideoMetadataIPTC']
            title = iptc['title']['en']
            fmg = video_data.get('photoVideoMetadata_fmg') or {}
            tvss_domain = fmg.get('tvssDomain') or 'https://auth.univision.com'
            data = self._download_json(
                tvss_domain + '/api/v3/video-auth/url-signature-tokens',
                video_id, query={'mcpids': video_id})['data'][0]
            formats = []

            rendition_url = data.get('renditionUrl')
            if rendition_url:
                formats = self._extract_m3u8_formats(
                    rendition_url, video_id, 'mp4',
                    'm3u8_native', m3u8_id='hls', fatal=False)

            fallback_rendition_url = data.get('fallbackRenditionUrl')
            if fallback_rendition_url:
                formats.append({
                    'format_id': 'fallback',
                    'tbr': int_or_none(self._search_regex(
                        r'_(\d+)\.mp4', fallback_rendition_url,
                        'bitrate', default=None)),
                    'url': fallback_rendition_url,
                })

            return {
                'id': video_id,
                'title': title,
                'thumbnail': try_get(iptc, lambda x: x['cloudinaryLink']['link'], compat_str),
                'uploader': fmg.get('network'),
                'duration': int_or_none(iptc.get('fileDuration')),
                'formats': formats,
                'description': try_get(iptc, lambda x: x['description']['en'], compat_str),
                'timestamp': parse_iso8601(iptc.get('dateReleased')),
            }
