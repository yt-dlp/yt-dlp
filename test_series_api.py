import urllib.request
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Origin': 'https://aryplus.tv',
    'Referer': 'https://aryplus.tv/',
    'x-api-key': 'ak_37515186786306625012043079404171'
}

endpoints = [
    'https://be.aryplus.tv/api/series/6a57868b5bf57c474cc00a50',
    'https://be.aryplus.tv/api/cdn/6a57868b5bf57c474cc00a50',
    'https://be.aryplus.tv/api/v2/cdn/pg/6a57868b5bf57c474cc00a50?page=1&limit=10&sort=asc'
]

for url in endpoints:
    print('Testing URL:', url)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print('Success!')
            if isinstance(data, dict):
                print('Keys:', list(data.keys()))
                if 'episode' in data:
                    print('Episodes count in episode:', len(data['episode']))
                    if len(data['episode']) > 0:
                        ep0 = data['episode'][0]
                        print('Episode 0:', {k: ep0.get(k) for k in ['_id', 'title', 'videoSource', 'drmEnabled', 'imagePath']})
            elif isinstance(data, list):
                print('List items count:', len(data))
    except Exception as e:
        print('Error:', e)
    print('-'*50)

