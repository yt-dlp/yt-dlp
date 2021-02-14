from __future__ import unicode_literals

import functools
import re

from .turner import TurnerBaseIE
from ..compat import (
    compat_parse_qs,
    compat_str,
    compat_urllib_parse_unquote,
    compat_urllib_parse_urlparse,
)
from ..utils import (
    int_or_none,
    merge_dicts,
    OnDemandPagedList,
    parse_duration,
    parse_iso8601,
    try_get,
    update_url_query,
    urljoin,
)


class NBACVPBaseIE(TurnerBaseIE):
    def _extract_nba_cvp_info(self, path, video_id, fatal=False):
        return self._extract_cvp_info(
            'http://secure.nba.com/%s' % path, video_id, {
                'default': {
                    'media_src': 'http://nba.cdn.turner.com/nba/big',
                },
                'm3u8': {
                    'media_src': 'http://nbavod-f.akamaihd.net',
                },
            }, fatal=fatal)


class NBAWatchBaseIE(NBACVPBaseIE):
    _VALID_URL_BASE = r'https?://(?:(?:www\.)?nba\.com(?:/watch)?|watch\.nba\.com)/'

    def _extract_video(self, filter_key, filter_value):
        video = self._download_json(
            'https://neulionscnbav2-a.akamaihd.net/solr/nbad_program/usersearch',
            filter_value, query={
                'fl': 'description,image,name,pid,releaseDate,runtime,tags,seoName',
                'q': filter_key + ':' + filter_value,
                'wt': 'json',
            })['response']['docs'][0]

        video_id = str(video['pid'])
        title = video['name']

        formats = []
        m3u8_url = (self._download_json(
            'https://watch.nba.com/service/publishpoint', video_id, query={
                'type': 'video',
                'format': 'json',
                'id': video_id,
            }, headers={
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0_1 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A402 Safari/604.1',
            }, fatal=False) or {}).get('path')
        if m3u8_url:
            m3u8_formats = self._extract_m3u8_formats(
                re.sub(r'_(?:pc|iphone)\.', '.', m3u8_url), video_id, 'mp4',
                'm3u8_native', m3u8_id='hls', fatal=False)
            formats.extend(m3u8_formats)
            for f in m3u8_formats:
                http_f = f.copy()
                http_f.update({
                    'format_id': http_f['format_id'].replace('hls-', 'http-'),
                    'protocol': 'http',
                    'url': http_f['url'].replace('.m3u8', ''),
                })
                formats.append(http_f)

        info = {
            'id': video_id,
            'title': title,
            'thumbnail': urljoin('https://nbadsdmt.akamaized.net/media/nba/nba/thumbs/', video.get('image')),
            'description': video.get('description'),
            'duration': int_or_none(video.get('runtime')),
            'timestamp': parse_iso8601(video.get('releaseDate')),
            'tags': video.get('tags'),
        }

        seo_name = video.get('seoName')
        if seo_name and re.search(r'\d{4}/\d{2}/\d{2}/', seo_name):
            base_path = ''
            if seo_name.startswith('teams/'):
                base_path += seo_name.split('/')[1] + '/'
            base_path += 'video/'
            cvp_info = self._extract_nba_cvp_info(
                base_path + seo_name + '.xml', video_id, False)
            if cvp_info:
                formats.extend(cvp_info['formats'])
                info = merge_dicts(info, cvp_info)

        self._sort_formats(formats)
        info['formats'] = formats
        return info


