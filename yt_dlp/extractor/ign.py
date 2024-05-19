import re
import urllib.parse

from .common import InfoExtractor
from ..compat import compat_parse_qs
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    determine_ext,
    error_to_compat_str,
    extract_attributes,
    int_or_none,
    merge_dicts,
    parse_iso8601,
    strip_or_none,
    traverse_obj,
    url_or_none,
    urljoin,
)


class IGNBaseIE(InfoExtractor):
    def _call_api(self, slug):
        return self._download_json(
            'http://apis.ign.com/{0}/v3/{0}s/slug/{1}'.format(self._PAGE_TYPE, slug), slug)

    def _checked_call_api(self, slug):
        try:
            return self._call_api(slug)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 404:
                e.cause.args = e.cause.args or [
                    e.cause.response.url, e.cause.status, e.cause.reason]
                raise ExtractorError(
                    'Content not found: expired?', cause=e.cause,
                    expected=True)
            raise

    def _extract_video_info(self, video, fatal=True):
        video_id = video['videoId']

        formats = []
        refs = traverse_obj(video, 'refs', expected_type=dict) or {}

        m3u8_url = url_or_none(refs.get('m3uUrl'))
        if m3u8_url:
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', 'm3u8_native',
                m3u8_id='hls', fatal=False))

        f4m_url = url_or_none(refs.get('f4mUrl'))
        if f4m_url:
            formats.extend(self._extract_f4m_formats(
                f4m_url, video_id, f4m_id='hds', fatal=False))

        for asset in (video.get('assets') or []):
            asset_url = url_or_none(asset.get('url'))
            if not asset_url:
                continue
            formats.append({
                'url': asset_url,
                'tbr': int_or_none(asset.get('bitrate'), 1000),
                'fps': int_or_none(asset.get('frame_rate')),
                'height': int_or_none(asset.get('height')),
                'width': int_or_none(asset.get('width')),
            })

        mezzanine_url = traverse_obj(
            video, ('system', 'mezzanineUrl'), expected_type=url_or_none)
        if mezzanine_url:
            formats.append({
                'ext': determine_ext(mezzanine_url, 'mp4'),
                'format_id': 'mezzanine',
                'quality': 1,
                'url': mezzanine_url,
            })

        thumbnails = traverse_obj(
            video, ('thumbnails', ..., {'url': 'url'}), expected_type=url_or_none)
        tags = traverse_obj(
            video, ('tags', ..., 'displayName'),
            expected_type=lambda x: x.strip() or None)

        metadata = traverse_obj(video, 'metadata', expected_type=dict) or {}
        title = traverse_obj(
            metadata, 'longTitle', 'title', 'name',
            expected_type=lambda x: x.strip() or None)

        return {
            'id': video_id,
            'title': title,
            'description': strip_or_none(metadata.get('description')),
            'timestamp': parse_iso8601(metadata.get('publishDate')),
            'duration': int_or_none(metadata.get('duration')),
            'thumbnails': thumbnails,
            'formats': formats,
            'tags': tags,
        }


