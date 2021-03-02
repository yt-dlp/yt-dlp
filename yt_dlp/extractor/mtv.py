# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_xpath,
)
from ..utils import (
    ExtractorError,
    find_xpath_attr,
    fix_xml_ampersands,
    float_or_none,
    HEADRequest,
    RegexNotFoundError,
    sanitized_Request,
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

    def _get_feed_url(self, uri):
        return self._FEED_URL

    def _get_thumbnail_url(self, uri, itemdoc):
        search_path = '%s/%s' % (_media_xml_tag('group'), _media_xml_tag('thumbnail'))
        thumb_node = itemdoc.find(search_path)
        if thumb_node is None:
            return None
        return thumb_node.get('url') or thumb_node.text or None

    def _extract_mobile_video_formats(self, mtvn_id):
        webpage_url = self._MOBILE_TEMPLATE % mtvn_id
        req = sanitized_Request(webpage_url)
        # Otherwise we get a webpage that would execute some javascript
        req.add_header('User-Agent', 'curl/7')
        webpage = self._download_webpage(req, mtvn_id,
                                         'Downloading mobile page')
        metrics_url = unescapeHTML(self._search_regex(r'<a href="(http://metrics.+?)"', webpage, 'url'))
        req = HEADRequest(metrics_url)
        response = self._request_webpage(req, mtvn_id, 'Resolving url')
        url = response.geturl()
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
                        'format_id': '-'.join(filter(None, [
                            'rtmp' if rtmp_video_url.startswith('rtmp') else None,
                            rendition.get('bitrate')])),
                        'width': int(rendition.get('width')),
                        'height': int(rendition.get('height')),
                    }])
                except (KeyError, TypeError):
                    raise ExtractorError('Invalid rendition field.')
        if formats:
            self._sort_formats(formats)
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

        if mediagen_doc is False:
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
            title_el = itemdoc.find(compat_xpath('.//{http://search.yahoo.com/mrss/}title'))
        if title_el is None:
            title_el = itemdoc.find(compat_xpath('.//title'))
            if title_el.text is None:
                title_el = None

        title = title_el.text
        if title is None:
            raise ExtractorError('Could not find video title')
        title = title.strip()

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

        self._sort_formats(formats)

        return {
            'title': title,
            'formats': formats,
            'subtitles': self._extract_subtitles(mediagen_doc, mtvn_id),
            'id': video_id,
            'thumbnail': self._get_thumbnail_url(uri, itemdoc),
            'description': description,
            'duration': float_or_none(content_el.attrib.get('duration')),
            'timestamp': timestamp,
        }

    def _get_feed_query(self, uri):
        data = {'uri': uri}
        if self._LANG:
            data['lang'] = self._LANG
        return data

    def _get_videos_info(self, uri, use_hls=True):
        video_id = self._id_from_uri(uri)
        feed_url = self._get_feed_url(uri)
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
        return next(c for c in parent['children'] if c.get('type') == t)

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
            video_player = self._extract_child_with_type(main_container, 'VideoPlayer')
            mgid = video_player['props']['media']['video']['config']['uri']

        return mgid

    def _real_extract(self, url):
        title = url_basename(url)
        webpage = self._download_webpage(url, title)
        mgid = self._extract_mgid(webpage)
        videos_info = self._get_videos_info(mgid)
        return videos_info


class MTVServicesEmbeddedIE(MTVServicesInfoExtractor):
    IE_NAME = 'mtvservices:embedded'
    _VALID_URL = r'https?://media\.mtvnservices\.com/embed/(?P<mgid>.+?)(\?|/|$)'

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

    @staticmethod
    def _extract_url(webpage):
        mobj = re.search(
            r'<iframe[^>]+?src=(["\'])(?P<url>(?:https?:)?//media.mtvnservices.com/embed/.+?)\1', webpage)
        if mobj:
            return mobj.group('url')

    def _get_feed_url(self, uri):
        video_id = self._id_from_uri(uri)
        config = self._download_json(
            'http://media.mtvnservices.com/pmt/e1/access/index.html?uri=%s&configtype=edge' % uri, video_id)
        return self._remove_template_parameter(config['feedWithQueryParams'])

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
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
        mobj = re.match(self._VALID_URL, url)
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
