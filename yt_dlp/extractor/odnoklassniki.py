import urllib.parse

from .common import InfoExtractor
from ..compat import compat_etree_fromstring
from ..networking import HEADRequest
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    qualities,
    smuggle_url,
    traverse_obj,
    unescapeHTML,
    unified_strdate,
    unsmuggle_url,
    url_or_none,
    urlencode_postdata,
)


class OdnoklassnikiIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                https?://
                    (?:(?:www|m|mobile)\.)?
                    (?:odnoklassniki|ok)\.ru/
                    (?:
                        video(?P<embed>embed)?/|
                        web-api/video/moviePlayer/|
                        live/|
                        dk\?.*?st\.mvId=
                    )
                    (?P<id>[\d-]+)
                '''
    _EMBED_REGEX = [r'<iframe[^>]+src=(["\'])(?P<url>(?:https?:)?//(?:odnoklassniki|ok)\.ru/videoembed/.+?)\1']
    _TESTS = [{
        'note': 'Coub embedded',
        'url': 'http://ok.ru/video/1484130554189',
        'info_dict': {
            'id': '1keok9',
            'ext': 'mp4',
            'timestamp': 1545580896,
            'view_count': int,
            'thumbnail': r're:^https?://.*\.jpg$',
            'title': 'Народная забава',
            'uploader': 'Nevata',
            'upload_date': '20181223',
            'age_limit': 0,
            'uploader_id': 'nevata.s',
            'like_count': int,
            'duration': 8.08,
            'repost_count': int,
        },
    }, {
        'note': 'vk.com embedded',
        'url': 'https://ok.ru/video/3568183087575',
        'info_dict': {
            'id': '-165101755_456243749',
            'ext': 'mp4',
            'uploader_id': '-165101755',
            'duration': 132,
            'timestamp': 1642869935,
            'upload_date': '20220122',
            'thumbnail': str,
            'title': str,
            'uploader': str,
        },
        'skip': 'vk extractor error',
    }, {
        # metadata in JSON, webm_dash with Firefox UA
        'url': 'http://ok.ru/video/20079905452',
        'md5': '8f477d8931c531374a3e36daec617b2c',
        'info_dict': {
            'id': '20079905452',
            'ext': 'webm',
            'title': 'Культура меняет нас (прекрасный ролик!))',
            'thumbnail': str,
            'duration': 100,
            'upload_date': '20141207',
            'uploader_id': '330537914540',
            'uploader': 'Виталий Добровольский',
            'like_count': int,
            'age_limit': 0,
        },
        'params': {
            'format': 'bv[ext=webm]',
            'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0'},
        },
    }, {
        # metadataUrl
        'url': 'http://ok.ru/video/63567059965189-0?fromTime=5',
        'md5': '2bae2f58eefe1b3d26f3926c4a64d2f3',
        'info_dict': {
            'id': '63567059965189-0',
            'ext': 'mp4',
            'title': 'Девушка без комплексов ...',
            'thumbnail': str,
            'duration': 191,
            'upload_date': '20150518',
            'uploader_id': '534380003155',
            'uploader': '☭ Андрей Мещанинов ☭',
            'like_count': int,
            'age_limit': 0,
            'start_time': 5,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # YouTube embed (metadataUrl, provider == USER_YOUTUBE)
        'url': 'https://ok.ru/video/3952212382174',
        'md5': '5fb5f83ce16cb212d6bf887282b5da53',
        'info_dict': {
            'id': '5axVgHHDBvU',
            'ext': 'mp4',
            'title': 'Youtube-dl 101: What is it and HOW to use it! Full Download Walkthrough and Guide',
            'description': 'md5:b57209eeb9d5c2f20c984dfb58862097',
            'uploader': 'Lod Mer',
            'uploader_id': '575186401502',
            'duration': 1529,
            'age_limit': 0,
            'upload_date': '20210405',
            'comment_count': int,
            'live_status': 'not_live',
            'view_count': int,
            'thumbnail': 'https://i.mycdn.me/i?r=AEHujHvw2RjEbemUCNEorZbxYpb_p_9AcN2FmGik64Krkcmz37YtlY093oAM5-HIEAt7Zi9s0CiBOSDmbngC-I-k&fn=external_8',
            'uploader_url': 'https://www.youtube.com/@MrKewlkid94',
            'channel_follower_count': int,
            'tags': ['youtube-dl', 'youtube playlists', 'download videos', 'download audio'],
            'channel_id': 'UCVGtvURtEURYHtJFUegdSug',
            'like_count': int,
            'availability': 'public',
            'channel_url': 'https://www.youtube.com/channel/UCVGtvURtEURYHtJFUegdSug',
            'categories': ['Education'],
            'playable_in_embed': True,
            'channel': 'BornToReact',
        },
    }, {
        # YouTube embed (metadata, provider == USER_YOUTUBE, no metadata.movie.title field)
        'url': 'http://ok.ru/video/62036049272859-0',
        'info_dict': {
            'id': '62036049272859-0',
            'ext': 'mp4',
            'title': 'МУЗЫКА     ДОЖДЯ .',
            'description': 'md5:6f1867132bd96e33bf53eda1091e8ed0',
            'upload_date': '20120106',
            'uploader_id': '473534735899',
            'uploader': 'МARINA D',
            'age_limit': 0,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Video has not been found',
    }, {
        'note': 'Only available in mobile webpage',
        'url': 'https://m.ok.ru/video/2361249957145',
        'info_dict': {
            'id': '2361249957145',
            'ext': 'mp4',
            'title': 'Быковское крещение',
            'duration': 3038.181,
            'thumbnail': r're:^https?://i\.mycdn\.me/videoPreview\?.+',
        },
    }, {
        'note': 'subtitles',
        'url': 'https://ok.ru/video/4249587550747',
        'info_dict': {
            'id': '4249587550747',
            'ext': 'mp4',
            'title': 'Small Country An African Childhood (2020) (1080p) +subtitle',
            'uploader': 'Sunflower Movies',
            'uploader_id': '595802161179',
            'upload_date': '20220816',
            'duration': 6728,
            'age_limit': 0,
            'thumbnail': r're:^https?://i\.mycdn\.me/videoPreview\?.+',
            'like_count': int,
            'subtitles': dict,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://ok.ru/web-api/video/moviePlayer/20079905452',
        'only_matching': True,
    }, {
        'url': 'http://www.ok.ru/video/20648036891',
        'only_matching': True,
    }, {
        'url': 'http://www.ok.ru/videoembed/20648036891',
        'only_matching': True,
    }, {
        'url': 'http://m.ok.ru/video/20079905452',
        'only_matching': True,
    }, {
        'url': 'http://mobile.ok.ru/video/20079905452',
        'only_matching': True,
    }, {
        'url': 'https://www.ok.ru/live/484531969818',
        'only_matching': True,
    }, {
        'url': 'https://m.ok.ru/dk?st.cmd=movieLayer&st.discId=863789452017&st.retLoc=friend&st.rtu=%2Fdk%3Fst.cmd%3DfriendMovies%26st.mode%3Down%26st.mrkId%3D%257B%2522uploadedMovieMarker%2522%253A%257B%2522marker%2522%253A%25221519410114503%2522%252C%2522hasMore%2522%253Atrue%257D%252C%2522sharedMovieMarker%2522%253A%257B%2522marker%2522%253Anull%252C%2522hasMore%2522%253Afalse%257D%257D%26st.friendId%3D561722190321%26st.frwd%3Don%26_prevCmd%3DfriendMovies%26tkn%3D7257&st.discType=MOVIE&st.mvId=863789452017&_prevCmd=friendMovies&tkn=3648#lst#',
        'only_matching': True,
    }, {
        # Paid video
        'url': 'https://ok.ru/video/954886983203',
        'only_matching': True,
    }, {
        'url': 'https://ok.ru/videoembed/2932705602075',
        'info_dict': {
            'id': '2932705602075',
            'ext': 'mp4',
            'thumbnail': 'https://i.mycdn.me/videoPreview?id=1369902483995&type=37&idx=2&tkn=fqlnoQD_xwq5ovIlKfgNyU08qmM&fn=external_8',
            'title': 'Boosty для тебя!',
            'uploader_id': '597811038747',
            'like_count': 0,
            'duration': 35,
        },
    }]

    _WEBPAGE_TESTS = [{
        'url': 'https://boosty.to/ikakprosto/posts/56cedaca-b56a-4dfd-b3ed-98c79cfa0167',
        'info_dict': {
            'id': '3950343629563',
            'ext': 'mp4',
            'thumbnail': 'https://i.mycdn.me/videoPreview?id=2776238394107&type=37&idx=11&tkn=F3ejkUFcpuI4DnMRxrDGcH5YcmM&fn=external_8',
            'title': 'Заяц Бусти.mp4',
            'uploader_id': '571368965883',
            'like_count': 0,
            'duration': 10444,
        },
        'skip': 'Site no longer embeds',
    }]

    def _clear_cookies(self, cdn_url):
        # Direct http downloads will fail if CDN cookies are set
        # so we need to reset them after each format extraction
        self.cookiejar.clear(domain='.mycdn.me')
        self.cookiejar.clear(domain=urllib.parse.urlparse(cdn_url).hostname)

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        for x in super()._extract_embed_urls(url, webpage):
            yield smuggle_url(x, {'referrer': url})

    def _real_extract(self, url):
        try:
            return self._extract_desktop(url)
        except ExtractorError as e:
            try:
                return self._extract_mobile(url)
            except ExtractorError:
                # error message of desktop webpage is in English
                raise e

    def _extract_desktop(self, url):
        start_time = int_or_none(urllib.parse.parse_qs(
            urllib.parse.urlparse(url).query).get('fromTime', [None])[0])

        url, smuggled = unsmuggle_url(url, {})
        video_id, is_embed = self._match_valid_url(url).group('id', 'embed')
        mode = 'videoembed' if is_embed else 'video'

        webpage = self._download_webpage(
            f'https://ok.ru/{mode}/{video_id}', video_id,
            note='Downloading desktop webpage',
            headers={'Referer': smuggled['referrer']} if smuggled.get('referrer') else {})

        error = self._search_regex(
            r'[^>]+class="vp_video_stub_txt"[^>]*>([^<]+)<',
            webpage, 'error', default=None)
        # Direct link from boosty
        if (error == 'The author of this video has not been found or is blocked'
                and not smuggled.get('referrer') and mode == 'videoembed'):
            return self._extract_desktop(smuggle_url(url, {'referrer': 'https://boosty.to'}))
        elif error:
            raise ExtractorError(error, expected=True)

        player = self._parse_json(
            unescapeHTML(self._search_regex(
                rf'data-options=(?P<quote>["\'])(?P<player>{{.+?{video_id}.+?}})(?P=quote)',
                webpage, 'player', group='player')),
            video_id)

        # embedded external player
        if player.get('isExternalPlayer') and player.get('url'):
            return self.url_result(player['url'])

        flashvars = player['flashvars']

        metadata = flashvars.get('metadata')
        if metadata:
            metadata = self._parse_json(metadata, video_id)
        else:
            data = {}
            st_location = flashvars.get('location')
            if st_location:
                data['st.location'] = st_location
            metadata = self._download_json(
                urllib.parse.unquote(flashvars['metadataUrl']),
                video_id, 'Downloading metadata JSON',
                data=urlencode_postdata(data))

        movie = metadata['movie']

        # Some embedded videos may not contain title in movie dict (e.g.
        # http://ok.ru/video/62036049272859-0) thus we allow missing title
        # here and it's going to be extracted later by an extractor that
        # will process the actual embed.
        provider = metadata.get('provider')
        title = movie['title'] if provider == 'UPLOADED_ODKL' else movie.get('title')

        thumbnail = movie.get('poster')
        duration = int_or_none(movie.get('duration'))

        author = metadata.get('author', {})
        uploader_id = author.get('id')
        uploader = author.get('name')

        upload_date = unified_strdate(self._html_search_meta(
            'ya:ovs:upload_date', webpage, 'upload date', default=None))

        age_limit = None
        adult = self._html_search_meta(
            'ya:ovs:adult', webpage, 'age limit', default=None)
        if adult:
            age_limit = 18 if adult == 'true' else 0

        like_count = int_or_none(metadata.get('likeCount'))

        subtitles = {}
        for sub in traverse_obj(metadata, ('movie', 'subtitleTracks', ...), expected_type=dict):
            sub_url = sub.get('url')
            if not sub_url:
                continue
            subtitles.setdefault(sub.get('language') or 'en', []).append({
                'url': sub_url,
                'ext': 'vtt',
            })

        info = {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'upload_date': upload_date,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'like_count': like_count,
            'age_limit': age_limit,
            'start_time': start_time,
            'subtitles': subtitles,
        }

        # pladform
        if provider == 'OPEN_GRAPH':
            info.update({
                '_type': 'url_transparent',
                'url': movie['contentId'],
            })
            return info

        if provider == 'USER_YOUTUBE':
            info.update({
                '_type': 'url_transparent',
                'url': movie['contentId'],
            })
            return info

        assert title
        if provider == 'LIVE_TV_APP':
            info['title'] = title

        quality = qualities(('4', '0', '1', '2', '3', '5', '6', '7'))

        formats = [{
            'url': f['url'],
            'ext': 'mp4',
            'format_id': f.get('name'),
        } for f in traverse_obj(metadata, ('videos', lambda _, v: url_or_none(v['url'])))]

        m3u8_url = traverse_obj(metadata, 'hlsManifestUrl', 'ondemandHls')
        if m3u8_url:
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', 'm3u8_native',
                m3u8_id='hls', fatal=False))
            self._clear_cookies(m3u8_url)

        for mpd_id, mpd_key in [('dash', 'ondemandDash'), ('webm', 'metadataWebmUrl')]:
            mpd_url = metadata.get(mpd_key)
            if mpd_url:
                formats.extend(self._extract_mpd_formats(
                    mpd_url, video_id, mpd_id=mpd_id, fatal=False))
                self._clear_cookies(mpd_url)

        dash_manifest = metadata.get('metadataEmbedded')
        if dash_manifest:
            formats.extend(self._parse_mpd_formats(
                compat_etree_fromstring(dash_manifest), 'mpd'))

        for fmt in formats:
            fmt_type = self._search_regex(
                r'\btype[/=](\d)', fmt['url'],
                'format type', default=None)
            if fmt_type:
                fmt['quality'] = quality(fmt_type)

        # Live formats
        m3u8_url = metadata.get('hlsMasterPlaylistUrl')
        if m3u8_url:
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', m3u8_id='hls', fatal=False))
            self._clear_cookies(m3u8_url)
        rtmp_url = metadata.get('rtmpUrl')
        if rtmp_url:
            formats.append({
                'url': rtmp_url,
                'format_id': 'rtmp',
                'ext': 'flv',
            })

        if not formats:
            payment_info = metadata.get('paymentInfo')
            if payment_info:
                self.raise_no_formats('This video is paid, subscribe to download it', expected=True)

        info['formats'] = formats
        return info

    def _extract_mobile(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            f'http://m.ok.ru/video/{video_id}', video_id,
            note='Downloading mobile webpage')

        error = self._search_regex(
            r'видео</a>\s*<div\s+class="empty">(.+?)</div>',
            webpage, 'error', default=None)
        if error:
            raise ExtractorError(error, expected=True)

        json_data = self._search_regex(
            r'data-video="(.+?)"', webpage, 'json data')
        json_data = self._parse_json(unescapeHTML(json_data), video_id) or {}

        redirect_url = self._request_webpage(HEADRequest(
            json_data['videoSrc']), video_id, 'Requesting download URL').url
        self._clear_cookies(redirect_url)

        return {
            'id': video_id,
            'title': json_data.get('videoName'),
            'duration': float_or_none(json_data.get('videoDuration'), scale=1000),
            'thumbnail': json_data.get('videoPosterSrc'),
            'formats': [{
                'format_id': 'mobile',
                'url': redirect_url,
                'ext': 'mp4',
            }],
        }
