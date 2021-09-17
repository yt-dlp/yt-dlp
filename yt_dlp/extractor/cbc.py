# coding: utf-8
from __future__ import unicode_literals

import re
from xml.sax.saxutils import escape

from .common import InfoExtractor
from ..compat import (
    compat_str,
)
from ..utils import (
    js_to_json,
    smuggle_url,
    try_get,
    orderedSet,
    strip_or_none,
    ExtractorError,
    list_get,
)


class CBCIE(InfoExtractor):
    IE_NAME = 'cbc.ca'
    _VALID_URL = r'https?://(?:www\.)?cbc\.ca/(?!player/)(?:[^/]+/)+(?P<id>[^/?#]+)'
    _TESTS = [{
        # with mediaId
        'url': 'http://www.cbc.ca/22minutes/videos/clips-season-23/don-cherry-play-offs',
        'md5': '97e24d09672fc4cf56256d6faa6c25bc',
        'info_dict': {
            'id': '2682904050',
            'ext': 'mp4',
            'title': 'Don Cherry – All-Stars',
            'description': 'Don Cherry has a bee in his bonnet about AHL player John Scott because that guy’s got heart.',
            'timestamp': 1454463000,
            'upload_date': '20160203',
            'uploader': 'CBCC-NEW',
        },
        'skip': 'Geo-restricted to Canada',
    }, {
        # with clipId, feed available via tpfeed.cbc.ca and feed.theplatform.com
        'url': 'http://www.cbc.ca/22minutes/videos/22-minutes-update/22-minutes-update-episode-4',
        'md5': '162adfa070274b144f4fdc3c3b8207db',
        'info_dict': {
            'id': '2414435309',
            'ext': 'mp4',
            'title': '22 Minutes Update: What Not To Wear Quebec',
            'description': "This week's latest Canadian top political story is What Not To Wear Quebec.",
            'upload_date': '20131025',
            'uploader': 'CBCC-NEW',
            'timestamp': 1382717907,
        },
    }, {
        # with clipId, feed only available via tpfeed.cbc.ca
        'url': 'http://www.cbc.ca/archives/entry/1978-robin-williams-freestyles-on-90-minutes-live',
        'md5': '0274a90b51a9b4971fe005c63f592f12',
        'info_dict': {
            'id': '2487345465',
            'ext': 'mp4',
            'title': 'Robin Williams freestyles on 90 Minutes Live',
            'description': 'Wacky American comedian Robin Williams shows off his infamous "freestyle" comedic talents while being interviewed on CBC\'s 90 Minutes Live.',
            'upload_date': '19780210',
            'uploader': 'CBCC-NEW',
            'timestamp': 255977160,
        },
    }, {
        # multiple iframes
        'url': 'http://www.cbc.ca/natureofthings/blog/birds-eye-view-from-vancouvers-burrard-street-bridge-how-we-got-the-shot',
        'playlist': [{
            'md5': '377572d0b49c4ce0c9ad77470e0b96b4',
            'info_dict': {
                'id': '2680832926',
                'ext': 'mp4',
                'title': 'An Eagle\'s-Eye View Off Burrard Bridge',
                'description': 'Hercules the eagle flies from Vancouver\'s Burrard Bridge down to a nearby park with a mini-camera strapped to his back.',
                'upload_date': '20160201',
                'timestamp': 1454342820,
                'uploader': 'CBCC-NEW',
            },
        }, {
            'md5': '415a0e3f586113894174dfb31aa5bb1a',
            'info_dict': {
                'id': '2658915080',
                'ext': 'mp4',
                'title': 'Fly like an eagle!',
                'description': 'Eagle equipped with a mini camera flies from the world\'s tallest tower',
                'upload_date': '20150315',
                'timestamp': 1426443984,
                'uploader': 'CBCC-NEW',
            },
        }],
        'skip': 'Geo-restricted to Canada',
    }, {
        # multiple CBC.APP.Caffeine.initInstance(...)
        'url': 'http://www.cbc.ca/news/canada/calgary/dog-indoor-exercise-winter-1.3928238',
        'info_dict': {
            'title': 'Keep Rover active during the deep freeze with doggie pushups and other fun indoor tasks',
            'id': 'dog-indoor-exercise-winter-1.3928238',
            'description': 'md5:c18552e41726ee95bd75210d1ca9194c',
        },
        'playlist_mincount': 6,
    }]

    @classmethod
    def suitable(cls, url):
        return False if CBCPlayerIE.suitable(url) else super(CBCIE, cls).suitable(url)

    def _extract_player_init(self, player_init, display_id):
        player_info = self._parse_json(player_init, display_id, js_to_json)
        media_id = player_info.get('mediaId')
        if not media_id:
            clip_id = player_info['clipId']
            feed = self._download_json(
                'http://tpfeed.cbc.ca/f/ExhSPC/vms_5akSXx4Ng_Zn?byCustomValue={:mpsReleases}{%s}' % clip_id,
                clip_id, fatal=False)
            if feed:
                media_id = try_get(feed, lambda x: x['entries'][0]['guid'], compat_str)
            if not media_id:
                media_id = self._download_json(
                    'http://feed.theplatform.com/f/h9dtGB/punlNGjMlc1F?fields=id&byContent=byReleases%3DbyId%253D' + clip_id,
                    clip_id)['entries'][0]['id'].split('/')[-1]
        return self.url_result('cbcplayer:%s' % media_id, 'CBCPlayer', media_id)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        title = self._og_search_title(webpage, default=None) or self._html_search_meta(
            'twitter:title', webpage, 'title', default=None) or self._html_search_regex(
                r'<title>([^<]+)</title>', webpage, 'title', fatal=False)
        entries = [
            self._extract_player_init(player_init, display_id)
            for player_init in re.findall(r'CBC\.APP\.Caffeine\.initInstance\(({.+?})\);', webpage)]
        media_ids = []
        for media_id_re in (
                r'<iframe[^>]+src="[^"]+?mediaId=(\d+)"',
                r'<div[^>]+\bid=["\']player-(\d+)',
                r'guid["\']\s*:\s*["\'](\d+)'):
            media_ids.extend(re.findall(media_id_re, webpage))
        entries.extend([
            self.url_result('cbcplayer:%s' % media_id, 'CBCPlayer', media_id)
            for media_id in orderedSet(media_ids)])
        return self.playlist_result(
            entries, display_id, strip_or_none(title),
            self._og_search_description(webpage))


