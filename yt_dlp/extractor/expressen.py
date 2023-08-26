from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    unescapeHTML,
    unified_timestamp,
)


class ExpressenIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?(?:expressen|di)\.se/
                        (?:(?:tvspelare/video|videoplayer/embed)/)?
                        tv/(?:[^/]+/)*
                        (?P<id>[^/?#&]+)
                    '''
    _EMBED_REGEX = [r'<iframe[^>]+\bsrc=(["\'])(?P<url>(?:https?:)?//(?:www\.)?(?:expressen|di)\.se/(?:tvspelare/video|videoplayer/embed)/tv/.+?)\1']
    _TESTS = [{
        'url': 'https://www.expressen.se/tv/ledare/ledarsnack/ledarsnack-om-arbetslosheten-bland-kvinnor-i-speciellt-utsatta-omraden/',
        'md5': 'deb2ca62e7b1dcd19fa18ba37523f66e',
        'info_dict': {
            'id': 'ba90f5a9-78d1-4511-aa02-c177b9c99136',
            'display_id': 'ledarsnack-om-arbetslosheten-bland-kvinnor-i-speciellt-utsatta-omraden',
            'ext': 'mp4',
            'title': 'Ledarsnack: Om arbetslösheten bland kvinnor i speciellt utsatta områden',
            'description': 'md5:f38c81ff69f3de4d269bbda012fcbbba',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 788,
            'timestamp': 1526639109,
            'upload_date': '20180518',
        },
    }, {
        'url': 'https://www.expressen.se/tv/kultur/kulturdebatt-med-expressens-karin-olsson/',
        'only_matching': True,
    }, {
        'url': 'https://www.expressen.se/tvspelare/video/tv/ditv/ekonomistudion/experterna-har-ar-fragorna-som-avgor-valet/?embed=true&external=true&autoplay=true&startVolume=0&partnerId=di',
        'only_matching': True,
    }, {
        'url': 'https://www.expressen.se/videoplayer/embed/tv/ditv/ekonomistudion/experterna-har-ar-fragorna-som-avgor-valet/?embed=true&external=true&autoplay=true&startVolume=0&partnerId=di',
        'only_matching': True,
    }, {
        'url': 'https://www.di.se/videoplayer/embed/tv/ditv/borsmorgon/implantica-rusar-70--under-borspremiaren-hor-styrelsemedlemmen/?embed=true&external=true&autoplay=true&startVolume=0&partnerId=di',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        def extract_data(name):
            return self._parse_json(
                self._search_regex(
                    r'data-%s=(["\'])(?P<value>(?:(?!\1).)+)\1' % name,
                    webpage, 'info', group='value'),
                display_id, transform_source=unescapeHTML)

        info = extract_data('video-tracking-info')
        video_id = info['contentId']

        data = extract_data('article-data')
        stream = data['stream']

        if determine_ext(stream) == 'm3u8':
            formats = self._extract_m3u8_formats(
                stream, display_id, 'mp4', entry_protocol='m3u8_native',
                m3u8_id='hls')
        else:
            formats = [{
                'url': stream,
            }]

        title = info.get('titleRaw') or data['title']
        description = info.get('descriptionRaw')
        thumbnail = info.get('socialMediaImage') or data.get('image')
        duration = int_or_none(info.get('videoTotalSecondsDuration')
                               or data.get('totalSecondsDuration'))
        timestamp = unified_timestamp(info.get('publishDate'))

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'timestamp': timestamp,
            'formats': formats,
        }
