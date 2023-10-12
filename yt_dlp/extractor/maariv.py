from yt_dlp.extractor.common import InfoExtractor
import re

class MaarivIE(InfoExtractor):
    IE_NAME = 'maariv.co.il'
    _VALID_URL = r'(https?://)?(www\.)?(m\.)?maariv\.co\.il(?:/[^/]+)*/Article-(?P<id>\d{7})'
    _TESTS = [
        {
            'url': 'https://www.maariv.co.il/news/law/Article-1044008',
            'info_dict': {
                'id': '1044008',
                'title': '.*',
            },
        }
    ]

    @staticmethod
    def extract_resolution(url):
        pattern = r'(\d{2,4}x\d{2,4})\.mp4$'
        match = re.search(pattern, url)
        return match.group(1) if match else None

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # Find the correct iframes
        video_urls = re.findall(r'<iframe .*?poster="(.*?)" src="(.*?)"', webpage)
        video_info_list = []

        for thumbnail, src in video_urls:
            media_param = re.search(r'media=(\d+)', src).group(1)
            info_url = f"https://dal.walla.co.il/media/{media_param}?origin=player.maariv.co.il"
            info_json = self._download_json(info_url, video_id)
            data = info_json['data']
            main_video_to_download_filename = data['video']['file_name']
            main_video_to_download_url = data['video']['url']
            duration_seconds = int(data['video']['duration'])

            format_list = [
                {
                    'format_id': '0',
                    'url': main_video_to_download_url,
                    'resolution': 'Main Video',
                }
            ]

            for format_id, stream_url_object in enumerate(data['video']['stream_urls'], start=1):
                stream_url = stream_url_object['stream_url']
                resolution = self.extract_resolution(stream_url)
                format_info = {
                    'format_id': str(format_id),
                    'url': stream_url,
                    'resolution': resolution,
                }
                format_list.append(format_info)

            video_info = {
                'id': media_param,
                'title': main_video_to_download_filename,
                'thumbnail': thumbnail,
                'duration': duration_seconds,
                'formats': format_list,
            }

            video_info_list.append(video_info)

        if len(video_info_list) == 1:
            return video_info_list[0]
        else:
            # If there are multiple videos, create a playlist
            return self.playlist_result(video_info_list, video_id)
