import re

from .common import InfoExtractor
from .vimple import SprutoBaseIE


class MyviIE(SprutoBaseIE):
    _VALID_URL = r'''(?x)
                        (?:
                            https?://
                                (?:www\.)?
                                myvi\.
                                (?:
                                    (?:ru/player|tv)/
                                    (?:
                                        (?:
                                            embed/html|
                                            flash|
                                            api/Video/Get
                                        )/|
                                        content/preloader\.swf\?.*\bid=
                                    )|
                                    ru/watch/
                                )|
                            myvi:
                        )
                        (?P<id>[\da-zA-Z_-]+)
                    '''
    _TESTS = [{
        'url': 'http://myvi.ru/player/embed/html/oOy4euHA6LVwNNAjhD9_Jq5Ha2Qf0rtVMVFMAZav8wObeRTZaCATzucDQIDph8hQU0',
        'md5': '571bbdfba9f9ed229dc6d34cc0f335bf',
        'info_dict': {
            'id': 'f16b2bbd-cde8-481c-a981-7cd48605df43',
            'ext': 'mp4',
            'title': 'хозяин жизни',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 25,
        },
    }, {
        'url': 'http://myvi.ru/player/content/preloader.swf?id=oOy4euHA6LVwNNAjhD9_Jq5Ha2Qf0rtVMVFMAZav8wOYf1WFpPfc_bWTKGVf_Zafr0',
        'only_matching': True,
    }, {
        'url': 'http://myvi.ru/player/api/Video/Get/oOy4euHA6LVwNNAjhD9_Jq5Ha2Qf0rtVMVFMAZav8wObeRTZaCATzucDQIDph8hQU0',
        'only_matching': True,
    }, {
        'url': 'http://myvi.tv/embed/html/oTGTNWdyz4Zwy_u1nraolwZ1odenTd9WkTnRfIL9y8VOgHYqOHApE575x4_xxS9Vn0?ap=0',
        'only_matching': True,
    }, {
        'url': 'http://myvi.ru/player/flash/ocp2qZrHI-eZnHKQBK4cZV60hslH8LALnk0uBfKsB-Q4WnY26SeGoYPi8HWHxu0O30',
        'only_matching': True,
    }, {
        'url': 'https://www.myvi.ru/watch/YwbqszQynUaHPn_s82sx0Q2',
        'only_matching': True,
    }, {
        'url': 'myvi:YwbqszQynUaHPn_s82sx0Q2',
        'only_matching': True,
    }]

    @classmethod
    def _extract_url(cls, webpage):
        mobj = re.search(
            r'<iframe[^>]+?src=(["\'])(?P<url>(?:https?:)?//myvi\.(?:ru/player|tv)/(?:embed/html|flash)/[^"]+)\1', webpage)
        if mobj:
            return mobj.group('url')

    def _real_extract(self, url):
        video_id = self._match_id(url)

        spruto = self._download_json(
            'http://myvi.ru/player/api/Video/Get/%s?sig' % video_id, video_id)['sprutoData']

        return self._extract_spruto(spruto, video_id)


class MyviEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?myvi\.tv/(?:[^?]+\?.*?\bv=|embed/)(?P<id>[\da-z]+)'
    _TESTS = [{
        'url': 'https://www.myvi.tv/embed/ccdqic3wgkqwpb36x9sxg43t4r',
        'info_dict': {
            'id': 'b3ea0663-3234-469d-873e-7fecf36b31d1',
            'ext': 'mp4',
            'title': 'Твоя (original song).mp4',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 277,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.myvi.tv/idmi6o?v=ccdqic3wgkqwpb36x9sxg43t4r#watch',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if MyviIE.suitable(url) else super(MyviEmbedIE, cls).suitable(url)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            'https://www.myvi.tv/embed/%s' % video_id, video_id)

        myvi_id = self._search_regex(
            r'CreatePlayer\s*\(\s*["\'].*?\bv=([\da-zA-Z_]+)',
            webpage, 'video id')

        return self.url_result('myvi:%s' % myvi_id, ie=MyviIE.ie_key())
