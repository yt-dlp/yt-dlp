from .common import InfoExtractor
from ..utils import int_or_none, traverse_obj, url_or_none


class IdolPlusIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?idolplus\.com/z[us]/contents?.+albumId=(?P<id>[A-Z0-9]+)'
    _TESTS = [
        {
            'url': 'https://idolplus.com/zs/contents?albumId=M012077298PPV00',
            'md5': '2ace3f4661c943a2f7e79f0b88cea1e7',
            'info_dict': {
                'id': 'M012077298PPV00',
                'ext': 'mp4',
                'title': '[MultiCam] Aegyo on Top of Aegyo (IZ*ONE EATING TRIP)',
                'release_date': '20200707',
                'formats': 'count:65',
            },
            'params': {
                'format': '532-KIM_MINJU',
            },
        },
        {
            'url': 'https://idolplus.com/zs/contents?albumId=M01232H058PPV00&catId=E9TX5',
            'info_dict': {
                'id': 'M01232H058PPV00',
                'ext': 'mp4',
                'title': 'YENA (CIRCLE CHART MUSIC AWARDS 2022 RED CARPET)',
                'release_date': '20230218',
                'formats': 'count:5',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # live stream
            'url': 'https://idolplus.com/zu/contents?albumId=M012323174PPV00',
            'info_dict': {
                'id': 'M012323174PPV00',
                'ext': 'mp4',
                'title': 'Hanteo Music Awards 2022 DAY2',
                'release_date': '20230211',
                'formats': 'count:5',
            },
            'params': {
                'skip_download': True,
            },
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data_list = traverse_obj(
            self._download_json(
                'https://idolplus.com/api/zs/viewdata/ruleset/build',
                video_id=video_id,
                query={
                    'rulesetId': 'contents',
                    'albumId': video_id,
                    'distribute': 'PRD',
                    'loggedIn': 'false',
                    'region': 'zs',
                    'countryGroup': '00010',
                    'lang': 'en',
                    'saId': '999999999998',
                },
                headers={'App_type': 'web', 'Country_Code': 'KR'}),
            ('data', 'viewData')) or []

        player_data = {}
        while len(data_list) > 0:
            player_data = data_list.pop()
            try:
                if player_data.get('type', '') == 'player':
                    break
                data_list += player_data.get('dataList', [])
            except AttributeError:
                pass
        if not (player_data and player_data.get('vodPlayerList')):
            self.raise_no_formats('No video content found')

        video_url = traverse_obj(
            player_data,
            ('vodPlayerList', 'vodProfile', 0, 'vodServer', 0, 'video_url'),
            expected_type=url_or_none)
        if not video_url:
            self.raise_no_formats('No video url found')

        formats = self._extract_m3u8_formats(
            traverse_obj(player_data, ('vodPlayerList', 'vodProfile', 0, 'vodServer', 0, 'video_url')),
            video_id=video_id)

        subtitles = {}
        for caption in traverse_obj(player_data, ('vodPlayerList', 'caption')) or []:
            subtitles.setdefault(caption.get('lang'), []).append({
                'url': caption.get('smi_url'), 'ext': 'vtt'})

        # Add member multicams as alternative formats
        has_cuesheet = (traverse_obj(player_data, ('detail', 'has_cuesheet')) or '') == 'Y'
        is_omni_member = (traverse_obj(player_data, ('detail', 'is_omni_member')) or '') == 'Y'
        if has_cuesheet and is_omni_member:
            cuesheet = traverse_obj(
                self._download_json(
                    'https://idolplus.com/gapi/contents/v1.0/content/cuesheet',
                    video_id=video_id,
                    query={
                        'ALBUM_ID': video_id,
                        'COUNTRY_GRP': '00010',
                        'LANG': 'en',
                        'SA_ID': '999999999998',
                        'COUNTRY_CODE': 'KR',
                    },
                    headers={'App_type': 'web', 'Country_Code': 'KR'},
                    note='Downloading JSON metadata for member multicams'),
                ('data', 'cuesheet_item', 0))

            omni_views = cuesheet.get('omni_view', [])
            members = [m for m in cuesheet.get('members', [])
                       if int_or_none(m.get('omni_view_index'))]
            for member in members:
                member_video_url = traverse_obj(
                    omni_views[member['omni_view_index'] - 1], ('cdn_url', 0, 'url'),
                    expected_type=url_or_none)
                if not member_video_url:
                    continue
                member_formats = self._extract_m3u8_formats(
                    member_video_url, video_id=video_id,
                    note=f'Downloading m3u8 information for multicam {member["name"]}')
                for mf in member_formats:
                    mf['format_id'] = f'{mf["format_id"]}-{member["name"].replace(" ", "_")}'
                    formats.append(mf)

        return {
            'id': video_id,
            'title': traverse_obj(player_data, ('detail', 'albumName')),
            'formats': formats,
            'subtitles': subtitles,
            'release_date': traverse_obj(player_data, ('detail', 'broadcastDate')),
        }
