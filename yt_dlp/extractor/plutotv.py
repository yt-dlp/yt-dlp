import re
import urllib.parse
import uuid

from .common import InfoExtractor
from ..utils import ExtractorError, float_or_none, traverse_obj


class PlutoTVBase(InfoExtractor):
    _START_QUERY = {
        'appName': 'web',
        'appVersion': 'na',
        'clientID': str(uuid.uuid1()),
        'clientModelNumber': 'na',
        'serverSideAds': 'false',
        'deviceMake': 'unknown',
        'deviceModel': 'web',
        'deviceType': 'web',
        'deviceVersion': 'unknown',
    }

    def _extract_formats(self, start, element):
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(start['servers']['stitcher'] + '/v2' + element['stitched']['path'] + '?' + start['stitcherParams'] + '&jwt=' + start['sessionToken'], element['id'])
        for f in formats:
            f['url'] += '&jwt=' + start['sessionToken']
            if f.get('vcodec') is None:
                f['vcodec'] = 'avc1.64001f'
            if f.get('acodec') is None:
                f['acodec'] = 'mp4a.40.2'
            if f.get('fps') is None:
                f['fps'] = 30
        return formats, subtitles


class PlutoTVIE(PlutoTVBase):
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?pluto\.tv(?:/[^/]+)?/on-demand
        /(?P<video_type>movies|series)
        /(?P<slug>[^/]+)
        (?:
            (?:/seasons?/(?P<season_no>\d+))?
            (?:/episode/(?P<episode_slug>[^/]+))?
        )?
        /?(?:$|[#?])'''

    def _to_ad_free_formats(self, video_id, formats, subtitles):
        ad_free_formats, ad_free_subtitles, m3u8_urls = [], {}, set()
        for fmt in formats:
            res = self._download_webpage(
                fmt.get('url'), video_id, note='Downloading m3u8 playlist',
                fatal=False)
            if not res:
                continue
            first_segment_url = re.search(
                r'^(https?://.*/)0\-(end|[0-9]+)/[^/]+\.ts$', res,
                re.MULTILINE)
            if first_segment_url:
                m3u8_urls.add(
                    urllib.parse.urljoin(first_segment_url.group(1), '0-end/master.m3u8'))
                continue
            first_segment_url = re.search(
                r'^(https?://.*/).+\-0+[0-1]0\.ts$', res,
                re.MULTILINE)
            if first_segment_url:
                m3u8_urls.add(
                    urllib.parse.urljoin(first_segment_url.group(1), 'master.m3u8'))
                continue

        for m3u8_url in m3u8_urls:
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                m3u8_url, video_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False)
            ad_free_formats.extend(fmts)
            ad_free_subtitles = self._merge_subtitles(ad_free_subtitles, subs)
        if ad_free_formats:
            formats, subtitles = ad_free_formats, ad_free_subtitles
        else:
            self.report_warning('Unable to find ad-free formats')
        return formats, subtitles

    def _get_video_info(self, video_json, series, video, season_number):
        formats, subtitles = self._extract_formats(video_json, video)
        thumbnails = [{
            'url': cover['url'],
            'width': int(m.group(1)) if (m := re.search(r'w=(\d+)&h=(\d+)', cover['url'])) else None,
            'height': int(m.group(2)) if m else None,
        } for cover in video.get('covers', [])]
        first_cover = traverse_obj(video, ('covers', 0, 'url'))
        if first_cover:
            thumbnails.append({
                'id': 'original',
                'url': re.sub(r'\?.*$', '?fm=png&q=100', first_cover),
                'preference': 1,
            })
        return {
            'id': video['id'],
            'title': video.get('name'),
            'display_id': video.get('slug'),
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
            'description': video.get('description'),
            'duration': float_or_none(video.get('duration'), scale=1000),
            'genres': [video.get('genre')],
            'series_id': series.get('id'),
            'series': series.get('name'),
            'episode': video.get('name'),
            'episode_id': video['id'],
            'season_number': season_number,
        }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url).groupdict()
        info_slug = mobj['slug']

        if mobj['video_type'] == 'series':
            season_number, episode_slug = mobj.get('season_no'), mobj.get('episode_slug')
            if episode_slug is not None:
                video_json = self._download_json('https://boot.pluto.tv/v4/start', info_slug, 'Downloading info json', query={**self._START_QUERY, 'seriesIDs': info_slug, 'episodeIDs': episode_slug})
                series, video = video_json['VOD']
                return self._get_video_info(video_json, series, video, season_number)
            video_json = self._download_json('https://boot.pluto.tv/v4/start', info_slug, 'Downloading info json', query={**self._START_QUERY, 'seriesIDs': info_slug})
            series = video_json['VOD'][0]
            if season_number is not None:
                for season in series['seasons']:
                    if season['number'] == int(season_number):
                        return self.playlist_result(
                            [self._get_video_info(video_json, series, episode, season_number) for episode in season['episodes']],
                            f"{series['id']}-{season_number}",
                            f"{series['name']} - Season {season_number}",
                        )
                raise ExtractorError('Failed to find season %s' % season_number)
            return self.playlist_result(
                [self._get_video_info(video_json, series, episode, season['number']) for season in series['seasons'] for episode in season['episodes']],
                series['id'],
                series['name'],
            )
        raise ExtractorError('Not implemented')


