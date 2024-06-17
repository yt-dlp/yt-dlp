from .common import InfoExtractor
import base64
import re
import pprint
import json

def decode_link(link: str) -> str:
    zc = ord('Z')

    def replacer(match: re.Match[str]):
        ec = ord(match[0])
        eccpy = ec + 13
        return chr(eccpy if ((90 if ec <= zc else 122) >= eccpy) else eccpy - 26)

    finalstr = re.sub(r"[a-zA-Z]", replacer, link)
    return 'https:' + base64.b64decode(finalstr).decode()

class KodikIE(InfoExtractor):
    _VALID_URL = r"^(?P<protocol>http[s]?:|)\/\/(?P<host>[a-z0-9]+\.[a-z]+)\/(?P<type>[a-z]+)\/(?P<id>\d+)\/(?P<hash>[0-9a-z]+)\/(?P<quality>\d+p)$"
    
    def _real_extract(self, url):
        match = self._match_valid_url(url)
        video_id = match['id'] + '-' + match['hash'] + '-' + match['quality']

        json = self._download_json(f"{match['protocol']}//{match['host']}/gvi", data = b'', 
            video_id = video_id, query = {
            'id': match['id'], 
            'hash': match['hash'], 
            'quality': match['quality'],
            'type': match['type']
        })
        
        webpage: str = self._download_webpage(url, video_id=video_id, headers = {'Referer': url})
        tb = re.findall(r'\"(//[^\"]+\.jpg|png)\"', webpage)[0]

        formats = []
        for lnk in json['links']:
            link = decode_link(json['links'][lnk][0]['src'])
            fmt = self._extract_m3u8_formats(link, video_id, 'mp4', 'm3u8_native')
            print(link)
            for f in fmt:
                f.update({
                    'thumbnail' : 'https:' + tb,
                    'quality': re.findall(r'(\d+).mp4', link)[0]
                })
            formats.extend(fmt)
        
        return {
            'formats': formats,
            'id': video_id,
            'title': video_id,
        }
        
        