class CBCPlayerIE(InfoExtractor):
    IE_NAME = 'cbc.ca:player'
    _VALID_URL = r'(?:cbcplayer:|https?://(?:www\.)?cbc\.ca/(?:player/play/|i/caffeine/syndicate/\?mediaId=))(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.cbc.ca/player/play/2683190193',
        'md5': '64d25f841ddf4ddb28a235338af32e2c',
        'info_dict': {
            'id': '2683190193',
            'ext': 'mp4',
            'title': 'Gerry Runs a Sweat Shop',
            'description': 'md5:b457e1c01e8ff408d9d801c1c2cd29b0',
            'timestamp': 1455071400,
            'upload_date': '20160210',
            'uploader': 'CBCC-NEW',
        },
        'skip': 'Geo-restricted to Canada',
    }, {
        # Redirected from http://www.cbc.ca/player/AudioMobile/All%20in%20a%20Weekend%20Montreal/ID/2657632011/
        'url': 'http://www.cbc.ca/player/play/2657631896',
        'md5': 'e5e708c34ae6fca156aafe17c43e8b75',
        'info_dict': {
            'id': '2657631896',
            'ext': 'mp3',
            'title': 'CBC Montreal is organizing its first ever community hackathon!',
            'description': 'The modern technology we tend to depend on so heavily, is never without it\'s share of hiccups and headaches. Next weekend - CBC Montreal will be getting members of the public for its first Hackathon.',
            'timestamp': 1425704400,
            'upload_date': '20150307',
            'uploader': 'CBCC-NEW',
        },
    }, {
        'url': 'http://www.cbc.ca/player/play/2164402062',
        'md5': '33fcd8f6719b9dd60a5e73adcb83b9f6',
        'info_dict': {
            'id': '2164402062',
            'ext': 'mp4',
            'title': 'Cancer survivor four times over',
            'description': 'Tim Mayer has beaten three different forms of cancer four times in five years.',
            'timestamp': 1320410746,
            'upload_date': '20111104',
            'uploader': 'CBCC-NEW',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return {
            '_type': 'url_transparent',
            'ie_key': 'ThePlatform',
            'url': smuggle_url(
                'http://link.theplatform.com/s/ExhSPC/media/guid/2655402169/%s?mbr=true&formats=MPEG4,FLV,MP3' % video_id, {
                    'force_smil_url': True
                }),
            'id': video_id,
        }


class CBCGemIE(InfoExtractor):
    IE_NAME = 'gem.cbc.ca'
    _VALID_URL = r'https?://gem\.cbc\.ca/media/(?P<id>[0-9a-z-]+/[0-9a-z-]+)'
    _TESTS = [{
        # geo-restricted to Canada, bypassable
        # This is a normal, public, TV show video
        'url': 'https://gem.cbc.ca/media/schitts-creek/s06e01',
        'md5': '93dbb31c74a8e45b378cf13bd3f6f11e',
        'info_dict': {
            'id': 'schitts-creek/s06e01',
            'ext': 'mp4',
            'title': 'Smoke Signals',
            'description': 'md5:929868d20021c924020641769eb3e7f1',
            'thumbnail': 'https://images.radio-canada.ca/v1/synps-cbc/episode/perso/cbc_schitts_creek_season_06e01_thumbnail_v01.jpg?im=Resize=(Size)',
            'duration': 1314,
            'categories': ['comedy'],
            'series': 'Schitt\'s Creek',
            'season': 'Season 6',
            'season_number': 6,
            'episode': 'Smoke Signals',
            'episode_number': 1,
            'episode_id': 'schitts-creek/s06e01',
        },
        'params': {'format': 'bv',}, # No format has audio and video combined
    }, {
        # geo-restricted to Canada, bypassable
        # This video requires an account in the browser, but works fine in yt-dlp
        'url': 'https://gem.cbc.ca/media/schitts-creek/s01e01',
        'md5': '297a9600f554f2258aed01514226a697',
        'info_dict': {
            'id': 'schitts-creek/s01e01',
            'ext': 'mp4',
            'title': 'The Cup Runneth Over',
            'description': 'md5:9bca14ea49ab808097530eb05a29e797',
            'thumbnail': 'https://images.radio-canada.ca/v1/synps-cbc/episode/perso/cbc_schitts_creek_season_01e01_thumbnail_v01.jpg?im=Resize=(Size)',
            'series': 'Schitt\'s Creek',
            'season_number': 1,
            'season': 'Season 1',
            'episode_number': 1,
            'episode': 'The Cup Runneth Over',
            'episode_id': 'schitts-creek/s01e01',
            'duration': 1309,
            'categories': ['comedy'],
        },
        'params': {'format': 'bv',}, # No format has audio and video combined
    },{
        # geo-restricted to Canada, bypassable
        # TV show playlist, all public videos at time of coding, 2021-09)
        'url': 'https://gem.cbc.ca/media/schitts-creek/s06',
        'playlist_count': 16,
        'info_dict': {
            'id': 'schitts-creek/s06',
            'title': 'Season 6',
            'description': 'md5:6a92104a56cbeb5818cc47884d4326a2',
        },
    }]
    _API_BASE = 'https://services.radio-canada.ca/ott/cbc-api/v2/'
    _API_VIDEO = _API_BASE + 'assets/'
    _API_SHOW = _API_BASE + 'shows/'
    _BROWSER_BASE = 'https://gem.cbc.ca/media/'
    # Regexes for analyzing video_id - the id group of _VALID_URL
    _VIDEO_ID = r'[0-9a-z-]+/s[0-9]+[a-z][0-9]+'
    _PLAYLIST_ID = r'([0-9a-z-]+)/s([0-9]+)'

    def _real_extract(self, url):
        url_id = self._match_id(url)

        playlist_match = re.fullmatch(self._PLAYLIST_ID, url_id)
        if playlist_match:
            season_id = url_id
            show = playlist_match.group(1)
            show_info = self._download_json(self._API_SHOW + show, season_id)
            season = int(playlist_match.group(2))
            season_info = list_get(show_info['seasons'], season-1)

            if season_info is None:
                raise ExtractorError(f"Couldn't find season {season} of {show}")

            episodes = []
            for episode in season_info['assets']:
                episodes.append({
                    '_type': 'url_transparent',
                    'ie_key': 'CBCGem',
                    'url': self._BROWSER_BASE + episode['id'],
                    'id': episode['id'],
                    'title': episode.get('title'),
                    'description': episode.get('description'),
                    'thumbnail': episode.get('image'),
                    'series': episode.get('series'),
                    'season_number': episode.get('season'),
                    'season': season_info['title'],
                    'season_id': season_info.get('id'),
                    'episode_number': episode.get('episode'),
                    'episode': episode.get('title'),
                    'episode_id': episode['id'],
                    'duration': episode.get('duration'),
                    'categories': [episode.get('category')],
                })
            
            thumbnail = None
            tn_uri = season_info.get('image')
            if tn_uri is not None and not tn_uri.startswith('data:'):
                # the-national was observed to use a "data:image/png;base64"
                # URI for their 'image' value. The image was 1x1, and is
                # probably just a placeholder, so it is ignored.
                thumbnail = tn_uri

            return {
                '_type': 'playlist',
                'entries': episodes,
                'id': season_id,
                'title': season_info['title'],
                'description': season_info.get('description'),
                'thumbnail': thumbnail,
                'series': show_info.get('title'),
                'season_number': season_info.get('season'),
                'season': season_info['title'],
            }

        elif re.fullmatch(self._VIDEO_ID, url_id) is None:
            # Not a playlist or video
            raise ExtractorError(f"Could't recognize ID '{url_id}' as a playlist or video")

        # It's a single video

        video_id = url_id
        video_info = self._download_json(self._API_VIDEO + video_id, video_id)
        # Sometimes the m3u8 URL is a not available and there is an error in
        # the JSON instead. This might only happen with member content. But
        # just retrying seems to work fine.
        m3u8_url = None
        i = 0
        while m3u8_url is None:
            if i == 15:
                # Didn't work after 15 tries, give up
                raise ExtractorError("Couldn't retrieve m3u8 URL")
            m3u8_url = self._download_json(
                video_info['playSession']['url'], video_id)['url']
            i += 1

        formats = self._extract_m3u8_formats_and_subtitles(
            m3u8_url, video_id)[0]
        self._remove_duplicate_formats(formats)

        # Post-process format list
        for i, format in enumerate(formats):
            if format.get('vcodec') == 'none':
                # Audio-only
                
                # Only AAC audio is used
                if format.get('ext') is None:
                    format['ext'] = 'm4a'
                if format.get('acodec') is None:
                    format['acodec'] = 'aac'

                # Make IDs easier to use
                format['format_id'] = format['format_id'].lower().replace(
                    '(', '').replace(')', '')
                # Remove the needless 'audio-' prefix from format IDs, making for
                # easier selection on the CLI.
                if format['format_id'].startswith('audio-'):
                    format['format_id'] = format['format_id'][6:]

                # Put described audio at the beginning of the list, so that it
                # isn't chosen by default, as most people won't want it.
                if 'descriptive' in format['format_id'].lower():
                    format['preference'] = -2

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video_info['title'],
            'description': video_info.get('description'),
            'thumbnail': video_info.get('image'),
            'series': video_info.get('series'),
            'season_number': video_info.get('season'),
            'season': f"Season {video_info.get('season')}",
            'episode_number': video_info.get('episode'),
            'episode': video_info.get('title'),
            'episode_id': video_id,
            'duration': video_info.get('duration'),
            'categories': [video_info.get('category')],
            'formats': formats,
            'release_timestamp': video_info.get('airDate'),
            'timestamp': video_info.get('availableDate'),
        }

# TODO: live videos