import json

from .common import InfoExtractor


class ManyVidsIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'(?i)https?://(?:www\.)?manyvids\.com/video/(?P<id>\d+)'
    _TESTS = [{
        # preview video
        'url': 'https://www.manyvids.com/Video/1856601/Horny-Asian-Bunny-Needs-Cock/',
        'info_dict': {
            'id': '1856601',
            'ext': 'mp4',
            'title': 'Horny Asian Bunny Needs Cock',
            'description': "This naughty little Asian bunny is bored and horny. Feed her something hard and big.",
            'uploader': 'nicoledoshi',
            'like_count': int,
        },
    }, {
        # full video
        'url': 'https://www.manyvids.com/Video/4957054/Latex-Dress-JOI/',
        'info_dict': {
            'id': '4957054',
            'ext': 'mp4',
            'title': 'Latex Dress JOI',
            'description': "My new latex dress feels so good on my skin! Just wearing it for you makes me horny. Jerk your cock while I show off my latex-clad body from all angles, rubbing my hands over my body and describing how good it feels. I can't help but touch my pussy, and I give you a countdown when I'm close so we can cum together for my new latex dress!",
            'uploader': "Kylee Nash",
            'like_count': int,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        infos_url = f'https://www.manyvids.com/bff/store/video/{video_id}'
        info_webpage = self._download_webpage(infos_url, video_id, expected_status=200)
        info: dict = json.loads(info_webpage).get('data')

        download_url = f'https://www.manyvids.com/bff/store/video/{video_id}/private'
        download_webpage = self._download_webpage(download_url, video_id, expected_status=200)
        download: dict = json.loads(download_webpage).get('data')

        is_free: bool = info["isFree"]

        title = info["title"]
        if title and is_free is False:
            title += " (Preview)"

        if is_free:
            download_url = download["filepath"]
        else:
            download_url = download.get("teaser", {}).get("filepath")
            if download_url is None:
                raise ValueError('this video has no preview')
                # They are rare, but they exist. You can find such videos using the following link:
                # https://www.manyvids.com/Vids/?content_type=1,2,3&other=blocked&search_type=0&sort=13&page=1
        return {
            'id': video_id,
            'url': download_url,
            'title': title,
            'description': info.get("description") or None,
            'uploader': info["model"]["displayName"],
            'like_count': int(info["likes"]),
        }
