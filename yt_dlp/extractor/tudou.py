from .common import InfoExtractor


class TudouIE(InfoExtractor):
    _VALID_URL = r'https?://(?:play\.)?tudou\.com/v_show/(?P<id>id_[\w=.]+)'
    _TESTS = [{
        'url': 'https://play.tudou.com/v_show/id_XNjAxNjI2OTU3Ng',
        'md5': 'to be updated',

        'info_dict': {
            'id': 'XNjAxNjI2OTU3Ng==',
            'ext': 'mp4',
            'title': '阿斯塔意识到哈里杀了人，自己被骗了',
            'show_name': '外星居民 第一季',
        },
        # 'skip': 'testing skip function',
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        data = self._search_json(r'window\.__INITIAL_DATA__\s*=', webpage, 'initial data', video_id)
        # print('==========')
        # print(webpage)
        # print(data)

        # The json file produced same results as the regex did, but it's much cleaner, thanks for the guide
        video_id = data['data']['data']['data']['extra']['videoId']
        videoLongId = str(data['data']['data']['data']['extra']['videoLongId'])
        title = data['data']['data']['data']['extra']['videoTitle']
        show_name = data['data']['data']['data']['extra']['showName']

        video_url = 'https://play.tudou.com' + data['config']['url']
        # About video_url
        # The video url is not stored in the json file above, instead, the website uses m3u8 scheme
        # With F12 developer tool, I've locked one request.
        # Each time I click the button to play the video, the browser will GET a .m3u8 file which contains urls of all clips of that video, in currently selected resolution (in the webpage player).
        # In Debugger panel, I also found a get.json file. Can't visit the source url, it'll fail, but can right-click and download the get.json. In get.json file, there're 4 m3u8_url that represent all 4 resolutions available for this video.
        # These 2 files might be what I should be looking for, guess so.

        # Tried to copy the link and send the request via PYTHON request module, with headers, fail, 403
        # Tried to copy the cUrl and send via Insomnia, fail again, 403 forbidden
        # Tudou.com is a bit similar to Youku.com(already available in yt-dlp), Tudou.com is acquired by Youku.com many years ago, they're probably sharing some servers and I do find similar domains in these 2 sites
        # Therefore I also checked the Youku extractor, but don't know how they get to things like, line 119 'https://log.mmstat.com/eg.js'
        # I also searched the internet and found another code for Youku.com, in that code there're token settings, appKey, sign, etc..

        # So I'm guessing, for Tudou.com, there might be something to do with the token too pass the authentication...
        # I'll keep looking into it, but if you can come up with any tips it'll be appreciated.

        print('==========')
        print(f'videoId = {video_id}')
        print(f'videoLongId = {videoLongId}')
        print(f'title = {title}')
        print(f'show_name = {show_name}')
        print(f'video_url = {video_url}')
        print('==========')

        return {
            'id': video_id,
            'title': title,
            'ext': 'mp4',
            'url': video_url,
            'show_name': show_name,
        }
