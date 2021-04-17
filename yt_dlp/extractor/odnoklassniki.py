# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_etree_fromstring,
    compat_parse_qs,
    compat_urllib_parse_unquote,
    compat_urllib_parse_urlparse,
)
from ..utils import (
    ExtractorError,
    unified_strdate,
    int_or_none,
    qualities,
    unescapeHTML,
    urlencode_postdata,
)


class OdnoklassnikiIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                https?://
                    (?:(?:www|m|mobile)\.)?
                    (?:odnoklassniki|ok)\.ru/
                    (?:
                        video(?:embed)?/|
                        web-api/video/moviePlayer/|
                        live/|
                        dk\?.*?st\.mvId=
                    )
                    (?P<id>[\d-]+)
                '''
    _TESTS = [{
        # metadata in JSON
        'url': 'http://ok.ru/video/20079905452',
        'md5': '0b62089b479e06681abaaca9d204f152',
        'info_dict': {
            'id': '20079905452',
            'ext': 'mp4',
            'title': 'Культура меняет нас (прекрасный ролик!))',
            'duration': 100,
            'upload_date': '20141207',
            'uploader_id': '330537914540',
            'uploader': 'Виталий Добровольский',
            'like_count': int,
            'age_limit': 0,
        },
    }, {
        # metadataUrl
        'url': 'http://ok.ru/video/63567059965189-0?fromTime=5',
        'md5': '6ff470ea2dd51d5d18c295a355b0b6bc',
        'info_dict': {
            'id': '63567059965189-0',
            'ext': 'mp4',
            'title': 'Девушка без комплексов ...',
            'duration': 191,
            'upload_date': '20150518',
            'uploader_id': '534380003155',
            'uploader': '☭ Андрей Мещанинов ☭',
            'like_count': int,
            'age_limit': 0,
            'start_time': 5,
        },
    }, {
        # YouTube embed (metadataUrl, provider == USER_YOUTUBE)
        'url': 'http://ok.ru/video/64211978996595-1',
        'md5': '2f206894ffb5dbfcce2c5a14b909eea5',
        'info_dict': {
            'id': 'V_VztHT5BzY',
            'ext': 'mp4',
            'title': 'Космическая среда от 26 августа 2015',
            'description': 'md5:848eb8b85e5e3471a3a803dae1343ed0',
            'duration': 440,
            'upload_date': '20150826',
            'uploader_id': 'tvroscosmos',
            'uploader': 'Телестудия Роскосмоса',
            'age_limit': 0,
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
    }]

    @staticmethod
    def _extract_url(webpage):
        mobj = re.search(
            r'<iframe[^>]+src=(["\'])(?P<url>(?:https?:)?//(?:odnoklassniki|ok)\.ru/videoembed/.+?)\1', webpage)
        if mobj:
            return mobj.group('url')

    def _real_extract(self, url):
        start_time = int_or_none(compat_parse_qs(
            compat_urllib_parse_urlparse(url).query).get('fromTime', [None])[0])

        video_id = self._match_id(url)

        webpage = self._download_webpage(
            'http://ok.ru/video/%s' % video_id, video_id)

        error = self._search_regex(
            r'[^>]+class="vp_video_stub_txt"[^>]*>([^<]+)<',
            webpage, 'error', default=None)
        if error:
            raise ExtractorError(error, expected=True)

        player = self._parse_json(
            unescapeHTML(self._search_regex(
                r'data-options=(?P<quote>["\'])(?P<player>{.+?%s.+?})(?P=quote)' % video_id,
                webpage, 'player', group='player')),
            video_id)

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
                compat_urllib_parse_unquote(flashvars['metadataUrl']),
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
        }

        if provider == 'USER_YOUTUBE':
            info.update({
                '_type': 'url_transparent',
                'url': movie['contentId'],
            })
            return info

        assert title
        if provider == 'LIVE_TV_APP':
            info['title'] = self._live_title(title)

        quality = qualities(('4', '0', '1', '2', '3', '5'))

        formats = [{
            'url': f['url'],
            'ext': 'mp4',
            'format_id': f['name'],
        } for f in metadata['videos']]

        m3u8_url = metadata.get('hlsManifestUrl')
        if m3u8_url:
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', 'm3u8_native',
                m3u8_id='hls', fatal=False))

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
                m3u8_url, video_id, 'mp4', entry_protocol='m3u8',
                m3u8_id='hls', fatal=False))
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

        self._sort_formats(formats)

        info['formats'] = formats
        return info
