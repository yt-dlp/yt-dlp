import re
import xml.etree.ElementTree

from .common import InfoExtractor
from ..compat import compat_str
from ..networking import HEADRequest, Request
from ..utils import (
    ExtractorError,
    RegexNotFoundError,
    find_xpath_attr,
    fix_xml_ampersands,
    float_or_none,
    int_or_none,
    join_nonempty,
    strip_or_none,
    timeconvert,
    try_get,
    unescapeHTML,
    update_url_query,
    url_basename,
    xpath_text,
)


def _media_xml_tag(tag):
    return '{http://search.yahoo.com/mrss/}%s' % tag


class MTVServicesInfoExtractor(InfoExtractor):
    _MOBILE_TEMPLATE = None
    _LANG = None

    @staticmethod
    def _id_from_uri(uri):
        return uri.split(':')[-1]

    @staticmethod
    def _remove_template_parameter(url):
        # Remove the templates, like &device={device}
        return re.sub(r'&[^=]*?={.*?}(?=(&|$))', '', url)

    def _get_feed_url(self, uri, url=None):
        return self._FEED_URL

    def _get_thumbnail_url(self, uri, itemdoc):
        search_path = '%s/%s' % (_media_xml_tag('group'), _media_xml_tag('thumbnail'))
        thumb_node = itemdoc.find(search_path)
        if thumb_node is None:
            return None
        return thumb_node.get('url') or thumb_node.text or None

    def _extract_mobile_video_formats(self, mtvn_id):
        webpage_url = self._MOBILE_TEMPLATE % mtvn_id
        req = Request(webpage_url)
        # Otherwise we get a webpage that would execute some javascript
        req.headers['User-Agent'] = 'curl/7'
        webpage = self._download_webpage(req, mtvn_id,
                                         'Downloading mobile page')
        metrics_url = unescapeHTML(self._search_regex(r'<a href="(http://metrics.+?)"', webpage, 'url'))
        req = HEADRequest(metrics_url)
        response = self._request_webpage(req, mtvn_id, 'Resolving url')
        url = response.url
        # Transform the url to get the best quality:
        url = re.sub(r'.+pxE=mp4', 'http://mtvnmobile.vo.llnwd.net/kip0/_pxn=0+_pxK=18639+_pxE=mp4', url, 1)
        return [{'url': url, 'ext': 'mp4'}]

    def _extract_video_formats(self, mdoc, mtvn_id, video_id):
        if re.match(r'.*/(error_country_block\.swf|geoblock\.mp4|copyright_error\.flv(?:\?geo\b.+?)?)$', mdoc.find('.//src').text) is not None:
            if mtvn_id is not None and self._MOBILE_TEMPLATE is not None:
                self.to_screen('The normal version is not available from your '
                               'country, trying with the mobile version')
                return self._extract_mobile_video_formats(mtvn_id)
            raise ExtractorError('This video is not available from your country.',
                                 expected=True)

        formats = []
        for rendition in mdoc.findall('.//rendition'):
            if rendition.get('method') == 'hls':
                hls_url = rendition.find('./src').text
                formats.extend(self._extract_m3u8_formats(
                    hls_url, video_id, ext='mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                # fms
                try:
                    _, _, ext = rendition.attrib['type'].partition('/')
                    rtmp_video_url = rendition.find('./src').text
                    if 'error_not_available.swf' in rtmp_video_url:
                        raise ExtractorError(
                            '%s said: video is not available' % self.IE_NAME,
                            expected=True)
                    if rtmp_video_url.endswith('siteunavail.png'):
                        continue
                    formats.extend([{
                        'ext': 'flv' if rtmp_video_url.startswith('rtmp') else ext,
                        'url': rtmp_video_url,
                        'format_id': join_nonempty(
                            'rtmp' if rtmp_video_url.startswith('rtmp') else None,
                            rendition.get('bitrate')),
                        'width': int(rendition.get('width')),
                        'height': int(rendition.get('height')),
                    }])
                except (KeyError, TypeError):
                    raise ExtractorError('Invalid rendition field.')
        return formats

    def _extract_subtitles(self, mdoc, mtvn_id):
        subtitles = {}
        for transcript in mdoc.findall('.//transcript'):
            if transcript.get('kind') != 'captions':
                continue
            lang = transcript.get('srclang')
            for typographic in transcript.findall('./typographic'):
                sub_src = typographic.get('src')
                if not sub_src:
                    continue
                ext = typographic.get('format')
                if ext == 'cea-608':
                    ext = 'scc'
                subtitles.setdefault(lang, []).append({
                    'url': compat_str(sub_src),
                    'ext': ext
                })
        return subtitles

    def _get_video_info(self, itemdoc, use_hls=True):
        uri = itemdoc.find('guid').text
        video_id = self._id_from_uri(uri)
        self.report_extraction(video_id)
        content_el = itemdoc.find('%s/%s' % (_media_xml_tag('group'), _media_xml_tag('content')))
        mediagen_url = self._remove_template_parameter(content_el.attrib['url'])
        mediagen_url = mediagen_url.replace('device={device}', '')
        if 'acceptMethods' not in mediagen_url:
            mediagen_url += '&' if '?' in mediagen_url else '?'
            mediagen_url += 'acceptMethods='
            mediagen_url += 'hls' if use_hls else 'fms'

        mediagen_doc = self._download_xml(
            mediagen_url, video_id, 'Downloading video urls', fatal=False)

        if not isinstance(mediagen_doc, xml.etree.ElementTree.Element):
            return None

        item = mediagen_doc.find('./video/item')
        if item is not None and item.get('type') == 'text':
            message = '%s returned error: ' % self.IE_NAME
            if item.get('code') is not None:
                message += '%s - ' % item.get('code')
            message += item.text
            raise ExtractorError(message, expected=True)

        description = strip_or_none(xpath_text(itemdoc, 'description'))

        timestamp = timeconvert(xpath_text(itemdoc, 'pubDate'))

        title_el = None
        if title_el is None:
            title_el = find_xpath_attr(
                itemdoc, './/{http://search.yahoo.com/mrss/}category',
                'scheme', 'urn:mtvn:video_title')
        if title_el is None:
            title_el = itemdoc.find('.//{http://search.yahoo.com/mrss/}title')
        if title_el is None:
            title_el = itemdoc.find('.//title')
            if title_el.text is None:
                title_el = None

        title = title_el.text
        if title is None:
            raise ExtractorError('Could not find video title')
        title = title.strip()

        series = find_xpath_attr(
            itemdoc, './/{http://search.yahoo.com/mrss/}category',
            'scheme', 'urn:mtvn:franchise')
        season = find_xpath_attr(
            itemdoc, './/{http://search.yahoo.com/mrss/}category',
            'scheme', 'urn:mtvn:seasonN')
        episode = find_xpath_attr(
            itemdoc, './/{http://search.yahoo.com/mrss/}category',
            'scheme', 'urn:mtvn:episodeN')
        series = series.text if series is not None else None
        season = season.text if season is not None else None
        episode = episode.text if episode is not None else None
        if season and episode:
            # episode number includes season, so remove it
            episode = re.sub(r'^%s' % season, '', episode)

        # This a short id that's used in the webpage urls
        mtvn_id = None
        mtvn_id_node = find_xpath_attr(itemdoc, './/{http://search.yahoo.com/mrss/}category',
                                       'scheme', 'urn:mtvn:id')
        if mtvn_id_node is not None:
            mtvn_id = mtvn_id_node.text

        formats = self._extract_video_formats(mediagen_doc, mtvn_id, video_id)

        # Some parts of complete video may be missing (e.g. missing Act 3 in
        # http://www.southpark.de/alle-episoden/s14e01-sexual-healing)
        if not formats:
            return None

        return {
            'title': title,
            'formats': formats,
            'subtitles': self._extract_subtitles(mediagen_doc, mtvn_id),
            'id': video_id,
            'thumbnail': self._get_thumbnail_url(uri, itemdoc),
            'description': description,
            'duration': float_or_none(content_el.attrib.get('duration')),
            'timestamp': timestamp,
            'series': series,
            'season_number': int_or_none(season),
            'episode_number': int_or_none(episode),
        }

    def _get_feed_query(self, uri):
        data = {'uri': uri}
        if self._LANG:
            data['lang'] = self._LANG
        return data

    def _get_videos_info(self, uri, use_hls=True, url=None):
        video_id = self._id_from_uri(uri)
        feed_url = self._get_feed_url(uri, url)
        info_url = update_url_query(feed_url, self._get_feed_query(uri))
        return self._get_videos_info_from_url(info_url, video_id, use_hls)

    def _get_videos_info_from_url(self, url, video_id, use_hls=True):
        idoc = self._download_xml(
            url, video_id,
            'Downloading info', transform_source=fix_xml_ampersands)

        title = xpath_text(idoc, './channel/title')
        description = xpath_text(idoc, './channel/description')

        entries = []
        for item in idoc.findall('.//item'):
            info = self._get_video_info(item, use_hls)
            if info:
                entries.append(info)

        # TODO: should be multi-video
        return self.playlist_result(
            entries, playlist_title=title, playlist_description=description)

    def _extract_triforce_mgid(self, webpage, data_zone=None, video_id=None):
        triforce_feed = self._parse_json(self._search_regex(
            r'triforceManifestFeed\s*=\s*({.+?})\s*;\s*\n', webpage,
            'triforce feed', default='{}'), video_id, fatal=False)

        data_zone = self._search_regex(
            r'data-zone=(["\'])(?P<zone>.+?_lc_promo.*?)\1', webpage,
            'data zone', default=data_zone, group='zone')

        feed_url = try_get(
            triforce_feed, lambda x: x['manifest']['zones'][data_zone]['feed'],
            compat_str)
        if not feed_url:
            return

        feed = self._download_json(feed_url, video_id, fatal=False)
        if not feed:
            return

        return try_get(feed, lambda x: x['result']['data']['id'], compat_str)

    @staticmethod
    def _extract_child_with_type(parent, t):
        for c in parent['children']:
            if c.get('type') == t:
                return c

    def _extract_mgid(self, webpage):
        try:
            # the url can be http://media.mtvnservices.com/fb/{mgid}.swf
            # or http://media.mtvnservices.com/{mgid}
            og_url = self._og_search_video_url(webpage)
            mgid = url_basename(og_url)
            if mgid.endswith('.swf'):
                mgid = mgid[:-4]
        except RegexNotFoundError:
            mgid = None

        if mgid is None or ':' not in mgid:
            mgid = self._search_regex(
                [r'data-mgid="(.*?)"', r'swfobject\.embedSWF\(".*?(mgid:.*?)"'],
                webpage, 'mgid', default=None)

        if not mgid:
            sm4_embed = self._html_search_meta(
                'sm4:video:embed', webpage, 'sm4 embed', default='')
            mgid = self._search_regex(
                r'embed/(mgid:.+?)["\'&?/]', sm4_embed, 'mgid', default=None)

        if not mgid:
            mgid = self._extract_triforce_mgid(webpage)

        if not mgid:
            data = self._parse_json(self._search_regex(
                r'__DATA__\s*=\s*({.+?});', webpage, 'data'), None)
            main_container = self._extract_child_with_type(data, 'MainContainer')
            ab_testing = self._extract_child_with_type(main_container, 'ABTesting')
            video_player = self._extract_child_with_type(ab_testing or main_container, 'VideoPlayer')
            if video_player:
                mgid = try_get(video_player, lambda x: x['props']['media']['video']['config']['uri'])
            else:
                flex_wrapper = self._extract_child_with_type(ab_testing or main_container, 'FlexWrapper')
                auth_suite_wrapper = self._extract_child_with_type(flex_wrapper, 'AuthSuiteWrapper')
                player = self._extract_child_with_type(auth_suite_wrapper or flex_wrapper, 'Player')
                if player:
                    mgid = try_get(player, lambda x: x['props']['videoDetail']['mgid'])

        if not mgid:
            raise ExtractorError('Could not extract mgid')

        return mgid

    def _real_extract(self, url):
        title = url_basename(url)
        webpage = self._download_webpage(url, title)
        mgid = self._extract_mgid(webpage)
        videos_info = self._get_videos_info(mgid, url=url)
        return videos_info


class MTVServicesEmbeddedIE(MTVServicesInfoExtractor):
    IE_NAME = 'mtvservices:embedded'
    _VALID_URL = r'https?://media\.mtvnservices\.com/embed/(?P<mgid>.+?)(\?|/|$)'
    _EMBED_REGEX = [r'<iframe[^>]+?src=(["\'])(?P<url>(?:https?:)?//media\.mtvnservices\.com/embed/.+?)\1']

    _TEST = {
        # From http://www.thewrap.com/peter-dinklage-sums-up-game-of-thrones-in-45-seconds-video/
        'url': 'http://media.mtvnservices.com/embed/mgid:uma:video:mtv.com:1043906/cp~vid%3D1043906%26uri%3Dmgid%3Auma%3Avideo%3Amtv.com%3A1043906',
        'md5': 'cb349b21a7897164cede95bd7bf3fbb9',
        'info_dict': {
            'id': '1043906',
            'ext': 'mp4',
            'title': 'Peter Dinklage Sums Up \'Game Of Thrones\' In 45 Seconds',
            'description': '"Sexy sexy sexy, stabby stabby stabby, beautiful language," says Peter Dinklage as he tries summarizing "Game of Thrones" in under a minute.',
            'timestamp': 1400126400,
            'upload_date': '20140515',
        },
    }

    def _get_feed_url(self, uri, url=None):
        video_id = self._id_from_uri(uri)
        config = self._download_json(
            'http://media.mtvnservices.com/pmt/e1/access/index.html?uri=%s&configtype=edge' % uri, video_id)
        return self._remove_template_parameter(config['feedWithQueryParams'])

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        mgid = mobj.group('mgid')
        return self._get_videos_info(mgid)


class MTVIE(MTVServicesInfoExtractor):
    IE_NAME = 'mtv'
    _VALID_URL = r'https?://(?:www\.)?mtv\.com/(?:video-clips|(?:full-)?episodes)/(?P<id>[^/?#.]+)'
    _FEED_URL = 'http://www.mtv.com/feeds/mrss/'

    _TESTS = [{
        'url': 'http://www.mtv.com/video-clips/vl8qof/unlocking-the-truth-trailer',
        'md5': '1edbcdf1e7628e414a8c5dcebca3d32b',
        'info_dict': {
            'id': '5e14040d-18a4-47c4-a582-43ff602de88e',
            'ext': 'mp4',
            'title': 'Unlocking The Truth|July 18, 2016|1|101|Trailer',
            'description': '"Unlocking the Truth" premieres August 17th at 11/10c.',
            'timestamp': 1468846800,
            'upload_date': '20160718',
        },
    }, {
        'url': 'http://www.mtv.com/full-episodes/94tujl/unlocking-the-truth-gates-of-hell-season-1-ep-101',
        'only_matching': True,
    }, {
        'url': 'http://www.mtv.com/episodes/g8xu7q/teen-mom-2-breaking-the-wall-season-7-ep-713',
        'only_matching': True,
    }]


class MTVJapanIE(MTVServicesInfoExtractor):
    IE_NAME = 'mtvjapan'
    _VALID_URL = r'https?://(?:www\.)?mtvjapan\.com/videos/(?P<id>[0-9a-z]+)'

    _TEST = {
        'url': 'http://www.mtvjapan.com/videos/prayht/fresh-info-cadillac-escalade',
        'info_dict': {
            'id': 'bc01da03-6fe5-4284-8880-f291f4e368f5',
            'ext': 'mp4',
            'title': '【Fresh Info】Cadillac ESCALADE Sport Edition',
        },
        'params': {
            'skip_download': True,
        },
    }
    _GEO_COUNTRIES = ['JP']
    _FEED_URL = 'http://feeds.mtvnservices.com/od/feed/intl-mrss-player-feed'

    def _get_feed_query(self, uri):
        return {
            'arcEp': 'mtvjapan.com',
            'mgid': uri,
        }


class MTVVideoIE(MTVServicesInfoExtractor):
    IE_NAME = 'mtv:video'
    _VALID_URL = r'''(?x)^https?://
        (?:(?:www\.)?mtv\.com/videos/.+?/(?P<videoid>[0-9]+)/[^/]+$|
           m\.mtv\.com/videos/video\.rbml\?.*?id=(?P<mgid>[^&]+))'''

    _FEED_URL = 'http://www.mtv.com/player/embed/AS3/rss/'

    _TESTS = [
        {
            'url': 'http://www.mtv.com/videos/misc/853555/ours-vh1-storytellers.jhtml',
            'md5': '850f3f143316b1e71fa56a4edfd6e0f8',
            'info_dict': {
                'id': '853555',
                'ext': 'mp4',
                'title': 'Taylor Swift - "Ours (VH1 Storytellers)"',
                'description': 'Album: Taylor Swift performs "Ours" for VH1 Storytellers at Harvey Mudd College.',
                'timestamp': 1352610000,
                'upload_date': '20121111',
            },
        },
    ]

    def _get_thumbnail_url(self, uri, itemdoc):
        return 'http://mtv.mtvnimages.com/uri/' + uri

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('videoid')
        uri = mobj.groupdict().get('mgid')
        if uri is None:
            webpage = self._download_webpage(url, video_id)

            # Some videos come from Vevo.com
            m_vevo = re.search(
                r'(?s)isVevoVideo = true;.*?vevoVideoId = "(.*?)";', webpage)
            if m_vevo:
                vevo_id = m_vevo.group(1)
                self.to_screen('Vevo video detected: %s' % vevo_id)
                return self.url_result('vevo:%s' % vevo_id, ie='Vevo')

            uri = self._html_search_regex(r'/uri/(.*?)\?', webpage, 'uri')
        return self._get_videos_info(uri)


class MTVDEIE(MTVServicesInfoExtractor):
    _WORKING = False
    IE_NAME = 'mtv.de'
    _VALID_URL = r'https?://(?:www\.)?mtv\.de/(?:musik/videoclips|folgen|news)/(?P<id>[0-9a-z]+)'
    _TESTS = [{
        'url': 'http://www.mtv.de/musik/videoclips/2gpnv7/Traum',
        'info_dict': {
            'id': 'd5d472bc-f5b7-11e5-bffd-a4badb20dab5',
            'ext': 'mp4',
            'title': 'Traum',
            'description': 'Traum',
        },
        'params': {
            # rtmp download
            'skip_download': True,
        },
        'skip': 'Blocked at Travis CI',
    }, {
        # mediagen URL without query (e.g. http://videos.mtvnn.com/mediagen/e865da714c166d18d6f80893195fcb97)
        'url': 'http://www.mtv.de/folgen/6b1ylu/teen-mom-2-enthuellungen-S5-F1',
        'info_dict': {
            'id': '1e5a878b-31c5-11e7-a442-0e40cf2fc285',
            'ext': 'mp4',
            'title': 'Teen Mom 2',
            'description': 'md5:dc65e357ef7e1085ed53e9e9d83146a7',
        },
        'params': {
            # rtmp download
            'skip_download': True,
        },
        'skip': 'Blocked at Travis CI',
    }, {
        'url': 'http://www.mtv.de/news/glolix/77491-mtv-movies-spotlight--pixels--teil-3',
        'info_dict': {
            'id': 'local_playlist-4e760566473c4c8c5344',
            'ext': 'mp4',
            'title': 'Article_mtv-movies-spotlight-pixels-teil-3_short-clips_part1',
            'description': 'MTV Movies Supercut',
        },
        'params': {
            # rtmp download
            'skip_download': True,
        },
        'skip': 'Das Video kann zur Zeit nicht abgespielt werden.',
    }]
    _GEO_COUNTRIES = ['DE']
    _FEED_URL = 'http://feeds.mtvnservices.com/od/feed/intl-mrss-player-feed'

    def _get_feed_query(self, uri):
        return {
            'arcEp': 'mtv.de',
            'mgid': uri,
        }


class MTVItaliaIE(MTVServicesInfoExtractor):
    IE_NAME = 'mtv.it'
    _VALID_URL = r'https?://(?:www\.)?mtv\.it/(?:episodi|video|musica)/(?P<id>[0-9a-z]+)'
    _TESTS = [{
        'url': 'http://www.mtv.it/episodi/24bqab/mario-una-serie-di-maccio-capatonda-cavoli-amario-episodio-completo-S1-E1',
        'info_dict': {
            'id': '0f0fc78e-45fc-4cce-8f24-971c25477530',
            'ext': 'mp4',
            'title': 'Cavoli amario (episodio completo)',
            'description': 'md5:4962bccea8fed5b7c03b295ae1340660',
            'series': 'Mario - Una Serie Di Maccio Capatonda',
            'season_number': 1,
            'episode_number': 1,
        },
        'params': {
            'skip_download': True,
        },
    }]
    _GEO_COUNTRIES = ['IT']
    _FEED_URL = 'http://feeds.mtvnservices.com/od/feed/intl-mrss-player-feed'

    def _get_feed_query(self, uri):
        return {
            'arcEp': 'mtv.it',
            'mgid': uri,
        }


class MTVItaliaProgrammaIE(MTVItaliaIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'mtv.it:programma'
    _VALID_URL = r'https?://(?:www\.)?mtv\.it/(?:programmi|playlist)/(?P<id>[0-9a-z]+)'
    _TESTS = [{
        # program page: general
        'url': 'http://www.mtv.it/programmi/s2rppv/mario-una-serie-di-maccio-capatonda',
        'info_dict': {
            'id': 'a6f155bc-8220-4640-aa43-9b95f64ffa3d',
            'title': 'Mario - Una Serie Di Maccio Capatonda',
            'description': 'md5:72fbffe1f77ccf4e90757dd4e3216153',
        },
        'playlist_count': 2,
        'params': {
            'skip_download': True,
        },
    }, {
        # program page: specific season
        'url': 'http://www.mtv.it/programmi/d9ncjf/mario-una-serie-di-maccio-capatonda-S2',
        'info_dict': {
            'id': '4deeb5d8-f272-490c-bde2-ff8d261c6dd1',
            'title': 'Mario - Una Serie Di Maccio Capatonda - Stagione 2',
        },
        'playlist_count': 34,
        'params': {
            'skip_download': True,
        },
    }, {
        # playlist page + redirect
        'url': 'http://www.mtv.it/playlist/sexy-videos/ilctal',
        'info_dict': {
            'id': 'dee8f9ee-756d-493b-bf37-16d1d2783359',
            'title': 'Sexy Videos',
        },
        'playlist_mincount': 145,
        'params': {
            'skip_download': True,
        },
    }]
    _GEO_COUNTRIES = ['IT']
    _FEED_URL = 'http://www.mtv.it/feeds/triforce/manifest/v8'

    def _get_entries(self, title, url):
        while True:
            pg = self._search_regex(r'/(\d+)$', url, 'entries', '1')
            entries = self._download_json(url, title, 'page %s' % pg)
            url = try_get(
                entries, lambda x: x['result']['nextPageURL'], compat_str)
            entries = try_get(
                entries, (
                    lambda x: x['result']['data']['items'],
                    lambda x: x['result']['data']['seasons']),
                list)
            for entry in entries or []:
                if entry.get('canonicalURL'):
                    yield self.url_result(entry['canonicalURL'])
            if not url:
                break

    def _real_extract(self, url):
        query = {'url': url}
        info_url = update_url_query(self._FEED_URL, query)
        video_id = self._match_id(url)
        info = self._download_json(info_url, video_id).get('manifest')

        redirect = try_get(
            info, lambda x: x['newLocation']['url'], compat_str)
        if redirect:
            return self.url_result(redirect)

        title = info.get('title')
        video_id = try_get(
            info, lambda x: x['reporting']['itemId'], compat_str)
        parent_id = try_get(
            info, lambda x: x['reporting']['parentId'], compat_str)

        playlist_url = current_url = None
        for z in (info.get('zones') or {}).values():
            if z.get('moduleName') in ('INTL_M304', 'INTL_M209'):
                info_url = z.get('feed')
            if z.get('moduleName') in ('INTL_M308', 'INTL_M317'):
                playlist_url = playlist_url or z.get('feed')
            if z.get('moduleName') in ('INTL_M300',):
                current_url = current_url or z.get('feed')

        if not info_url:
            raise ExtractorError('No info found')

        if video_id == parent_id:
            video_id = self._search_regex(
                r'([^\/]+)/[^\/]+$', info_url, 'video_id')

        info = self._download_json(info_url, video_id, 'Show infos')
        info = try_get(info, lambda x: x['result']['data'], dict)
        title = title or try_get(
            info, (
                lambda x: x['title'],
                lambda x: x['headline']),
            compat_str)
        description = try_get(info, lambda x: x['content'], compat_str)

        if current_url:
            season = try_get(
                self._download_json(playlist_url, video_id, 'Seasons info'),
                lambda x: x['result']['data'], dict)
            current = try_get(
                season, lambda x: x['currentSeason'], compat_str)
            seasons = try_get(
                season, lambda x: x['seasons'], list) or []

            if current in [s.get('eTitle') for s in seasons]:
                playlist_url = current_url

        title = re.sub(
            r'[-|]\s*(?:mtv\s*italia|programma|playlist)',
            '', title, flags=re.IGNORECASE).strip()

        return self.playlist_result(
            self._get_entries(title, playlist_url),
            video_id, title, description)
