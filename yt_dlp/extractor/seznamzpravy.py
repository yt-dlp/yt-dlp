from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urllib_parse_urlparse,
)
from ..utils import (
    urljoin,
    int_or_none,
    parse_codecs,
    parse_qs,
    try_get,
)


def _raw_id(src_url):
    return compat_urllib_parse_urlparse(src_url).path.split('/')[-1]


class SeznamZpravyIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?seznamzpravy\.cz/iframe/player\?.*\bsrc='
    _EMBED_REGEX = [r'<iframe\b[^>]+\bsrc=(["\'])(?P<url>(?:https?:)?//(?:www\.)?seznamzpravy\.cz/iframe/player\?.*?)\1']
    _TESTS = [{
        'url': 'https://www.seznamzpravy.cz/iframe/player?duration=241&serviceSlug=zpravy&src=https%3A%2F%2Fv39-a.sdn.szn.cz%2Fv_39%2Fvmd%2F5999c902ea707c67d8e267a9%3Ffl%3Dmdk%2C432f65a0%7C&itemType=video&autoPlay=false&title=Sv%C4%9Bt%20bez%20obalu%3A%20%C4%8Ce%C5%A1t%C3%AD%20voj%C3%A1ci%20na%20mis%C3%ADch%20(kr%C3%A1tk%C3%A1%20verze)&series=Sv%C4%9Bt%20bez%20obalu&serviceName=Seznam%20Zpr%C3%A1vy&poster=%2F%2Fd39-a.sdn.szn.cz%2Fd_39%2Fc_img_F_I%2FR5puJ.jpeg%3Ffl%3Dcro%2C0%2C0%2C1920%2C1080%7Cres%2C1200%2C%2C1%7Cjpg%2C80%2C%2C1&width=1920&height=1080&cutFrom=0&cutTo=0&splVersion=VOD&contentId=170889&contextId=35990&showAdvert=true&collocation=&autoplayPossible=true&embed=&isVideoTooShortForPreroll=false&isVideoTooLongForPostroll=true&videoCommentOpKey=&videoCommentId=&version=4.0.76&dotService=zpravy&gemiusPrismIdentifier=bVc1ZIb_Qax4W2v5xOPGpMeCP31kFfrTzj0SqPTLh_b.Z7&zoneIdPreroll=seznam.pack.videospot&skipOffsetPreroll=5&sectionPrefixPreroll=%2Fzpravy',
        'info_dict': {
            'id': '170889',
            'ext': 'mp4',
            'title': 'Svět bez obalu: Čeští vojáci na misích (krátká verze)',
            'thumbnail': r're:^https?://.*\.jpe?g',
            'duration': 241,
            'series': 'Svět bez obalu',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # with Location key
        'url': 'https://www.seznamzpravy.cz/iframe/player?duration=null&serviceSlug=zpravy&src=https%3A%2F%2Flive-a.sdn.szn.cz%2Fv_39%2F59e468fe454f8472a96af9fa%3Ffl%3Dmdk%2C5c1e2840%7C&itemType=livevod&autoPlay=false&title=P%C5%99edseda%20KDU-%C4%8CSL%20Pavel%20B%C4%9Blobr%C3%A1dek%20ve%20volebn%C3%AD%20V%C3%BDzv%C4%9B%20Seznamu&series=V%C3%BDzva&serviceName=Seznam%20Zpr%C3%A1vy&poster=%2F%2Fd39-a.sdn.szn.cz%2Fd_39%2Fc_img_G_J%2FjTBCs.jpeg%3Ffl%3Dcro%2C0%2C0%2C1280%2C720%7Cres%2C1200%2C%2C1%7Cjpg%2C80%2C%2C1&width=16&height=9&cutFrom=0&cutTo=0&splVersion=VOD&contentId=185688&contextId=38489&showAdvert=true&collocation=&hideFullScreen=false&hideSubtitles=false&embed=&isVideoTooShortForPreroll=false&isVideoTooShortForPreroll2=false&isVideoTooLongForPostroll=false&fakePostrollZoneID=seznam.clanky.zpravy.preroll&fakePrerollZoneID=seznam.clanky.zpravy.preroll&videoCommentId=&trim=default_16x9&noPrerollVideoLength=30&noPreroll2VideoLength=undefined&noMidrollVideoLength=0&noPostrollVideoLength=999999&autoplayPossible=true&version=5.0.41&dotService=zpravy&gemiusPrismIdentifier=zD3g7byfW5ekpXmxTVLaq5Srjw5i4hsYo0HY1aBwIe..27&zoneIdPreroll=seznam.pack.videospot&skipOffsetPreroll=5&sectionPrefixPreroll=%2Fzpravy%2Fvyzva&zoneIdPostroll=seznam.pack.videospot&skipOffsetPostroll=5&sectionPrefixPostroll=%2Fzpravy%2Fvyzva&regression=false',
        'info_dict': {
            'id': '185688',
            'ext': 'mp4',
            'title': 'Předseda KDU-ČSL Pavel Bělobrádek ve volební Výzvě Seznamu',
            'thumbnail': r're:^https?://.*\.jpe?g',
            'series': 'Výzva',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _extract_sdn_formats(self, sdn_url, video_id):
        sdn_data = self._download_json(sdn_url, video_id)

        if sdn_data.get('Location'):
            sdn_url = sdn_data['Location']
            sdn_data = self._download_json(sdn_url, video_id)

        formats = []
        mp4_formats = try_get(sdn_data, lambda x: x['data']['mp4'], dict) or {}
        for format_id, format_data in mp4_formats.items():
            relative_url = format_data.get('url')
            if not relative_url:
                continue

            try:
                width, height = format_data.get('resolution')
            except (TypeError, ValueError):
                width, height = None, None

            f = {
                'url': urljoin(sdn_url, relative_url),
                'format_id': 'http-%s' % format_id,
                'tbr': int_or_none(format_data.get('bandwidth'), scale=1000),
                'width': int_or_none(width),
                'height': int_or_none(height),
            }
            f.update(parse_codecs(format_data.get('codec')))
            formats.append(f)

        pls = sdn_data.get('pls', {})

        def get_url(format_id):
            return try_get(pls, lambda x: x[format_id]['url'], compat_str)

        dash_rel_url = get_url('dash')
        if dash_rel_url:
            formats.extend(self._extract_mpd_formats(
                urljoin(sdn_url, dash_rel_url), video_id, mpd_id='dash',
                fatal=False))

        hls_rel_url = get_url('hls')
        if hls_rel_url:
            formats.extend(self._extract_m3u8_formats(
                urljoin(sdn_url, hls_rel_url), video_id, ext='mp4',
                m3u8_id='hls', fatal=False))

        return formats

    def _real_extract(self, url):
        params = parse_qs(url)

        src = params['src'][0]
        title = params['title'][0]
        video_id = params.get('contentId', [_raw_id(src)])[0]
        formats = self._extract_sdn_formats(src + 'spl2,2,VOD', video_id)

        duration = int_or_none(params.get('duration', [None])[0])
        series = params.get('series', [None])[0]
        thumbnail = params.get('poster', [None])[0]

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'series': series,
            'formats': formats,
        }


class SeznamZpravyArticleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:seznam\.cz/zpravy|seznamzpravy\.cz)/clanek/(?:[^/?#&]+)-(?P<id>\d+)'
    _API_URL = 'https://apizpravy.seznam.cz/'

    _TESTS = [{
        # two videos on one page, with SDN URL
        'url': 'https://www.seznamzpravy.cz/clanek/jejich-svet-na-nas-utoci-je-lepsi-branit-se-na-jejich-pisecku-rika-reziser-a-major-v-zaloze-marhoul-35990',
        'info_dict': {
            'id': '35990',
            'title': 'md5:6011c877a36905f28f271fcd8dcdb0f2',
            'description': 'md5:933f7b06fa337a814ba199d3596d27ba',
        },
        'playlist_count': 2,
    }, {
        # video with live stream URL
        'url': 'https://www.seznam.cz/zpravy/clanek/znovu-do-vlady-s-ano-pavel-belobradek-ve-volebnim-specialu-seznamu-38489',
        'info_dict': {
            'id': '38489',
            'title': 'md5:8fa1afdc36fd378cf0eba2b74c5aca60',
            'description': 'md5:428e7926a1a81986ec7eb23078004fb4',
        },
        'playlist_count': 1,
    }]

    def _real_extract(self, url):
        article_id = self._match_id(url)

        webpage = self._download_webpage(url, article_id)

        info = self._search_json_ld(webpage, article_id, default={})

        title = info.get('title') or self._og_search_title(webpage, fatal=False)
        description = info.get('description') or self._og_search_description(webpage)

        return self.playlist_result([
            self.url_result(entry_url, ie=SeznamZpravyIE.ie_key())
            for entry_url in SeznamZpravyIE._extract_embed_urls(url, webpage)],
            article_id, title, description)
