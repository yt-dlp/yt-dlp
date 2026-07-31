import gzip
import json


def yt_music_MPADUC_fix(self, browseid: str) -> list[str]:
    browseid = browseid.removeprefix('https://music.youtube.com/browse/')

    headers = {
        # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Content-Encoding': 'gzip',
        'Content-Type': 'application/json',
    }

    # data = gzip.compress(
    data = gzip.compress(json.dumps({
        'context': {
            'client': {
                'clientName': 'WEB_REMIX',
                'clientVersion': '1.20260728.15.00',
            },
        },
        'browseId': browseid,
    }).encode())

    r2 = self._download_json('https://music.youtube.com/youtubei/v1/browse', browseid, headers=headers, data=data)
    items = r2['contents']['singleColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['sectionListRenderer']['contents'][0]['gridRenderer']['items']

    results = []
    for item in items:
        browseid = item['musicTwoRowItemRenderer']['title']['runs'][0]['navigationEndpoint']['browseEndpoint']['browseId']
        results.append(f'https://music.youtube.com/browse/{browseid}')
    return results
