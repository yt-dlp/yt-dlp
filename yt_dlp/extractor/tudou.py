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

        # The .json file is much cleaner, thanks for the guide
        video_id = data['data']['data']['data']['extra']['videoId']
        title = data['data']['data']['data']['extra']['videoTitle']
        show_name = data['data']['data']['data']['extra']['showName']

        params1 = {
            "vid": "XNjAwMjk3Nzk1Mg==",
            "play_ability": "16782592",
            "current_showid": "590457",
            "preferClarity": "2",
            "extag": "EXT-X-PRIVINF",
            "master_m3u8": "1",
            "media_type": "standard,subtitle",
            "app_ver": "2.1.75",
            "ccode": "050F",
            "client_ip": "192.168.1.1",
            "utid": "bIeZHQHll0oCAXj0ME8oOTqH",
            "client_ts": "1695807088",
            "ckey": "140#XvSoigEEzzPw6zo2K5XTwpN8s9xI9h7FQeSkq6lrpeQ3Qm8xyFnPG9Uxtq6aSBxXVXwkqv6L4/GKvKzgD5oqlbzxhQfIlJgkzFnb0OK7lpTzzPzbVXlqlbrofJH+V3hqabzi228++bP0EHmiuZsHofFc74upoC6MkpscNHvXzJK+//Wna4Zt+dTHiQWqckfMQdZWTBs1ZpU/wadIq8nYxy5uZ+cRepqZMra+XLkaqMgGBcF/Ie/igRJDCcHl4d28aId7B+XOW/V6+gNOtDc+y6piEy1V51R4rYd41m6FkoEE4ix4eQE3VY7wvREVNJfR54V4qc3aqV4zzx+dkH8STo4ABYgr27bP9Vi0NBwse6wOOAJfYbnYZQdqQ4rlte/TfegJDmiufcPHd7sUG/A0RYx3pHQ9wYa3lQS3MjIjWejRlGzQdt0fxqEhcHuu10zfo4lhobcXARy7rDT2fb6wJrCHf98c0l8iGiOTSXVZVvWiQMM1est+EACvaMFB/baJm1BjCMKeS2zQEgUkRmulz00icM/W0BS8sEOR1RpOP4WXpji1HjEDpt2MTVHGqUwo223u03IGTHK3Z+Ki1ujWXKKUP+E1VESmBF0rzBkR/dyP20hRbGSpfX7eRVABF6npnWgdgjzQB4FOxAjHPn5CupypFZDYIdKyfQyC45mGS5WI6Wz9JmoFjxO7ikUKKP6p0KP3nj+5YTtbwUNpciVhD+mOZZKq6+dT6G7cfBhOzZQFXs66gZ3174KWt6sLTcvLzEezfoA0mO0NIx0mZZlL1lYonycOtcByLpKmSW5Xd96FWP5fuenIBUUJZCectNPgB/nFNGpeZuhruYbBbG843gwtfiXaRp2r4ssDM07/pPsEfk6MzcmtAxIimwdRjv6lSx+QSEANWRazykZneHEpH1R0uB0BjJdozYDKK84KMsNd+jjg6XTz9Ai0KZYMUJXN1Vz=",
            "version": "2.1.75",
            "vs": "1.0",
            "pver": "2.1.75",
            "sver": "2.0",
            "site": "-1",
            "aw": "w",
            "fu": "0",
            "d": "0",
            "bt": "pc",
            "os": "win",
            "osv": "10",
            "dq": "auto",
            "atm": "",
            "partnerid": "null",
            "wintype": "interior",
            "isvert": "0",
            "vip": "0",
            "emb": "",
            "p": "1",
            "rst": "mp4",
            "needbf": "2",
            "avs": "1.0",
            "callback": "",  # youkuPlayer_call_1695807088862
            "_t": "08847696931775378"
        }

        headers1 = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
            "cookie": "_m_h5_tk=da6bb02219fb5a5f223d967490e4cb67_1695744613439; _m_h5_tk_enc=8c8b786a476dbcc04fd0e19c70a5317d",
            "Referer": "https://play.tudou.com/"
        }

        # About video_url
        # The video url is not stored in the json file above, instead, the website uses m3u8 scheme
        # This get.json file contains 4 cdn_url and 4 m3u8_url
        # I'm not sure what cdn_url stands for, but it also delivers the full video
        # I'll put the cdn_url here for now, if needed I can replace it with m3u8_url
        # I probably need to do a bit more on stuff like cookies, to pass the authentication, I wonder how those values are calculated

        # And about params1{} in line 32 (sometimes they call it querystring?)
        # IS there a way to know which value is essential for the request process below?
        # Maybe I can just leave it, it works anyway.
        # But I still want to simplify it, it's a bit too long.

        data_m3u8 = self._download_json(
            'https://ups.youku.com/ups/get.json', video_id,
            'Downloading JSON metadata',
            query=params1, headers=headers1)

        list_of_url = []
        for item in data_m3u8['data']['stream']:
            item_of_url = {
                'width': item['width'],
                'height': item['height'],
                'size': item['size'],
                'cdn_url': item['segs'][0]['cdn_url'].replace('http://', 'https://'),
            }
            list_of_url.append(item_of_url)
        # Sort urls in descending order, according to size, so the first one in the list will always be the best quality one
        sorted_list_of_url = sorted(list_of_url, key=lambda d: d['size'], reverse=True)

        return {
            'id': video_id,
            'title': title,
            'ext': 'mp4',
            'url': sorted_list_of_url[0]['cdn_url'],
            'show_name': show_name,
        }
