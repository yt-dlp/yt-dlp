from .common import InfoExtractor
from ..utils import (
    determine_ext,
    merge_dicts,
    parse_duration,
    url_or_none,
)


class BYUtvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?byutv\.org/(?:watch|player)/(?!event/)(?P<id>[0-9a-f-]+)(?:/(?P<display_id>[^/?#&]+))?'
    _TESTS = [{
        # ooyalaVOD
        'url': 'http://www.byutv.org/watch/6587b9a3-89d2-42a6-a7f7-fd2f81840a7d/studio-c-season-5-episode-5',
        'info_dict': {
            'id': 'ZvanRocTpW-G5_yZFeltTAMv6jxOU9KH',
            'display_id': 'studio-c-season-5-episode-5',
            'ext': 'mp4',
            'title': 'Season 5 Episode 5',
            'description': 'md5:1d31dc18ef4f075b28f6a65937d22c65',
            'thumbnail': r're:^https?://.*',
            'duration': 1486.486,
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': ['Ooyala'],
    }, {
        # dvr
        'url': 'https://www.byutv.org/player/8f1dab9b-b243-47c8-b525-3e2d021a3451/byu-softball-pacific-vs-byu-41219---game-2',
        'info_dict': {
            'id': '8f1dab9b-b243-47c8-b525-3e2d021a3451',
            'display_id': 'byu-softball-pacific-vs-byu-41219---game-2',
            'ext': 'mp4',
            'title': 'Pacific vs. BYU (4/12/19)',
            'description': 'md5:1ac7b57cb9a78015910a4834790ce1f3',
            'duration': 11645,
        },
        'params': {
            'skip_download': True
        },
    }, {
        'url': 'http://www.byutv.org/watch/6587b9a3-89d2-42a6-a7f7-fd2f81840a7d',
        'only_matching': True,
    }, {
        'url': 'https://www.byutv.org/player/27741493-dc83-40b0-8420-e7ae38a2ae98/byu-football-toledo-vs-byu-93016?listid=4fe0fee5-0d3c-4a29-b725-e4948627f472&listindex=0&q=toledo',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        display_id = mobj.group('display_id') or video_id

        video = self._download_json(
            'https://api.byutv.org/api3/catalog/getvideosforcontent',
            display_id, query={
                'contentid': video_id,
                'channel': 'byutv',
                'x-byutv-context': 'web$US',
            }, headers={
                'x-byutv-context': 'web$US',
                'x-byutv-platformkey': 'xsaaw9c7y5',
            })

        ep = video.get('ooyalaVOD')
        if ep:
            return {
                '_type': 'url_transparent',
                'ie_key': 'Ooyala',
                'url': 'ooyala:%s' % ep['providerId'],
                'id': video_id,
                'display_id': display_id,
                'title': ep.get('title'),
                'description': ep.get('description'),
                'thumbnail': ep.get('imageThumbnail'),
            }

        info = {}
        formats = []
        subtitles = {}
        for format_id, ep in video.items():
            if not isinstance(ep, dict):
                continue
            video_url = url_or_none(ep.get('videoUrl'))
            if not video_url:
                continue
            ext = determine_ext(video_url)
            if ext == 'm3u8':
                m3u8_fmts, m3u8_subs = self._extract_m3u8_formats_and_subtitles(
                    video_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False)
                formats.extend(m3u8_fmts)
                subtitles = self._merge_subtitles(subtitles, m3u8_subs)
            elif ext == 'mpd':
                mpd_fmts, mpd_subs = self._extract_mpd_formats_and_subtitles(
                    video_url, video_id, mpd_id='dash', fatal=False)
                formats.extend(mpd_fmts)
                subtitles = self._merge_subtitles(subtitles, mpd_subs)
            else:
                formats.append({
                    'url': video_url,
                    'format_id': format_id,
                })
            merge_dicts(info, {
                'title': ep.get('title'),
                'description': ep.get('description'),
                'thumbnail': ep.get('imageThumbnail'),
                'duration': parse_duration(ep.get('length')),
            })

        return merge_dicts(info, {
            'id': video_id,
            'display_id': display_id,
            'title': display_id,
            'formats': formats,
            'subtitles': subtitles,
        })
