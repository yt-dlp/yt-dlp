from .theplatform import ThePlatformIE
from ..utils import (
    ExtractorError,
    GeoRestrictedError,
    int_or_none,
    remove_start,
    traverse_obj,
    update_url_query,
    urlencode_postdata,
)


class AENetworksBaseIE(ThePlatformIE):  # XXX: Do not subclass from concrete IE
    _BASE_URL_REGEX = r'''(?x)https?://
        (?:(?:www|play|watch)\.)?
        (?P<domain>
            (?:history(?:vault)?|aetv|mylifetime|lifetimemovieclub)\.com|
            fyi\.tv
        )/'''
    _THEPLATFORM_KEY = '43jXaGRQud'
    _THEPLATFORM_SECRET = 'S10BPXHMlb'
    _DOMAIN_MAP = {
        'history.com': ('HISTORY', 'history'),
        'aetv.com': ('AETV', 'aetv'),
        'mylifetime.com': ('LIFETIME', 'lifetime'),
        'lifetimemovieclub.com': ('LIFETIMEMOVIECLUB', 'lmc'),
        'fyi.tv': ('FYI', 'fyi'),
        'historyvault.com': (None, 'historyvault'),
        'biography.com': (None, 'biography'),
    }

    def _extract_aen_smil(self, smil_url, video_id, auth=None):
        query = {
            'mbr': 'true',
            'formats': 'M3U+none,MPEG-DASH+none,MPEG4,MP3',
        }
        if auth:
            query['auth'] = auth
        TP_SMIL_QUERY = [{
            'assetTypes': 'high_video_ak',
            'switch': 'hls_high_ak',
        }, {
            'assetTypes': 'high_video_s3',
        }, {
            'assetTypes': 'high_video_s3',
            'switch': 'hls_high_fastly',
        }]
        formats = []
        subtitles = {}
        last_e = None
        for q in TP_SMIL_QUERY:
            q.update(query)
            m_url = update_url_query(smil_url, q)
            m_url = self._sign_url(m_url, self._THEPLATFORM_KEY, self._THEPLATFORM_SECRET)
            try:
                tp_formats, tp_subtitles = self._extract_theplatform_smil(
                    m_url, video_id, 'Downloading %s SMIL data' % (q.get('switch') or q['assetTypes']))
            except ExtractorError as e:
                if isinstance(e, GeoRestrictedError):
                    raise
                last_e = e
                continue
            formats.extend(tp_formats)
            subtitles = self._merge_subtitles(subtitles, tp_subtitles)
        if last_e and not formats:
            raise last_e
        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
        }

    def _extract_aetn_info(self, domain, filter_key, filter_value, url):
        requestor_id, brand = self._DOMAIN_MAP[domain]
        result = self._download_json(
            'https://feeds.video.aetnd.com/api/v2/%s/videos' % brand,
            filter_value, query={'filter[%s]' % filter_key: filter_value})
        result = traverse_obj(
            result, ('results',
                     lambda k, v: k == 0 and v[filter_key] == filter_value),
            get_all=False)
        if not result:
            raise ExtractorError('Show not found in A&E feed (too new?)', expected=True,
                                 video_id=remove_start(filter_value, '/'))
        title = result['title']
        video_id = result['id']
        media_url = result['publicUrl']
        theplatform_metadata = self._download_theplatform_metadata(self._search_regex(
            r'https?://link\.theplatform\.com/s/([^?]+)', media_url, 'theplatform_path'), video_id)
        info = self._parse_theplatform_metadata(theplatform_metadata)
        auth = None
        if theplatform_metadata.get('AETN$isBehindWall'):
            resource = self._get_mvpd_resource(
                requestor_id, theplatform_metadata['title'],
                theplatform_metadata.get('AETN$PPL_pplProgramId') or theplatform_metadata.get('AETN$PPL_pplProgramId_OLD'),
                theplatform_metadata['ratings'][0]['rating'])
            auth = self._extract_mvpd_auth(
                url, video_id, requestor_id, resource)
        info.update(self._extract_aen_smil(media_url, video_id, auth))
        info.update({
            'title': title,
            'series': result.get('seriesName'),
            'season_number': int_or_none(result.get('tvSeasonNumber')),
            'episode_number': int_or_none(result.get('tvSeasonEpisodeNumber')),
        })
        return info