class IGNIE(IGNBaseIE):
    """
    Extractor for some of the IGN sites, like www.ign.com, es.ign.com de.ign.com.
    Some videos of it.ign.com are also supported
    """
    _VIDEO_PATH_RE = r'/(?:\d{4}/\d{2}/\d{2}/)?(?P<id>.+?)'
    _PLAYLIST_PATH_RE = r'(?:/?\?(?P<filt>[^&#]+))?'
    _VALID_URL = (
        r'https?://(?:.+?\.ign|www\.pcmag)\.com/videos(?:%s)'
        % '|'.join((_VIDEO_PATH_RE + r'(?:[/?&#]|$)', _PLAYLIST_PATH_RE)))
    IE_NAME = 'ign.com'
    _PAGE_TYPE = 'video'

    _TESTS = [{
        'url': 'http://www.ign.com/videos/2013/06/05/the-last-of-us-review',
        'md5': 'd2e1586d9987d40fad7867bf96a018ea',
        'info_dict': {
            'id': '8f862beef863986b2785559b9e1aa599',
            'ext': 'mp4',
            'title': 'The Last of Us Review',
            'description': 'md5:c8946d4260a4d43a00d5ae8ed998870c',
            'timestamp': 1370440800,
            'upload_date': '20130605',
            'tags': 'count:9',
            'display_id': 'the-last-of-us-review',
            'thumbnail': 'https://assets1.ignimgs.com/vid/thumbnails/user/2014/03/26/lastofusreviewmimig2.jpg',
            'duration': 440,
        },
        'params': {
            'nocheckcertificate': True,
        },
    }, {
        'url': 'http://www.pcmag.com/videos/2015/01/06/010615-whats-new-now-is-gogo-snooping-on-your-data',
        'md5': 'f1581a6fe8c5121be5b807684aeac3f6',
        'info_dict': {
            'id': 'ee10d774b508c9b8ec07e763b9125b91',
            'ext': 'mp4',
            'title': 'What\'s New Now: Is GoGo Snooping on Your Data?',
            'description': 'md5:817a20299de610bd56f13175386da6fa',
            'timestamp': 1420571160,
            'upload_date': '20150106',
            'tags': 'count:4',
        },
        'skip': '404 Not Found',
    }, {
        'url': 'https://www.ign.com/videos/is-a-resident-evil-4-remake-on-the-way-ign-daily-fix',
        'only_matching': True,
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        grids = re.findall(
            r'''(?s)<section\b[^>]+\bclass\s*=\s*['"](?:[\w-]+\s+)*?content-feed-grid(?!\B|-)[^>]+>(.+?)</section[^>]*>''',
            webpage)
        return filter(None,
                      (urljoin(url, m.group('path')) for m in re.finditer(
                          r'''<a\b[^>]+\bhref\s*=\s*('|")(?P<path>/videos%s)\1'''
                          % cls._VIDEO_PATH_RE, grids[0] if grids else '')))

    def _real_extract(self, url):
        display_id, filt = self._match_valid_url(url).group('id', 'filt')
        if display_id:
            return self._extract_video(url, display_id)
        return self._extract_playlist(url, filt or 'all')

    def _extract_playlist(self, url, display_id):
        webpage = self._download_webpage(url, display_id)

        return self.playlist_result(
            (self.url_result(u, self.ie_key())
             for u in self._extract_embed_urls(url, webpage)),
            playlist_id=display_id)

    def _extract_video(self, url, display_id):
        video = self._checked_call_api(display_id)

        info = self._extract_video_info(video)

        return merge_dicts({
            'display_id': display_id,
        }, info)


class IGNVideoIE(IGNBaseIE):
    _VALID_URL = r'https?://.+?\.ign\.com/(?:[a-z]{2}/)?[^/]+/(?P<id>\d+)/(?:video|trailer)/'
    _TESTS = [{
        'url': 'http://me.ign.com/en/videos/112203/video/how-hitman-aims-to-be-different-than-every-other-s',
        'md5': 'dd9aca7ed2657c4e118d8b261e5e9de1',
        'info_dict': {
            'id': 'e9be7ea899a9bbfc0674accc22a36cc8',
            'ext': 'mp4',
            'title': 'How Hitman Aims to Be Different Than Every Other Stealth Game - NYCC 2015',
            'description': 'Taking out assassination targets in Hitman has never been more stylish.',
            'timestamp': 1444665600,
            'upload_date': '20151012',
            'display_id': '112203',
            'thumbnail': 'https://sm.ign.com/ign_me/video/h/how-hitman/how-hitman-aims-to-be-different-than-every-other-s_8z14.jpg',
            'duration': 298,
            'tags': 'count:13',
        },
        'expected_warnings': ['HTTP Error 400: Bad Request'],
    }, {
        'url': 'http://me.ign.com/ar/angry-birds-2/106533/video/lrd-ldyy-lwl-lfylm-angry-birds',
        'only_matching': True,
    }, {
        # Youtube embed
        'url': 'https://me.ign.com/ar/ratchet-clank-rift-apart/144327/trailer/embed',
        'only_matching': True,
    }, {
        # Twitter embed
        'url': 'http://adria.ign.com/sherlock-season-4/9687/trailer/embed',
        'only_matching': True,
    }, {
        # Vimeo embed
        'url': 'https://kr.ign.com/bic-2018/3307/trailer/embed',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        parsed_url = urllib.parse.urlparse(url)
        embed_url = urllib.parse.urlunparse(
            parsed_url._replace(path=parsed_url.path.rsplit('/', 1)[0] + '/embed'))

        webpage, urlh = self._download_webpage_handle(embed_url, video_id)
        new_url = urlh.url
        ign_url = compat_parse_qs(
            urllib.parse.urlparse(new_url).query).get('url', [None])[-1]
        if ign_url:
            return self.url_result(ign_url, IGNIE.ie_key())
        video = self._search_regex(r'(<div\b[^>]+\bdata-video-id\s*=\s*[^>]+>)', webpage, 'video element', fatal=False)
        if not video:
            if new_url == url:
                raise ExtractorError('Redirect loop: ' + url)
            return self.url_result(new_url)
        video = extract_attributes(video)
        video_data = video.get('data-settings') or '{}'
        video_data = self._parse_json(video_data, video_id)['video']
        info = self._extract_video_info(video_data)

        return merge_dicts({
            'display_id': video_id,
        }, info)


class IGNArticleIE(IGNBaseIE):
    _VALID_URL = r'https?://.+?\.ign\.com/(?:articles(?:/\d{4}/\d{2}/\d{2})?|(?:[a-z]{2}/)?(?:[\w-]+/)*?feature/\d+)/(?P<id>[^/?&#]+)'
    _PAGE_TYPE = 'article'
    _TESTS = [{
        'url': 'http://me.ign.com/en/feature/15775/100-little-things-in-gta-5-that-will-blow-your-mind',
        'info_dict': {
            'id': '72113',
            'title': '100 Little Things in GTA 5 That Will Blow Your Mind',
        },
        'playlist': [
            {
                'info_dict': {
                    'id': '5ebbd138523268b93c9141af17bec937',
                    'ext': 'mp4',
                    'title': 'Grand Theft Auto V Video Review',
                    'description': 'Rockstar drops the mic on this generation of games. Watch our review of the masterly Grand Theft Auto V.',
                    'timestamp': 1379339880,
                    'upload_date': '20130916',
                    'tags': 'count:12',
                    'thumbnail': 'https://assets1.ignimgs.com/thumbs/userUploaded/2021/8/16/gta-v-heistsjpg-e94705-1629138553533.jpeg',
                    'display_id': 'grand-theft-auto-v-video-review',
                    'duration': 501,
                },
            },
            {
                'info_dict': {
                    'id': '638672ee848ae4ff108df2a296418ee2',
                    'ext': 'mp4',
                    'title': 'GTA 5 In Slow Motion',
                    'description': 'The twisted beauty of GTA 5 in stunning slow motion.',
                    'timestamp': 1386878820,
                    'upload_date': '20131212',
                    'duration': 202,
                    'tags': 'count:25',
                    'display_id': 'gta-5-in-slow-motion',
                    'thumbnail': 'https://assets1.ignimgs.com/vid/thumbnails/user/2013/11/03/GTA-SLO-MO-1.jpg',
                },
            },
        ],
        'params': {
            'skip_download': True,
        },
        'expected_warnings': ['Backend fetch failed'],
    }, {
        'url': 'http://www.ign.com/articles/2014/08/15/rewind-theater-wild-trailer-gamescom-2014?watch',
        'info_dict': {
            'id': '53ee806780a81ec46e0790f8',
            'title': 'Rewind Theater - Wild Trailer Gamescom 2014',
        },
        'playlist_count': 1,
        'expected_warnings': ['Backend fetch failed'],
    }, {
        # videoId pattern
        'url': 'http://www.ign.com/articles/2017/06/08/new-ducktales-short-donalds-birthday-doesnt-go-as-planned',
        'only_matching': True,
    }, {
        # Youtube embed
        'url': 'https://www.ign.com/articles/2021-mvp-named-in-puppy-bowl-xvii',
        'only_matching': True,
    }, {
        # IMDB embed
        'url': 'https://www.ign.com/articles/2014/08/07/sons-of-anarchy-final-season-trailer',
        'only_matching': True,
    }, {
        # Facebook embed
        'url': 'https://www.ign.com/articles/2017/09/20/marvels-the-punisher-watch-the-new-trailer-for-the-netflix-series',
        'only_matching': True,
    }, {
        # Brightcove embed
        'url': 'https://www.ign.com/articles/2016/01/16/supergirl-goes-flying-with-martian-manhunter-in-new-clip',
        'only_matching': True,
    }]

    def _checked_call_api(self, slug):
        try:
            return self._call_api(slug)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError):
                e.cause.args = e.cause.args or [
                    e.cause.response.url, e.cause.status, e.cause.reason]
                if e.cause.status == 404:
                    raise ExtractorError(
                        'Content not found: expired?', cause=e.cause,
                        expected=True)
                elif e.cause.status == 503:
                    self.report_warning(error_to_compat_str(e.cause))
                    return
            raise

    def _real_extract(self, url):
        display_id = self._match_id(url)
        article = self._checked_call_api(display_id)

        if article:
            # obsolete ?
            def entries():
                media_url = traverse_obj(
                    article, ('mediaRelations', 0, 'media', 'metadata', 'url'),
                    expected_type=url_or_none)
                if media_url:
                    yield self.url_result(media_url, IGNIE.ie_key())
                for content in (article.get('content') or []):
                    for video_url in re.findall(r'(?:\[(?:ignvideo\s+url|youtube\s+clip_id)|<iframe[^>]+src)="([^"]+)"', content):
                        if url_or_none(video_url):
                            yield self.url_result(video_url)

            return self.playlist_result(
                entries(), article.get('articleId'),
                traverse_obj(
                    article, ('metadata', 'headline'),
                    expected_type=lambda x: x.strip() or None))

        webpage = self._download_webpage(url, display_id)

        playlist_id = self._html_search_meta('dable:item_id', webpage, default=None)
        if playlist_id:

            def entries():
                for m in re.finditer(
                        r'''(?s)<object\b[^>]+\bclass\s*=\s*("|')ign-videoplayer\1[^>]*>(?P<params>.+?)</object''',
                        webpage):
                    flashvars = self._search_regex(
                        r'''(<param\b[^>]+\bname\s*=\s*("|')flashvars\2[^>]*>)''',
                        m.group('params'), 'flashvars', default='')
                    flashvars = compat_parse_qs(extract_attributes(flashvars).get('value') or '')
                    v_url = url_or_none((flashvars.get('url') or [None])[-1])
                    if v_url:
                        yield self.url_result(v_url)
        else:
            playlist_id = self._search_regex(
                r'''\bdata-post-id\s*=\s*("|')(?P<id>[\da-f]+)\1''',
                webpage, 'id', group='id', default=None)

            nextjs_data = self._search_nextjs_data(webpage, display_id)

            def entries():
                for player in traverse_obj(
                        nextjs_data,
                        ('props', 'apolloState', 'ROOT_QUERY', lambda k, _: k.startswith('videoPlayerProps('), '__ref')):
                    # skip promo links (which may not always be served, eg GH CI servers)
                    if traverse_obj(nextjs_data,
                                    ('props', 'apolloState', player.replace('PlayerProps', 'ModernContent')),
                                    expected_type=dict):
                        continue
                    video = traverse_obj(nextjs_data, ('props', 'apolloState', player), expected_type=dict) or {}
                    info = self._extract_video_info(video, fatal=False)
                    if info:
                        yield merge_dicts({
                            'display_id': display_id,
                        }, info)

        return self.playlist_result(
            entries(), playlist_id or display_id,
            re.sub(r'\s+-\s+IGN\s*$', '', self._og_search_title(webpage, default='')) or None)