class PlutoTVLiveIE(PlutoTVBase):
    _VALID_URL = r'https?://(?:www\.)?pluto\.tv(?:/[^/]+)?/live-tv/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://pluto.tv/live-tv/6093f9281db477000759fce0',
        'info_dict': {
            'id': '6093f9281db477000759fce0',
            'ext': 'mp4',
            'live_status': 'is_live',
            'thumbnail': 'http://images.pluto.tv/channels/6093f9281db477000759fce0/featuredImage.jpg?fm=png&q=100',
            'title': r're:Super! SpongeBob',
            'display_id': 'super-spongebob-it',
            'episode_id': str,
            'series': 'Super! SpongeBob',
            'series_id': str,
            'episode': str,
            'description': str,
        },
    }, {
        'url': 'https://pluto.tv/it/live-tv/64c109a4798def0008a6e03e',
        'info_dict': {
            'id': '64c109a4798def0008a6e03e',
            'ext': 'mp4',
            'thumbnail': 'http://images.pluto.tv/channels/64c109a4798def0008a6e03e/featuredImage.jpg?fm=png&q=100',
            'description': str,
            'live_status': 'is_live',
            'series_id': str,
            'series': 'Top Gear',
            'episode': str,
            'title': r're:(?s)Top Gear: .+',
            'episode_id': str,
            'display_id': 'top-gear-it',
        },
    }]

    def _real_extract(self, url):
        slug = self._match_id(url)
        start = self._download_json('https://boot.pluto.tv/v4/start', slug, 'Downloading info json', query={**self._START_QUERY, 'channelSlug': slug})
        channel = start['EPG'][0]
        program = channel['timelines'][0]
        formats, subtitles = self._extract_formats(start, channel)
        thumbnails = []
        for image in channel['images']:
            if image['type'] == 'featuredImage':
                thumbnails.append({
                    'id': 'original',
                    'url': re.sub(r'\?.*$', '?fm=png&q=100', image['url']),
                    'preference': 1,
                })
            thumbnails.append({
                'id': image['type'],
                'url': image['url'],
                'width': image.get('defaultWidth'),
                'height': image.get('defaultHeight'),
            })
        return {
            'id': channel['id'],
            'title': program.get('title'),
            'display_id': channel.get('slug'),
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': True,
            'description': traverse_obj(program, ('episode', 'description')),
            'episode': traverse_obj(program, ('episode', 'name')),
            'series': traverse_obj(program, ('episode', 'series', 'name')),
            'series_id': traverse_obj(program, ('episode', 'series', '_id')),
            'episode_id': traverse_obj(program, ('episode', '_id')),
        }
