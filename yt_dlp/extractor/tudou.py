from .common import InfoExtractor
import time
import re


class TudouIE(InfoExtractor):
    _VALID_URL = r'https?://(?:play\.)?tudou\.com/v_show/(?P<id>id_[\w=]+).html[\w\W]+'
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

        # The .json file is much cleaner, thanks for the guide
        video_id = data['data']['data']['data']['extra']['videoId']
        title = data['data']['data']['data']['extra']['videoTitle']
        show_name = data['data']['data']['data']['extra']['showName']

        _, urlh = self._download_webpage_handle(
            "https://log.mmstat.com/yt.gif", video_id, 'Retrieving cna info'
        )
        re_cna = re.compile(r'cna=([\w\W]+; expires)')
        cna = re.findall(re_cna, urlh.headers['set-cookie'])[0].replace("; expires", "")
        ts1 = time.time() * 1000

        params1 = {
            "vid": video_id,
            "ccode": "050F",
            "client_ip": "192.168.1.1",
            "utid": cna,
            "client_ts": ts1,
            "ckey": "140#XvSoigEEzzPw6zo2K5XTwpN8s9xI9h7FQeSkq6lrpeQ3Qm8xyFnPG9Uxtq6aSBxXVXwkqv6L4/GKvKzgD5oqlbzxhQfIlJgkzFnb0OK7lpTzzPzbVXlqlbrofJH+V3hqabzi228++bP0EHmiuZsHofFc74upoC6MkpscNHvXzJK+//Wna4Zt+dTHiQWqckfMQdZWTBs1ZpU/wadIq8nYxy5uZ+cRepqZMra+XLkaqMgGBcF/Ie/igRJDCcHl4d28aId7B+XOW/V6+gNOtDc+y6piEy1V51R4rYd41m6FkoEE4ix4eQE3VY7wvREVNJfR54V4qc3aqV4zzx+dkH8STo4ABYgr27bP9Vi0NBwse6wOOAJfYbnYZQdqQ4rlte/TfegJDmiufcPHd7sUG/A0RYx3pHQ9wYa3lQS3MjIjWejRlGzQdt0fxqEhcHuu10zfo4lhobcXARy7rDT2fb6wJrCHf98c0l8iGiOTSXVZVvWiQMM1est+EACvaMFB/baJm1BjCMKeS2zQEgUkRmulz00icM/W0BS8sEOR1RpOP4WXpji1HjEDpt2MTVHGqUwo223u03IGTHK3Z+Ki1ujWXKKUP+E1VESmBF0rzBkR/dyP20hRbGSpfX7eRVABF6npnWgdgjzQB4FOxAjHPn5CupypFZDYIdKyfQyC45mGS5WI6Wz9JmoFjxO7ikUKKP6p0KP3nj+5YTtbwUNpciVhD+mOZZKq6+dT6G7cfBhOzZQFXs66gZ3174KWt6sLTcvLzEezfoA0mO0NIx0mZZlL1lYonycOtcByLpKmSW5Xd96FWP5fuenIBUUJZCectNPgB/nFNGpeZuhruYbBbG843gwtfiXaRp2r4ssDM07/pPsEfk6MzcmtAxIimwdRjv6lSx+QSEANWRazykZneHEpH1R0uB0BjJdozYDKK84KMsNd+jjg6XTz9Ai0KZYMUJXN1Vz=",
            "vip": "0",
        }

        headers1 = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
            "Referer": "https://play.tudou.com/"
        }

        # About video_url
        # The video url is not stored in the json file above, instead, the website uses m3u8 scheme
        # This get.json file contains 4 cdn_url and 4 m3u8_url
        # I'm not sure what cdn_url stands for, but it also delivers the full video
        # I'll put the cdn_url here for now, if needed I can replace it with m3u8_url
        data_m3u8 = self._download_json(
            'https://ups.youku.com/ups/get.json', video_id,
            'Downloading JSON metadata',
            query=params1, headers=headers1)

        list_of_video_data = []
        for item in data_m3u8['data']['stream']:
            item_of_video_data = {
                'url': item['segs'][0]['cdn_url'].replace('http://', 'https://'),
                'ext': 'mp4',
                'filesize': item['size'],
                'width': item['width'],
                'height': item['height'],
            }
            list_of_video_data.append(item_of_video_data)
        sorted_list_of_video_data = sorted(list_of_video_data, key= lambda d: d ['filesize'], reverse= False)

        return {
            'id': video_id,
            'title': title,
            'show_name': show_name,
            'ext': 'mp4',
            'formats': sorted_list_of_video_data,
        }
