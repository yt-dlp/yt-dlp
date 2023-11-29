from .common import InfoExtractor
import json
import urllib.request


class LoomIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?loom\.com/share/(?P<id>[a-z0-9]+)'
    # https://www.loom.com/share/3c1284df64d9454b8854f112d62dce91
    _TESTS = [
    {
        'url': 'https://www.loom.com/share/43d05f362f734614a2e81b4694a3a523',
        'md5': '2b0d36e4999c39fabdb617188f21ea1e',
        'info_dict': {
            'id': '43d05f362f734614a2e81b4694a3a523',
            'ext': 'mp4',
            'title': 'A Ruler for Windows - 28 March 2022',
            'uploader': 'wILLIAM PIP',
        }
                  
    }]

    def fetch_loom_download_url(self, id):
        request = urllib.request.Request(
            url=f"https://www.loom.com/api/campaigns/sessions/{id}/transcoded-url",
            headers={},
            method="POST",
        )
        response = urllib.request.urlopen(request)
        body = response.read()
        content = json.loads(body.decode("utf-8"))
        url = content["url"]
        return url

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # print(f'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n')
        # print(f'Id: {video_id}')
        # print(f'\n\n\n\n\n\n\n\nWebpage: {webpage}\n\n\n\n\n\n\n\n')

        # TODO more code goes here, for example ...
        # title = self._html_search_regex(r'<h1>(.+?)</h1>', webpage, 'title')
        # match = re.search(r'', text)
        # if match:
        #     first_video_name = match.group(1)

        title = self._search_regex(r'"name":"([^"]+)"', webpage, 'title')
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
            'ext' : ext,
            # 'format_id': ext,
            # 'filesize': int(filesize),
        })

        return {
            'id': video_id,
            'title': title,
            'uploader': uploader,
            'formats': formats,
            # TODO more properties (see yt_dlp/extractor/common.py)
        }