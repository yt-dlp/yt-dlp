import urllib.request
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Origin': 'https://aryplus.tv',
    'Referer': 'https://aryplus.tv/',
    'x-api-key': 'ak_37515186786306625012043079404171'
}

url = 'https://be.aryplus.tv/api/v2/shorts?page=1&limit=5'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    print("Shorts result keys:", list(data.keys()))
    shorts_list = data.get('data', [])
    print(f"Got {len(shorts_list)} shorts")
    if shorts_list:
        print("First short:", json.dumps(shorts_list[0], indent=2))

