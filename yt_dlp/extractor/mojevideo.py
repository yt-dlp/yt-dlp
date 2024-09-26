from .common import InfoExtractor
from ..utils import js_to_json, remove_end, update_url_query


class MojevideoIE(InfoExtractor):
    IE_DESC = 'mojevideo.sk'
    _VALID_URL = r'https?://(?:www\.)?mojevideo\.sk/video/(?P<id>\w+)/(?P<display_id>[\w()]+?)\.html'

    _TESTS = [{
        'url': 'https://www.mojevideo.sk/video/3d17c/chlapci_dobetonovali_sme_mame_hotovo.html',
        'md5': '384a4628bd2bbd261c5206cf77c38c17',
        'info_dict': {
            'id': '3d17c',
            'ext': 'mp4',
            'title': 'Chlapci dobetónovali sme, máme hotovo!',
            'display_id': 'chlapci_dobetonovali_sme_mame_hotovo',
            'description': 'md5:a0822126044050d304a9ef58c92ddb34',
            'thumbnail': 'https://fs5.mojevideo.sk/imgfb/250236.jpg',
            'duration': 21.0,
            'upload_date': '20230919',
            'timestamp': 1695129706,
            'like_count': int,
            'dislike_count': int,
            'view_count': int,
            'comment_count': int,
        },
    }, {
        # 720p
        'url': 'https://www.mojevideo.sk/video/14677/den_blbec.html',
        'md5': '517c3e111c53a67d10b429c1f344ba2f',
        'info_dict': {
            'id': '14677',
            'ext': 'mp4',
            'title': 'Deň blbec?',
            'display_id': 'den_blbec',
            'description': 'I maličkosť vám môže zmeniť celý deň. Nikdy nezahadzujte žuvačky na zem!',
            'thumbnail': 'https://fs5.mojevideo.sk/imgfb/83575.jpg',
            'duration': 100.0,
            'upload_date': '20120515',
            'timestamp': 1337076481,
            'like_count': int,
            'dislike_count': int,
            'view_count': int,
            'comment_count': int,
        },
    }, {
        # 1080p
        'url': 'https://www.mojevideo.sk/video/2feb2/band_maid_onset_(instrumental)_live_zepp_tokyo_(full_hd).html',
        'md5': '64599a23d3ac31cf2fe069e4353d8162',
        'info_dict': {
            'id': '2feb2',
            'ext': 'mp4',
            'title': 'BAND-MAID - onset (Instrumental) Live - Zepp Tokyo (Full HD)',
            'display_id': 'band_maid_onset_(instrumental)_live_zepp_tokyo_(full_hd)',
            'description': 'Výborná inštrumentálna skladba od skupiny BAND-MAID.',
            'thumbnail': 'https://fs5.mojevideo.sk/imgfb/196274.jpg',
            'duration': 240.0,
            'upload_date': '20190708',
            'timestamp': 1562576592,
            'like_count': int,
            'dislike_count': int,
            'view_count': int,
            'comment_count': int,
        },
    }, {
        # 720p
        'url': 'https://www.mojevideo.sk/video/358c8/dva_nissany_skyline_strielaju_v_londyne.html',
        'only_matching': True,
    }, {
        # 720p
        'url': 'https://www.mojevideo.sk/video/2455d/gopro_hero4_session_nova_sportova_vodotesna_kamera.html',
        'only_matching': True,
    }, {
        # 1080p
        'url': 'https://www.mojevideo.sk/video/352ee/amd_rx_6800_xt_vs_nvidia_rtx_3080_(test_v_9_hrach).html',
        'only_matching': True,
    }, {
        # 1080p
        'url': 'https://www.mojevideo.sk/video/2cbeb/trailer_z_avengers_infinity_war.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).groups()
        webpage = self._download_webpage(url, video_id)

        video_id_dec = self._search_regex(
            r'\bvId\s*=\s*(\d+)', webpage, 'video id', fatal=False) or str(int(video_id, 16))
        video_exp = self._search_regex(r'\bvEx\s*=\s*["\'](\d+)', webpage, 'video expiry')
        video_hashes = self._search_json(
            r'\bvHash\s*=', webpage, 'video hashes', video_id,
            contains_pattern=r'\[(?s:.+)\]', transform_source=js_to_json)

        formats = []
        for video_hash, (suffix, quality, format_note) in zip(video_hashes, [
            ('', 1, 'normálna kvalita'),
            ('_lq', 0, 'nízka kvalita'),
            ('_hd', 2, 'HD-720p'),
            ('_fhd', 3, 'FULL HD-1080p'),
            ('_2k', 4, '2K-1440p'),
        ]):
            formats.append({
                'format_id': f'mp4-{quality}',
                'quality': quality,
                'format_note': format_note,
                'url': update_url_query(
                    f'https://cache01.mojevideo.sk/securevideos69/{video_id_dec}{suffix}.mp4', {
                        'md5': video_hash,
                        'expires': video_exp,
                    }),
            })

        return {
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            'title': (self._og_search_title(webpage, default=None)
                      or remove_end(self._html_extract_title(webpage, 'title'), ' - Mojevideo')),
            'description': self._og_search_description(webpage),
            **self._search_json_ld(webpage, video_id, default={}),
        }
