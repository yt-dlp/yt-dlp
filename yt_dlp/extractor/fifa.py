from urllib import parse as urlparse

from .common import InfoExtractor

from ..utils import (
    int_or_none,
    traverse_obj,
    unified_timestamp,
)


class FifaIE(InfoExtractor):
    _VALID_URL = r'https?://www.fifa.com/fifaplus/(?P<locale>\w{2})/watch/(?P<id>\w+)/?$'
    _TESTS = [{
        'url': 'https://www.fifa.com/fifaplus/en/watch/7on10qPcnyLajDDU3ntg6y',
        'info_dict': {
            'id': '7on10qPcnyLajDDU3ntg6y',
            'title': 'Italy v France | Final | 2006 FIFA World Cup Germany™ | Full Match Replay',
            'description': 'md5:f4520d0ee80529c8ba4134a7d692ff8b',
            'ext': 'mp4',
            'categories': ['FIFA Tournaments', 'Replay'],
            'thumbnail': 'https://digitalhub.fifa.com/transform/fa6f0b3e-a2e9-4cf7-9f32-53c57bcb7360/2006_Final_ITA_FRA',
            'duration': 8164,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.fifa.com/fifaplus/pt/watch/1cg5r5Qt6Qt12ilkDgb1sV',
        'info_dict': {
            'id': '1cg5r5Qt6Qt12ilkDgb1sV',
            'title': 'Brasil x Alemanha | Semifinais | Copa do Mundo FIFA Brasil 2014 | Compacto',
            'description': 'md5:ba4ffcc084802b062beffc3b4c4b19d6',
            'ext': 'mp4',
            'categories': ['FIFA Tournaments', 'Highlights'],
            'thumbnail': 'https://digitalhub.fifa.com/transform/d8fe6f61-276d-4a73-a7fe-6878a35fd082/FIFAPLS_100EXTHL_2014BRAvGER_TMB',
            'duration': 902,
            'release_timestamp': 1404777600,
            'release_date': '20140708',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.fifa.com/fifaplus/fr/watch/3C6gQH9C2DLwzNx7BMRQdp',
        'info_dict': {
            'id': '3C6gQH9C2DLwzNx7BMRQdp',
            'title': 'Le but de Josimar contre le Irlande du Nord | Buts classiques',
            'description': 'md5:16f9f789f09960bfe7220fe67af31f34',
            'ext': 'mp4',
            'categories': ['FIFA Tournaments', 'Goal'],
            'duration': 28,
            'thumbnail': 'https://digitalhub.fifa.com/transform/f9301391-f8d9-48b5-823e-c093ac5e3e11/CG_MEN_1986_JOSIMAR',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.fifa.com/fifaplus/en/watch/2KhLLn6aiGW3nr8sNm8Hkv',
        'info_dict': {
            'id': '2KhLLn6aiGW3nr8sNm8Hkv',
            'title': "Le Sommer: Lyon-Barcelona a beautiful final for women's football",
            'description': 'md5:12106ba87d30a1b4d38d305d638011f8',
            'ext': 'mp4',
            'categories': ['Feed', 'News Video'],
            'duration': 32,
            'thumbnail': 'md5:94dacfdbed26db723604665b7617f9e3',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id, locale = self._match_valid_url(url).group('id', 'locale')
        webpage = self._download_webpage(url, video_id)

        preconnect_link = self._search_regex(
            r'<link[^>]+rel\s*=\s*"preconnect"[^>]+href\s*=\s*"([^"]+)"', webpage, 'Preconnect Link')

        json_data = self._download_json(
            f'{preconnect_link}/video/GetVideoPlayerData/{video_id}', video_id,
            'Downloading Video Player Data', query={'includeIdents': True, 'locale': locale})

        video_details = self._download_json(
            f'{preconnect_link}/sections/videoDetails/{video_id}', video_id, 'Downloading Video Details', fatal=False)

        preplay_parameters = self._download_json(
            f'{preconnect_link}/video/GetVerizonPreplayParameters', video_id, 'Downloading Preplay Parameters', query={
                'entryId': video_id,
                'assetId': json_data['verizonAssetId'],
                'useExternalId': False,
                'requiresToken': json_data['requiresToken'],
                'adConfig': 'fifaplusvideo',
                'prerollAds': True,
                'adVideoId': json_data['externalVerizonAssetId'],
                'preIdentId': json_data['preIdentId'],
                'postIdentId': json_data['postIdentId'],
            })
        cid = f'{json_data["preIdentId"]},{json_data["verizonAssetId"]},{json_data["postIdentId"]}'
        query = preplay_parameters.get('queryStr')
        if not query:
            query = {'cid': cid}
            if preplay_parameters.get('preplayAPIVersion'):
                query['v'] = preplay_parameters['preplayAPIVersion']
            if preplay_parameters.get('tokenCheckAlgorithmVersion'):
                query['tc'] = preplay_parameters['tokenCheckAlgorithmVersion']
            if preplay_parameters.get('randomNumber'):
                query['rn'] = preplay_parameters['randomNumber']
            if preplay_parameters.get('tokenExpirationDate'):
                query['exp'] = preplay_parameters['tokenExpirationDate']
            if preplay_parameters.get('contentType'):
                query['ct'] = preplay_parameters['contentType']
            if preplay_parameters.get('tracksAssetNumber'):
                query['mbtracks'] = preplay_parameters['tracksAssetNumber']
            if preplay_parameters.get('adConfiguration'):
                query['ad'] = preplay_parameters['adConfiguration']
            if preplay_parameters.get('adPreroll'):
                query['ad.preroll'] = preplay_parameters['adPreroll']
            if preplay_parameters.get('adCMSSourceId'):
                query['ad.cmsid'] = preplay_parameters['adCMSSourceId']
            if preplay_parameters.get('adSourceVideoID'):
                query['ad.vid'] = preplay_parameters['adSourceVideoID']
            if preplay_parameters.get('signature'):
                query['sig'] = preplay_parameters['signature']
        else:
            query = urlparse.parse_qs(f'{query}&sig={preplay_parameters["signature"]}')

        content_data = self._download_json(
            f'https://content.uplynk.com/preplay/{cid}/multiple.json', video_id, 'Downloading Content Data', query=query)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(content_data['playURL'], video_id)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': json_data.get('title'),
            'description': json_data.get('description'),
            'duration': int_or_none(json_data.get('duration')),
            'release_timestamp': unified_timestamp(video_details.get('dateOfRelease')),
            'categories': traverse_obj(video_details, (('videoCategory', 'videoSubcategory'),)),
            'thumbnail': traverse_obj(video_details, ('backgroundImage', 'src')),
            'formats': formats,
            'subtitles': subtitles,
        }


class FifaArticlesIE(InfoExtractor):
    _VALID_URL = r'https?://www.fifa.com/fifaplus/(?P<locale>\w{2})/articles/(?P<id>[a-z0-9_-]+)[/?\?\#]?'
    _TESTS = [{
        'url': 'https://www.fifa.com/fifaplus/en/articles/foord-talks-2023-and-battling-kerr-for-the-wsl-title',
        'info_dict': {
            'id': 'foord-talks-2023-and-battling-kerr-for-the-wsl-title',
            'title': 'Foord talks 2023 and battling Kerr for the WSL title',
            'description': 'md5:065448015d15c75391a101e350531224',
        },
        'playlist_count': 2,
    }, {
        'url': 'https://www.fifa.com/fifaplus/en/articles/stars-set-to-collide-in-uwcl-final',
        'info_dict': {
            'id': 'stars-set-to-collide-in-uwcl-final',
            'title': 'Stars set to collide in Women’s Champions League final ',
            'description': 'md5:6c2a17ab66d82a5bf640006a1d976f62',
        },
        'playlist_count': 3,
    }]

    def _real_extract(self, url):
        video_id, locale = self._match_valid_url(url).group('id', 'locale')
        webpage = self._download_webpage(url, video_id)

        preconnect_link = self._search_regex(
            r'<link[^>]+rel\s*=\s*"preconnect"[^>]+href\s*=\s*"([^"]+)"', webpage, 'Preconnect Link')
        playlist_details = self._download_json(
            f'{preconnect_link}/pages/{locale}/articles/{video_id}', video_id, 'Downloading Playlist Details')
        section_detail = self._download_json(
            f'{preconnect_link}/sections/article/{playlist_details["pageId"]}',
            video_id, 'Downloading Playlist Details', query={'locale': locale})

        video_entry_ids = []
        if section_detail.get('heroVideoEntryId'):
            video_entry_ids.append({
                'id': section_detail['heroVideoEntryId'],
                'title': section_detail.get('articleTitle'),
            })

        more_contents = traverse_obj(section_detail, ('richtext', 'content'))
        if more_contents:
            for content in more_contents:
                if traverse_obj(content, ('data', 'target', 'sys', 'contentType', 'sys', 'id')) == 'video':
                    video_entry_ids.append({
                        'id': content['data']['target']['$id'],
                        'title': traverse_obj(content, ('data', 'target', 'title')),
                    })

        entries = [
            self.url_result(
                f'https://www.fifa.com/fifaplus/{locale}/watch/{entry["id"]}',
                FifaIE, entry['id'], entry.get('title'))
            for entry in video_entry_ids]

        return self.playlist_result(
            entries, video_id, traverse_obj(playlist_details, ('meta', 'title')),
            traverse_obj(playlist_details, ('meta', 'description')))


class FifaMoviesIE(InfoExtractor):
    _VALID_URL = r'https?://www.fifa.com/fifaplus/(?P<locale>\w{2})/watch/movie/(?P<id>\w+)[/?\?\#]?'
    _TESTS = [{
        'url': 'https://www.fifa.com/fifaplus/en/watch/movie/2OFuZ9TGyPH6x7nZsgnVBN',
        'info_dict': {
            'id': '2OFuZ9TGyPH6x7nZsgnVBN',
            'title': 'Bravas de Juárez',
            'description': 'md5:1c36885f34d1c142f66ddd5acd5226b2',
        },
        'playlist_count': 2,
    }, {
        'url': 'https://www.fifa.com/fifaplus/en/watch/movie/01ioUo8QHiajSisrvP3ES2',
        'info_dict': {
            'id': '01ioUo8QHiajSisrvP3ES2',
            'title': 'Le Moment | The Official Film of the 2019 FIFA Women’s World Cup™',
            'description': 'md5:12146ae1de093ff7b541ba7ffa67e758',
        },
        'playlist_count': 1,
    }]

    def _real_extract(self, url):
        video_id, locale = self._match_valid_url(url).group('id', 'locale')
        webpage = self._download_webpage(url, video_id)

        preconnect_link = self._search_regex(
            r'<link[^>]+rel\s*=\s*"preconnect"[^>]+href\s*=\s*"([^"]+)"', webpage, 'Preconnect Link')

        movie_details = self._download_json(
            f'{preconnect_link}/sections/movieDetails/{video_id}', video_id,
            'Downloading Movie Details', query={'locale': locale})

        title = None
        video_entry_ids = []
        if movie_details.get('trailers'):
            for trailer in movie_details['trailers']:
                title = trailer.get('title')
                video_entry_ids.append({'id': trailer['entryId'], 'title': title})

        if movie_details.get('video'):
            title = traverse_obj(movie_details, ('video', 'title')) or title
            video_entry_ids.append({'id': movie_details['video']['videoEntryId'], 'title': title})

        entries = [
            self.url_result(
                f'https://www.fifa.com/fifaplus/{locale}/watch/{entry["id"]}',
                FifaIE, entry['id'], entry.get('title'))
            for entry in video_entry_ids]

        return self.playlist_result(
            entries, video_id, title, traverse_obj(movie_details, ('video', 'description')))


class FifaSeriesIE(InfoExtractor):
    _VALID_URL = r'https?://www.fifa.com/fifaplus/(?P<locale>\w{2})/watch/series/(?P<serie_id>\w+)/(?P<season_id>\w+)/(?P<episode_id>\w+)[/?\?\#]?'
    _TESTS = [{
        'url': 'https://www.fifa.com/fifaplus/en/watch/series/48PQFX2J4TiDJcxWOxUPho/2ka5yomq8MBvfxe205zdQ9/6H72309PLWXafBIavvPzPQ#ReadMore',
        'info_dict': {
            'id': '48PQFX2J4TiDJcxWOxUPho',
            'title': 'Episode 1 | Kariobangi',
            'description': 'md5:ecbc8668f828d3cc2c0d00edcc0af04f',
        },
        'playlist_count': 4,
    }, {
        'url': 'https://www.fifa.com/fifaplus/en/watch/series/5Ja1dDLuudkFF95OVHcYBG/5epcWav73zMbjTJh2RxIOt/1NIHdDxPlYodbNobjS1iX5',
        'info_dict': {
            'id': '5Ja1dDLuudkFF95OVHcYBG',
            'title': 'Paul Pogba and Aaron Wan Bissaka | HD Cutz',
            'description': 'md5:16dc373774f503ef91f4489ca17c3f49',
        },
        'playlist_count': 2,
    }]

    def _real_extract(self, url):
        video_id, locale, season_id, episode_id = self._match_valid_url(url).group('serie_id', 'locale', 'season_id', 'episode_id')
        webpage = self._download_webpage(url, video_id)

        preconnect_link = self._search_regex(
            r'<link[^>]+rel\s*=\s*"preconnect"[^>]+href\s*=\s*"([^"]+)"', webpage, 'Preconnect Link')

        serie_details = self._download_json(
            f'{preconnect_link}/sections/videoEpisodeDetails', video_id,
            'Downloading Serie Details', query={
                'locale': locale,
                'seriesId': video_id,
                'seasonId': season_id,
                'episodeId': episode_id,
            })

        video_entry_ids = []
        if serie_details.get('trailers'):
            for trailer in serie_details['trailers']:
                video_entry_ids.append({'id': trailer['entryId'], 'title': trailer.get('title')})

        if serie_details.get('seasons'):
            for season in serie_details.get('seasons'):
                for episode in season.get('episodes'):
                    video_entry_ids.append({'id': episode['entryId'], 'title': episode.get('title')})

        entries = [
            self.url_result(
                f'https://www.fifa.com/fifaplus/{locale}/watch/{entry["id"]}',
                FifaIE, entry['id'], entry.get('title'))
            for entry in video_entry_ids]

        return self.playlist_result(
            entries, video_id, serie_details.get('title').strip(), serie_details.get('description').strip())
