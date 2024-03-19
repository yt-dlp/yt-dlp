from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from .theplatform import ThePlatformFeedIE
from .youtube import YoutubeIE
from ..utils import (
    ExtractorError,
    extract_attributes,
    get_element_html_by_id,
    int_or_none,
    find_xpath_attr,
    smuggle_url,
    xpath_element,
    xpath_text,
    update_url_query,
    url_or_none,
)


class CBSBaseIE(ThePlatformFeedIE):  # XXX: Do not subclass from concrete IE
    def _parse_smil_subtitles(self, smil, namespace=None, subtitles_lang='en'):
        subtitles = {}
        for k, ext in [('sMPTE-TTCCURL', 'tt'), ('ClosedCaptionURL', 'ttml'), ('webVTTCaptionURL', 'vtt')]:
            cc_e = find_xpath_attr(smil, self._xpath_ns('.//param', namespace), 'name', k)
            if cc_e is not None:
                cc_url = cc_e.get('value')
                if cc_url:
                    subtitles.setdefault(subtitles_lang, []).append({
                        'ext': ext,
                        'url': cc_url,
                    })
        return subtitles

    def _extract_common_video_info(self, content_id, asset_types, mpx_acc, extra_info):
        tp_path = 'dJ5BDC/media/guid/%d/%s' % (mpx_acc, content_id)
        tp_release_url = f'https://link.theplatform.com/s/{tp_path}'
        info = self._extract_theplatform_metadata(tp_path, content_id)

        formats, subtitles = [], {}
        last_e = None
        for asset_type, query in asset_types.items():
            try:
                tp_formats, tp_subtitles = self._extract_theplatform_smil(
                    update_url_query(tp_release_url, query), content_id,
                    'Downloading %s SMIL data' % asset_type)
            except ExtractorError as e:
                last_e = e
                if asset_type != 'fallback':
                    continue
                query['formats'] = ''  # blank query to check if expired
                try:
                    tp_formats, tp_subtitles = self._extract_theplatform_smil(
                        update_url_query(tp_release_url, query), content_id,
                        'Downloading %s SMIL data, trying again with another format' % asset_type)
                except ExtractorError as e:
                    last_e = e
                    continue
            formats.extend(tp_formats)
            subtitles = self._merge_subtitles(subtitles, tp_subtitles)
        if last_e and not formats:
            self.raise_no_formats(last_e, True, content_id)

        extra_info.update({
            'id': content_id,
            'formats': formats,
            'subtitles': subtitles,
        })
        info.update({k: v for k, v in extra_info.items() if v is not None})
        return info

    def _extract_video_info(self, *args, **kwargs):
        # Extract assets + metadata and call _extract_common_video_info
        raise NotImplementedError('This method must be implemented by subclasses')

    def _real_extract(self, url):
        return self._extract_video_info(self._match_id(url))


