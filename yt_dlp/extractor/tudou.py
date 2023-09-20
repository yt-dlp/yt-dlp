from .common import InfoExtractor


class TudouIE(InfoExtractor):
    _VALID_URL = r'https?://(?:play\.)?tudou\.com/v_show/(id_[a-zA-Z0-9_=.]+)'
    _TESTS = [{
        'url': 'https://play.tudou.com/v_show/id_XNjAxNjI2OTU3Ng',

        # this code successfully downloaded the .mp4 file, and passed the test, EXCEPT the md5 part.
        # I moved this code to the extractor folder of the released version of yt-dlp, trying to see if it works properly in there.
        # IF it worked, then I can calculate the md5 of the first 10kb, and compare the md5.
        # Unfortunately, it didn't.
        # I'm guessing it has problem in extracting the video id, but can't prove my guessing.

        # But it does work here, when run 'python test/test_download.py TestDownload.test_Tudou'
        # That's why it didn't pass the md5 test, because I couldn't download the first 10kb with the released version of yt-dlp.
        # So there's nothing to compare

        # I'm interested to know if there's another way to download the first 10kb.
        # Currently it's a paradox to me:
        # To finalise this code, I need to get the first 10kb, to do the last comparison.
        # But this code doesn't work in the released yt-dlp, so I can't get the first 10kb.
        # So how can I.....

        # 'f33b73e7470c45b7d3c4f7d8b34eda14',
        # this md5, is from the output of this command - 'python test/test_download.py TestDownload.test_Tudou'.
        # the downloaded file is deleted automatically, not giving me a chance to calculate its md5 manually.
        'md5': 'failed to get the first 10kb',

        'info_dict': {
            'id': 'XNjAxNjI2OTU3Ng==',
            'ext': 'mp4',
            'title': '外星居民 第一季 阿斯塔意识到哈里杀了人，自己被骗了-电视剧-高清完整正版视频在线观看-优酷',
        },
        # 'skip': 'testing skip function',
    }]

    def _real_extract(self, url):
        # About video_id
        #   .get_temp_id return None
        #   ._match_id doesn't work as well
        # I don't know how to fix this, but line 49 works, it extracts id from the webpage
        # I think there might be a smarter way, but I'm just not smart enough
        video_id = self.get_temp_id(url)
        webpage = self._download_webpage(url, video_id)

        # print('==========')
        # print(webpage)
        video_id = self._html_search_regex(r'currentEncodeVid: \'(.+?)\',', webpage, 'xhtml')
        title = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title')
        video_url = self._html_search_regex(r'<meta property="og:url" content="(.+?)"/>', webpage, 'og:url')

        print('==========')
        print(video_id)
        print(title)
        print(video_url)
        print('==========')

        return {
            'id': video_id,
            'title': title,
            'ext': 'mp4',
            'url': video_url
        }
