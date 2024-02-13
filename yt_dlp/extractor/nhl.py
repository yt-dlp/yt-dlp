from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    determine_ext,
    int_or_none,
    parse_duration,
    parse_iso8601,
)


class NHLBaseIE(InfoExtractor):
    def _real_extract(self, url):
        site, tmp_id = self._match_valid_url(url).groups()
        video_data = self._download_json(
            'https://%s/%s/%sid/v1/%s/details/web-v1.json'
            % (self._CONTENT_DOMAIN, site[:3], 'item/' if site == 'mlb' else '', tmp_id), tmp_id)
        if video_data.get('type') != 'video':
            video_data = video_data['media']
            video = video_data.get('video')
            if video:
                video_data = video
            else:
                videos = video_data.get('videos')
                if videos:
                    video_data = videos[0]

        video_id = compat_str(video_data['id'])
        title = video_data['title']

        formats = []
        for playback in video_data.get('playbacks', []):
            playback_url = playback.get('url')
            if not playback_url:
                continue
            ext = determine_ext(playback_url)
            if ext == 'm3u8':
                m3u8_formats = self._extract_m3u8_formats(
                    playback_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id=playback.get('name', 'hls'), fatal=False)
                self._check_formats(m3u8_formats, video_id)
                formats.extend(m3u8_formats)
            else:
                height = int_or_none(playback.get('height'))
                formats.append({
                    'format_id': playback.get('name', 'http' + ('-%dp' % height if height else '')),
                    'url': playback_url,
                    'width': int_or_none(playback.get('width')),
                    'height': height,
                    'tbr': int_or_none(self._search_regex(r'_(\d+)[kK]', playback_url, 'bitrate', default=None)),
                })

        thumbnails = []
        cuts = video_data.get('image', {}).get('cuts') or []
        if isinstance(cuts, dict):
            cuts = cuts.values()
        for thumbnail_data in cuts:
            thumbnail_url = thumbnail_data.get('src')
            if not thumbnail_url:
                continue
            thumbnails.append({
                'url': thumbnail_url,
                'width': int_or_none(thumbnail_data.get('width')),
                'height': int_or_none(thumbnail_data.get('height')),
            })

        return {
            'id': video_id,
            'title': title,
            'description': video_data.get('description'),
            'timestamp': parse_iso8601(video_data.get('date')),
            'duration': parse_duration(video_data.get('duration')),
            'thumbnails': thumbnails,
            'formats': formats,
        }


class NHLIE(NHLBaseIE):
    IE_NAME = 'nhl.com'
    _VALID_URL = r'https?://(?:www\.)?(?P<site>nhl|wch2016)\.com/(?:[^/]+/)*c-(?P<id>\d+)'
    _CONTENT_DOMAIN = 'nhl.bamcontent.com'
    _TESTS = [{
        # type=video
        'url': 'https://www.nhl.com/video/anisimov-cleans-up-mess/t-277752844/c-43663503',
        'md5': '0f7b9a8f986fb4b4eeeece9a56416eaf',
        'info_dict': {
            'id': '43663503',
            'ext': 'mp4',
            'title': 'Anisimov cleans up mess',
            'description': 'md5:a02354acdfe900e940ce40706939ca63',
            'timestamp': 1461288600,
            'upload_date': '20160422',
        },
    }, {
        # type=article
        'url': 'https://www.nhl.com/news/dennis-wideman-suspended/c-278258934',
        'md5': '1f39f4ea74c1394dea110699a25b366c',
        'info_dict': {
            'id': '40784403',
            'ext': 'mp4',
            'title': 'Wideman suspended by NHL',
            'description': 'Flames defenseman Dennis Wideman was banned 20 games for violation of Rule 40 (Physical Abuse of Officials)',
            'upload_date': '20160204',
            'timestamp': 1454544904,
        },
    }, {
        # Some m3u8 URLs are invalid (https://github.com/ytdl-org/youtube-dl/issues/10713)
        'url': 'https://www.nhl.com/predators/video/poile-laviolette-on-subban-trade/t-277437416/c-44315003',
        'md5': '50b2bb47f405121484dda3ccbea25459',
        'info_dict': {
            'id': '44315003',
            'ext': 'mp4',
            'title': 'Poile, Laviolette on Subban trade',
            'description': 'General manager David Poile and head coach Peter Laviolette share their thoughts on acquiring P.K. Subban from Montreal (06/29/16)',
            'timestamp': 1467242866,
            'upload_date': '20160629',
        },
    }, {
        'url': 'https://www.wch2016.com/video/caneur-best-of-game-2-micd-up/t-281230378/c-44983703',
        'only_matching': True,
    }, {
        'url': 'https://www.wch2016.com/news/3-stars-team-europe-vs-team-canada/c-282195068',
        'only_matching': True,
    }]