class NBAWatchEmbedIE(NBAWatchBaseIE):
    IENAME = 'nba:watch:embed'
    _VALID_URL = NBAWatchBaseIE._VALID_URL_BASE + r'embed\?.*?\bid=(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://watch.nba.com/embed?id=659395',
        'md5': 'b7e3f9946595f4ca0a13903ce5edd120',
        'info_dict': {
            'id': '659395',
            'ext': 'mp4',
            'title': 'Mix clip: More than 7 points of  Joe Ingles, Luc Mbah a Moute, Blake Griffin and 6 more in Utah Jazz vs. the Clippers, 4/15/2017',
            'description': 'Mix clip: More than 7 points of  Joe Ingles, Luc Mbah a Moute, Blake Griffin and 6 more in Utah Jazz vs. the Clippers, 4/15/2017',
            'timestamp': 1492228800,
            'upload_date': '20170415',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self._extract_video('pid', video_id)


class NBAWatchIE(NBAWatchBaseIE):
    IE_NAME = 'nba:watch'
    _VALID_URL = NBAWatchBaseIE._VALID_URL_BASE + r'(?:nba/)?video/(?P<id>.+?(?=/index\.html)|(?:[^/]+/)*[^/?#&]+)'
    _TESTS = [{
        'url': 'http://www.nba.com/video/games/nets/2012/12/04/0021200253-okc-bkn-recap.nba/index.html',
        'md5': '9d902940d2a127af3f7f9d2f3dc79c96',
        'info_dict': {
            'id': '70946',
            'ext': 'mp4',
            'title': 'Thunder vs. Nets',
            'description': 'Kevin Durant scores 32 points and dishes out six assists as the Thunder beat the Nets in Brooklyn.',
            'duration': 181,
            'timestamp': 1354597200,
            'upload_date': '20121204',
        },
    }, {
        'url': 'http://www.nba.com/video/games/hornets/2014/12/05/0021400276-nyk-cha-play5.nba/',
        'only_matching': True,
    }, {
        'url': 'http://watch.nba.com/video/channels/playoffs/2015/05/20/0041400301-cle-atl-recap.nba',
        'md5': 'b2b39b81cf28615ae0c3360a3f9668c4',
        'info_dict': {
            'id': '330865',
            'ext': 'mp4',
            'title': 'Hawks vs. Cavaliers Game 1',
            'description': 'md5:8094c3498d35a9bd6b1a8c396a071b4d',
            'duration': 228,
            'timestamp': 1432094400,
            'upload_date': '20150521',
        },
    }, {
        'url': 'http://watch.nba.com/nba/video/channels/nba_tv/2015/06/11/YT_go_big_go_home_Game4_061115',
        'only_matching': True,
    }, {
        # only CVP mp4 format available
        'url': 'https://watch.nba.com/video/teams/cavaliers/2012/10/15/sloan121015mov-2249106',
        'only_matching': True,
    }, {
        'url': 'https://watch.nba.com/video/top-100-dunks-from-the-2019-20-season?plsrc=nba&collection=2019-20-season-highlights',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        collection_id = compat_parse_qs(compat_urllib_parse_urlparse(url).query).get('collection', [None])[0]
        if collection_id:
            if self._downloader.params.get('noplaylist'):
                self.to_screen('Downloading just video %s because of --no-playlist' % display_id)
            else:
                self.to_screen('Downloading playlist %s - add --no-playlist to just download video' % collection_id)
                return self.url_result(
                    'https://www.nba.com/watch/list/collection/' + collection_id,
                    NBAWatchCollectionIE.ie_key(), collection_id)
        return self._extract_video('seoName', display_id)


class NBAWatchCollectionIE(NBAWatchBaseIE):
    IE_NAME = 'nba:watch:collection'
    _VALID_URL = NBAWatchBaseIE._VALID_URL_BASE + r'list/collection/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://watch.nba.com/list/collection/season-preview-2020',
        'info_dict': {
            'id': 'season-preview-2020',
        },
        'playlist_mincount': 43,
    }]
    _PAGE_SIZE = 100

    def _fetch_page(self, collection_id, page):
        page += 1
        videos = self._download_json(
            'https://content-api-prod.nba.com/public/1/endeavor/video-list/collection/' + collection_id,
            collection_id, 'Downloading page %d JSON metadata' % page, query={
                'count': self._PAGE_SIZE,
                'page': page,
            })['results']['videos']
        for video in videos:
            program = video.get('program') or {}
            seo_name = program.get('seoName') or program.get('slug')
            if not seo_name:
                continue
            yield {
                '_type': 'url',
                'id': program.get('id'),
                'title': program.get('title') or video.get('title'),
                'url': 'https://www.nba.com/watch/video/' + seo_name,
                'thumbnail': video.get('image'),
                'description': program.get('description') or video.get('description'),
                'duration': parse_duration(program.get('runtimeHours')),
                'timestamp': parse_iso8601(video.get('releaseDate')),
            }

    def _real_extract(self, url):
        collection_id = self._match_id(url)
        entries = OnDemandPagedList(
            functools.partial(self._fetch_page, collection_id),
            self._PAGE_SIZE)
        return self.playlist_result(entries, collection_id)


class NBABaseIE(NBACVPBaseIE):
    _VALID_URL_BASE = r'''(?x)
        https?://(?:www\.)?nba\.com/
            (?P<team>
                blazers|
                bucks|
                bulls|
                cavaliers|
                celtics|
                clippers|
                grizzlies|
                hawks|
                heat|
                hornets|
                jazz|
                kings|
                knicks|
                lakers|
                magic|
                mavericks|
                nets|
                nuggets|
                pacers|
                pelicans|
                pistons|
                raptors|
                rockets|
                sixers|
                spurs|
                suns|
                thunder|
                timberwolves|
                warriors|
                wizards
            )
        (?:/play\#)?/'''
    _CHANNEL_PATH_REGEX = r'video/channel|series'

    def _embed_url_result(self, team, content_id):
        return self.url_result(update_url_query(
            'https://secure.nba.com/assets/amp/include/video/iframe.html', {
                'contentId': content_id,
                'team': team,
            }), NBAEmbedIE.ie_key())

    def _call_api(self, team, content_id, query, resource):
        return self._download_json(
            'https://api.nba.net/2/%s/video,imported_video,wsc/' % team,
            content_id, 'Download %s JSON metadata' % resource,
            query=query, headers={
                'accessToken': 'internal|bb88df6b4c2244e78822812cecf1ee1b',
            })['response']['result']

    def _extract_video(self, video, team, extract_all=True):
        video_id = compat_str(video['nid'])
        team = video['brand']

        info = {
            'id': video_id,
            'title': video.get('title') or video.get('headline') or video['shortHeadline'],
            'description': video.get('description'),
            'timestamp': parse_iso8601(video.get('published')),
        }

        subtitles = {}
        captions = try_get(video, lambda x: x['videoCaptions']['sidecars'], dict) or {}
        for caption_url in captions.values():
            subtitles.setdefault('en', []).append({'url': caption_url})

        formats = []
        mp4_url = video.get('mp4')
        if mp4_url:
            formats.append({
                'url': mp4_url,
            })

        if extract_all:
            source_url = video.get('videoSource')
            if source_url and not source_url.startswith('s3://') and self._is_valid_url(source_url, video_id, 'source'):
                formats.append({
                    'format_id': 'source',
                    'url': source_url,
                    'preference': 1,
                })

            m3u8_url = video.get('m3u8')
            if m3u8_url:
                if '.akamaihd.net/i/' in m3u8_url:
                    formats.extend(self._extract_akamai_formats(
                        m3u8_url, video_id, {'http': 'pmd.cdn.turner.com'}))
                else:
                    formats.extend(self._extract_m3u8_formats(
                        m3u8_url, video_id, 'mp4',
                        'm3u8_native', m3u8_id='hls', fatal=False))

            content_xml = video.get('contentXml')
            if team and content_xml:
                cvp_info = self._extract_nba_cvp_info(
                    team + content_xml, video_id, fatal=False)
                if cvp_info:
                    formats.extend(cvp_info['formats'])
                    subtitles = self._merge_subtitles(subtitles, cvp_info['subtitles'])
                    info = merge_dicts(info, cvp_info)

            self._sort_formats(formats)
        else:
            info.update(self._embed_url_result(team, video['videoId']))

        info.update({
            'formats': formats,
            'subtitles': subtitles,
        })

        return info

    def _real_extract(self, url):
        team, display_id = re.match(self._VALID_URL, url).groups()
        if '/play#/' in url:
            display_id = compat_urllib_parse_unquote(display_id)
        else:
            webpage = self._download_webpage(url, display_id)
            display_id = self._search_regex(
                self._CONTENT_ID_REGEX + r'\s*:\s*"([^"]+)"', webpage, 'video id')
        return self._extract_url_results(team, display_id)


class NBAEmbedIE(NBABaseIE):
    IENAME = 'nba:embed'
    _VALID_URL = r'https?://secure\.nba\.com/assets/amp/include/video/(?:topI|i)frame\.html\?.*?\bcontentId=(?P<id>[^?#&]+)'
    _TESTS = [{
        'url': 'https://secure.nba.com/assets/amp/include/video/topIframe.html?contentId=teams/bulls/2020/12/04/3478774/1607105587854-20201204_SCHEDULE_RELEASE_FINAL_DRUPAL-3478774&team=bulls&adFree=false&profile=71&videoPlayerName=TAMPCVP&baseUrl=&videoAdsection=nba.com_mobile_web_teamsites_chicagobulls&ampEnv=',
        'only_matching': True,
    }, {
        'url': 'https://secure.nba.com/assets/amp/include/video/iframe.html?contentId=2016/10/29/0021600027boschaplay7&adFree=false&profile=71&team=&videoPlayerName=LAMPCVP',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        qs = compat_parse_qs(compat_urllib_parse_urlparse(url).query)
        content_id = qs['contentId'][0]
        team = qs.get('team', [None])[0]
        if not team:
            return self.url_result(
                'https://watch.nba.com/video/' + content_id, NBAWatchIE.ie_key())
        video = self._call_api(team, content_id, {'videoid': content_id}, 'video')[0]
        return self._extract_video(video, team)


class NBAIE(NBABaseIE):
    IENAME = 'nba'
    _VALID_URL = NBABaseIE._VALID_URL_BASE + '(?!%s)video/(?P<id>(?:[^/]+/)*[^/?#&]+)' % NBABaseIE._CHANNEL_PATH_REGEX
    _TESTS = [{
        'url': 'https://www.nba.com/bulls/video/teams/bulls/2020/12/04/3478774/1607105587854-20201204schedulereleasefinaldrupal-3478774',
        'info_dict': {
            'id': '45039',
            'ext': 'mp4',
            'title': 'AND WE BACK.',
            'description': 'Part 1 of our 2020-21 schedule is here! Watch our games on NBC Sports Chicago.',
            'duration': 94,
            'timestamp': 1607112000,
            'upload_date': '20201218',
        },
    }, {
        'url': 'https://www.nba.com/bucks/play#/video/teams%2Fbucks%2F2020%2F12%2F17%2F64860%2F1608252863446-Op_Dream_16x9-64860',
        'only_matching': True,
    }, {
        'url': 'https://www.nba.com/bucks/play#/video/wsc%2Fteams%2F2787C911AA1ACD154B5377F7577CCC7134B2A4B0',
        'only_matching': True,
    }]
    _CONTENT_ID_REGEX = r'videoID'

    def _extract_url_results(self, team, content_id):
        return self._embed_url_result(team, content_id)


class NBAChannelIE(NBABaseIE):
    IENAME = 'nba:channel'
    _VALID_URL = NBABaseIE._VALID_URL_BASE + '(?:%s)/(?P<id>[^/?#&]+)' % NBABaseIE._CHANNEL_PATH_REGEX
    _TESTS = [{
        'url': 'https://www.nba.com/blazers/video/channel/summer_league',
        'info_dict': {
            'title': 'Summer League',
        },
        'playlist_mincount': 138,
    }, {
        'url': 'https://www.nba.com/bucks/play#/series/On%20This%20Date',
        'only_matching': True,
    }]
    _CONTENT_ID_REGEX = r'videoSubCategory'
    _PAGE_SIZE = 100

    def _fetch_page(self, team, channel, page):
        results = self._call_api(team, channel, {
            'channels': channel,
            'count': self._PAGE_SIZE,
            'offset': page * self._PAGE_SIZE,
        }, 'page %d' % (page + 1))
        for video in results:
            yield self._extract_video(video, team, False)

    def _extract_url_results(self, team, content_id):
        entries = OnDemandPagedList(
            functools.partial(self._fetch_page, team, content_id),
            self._PAGE_SIZE)
        return self.playlist_result(entries, playlist_title=content_id)
