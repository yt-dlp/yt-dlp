import urllib.request
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Origin': 'https://aryplus.tv',
    'Referer': 'https://aryplus.tv/',
    'x-api-key': 'ak_37515186786306625012043079404171'
}

url = 'https://be.aryplus.tv/api/cdn/ep/6a6e0b1e9bc4b079859bc14b'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    print(json.dumps(data, indent=2))

