from .kaltura import KalturaIE


class UnitedNationWebTVExtractorIE(KalturaIE):
    _VALID_URL = r'https?://webtv.un.org/(ar|zh|en|fr|ru|es)/asset/\w+/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://webtv.un.org/en/asset/k1o/k1o7stmi6p',
        'md5': 'b2f8b3030063298ae841b4b7ddc01477',
        'info_dict': {
            'id': '1_o7stmi6p',
            'ext': 'mp4',
            'title': 'António Guterres (Secretary-General) on Israel and Iran - Security Council, 9939th meeting',
            'thumbnail': 'http://cfvod.kaltura.com/p/2503451/sp/250345100/thumbnail/entry_id/1_o7stmi6p/version/100021',
            'uploader_id': 'evgeniia.alisova@un.org',
            'upload_date': '20250620',
            'timestamp': 1750430976,
            'duration': 234,
            'view_count': int,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        partner_id = self._html_search_regex(
            r'partnerId:\s*(\w+)',
            webpage,
            'partner_id',
        )
        entry_id = self._html_search_regex(
            r'const\s+kentryID\s*=\s*["\'](\w+)["\'];',
            webpage,
            'kentry_id',
        )
        kaltura_api_response = self._get_video_info(entry_id, partner_id)

        try:
            kaltura_url = kaltura_api_response[1].get('dataUrl', None)
        except IndexError:
            return self.url_result(
                f'kaltura:{partner_id}:{entry_id}',
                KalturaIE.ie_key(),
            )

        kaltura_id = self._search_regex(
            r'http://cdnapi.kaltura.com/p/\w+/sp/\w+/playManifest/entryId/(\w+)/format/url/protocol/http',
            kaltura_url,
            'kaltura_id',
        )

        return self.url_result(
            f'kaltura:{partner_id}:{kaltura_id}',
            KalturaIE.ie_key(),
        )