class AENetworksIE(AENetworksBaseIE):
    IE_NAME = 'aenetworks'
    IE_DESC = 'A+E Networks: A&E, Lifetime, History.com, FYI Network and History Vault'
    _VALID_URL = AENetworksBaseIE._BASE_URL_REGEX + r'''(?P<id>
        shows/[^/]+/season-\d+/episode-\d+|
        (?:
            (?:movie|special)s/[^/]+|
            (?:shows/[^/]+/)?videos
        )/[^/?#&]+
    )'''
    _TESTS = [{
        'url': 'http://www.history.com/shows/mountain-men/season-1/episode-1',
        'info_dict': {
            'id': '22253814',
            'ext': 'mp4',
            'title': 'Winter is Coming',
            'description': 'md5:641f424b7a19d8e24f26dea22cf59d74',
            'timestamp': 1338306241,
            'upload_date': '20120529',
            'uploader': 'AENE-NEW',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'add_ie': ['ThePlatform'],
        'skip': 'Geo-restricted - This content is not available in your location.'
    }, {
        'url': 'http://www.aetv.com/shows/duck-dynasty/season-9/episode-1',
        'info_dict': {
            'id': '600587331957',
            'ext': 'mp4',
            'title': 'Inlawful Entry',
            'description': 'md5:57c12115a2b384d883fe64ca50529e08',
            'timestamp': 1452634428,
            'upload_date': '20160112',
            'uploader': 'AENE-NEW',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'add_ie': ['ThePlatform'],
        'skip': 'This video is only available for users of participating TV providers.',
    }, {
        'url': 'http://www.fyi.tv/shows/tiny-house-nation/season-1/episode-8',
        'only_matching': True
    }, {
        'url': 'http://www.mylifetime.com/shows/project-runway-junior/season-1/episode-6',
        'only_matching': True
    }, {
        'url': 'http://www.mylifetime.com/movies/center-stage-on-pointe/full-movie',
        'only_matching': True
    }, {
        'url': 'https://watch.lifetimemovieclub.com/movies/10-year-reunion/full-movie',
        'only_matching': True
    }, {
        'url': 'http://www.history.com/specials/sniper-into-the-kill-zone/full-special',
        'only_matching': True
    }, {
        'url': 'https://www.aetv.com/specials/hunting-jonbenets-killer-the-untold-story/preview-hunting-jonbenets-killer-the-untold-story',
        'only_matching': True
    }, {
        'url': 'http://www.history.com/videos/history-of-valentines-day',
        'only_matching': True
    }, {
        'url': 'https://play.aetv.com/shows/duck-dynasty/videos/best-of-duck-dynasty-getting-quack-in-shape',
        'only_matching': True
    }]

    def _real_extract(self, url):
        domain, canonical = self._match_valid_url(url).groups()
        return self._extract_aetn_info(domain, 'canonical', '/' + canonical, url)


class AENetworksListBaseIE(AENetworksBaseIE):
    def _call_api(self, resource, slug, brand, fields):
        return self._download_json(
            'https://yoga.appsvcs.aetnd.com/graphql',
            slug, query={'brand': brand}, data=urlencode_postdata({
                'query': '''{
  %s(slug: "%s") {
    %s
  }
}''' % (resource, slug, fields),
            }))['data'][resource]

    def _real_extract(self, url):
        domain, slug = self._match_valid_url(url).groups()
        _, brand = self._DOMAIN_MAP[domain]
        playlist = self._call_api(self._RESOURCE, slug, brand, self._FIELDS)
        base_url = 'http://watch.%s' % domain

        entries = []
        for item in (playlist.get(self._ITEMS_KEY) or []):
            doc = self._get_doc(item)
            canonical = doc.get('canonical')
            if not canonical:
                continue
            entries.append(self.url_result(
                base_url + canonical, AENetworksIE.ie_key(), doc.get('id')))

        description = None
        if self._PLAYLIST_DESCRIPTION_KEY:
            description = playlist.get(self._PLAYLIST_DESCRIPTION_KEY)

        return self.playlist_result(
            entries, playlist.get('id'),
            playlist.get(self._PLAYLIST_TITLE_KEY), description)


class AENetworksCollectionIE(AENetworksListBaseIE):
    IE_NAME = 'aenetworks:collection'
    _VALID_URL = AENetworksBaseIE._BASE_URL_REGEX + r'(?:[^/]+/)*(?:list|collections)/(?P<id>[^/?#&]+)/?(?:[?#&]|$)'
    _TESTS = [{
        'url': 'https://watch.historyvault.com/list/america-the-story-of-us',
        'info_dict': {
            'id': '282',
            'title': 'America The Story of Us',
        },
        'playlist_mincount': 12,
    }, {
        'url': 'https://watch.historyvault.com/shows/america-the-story-of-us-2/season-1/list/america-the-story-of-us',
        'only_matching': True
    }, {
        'url': 'https://www.historyvault.com/collections/mysteryquest',
        'only_matching': True
    }]
    _RESOURCE = 'list'
    _ITEMS_KEY = 'items'
    _PLAYLIST_TITLE_KEY = 'display_title'
    _PLAYLIST_DESCRIPTION_KEY = None
    _FIELDS = '''id
    display_title
    items {
      ... on ListVideoItem {
        doc {
          canonical
          id
        }
      }
    }'''

    def _get_doc(self, item):
        return item.get('doc') or {}


class AENetworksShowIE(AENetworksListBaseIE):
    IE_NAME = 'aenetworks:show'
    _VALID_URL = AENetworksBaseIE._BASE_URL_REGEX + r'shows/(?P<id>[^/?#&]+)/?(?:[?#&]|$)'
    _TESTS = [{
        'url': 'http://www.history.com/shows/ancient-aliens',
        'info_dict': {
            'id': 'SERIES1574',
            'title': 'Ancient Aliens',
            'description': 'md5:3f6d74daf2672ff3ae29ed732e37ea7f',
        },
        'playlist_mincount': 150,
    }]
    _RESOURCE = 'series'
    _ITEMS_KEY = 'episodes'
    _PLAYLIST_TITLE_KEY = 'title'
    _PLAYLIST_DESCRIPTION_KEY = 'description'
    _FIELDS = '''description
    id
    title
    episodes {
      canonical
      id
    }'''

    def _get_doc(self, item):
        return item


class HistoryTopicIE(AENetworksBaseIE):
    IE_NAME = 'history:topic'
    IE_DESC = 'History.com Topic'
    _VALID_URL = r'https?://(?:www\.)?history\.com/topics/[^/]+/(?P<id>[\w+-]+?)-video'
    _TESTS = [{
        'url': 'https://www.history.com/topics/valentines-day/history-of-valentines-day-video',
        'info_dict': {
            'id': '40700995724',
            'ext': 'mp4',
            'title': "History of Valentine’s Day",
            'description': 'md5:7b57ea4829b391995b405fa60bd7b5f7',
            'timestamp': 1375819729,
            'upload_date': '20130806',
            'uploader': 'AENE-NEW',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'add_ie': ['ThePlatform'],
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        return self.url_result(
            'http://www.history.com/videos/' + display_id,
            AENetworksIE.ie_key())


class HistoryPlayerIE(AENetworksBaseIE):
    IE_NAME = 'history:player'
    _VALID_URL = r'https?://(?:www\.)?(?P<domain>(?:history|biography)\.com)/player/(?P<id>\d+)'
    _TESTS = []

    def _real_extract(self, url):
        domain, video_id = self._match_valid_url(url).groups()
        return self._extract_aetn_info(domain, 'id', video_id, url)


class BiographyIE(AENetworksBaseIE):
    _VALID_URL = r'https?://(?:www\.)?biography\.com/video/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.biography.com/video/vincent-van-gogh-full-episode-2075049808',
        'info_dict': {
            'id': '30322987',
            'ext': 'mp4',
            'title': 'Vincent Van Gogh - Full Episode',
            'description': 'A full biography about the most influential 20th century painter, Vincent Van Gogh.',
            'timestamp': 1311970571,
            'upload_date': '20110729',
            'uploader': 'AENE-NEW',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'add_ie': ['ThePlatform'],
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        player_url = self._search_regex(
            r'<phoenix-iframe[^>]+src="(%s)' % HistoryPlayerIE._VALID_URL,
            webpage, 'player URL')
        return self.url_result(player_url, HistoryPlayerIE.ie_key())
