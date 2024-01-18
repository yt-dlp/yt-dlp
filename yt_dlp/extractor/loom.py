from .common import InfoExtractor
import json
import urllib.request
from datetime import datetime

'''
This scraper was made really fast without really following best practices.
The webpage string has json data inside it and it would be better if the
video data was grabbed from there instead of using regex.
Because loom could change their video requesting api at any time, I decided
not to work too much on this. If you want to make this scraper better, feel free to do so.
'''


class LoomIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?loom\.com/share/(?P<id>[a-z0-9]+)'
    _TESTS = [{
        'url': 'https://www.loom.com/share/43d05f362f734614a2e81b4694a3a523',
        'md5': '2b0d36e4999c39fabdb617188f21ea1e',
        'info_dict': {
            'id': '43d05f362f734614a2e81b4694a3a523',
            'ext': 'mp4',
            'title': 'A Ruler for Windows - 28 March 2022',
            'uploader': 'wILLIAM PIP',
            'upload_date': '20220328',
        }
    }, {
        'url': 'https://www.loom.com/share/c43a642f815f4378b6f80a889bb73d8d',
        'md5': '281c57772c6364c7a860fc222ea8d222',
        'info_dict': {
            'id': 'c43a642f815f4378b6f80a889bb73d8d',
            'ext': 'mp4',
            'title': 'Lilah Nielsen Intro Video',
            'uploader': 'Lilah Nielsen',
            'upload_date': '20200826',
        }
    }]

    def fetch_loom_download_url(self, id):
        json = self._download_json(f"https://www.loom.com/api/campaigns/sessions/{id}/transcoded-url", video_id=id, data=b'')
        return json["url"]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # print(f'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n')
        # print(f'Id: {video_id}')
        # print(f'\n\n\n\n\n\n\n\nWebpage: {webpage}\n\n\n\n\n\n\n\n')

        title = self._search_regex(r'"name":"([^"]+)"', webpage, 'title')
        
        # title = self._search_json()
        # print(f'Title: {title}')

        uploader = self._search_regex(r'"owner_full_name":"([^"]+)"', webpage, 'uploader', fatal=False)
        # print(f'Uploader: {uploader}')

        videourl = self.fetch_loom_download_url(video_id)
        # print(f'Url: {url}')

        ext = self._search_regex(r'([a-zA-Z0-9]+)(?=\?)', videourl, 'ext', fatal=False)
        # print(f'Ext: {ext}')

        width = self._search_regex(r'"width":([0-9]+)', webpage, 'width', fatal=False)
        # print(f'Width: {width}')

        height = self._search_regex(r'"height":([0-9]+)', webpage, 'height', fatal=False)
        # print(f'Height: {height}')

        date_string = self._search_regex(r'"visibility":"(?:[^"]+)","createdAt":"([^"]+)"', webpage, 'date', fatal=False)
        date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y%m%d")

        # filesize = self._search_regex(r'"file_size":([0-9]+)', webpage, 'filesize', fatal=False)
        # print(f'Filesize: {filesize}')

        # description =
        # print(description)
        # print(f'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n')

        formats = []
        formats.append({
            'url': videourl,
            'width': int(width),
            'height': int(height),
            'ext': ext,
            # 'filesize': int(filesize),
        })

        return {
            'id': video_id,
            'title': title,
            'uploader': uploader,
            'upload_date': date,
            'formats': formats,
            # TODO more properties (see yt_dlp/extractor/common.py)
        }
