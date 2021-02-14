from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_parse_qs,
    compat_urllib_parse_urlparse,
)
from ..utils import (
    HEADRequest,
    determine_ext,
    int_or_none,
    parse_iso8601,
    strip_or_none,
    try_get,
)


class IGNBaseIE(InfoExtractor):
    def _call_api(self, slug):
        return self._download_json(
            'http://apis.ign.com/{0}/v3/{0}s/slug/{1}'.format(self._PAGE_TYPE, slug), slug)


class IGNIE(IGNBaseIE):
    """
    Extractor for some of the IGN sites, like www.ign.com, es.ign.com de.ign.com.
    Some videos of it.ign.com are also supported
    """

    _VALID_URL = r'https?://(?:.+?\.ign|www\.pcmag)\.com/videos/(?:\d{4}/\d{2}/\d{2}/)?(?P<id>[^/?&#]+)'
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
        }
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
        }
    }, {
        'url': 'https://www.ign.com/videos/is-a-resident-evil-4-remake-on-the-way-ign-daily-fix',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        video = self._call_api(display_id)
        video_id = video['videoId']
        metadata = video['metadata']
        title = metadata.get('longTitle') or metadata.get('title') or metadata['name']

        formats = []
        refs = video.get('refs') or {}

        m3u8_url = refs.get('m3uUrl')
        if m3u8_url:
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', 'm3u8_native',
                m3u8_id='hls', fatal=False))

        f4m_url = refs.get('f4mUrl')
        if f4m_url:
            formats.extend(self._extract_f4m_formats(
                f4m_url, video_id, f4m_id='hds', fatal=False))

        for asset in (video.get('assets') or []):
            asset_url = asset.get('url')
            if not asset_url:
                continue
            formats.append({
                'url': asset_url,
                'tbr': int_or_none(asset.get('bitrate'), 1000),
                'fps': int_or_none(asset.get('frame_rate')),
                'height': int_or_none(asset.get('height')),
                'width': int_or_none(asset.get('width')),
            })

        mezzanine_url = try_get(video, lambda x: x['system']['mezzanineUrl'])
        if mezzanine_url:
            formats.append({
                'ext': determine_ext(mezzanine_url, 'mp4'),
                'format_id': 'mezzanine',
                'preference': 1,
                'url': mezzanine_url,
            })

        self._sort_formats(formats)

        thumbnails = []
        for thumbnail in (video.get('thumbnails') or []):
            thumbnail_url = thumbnail.get('url')
            if not thumbnail_url:
                continue
            thumbnails.append({
                'url': thumbnail_url,
            })

        tags = []
        for tag in (video.get('tags') or []):
            display_name = tag.get('displayName')
            if not display_name:
                continue
            tags.append(display_name)

        return {
            'id': video_id,
            'title': title,
            'description': strip_or_none(metadata.get('description')),
            'timestamp': parse_iso8601(metadata.get('publishDate')),
            'duration': int_or_none(metadata.get('duration')),
            'display_id': display_id,
            'thumbnails': thumbnails,
            'formats': formats,
            'tags': tags,
        }


class IGNVideoIE(InfoExtractor):
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
        }
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
        req = HEADRequest(url.rsplit('/', 1)[0] + '/embed')
        url = self._request_webpage(req, video_id).geturl()
        ign_url = compat_parse_qs(
            compat_urllib_parse_urlparse(url).query).get('url', [None])[0]
        if ign_url:
            return self.url_result(ign_url, IGNIE.ie_key())
        return self.url_result(url)


class IGNArticleIE(IGNBaseIE):
    _VALID_URL = r'https?://.+?\.ign\.com/(?:articles(?:/\d{4}/\d{2}/\d{2})?|(?:[a-z]{2}/)?feature/\d+)/(?P<id>[^/?&#]+)'
    _PAGE_TYPE = 'article'
    _TESTS = [{
        'url': 'http://me.ign.com/en/feature/15775/100-little-things-in-gta-5-that-will-blow-your-mind',
        'info_dict': {
            'id': '524497489e4e8ff5848ece34',
            'title': '100 Little Things in GTA 5 That Will Blow Your Mind',
        },
        'playlist': [
            {
                'info_dict': {
                    'id': '5ebbd138523268b93c9141af17bec937',
                    'ext': 'mp4',
                    'title': 'GTA 5 Video Review',
                    'description': 'Rockstar drops the mic on this generation of games. Watch our review of the masterly Grand Theft Auto V.',
                    'timestamp': 1379339880,
                    'upload_date': '20130916',
                },
            },
            {
                'info_dict': {
                    'id': '638672ee848ae4ff108df2a296418ee2',
                    'ext': 'mp4',
                    'title': '26 Twisted Moments from GTA 5 in Slow Motion',
                    'description': 'The twisted beauty of GTA 5 in stunning slow motion.',
                    'timestamp': 1386878820,
                    'upload_date': '20131212',
                },
            },
        ],
        'params': {
            'playlist_items': '2-3',
            'skip_download': True,
        },
    }, {
        'url': 'http://www.ign.com/articles/2014/08/15/rewind-theater-wild-trailer-gamescom-2014?watch',
        'info_dict': {
            'id': '53ee806780a81ec46e0790f8',
            'title': 'Rewind Theater - Wild Trailer Gamescom 2014',
        },
        'playlist_count': 2,
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

    def _real_extract(self, url):
        display_id = self._match_id(url)
        article = self._call_api(display_id)

        def entries():
            media_url = try_get(article, lambda x: x['mediaRelations'][0]['media']['metadata']['url'])
            if media_url:
                yield self.url_result(media_url, IGNIE.ie_key())
            for content in (article.get('content') or []):
                for video_url in re.findall(r'(?:\[(?:ignvideo\s+url|youtube\s+clip_id)|<iframe[^>]+src)="([^"]+)"', content):
                    yield self.url_result(video_url)

        return self.playlist_result(
            entries(), article.get('articleId'),
            strip_or_none(try_get(article, lambda x: x['metadata']['headline'])))
