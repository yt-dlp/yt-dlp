import gzip
import json

import requests


def yt_music_MPADUC_fix(browseid: str) -> list[str]:
    browseid = browseid.removeprefix('https://music.youtube.com/browse/')
    cookies = {
        'SOCS': 'CAI',
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Content-Encoding': 'gzip',
    }

    params = {
        'prettyPrint': 'false',
    }

    data = gzip.compress(json.dumps({
        'context': {
            'client': {
                'clientName': 'WEB_REMIX',
                'clientVersion': '1.20260728.15.00',
            },
        },
        'browseId': browseid,
    }).encode())

    r2 = requests.post('https://music.youtube.com/youtubei/v1/browse', params=params, cookies=cookies, headers=headers, data=data)
    items = r2.json()['contents']['singleColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['sectionListRenderer']['contents'][0]['gridRenderer']['items']

    results = []
    for item in items:
        browseid = item['musicTwoRowItemRenderer']['title']['runs'][0]['navigationEndpoint']['browseEndpoint']['browseId']
        results.append(f'https://music.youtube.com/browse/{browseid}')
    return results
