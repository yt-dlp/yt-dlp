from .common import InfoExtractor
from ..utils import traverse_obj, try_call, url_or_none


class IdolPlusIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?idolplus\.com/z[us]/(?:concert/|contents/?\?(?:[^#]+&)?albumId=)(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://idolplus.com/zs/contents?albumId=M012077298PPV00',
        'md5': '2ace3f4661c943a2f7e79f0b88cea1e7',
        'info_dict': {
            'id': 'M012077298PPV00',
            'ext': 'mp4',
            'title': '[MultiCam] Aegyo on Top of Aegyo (IZ*ONE EATING TRIP)',
            'release_date': '20200707',
            'formats': 'count:65',
        },
        'params': {'format': '532-KIM_MINJU'},
    }, {
        'url': 'https://idolplus.com/zs/contents?albumId=M01232H058PPV00&catId=E9TX5',
        'info_dict': {
            'id': 'M01232H058PPV00',
            'ext': 'mp4',
            'title': 'YENA (CIRCLE CHART MUSIC AWARDS 2022 RED CARPET)',
            'release_date': '20230218',
            'formats': 'count:5',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # live stream
        'url': 'https://idolplus.com/zu/contents?albumId=M012323174PPV00',
        'info_dict': {
            'id': 'M012323174PPV00',
            'ext': 'mp4',
            'title': 'Hanteo Music Awards 2022 DAY2',
            'release_date': '20230211',
            'formats': 'count:5',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://idolplus.com/zs/concert/M012323039PPV00',
        'info_dict': {
            'id': 'M012323039PPV00',
            'ext': 'mp4',
            'title': 'CIRCLE CHART MUSIC AWARDS 2022',
            'release_date': '20230218',
            'formats': 'count:5',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data_list = traverse_obj(self._download_json(
            'https://idolplus.com/api/zs/viewdata/ruleset/build', video_id,
            headers={'App_type': 'web', 'Country_Code': 'KR'}, query={
                'rulesetId': 'contents',
                'albumId': video_id,
                'distribute': 'PRD',
                'loggedIn': 'false',
                'region': 'zs',
                'countryGroup': '00010',
                'lang': 'en',
                'saId': '999999999998',
            }), ('data', 'viewData', ...))

        player_data = {}
        while data_list:
            player_data = data_list.pop()
            if traverse_obj(player_data, 'type') == 'player':
                break
            elif traverse_obj(player_data, ('dataList', ...)):
                data_list += player_data['dataList']

        formats = self._extract_m3u8_formats(traverse_obj(player_data, (
            'vodPlayerList', 'vodProfile', 0, 'vodServer', 0, 'video_url', {url_or_none})), video_id)

        subtitles = {}
        for caption in traverse_obj(player_data, ('vodPlayerList', 'caption')) or []:
            subtitles.setdefault(caption.get('lang') or 'und', []).append({
                'url': caption.get('smi_url'),
                'ext': 'vtt',
            })

        # Add member multicams as alternative formats
        if (traverse_obj(player_data, ('detail', 'has_cuesheet')) == 'Y'
                and traverse_obj(player_data, ('detail', 'is_omni_member')) == 'Y'):
            cuesheet = traverse_obj(self._download_json(
                'https://idolplus.com/gapi/contents/v1.0/content/cuesheet', video_id,
                'Downloading JSON metadata for member multicams',
                headers={'App_type': 'web', 'Country_Code': 'KR'}, query={
                    'ALBUM_ID': video_id,
                    'COUNTRY_GRP': '00010',
                    'LANG': 'en',
                    'SA_ID': '999999999998',
                    'COUNTRY_CODE': 'KR',
                }), ('data', 'cuesheet_item', 0))

            for member in traverse_obj(cuesheet, ('members', ...)):
                index = try_call(lambda: int(member['omni_view_index']) - 1)
                member_video_url = traverse_obj(cuesheet, ('omni_view', index, 'cdn_url', 0, 'url', {url_or_none}))
                if not member_video_url:
                    continue
                member_formats = self._extract_m3u8_formats(
                    member_video_url, video_id, note=f'Downloading m3u8 for multicam {member["name"]}')
                for mf in member_formats:
                    mf['format_id'] = f'{mf["format_id"]}-{member["name"].replace(" ", "_")}'
                formats.extend(member_formats)

        return {
            'id': video_id,
            'title': traverse_obj(player_data, ('detail', 'albumName')),
            'formats': formats,
            'subtitles': subtitles,
            'release_date': traverse_obj(player_data, ('detail', 'broadcastDate')),
        }
