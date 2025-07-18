
from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class LocipoIE(InfoExtractor):
    IE_DESC = 'Locipo (ロキポ) Video/Playlist'

    _VALID_URL = r'https?://locipo\.jp/creative/(?P<creative_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(\?.*list=(?P<playlist_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}))?'

    _TESTS = [
        {
            'url': 'https://locipo.jp/creative/fb5ffeaa-398d-45ce-bb49-0e221b5f94f1',
            'info_dict': {
                'ext': 'mp4',
                'id': 'fb5ffeaa-398d-45ce-bb49-0e221b5f94f1',
                'series': 'リアルカレカノ',
                'series_id': 'b865b972-99fe-41d5-a72c-8ed5c42132bd',
                'duration': 3622,
                'title': 'リアルカレカノ#4 ～伊達さゆりと勉強しよっ？～',
                'description': 'TVアニメ「ラブライブ！スーパースター!!」澁谷かのん役などで\n活躍中の人気声優「伊達さゆり」さんと、恋人気分が味わえるコンテンツが登場！\n\n全てカレシ・カノジョの1人称目線で撮影しているため\nこの動画でしか味わえない、ドキドキ感が満載！\n一緒に勉強したり…ご飯を食べたり…相談に乗ってもらったり…\nいろんなシチュエーションを楽しんでください！\n',
                'uploader': 'thk',
                'uploader_id': '1',
                'thumbnail': 'https://dophkbxgy39ig.cloudfront.net/store/creatives/99190/large-51fec5367d73fc55dc364250885dfb2e.png',
                'timestamp': 1711789200,
                'modified_timestamp': 1725415481,
                'upload_date': '20240330',
                'modified_date': '20240904',
            },
        },
        {
            'url': 'https://locipo.jp/creative/8be557b9-5a97-4092-825e-5cb8c72b36ab?list=3058b313-3a7c-4d64-b067-d3d870b4b17d&noautoplay=&redirect=true',
            'info_dict': {
                'id': '3058b313-3a7c-4d64-b067-d3d870b4b17d',
                'title': '達眼の戦士s ',
                'description': '今注目のeスポーツで活躍するプロに密着!\n勝利への強いこだわりに迫るドキュメントバラエティ',
            },
            'playlist_count': 2,
        },
        {
            'url': 'https://locipo.jp/creative/867176a9-cfd8-4807-b5f0-e41a549ba588?list=07738b35-6ce6-48b6-92f7-00167a95bb12',
            'info_dict': {
                'id': '07738b35-6ce6-48b6-92f7-00167a95bb12',
                'title': 'チャント！特集',
            },
            'playlist_mincount': 30,
        },
    ]

    def _get_creative_metadata(self, creative_data):
        return traverse_obj(creative_data, {
            'id': ('id', {str}),
            'duration': ('video', 'duration', {int_or_none}),
            'title': ('title', {str}),
            'description': ('description', {str}),
            'uploader': ('station_cd', {str}),
            'uploader_id': ('station_id', {str}),
            'thumbnail': ('thumb', {url_or_none}),
            'timestamp': ('broadcast_started_at', {parse_iso8601}),
            'modified_timestamp': ('updated_at', {parse_iso8601}),
        })

    def _real_extract(self, url: str):
        creative_id, playlist_id = self._match_valid_url(url).group('creative_id', 'playlist_id')  # type: ignore

        if not playlist_id:
            creative_data = self._download_json(
                f'https://api.locipo.jp/api/v1/creatives/{creative_id}',
                creative_id,
                headers={
                    'accept': 'application/json, text/plain, */*',
                    'origin': 'https://locipo.jp',
                    'referer': 'https://locipo.jp/',
                },
            )

            return {
                'formats': self._extract_m3u8_formats(m3u8_url=traverse_obj(creative_data, ('video', 'hls', {str})), video_id=creative_id),  # type: ignore
                'id': creative_id,
                **self._get_creative_metadata(creative_data),  # type: ignore
                **traverse_obj(
                    creative_data,
                    {
                        'series': ('playlist', 'title', {str}),
                        'series_id': ('playlist', 'id', {str}),
                    },
                ),  # type: ignore
            }

        playlist_data = self._download_json(
            f'https://api.locipo.jp/api/v1/playlists/{playlist_id}',
            playlist_id,
            headers={
                'accept': 'application/json, text/plain, */*',
                'origin': 'https://locipo.jp',
                'referer': 'https://locipo.jp/',
            },
        )

        # NOTE: This API can return up to 1000 videos. Since there doesn't seem to be any playlist with more than 1000 items at the moment, pagination is currently not implemented.
        playlist_creatives_data = self._download_json(
            f'https://api.locipo.jp/api/v1/playlists/{playlist_id}/creatives',
            None,
            headers={
                'accept': 'application/json, text/plain, */*',
                'origin': 'https://locipo.jp',
                'referer': 'https://locipo.jp/',
            },
        )

        entries = []
        for creative in playlist_creatives_data.get('items', []):  # type: ignore
            entries.append(
                {
                    'formats': self._extract_m3u8_formats(
                        m3u8_url=traverse_obj(creative, ('video', 'hls', {str})),  # type: ignore
                        video_id=traverse_obj(creative, ('id', {str})),  # type: ignore
                    ),
                    **self._get_creative_metadata(creative),  # type: ignore
                    **traverse_obj(
                        playlist_data,
                        {
                            'series': ('title', {str}),
                            'series_id': ('id', {str}),
                        },
                    ),  # type: ignore
                },
            )

        return self.playlist_result(
            entries=entries,
            playlist_id=playlist_id,
            playlist_title=traverse_obj(playlist_data, ('title', {str})),  # type: ignore
            playlist_description=traverse_obj(playlist_data, ('description', {str_or_none})),  # type: ignore
        )
