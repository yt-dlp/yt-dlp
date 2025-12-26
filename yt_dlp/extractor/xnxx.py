from .common import InfoExtractor
from ..utils import determine_ext, str_to_int, url_or_none


class XNXXIE(InfoExtractor):
    _VALID_URL = (
        r'https?://(?:\w{2,}\.)?xnxx\w{0,}\.(?:\w{2,})/video-(?P<id>[^/]+)/(?:.*)?'
    )
    _TESTS = [
        {
            'url': 'https://www.xnxx.com/video-ef92b3f/fitnessrooms_yoga_master_teaches_young_student_sexual_techniques',
            'info_dict': {
                'id': 'ef92b3f',
                'title': 'FitnessRooms Yoga master teaches young student sexual techniques',
                'thumbnail': r're:https?://.*\.jpg$',
                'duration': 724,
                'age_limit': 19,
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://xnxx.health/video-1bms31db/best_passionate_doggystyle_comp_',
            'info_dict': {
                'id': '1bms31db',
                'title': 'BEST PASSIONATE DOGGYSTYLE COMP!',
                'thumbnail': r're:https?://.*\.jpg$',
                'duration': 516,
                'age_limit': 19,
                'ext': 'mp4',
            },
        },
    ]

    @staticmethod
    def __html5prop_(prop: str) -> str:
        return rf'html5player\.set{prop}\((["\'])(.+?)\1\);'  # 1st group is quote

    def __get_html5prop(
        self, webpage, *props, prop_name='html5player', fatal=False, default='',
    ):
        patterns = [self.__html5prop_(p) for p in props]
        return self._search_regex(
            patterns, webpage, name=prop_name, fatal=fatal, default=default, group=2,  # type: ignore
        )

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id, tries=10, timeout=1)  # type: ignore

        title: str = str(
            self._og_search_property('title', webpage, 'Title', fatal=False)
            or self._html_search_meta('title', webpage, fatal=False)
            or video_id,
        )
        thumbnail = url_or_none(
            self._og_search_property('image', webpage, 'Thumbnail', fatal=False)
            or self._html_search_meta('image', webpage, 'Thumbnail', fatal=False)
            or self.__get_html5prop(
                webpage, 'ThumbUrl', 'ThumbUrl169', prop_name='Thumbnail',
            ),
        )
        duration = str_to_int(
            self._og_search_property('duration', webpage, 'Duration', fatal=False)
            or self._html_search_meta('duration', webpage, 'Duration', fatal=False),
        )

        formats = []
        for format_spec in ['VideoHLS', 'VideoUrlHigh', 'VideoUrlLow']:
            url = self.__get_html5prop(webpage, format_spec, prop_name='Content Url')
            ext = determine_ext(url)
            if not url:
                continue

            if ext in ('m3u8', 'hls'):
                formats.extend(
                    self._extract_m3u8_formats(
                        url,
                        video_id,
                        'mp4',
                        entry_protocol='m3u8_native',
                        quality=1,
                        m3u8_id='hls',
                        fatal=False,
                    ),
                )
            else:
                formats.append(
                    {
                        'format_id': str(hash(url)),
                        'url': url,
                        'quality': -1 if 'low' in format_spec.lower() else 0,
                    },
                )

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'age_limit': 19,
            'formats': formats,
        }