class CBSIE(CBSBaseIE):
    _WORKING = False
    _VALID_URL = r'''(?x)
        (?:
            cbs:|
            https?://(?:www\.)?(?:
                cbs\.com/(?:shows|movies)/(?:video|[^/]+/video|[^/]+)/|
                colbertlateshow\.com/(?:video|podcasts)/)
        )(?P<id>[\w-]+)'''

    # All tests are blocked outside US
    _TESTS = [{
        'url': 'https://www.cbs.com/shows/video/xrUyNLtl9wd8D_RWWAg9NU2F_V6QpB3R/',
        'info_dict': {
            'id': 'xrUyNLtl9wd8D_RWWAg9NU2F_V6QpB3R',
            'ext': 'mp4',
            'title': 'Tough As Nails - Dreams Never Die',
            'description': 'md5:a3535a62531cdd52b0364248a2c1ae33',
            'duration': 2588,
            'timestamp': 1639015200,
            'upload_date': '20211209',
            'uploader': 'CBSI-NEW',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': 'Subscription required',
    }, {
        'url': 'https://www.cbs.com/shows/video/sZH1MGgomIosZgxGJ1l263MFq16oMtW1/',
        'info_dict': {
            'id': 'sZH1MGgomIosZgxGJ1l263MFq16oMtW1',
            'title': 'The Late Show - 3/16/22 (Michael Buble, Rose Matafeo)',
            'timestamp': 1647488100,
            'description': 'md5:d0e6ec23c544b7fa8e39a8e6844d2439',
            'uploader': 'CBSI-NEW',
            'upload_date': '20220317',
        },
        'params': {
            'ignore_no_formats_error': True,
            'skip_download': True,
        },
        'expected_warnings': [
            'This content expired on', 'No video formats found', 'Requested format is not available'],
        'skip': '404 Not Found',
    }, {
        'url': 'http://colbertlateshow.com/video/8GmB0oY0McANFvp2aEffk9jZZZ2YyXxy/the-colbeard/',
        'only_matching': True,
    }, {
        'url': 'http://www.colbertlateshow.com/podcasts/dYSwjqPs_X1tvbV_P2FcPWRa_qT6akTC/in-the-bad-room-with-stephen/',
        'only_matching': True,
    }]

    def _extract_video_info(self, content_id, site='cbs', mpx_acc=2198311517):
        items_data = self._download_xml(
            'https://can.cbs.com/thunder/player/videoPlayerService.php',
            content_id, query={'partner': site, 'contentId': content_id})
        video_data = xpath_element(items_data, './/item')
        title = xpath_text(video_data, 'videoTitle', 'title') or xpath_text(video_data, 'videotitle', 'title')

        asset_types = {}
        has_drm = False
        for item in items_data.findall('.//item'):
            asset_type = xpath_text(item, 'assetType')
            query = {
                'mbr': 'true',
                'assetTypes': asset_type,
            }
            if not asset_type:
                # fallback for content_ids that videoPlayerService doesn't return anything for
                asset_type = 'fallback'
                query['formats'] = 'M3U+none,MPEG4,M3U+appleHlsEncryption,MP3'
                del query['assetTypes']
            if asset_type in asset_types:
                continue
            elif any(excluded in asset_type for excluded in ('HLS_FPS', 'DASH_CENC', 'OnceURL')):
                if 'DASH_CENC' in asset_type:
                    has_drm = True
                continue
            if asset_type.startswith('HLS') or 'StreamPack' in asset_type:
                query['formats'] = 'MPEG4,M3U'
            elif asset_type in ('RTMP', 'WIFI', '3G'):
                query['formats'] = 'MPEG4,FLV'
            asset_types[asset_type] = query

        if not asset_types and has_drm:
            self.report_drm(content_id)

        return self._extract_common_video_info(content_id, asset_types, mpx_acc, extra_info={
            'title': title,
            'series': xpath_text(video_data, 'seriesTitle'),
            'season_number': int_or_none(xpath_text(video_data, 'seasonNumber')),
            'episode_number': int_or_none(xpath_text(video_data, 'episodeNumber')),
            'duration': int_or_none(xpath_text(video_data, 'videoLength'), 1000),
            'thumbnail': url_or_none(xpath_text(video_data, 'previewImageURL')),
        })


class ParamountPressExpressIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?paramountpressexpress\.com(?:/[\w-]+)+/(?P<yt>yt-)?video/?\?watch=(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.paramountpressexpress.com/cbs-entertainment/shows/survivor/video/?watch=pnzew7e2hx',
        'md5': '56631dbcadaab980d1fc47cb7b76cba4',
        'info_dict': {
            'id': '6322981580112',
            'ext': 'mp4',
            'title': 'I’m Felicia',
            'description': 'md5:88fad93f8eede1c9c8f390239e4c6290',
            'uploader_id': '6055873637001',
            'upload_date': '20230320',
            'timestamp': 1679334960,
            'duration': 49.557,
            'thumbnail': r're:^https://.+\.jpg',
            'tags': [],
        },
    }, {
        'url': 'https://www.paramountpressexpress.com/cbs-entertainment/video/?watch=2s5eh8kppc',
        'md5': 'edcb03e3210b88a3e56c05aa863e0e5b',
        'info_dict': {
            'id': '6323036027112',
            'ext': 'mp4',
            'title': '‘Y&R’ Set Visit: Jerry O’Connell Quizzes Cast on Pre-Love Scene Rituals and More',
            'description': 'md5:b929867a357aac5544b783d834c78383',
            'uploader_id': '6055873637001',
            'upload_date': '20230321',
            'timestamp': 1679430180,
            'duration': 132.032,
            'thumbnail': r're:^https://.+\.jpg',
            'tags': [],
        },
    }, {
        'url': 'https://www.paramountpressexpress.com/paramount-plus/yt-video/?watch=OX9wJWOcqck',
        'info_dict': {
            'id': 'OX9wJWOcqck',
            'ext': 'mp4',
            'title': 'Rugrats | Season 2 Official Trailer | Paramount+',
            'description': 'md5:1f7e26f5625a9f0d6564d9ad97a9f7de',
            'uploader': 'Paramount Plus',
            'uploader_id': '@paramountplus',
            'uploader_url': 'http://www.youtube.com/@paramountplus',
            'channel': 'Paramount Plus',
            'channel_id': 'UCrRttZIypNTA1Mrfwo745Sg',
            'channel_url': 'https://www.youtube.com/channel/UCrRttZIypNTA1Mrfwo745Sg',
            'upload_date': '20230316',
            'duration': 88,
            'age_limit': 0,
            'availability': 'public',
            'live_status': 'not_live',
            'playable_in_embed': True,
            'view_count': int,
            'like_count': int,
            'channel_follower_count': int,
            'thumbnail': 'https://i.ytimg.com/vi/OX9wJWOcqck/maxresdefault.jpg',
            'categories': ['Entertainment'],
            'tags': ['Rugrats'],
        },
    }, {
        'url': 'https://www.paramountpressexpress.com/showtime/yt-video/?watch=_ljssSoDLkw',
        'info_dict': {
            'id': '_ljssSoDLkw',
            'ext': 'mp4',
            'title': 'Lavell Crawford: THEE Lavell Crawford Comedy Special Official Trailer | SHOWTIME',
            'description': 'md5:39581bcc3fd810209b642609f448af70',
            'uploader': 'SHOWTIME',
            'uploader_id': '@Showtime',
            'uploader_url': 'http://www.youtube.com/@Showtime',
            'channel': 'SHOWTIME',
            'channel_id': 'UCtwMWJr2BFPkuJTnSvCESSQ',
            'channel_url': 'https://www.youtube.com/channel/UCtwMWJr2BFPkuJTnSvCESSQ',
            'upload_date': '20230209',
            'duration': 49,
            'age_limit': 0,
            'availability': 'public',
            'live_status': 'not_live',
            'playable_in_embed': True,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'channel_follower_count': int,
            'thumbnail': 'https://i.ytimg.com/vi_webp/_ljssSoDLkw/maxresdefault.webp',
            'categories': ['People & Blogs'],
            'tags': 'count:27',
        },
    }]

    def _real_extract(self, url):
        display_id, is_youtube = self._match_valid_url(url).group('id', 'yt')
        if is_youtube:
            return self.url_result(display_id, YoutubeIE)

        webpage = self._download_webpage(url, display_id)
        video_id = self._search_regex(
            r'\bvideo_id\s*=\s*["\'](\d+)["\']\s*,', webpage, 'Brightcove ID')
        token = self._search_regex(r'\btoken\s*=\s*["\']([\w.-]+)["\']', webpage, 'token')

        player = extract_attributes(get_element_html_by_id('vcbrightcoveplayer', webpage) or '')
        account_id = player.get('data-account') or '6055873637001'
        player_id = player.get('data-player') or 'OtLKgXlO9F'
        embed = player.get('data-embed') or 'default'

        return self.url_result(smuggle_url(
            f'https://players.brightcove.net/{account_id}/{player_id}_{embed}/index.html?videoId={video_id}',
            {'token': token}), BrightcoveNewIE)
