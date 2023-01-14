import re

from .amp import AMPIE
from .common import InfoExtractor


class FoxNewsIE(AMPIE):
    IE_NAME = 'foxnews'
    IE_DESC = 'Fox News and Fox Business Video'
    _VALID_URL = r'https?://(?P<host>video\.(?:insider\.)?fox(?:news|business)\.com)/v/(?:video-embed\.html\?video_id=)?(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'http://video.foxnews.com/v/3937480/frozen-in-time/#sp=show-clips',
            'md5': '32aaded6ba3ef0d1c04e238d01031e5e',
            'info_dict': {
                'id': '3937480',
                'ext': 'flv',
                'title': 'Frozen in Time',
                'description': '16-year-old girl is size of toddler',
                'duration': 265,
                'timestamp': 1304411491,
                'upload_date': '20110503',
                'thumbnail': r're:^https?://.*\.jpg$',
            },
        },
        {
            'url': 'http://video.foxnews.com/v/3922535568001/rep-luis-gutierrez-on-if-obamas-immigration-plan-is-legal/#sp=show-clips',
            'md5': '5846c64a1ea05ec78175421b8323e2df',
            'info_dict': {
                'id': '3922535568001',
                'ext': 'mp4',
                'title': "Rep. Luis Gutierrez on if Obama's immigration plan is legal",
                'description': "Congressman discusses president's plan",
                'duration': 292,
                'timestamp': 1417662047,
                'upload_date': '20141204',
                'thumbnail': r're:^https?://.*\.jpg$',
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            },
        },
        {
            'url': 'http://video.foxnews.com/v/video-embed.html?video_id=3937480&d=video.foxnews.com',
            'only_matching': True,
        },
        {
            'url': 'http://video.foxbusiness.com/v/4442309889001',
            'only_matching': True,
        },
        {
            # From http://insider.foxnews.com/2016/08/25/univ-wisconsin-student-group-pushing-silence-certain-words
            'url': 'http://video.insider.foxnews.com/v/video-embed.html?video_id=5099377331001&autoplay=true&share_url=http://insider.foxnews.com/2016/08/25/univ-wisconsin-student-group-pushing-silence-certain-words&share_title=Student%20Group:%20Saying%20%27Politically%20Correct,%27%20%27Trash%27%20and%20%27Lame%27%20Is%20Offensive&share=true',
            'only_matching': True,
        },
    ]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        for mobj in re.finditer(
                r'''(?x)
                    <(?:script|(?:amp-)?iframe)[^>]+\bsrc=["\']
                    (?:https?:)?//video\.foxnews\.com/v/(?:video-embed\.html|embed\.js)\?
                    (?:[^>"\']+&)?(?:video_)?id=(?P<video_id>\d+)
                ''', webpage):
            yield f'https://video.foxnews.com/v/video-embed.html?video_id={mobj.group("video_id")}'

    def _real_extract(self, url):
        host, video_id = self._match_valid_url(url).groups()

        info = self._extract_feed_info(
            'http://%s/v/feed/video/%s.js?template=fox' % (host, video_id))
        info['id'] = video_id
        return info


class FoxNewsVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?foxnews\.com/video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.foxnews.com/video/6313058664112',
        'info_dict': {
            'id': '6313058664112',
            'ext': 'mp4',
            'thumbnail': r're:https://.+/1280x720/match/image\.jpg',
            'upload_date': '20220930',
            'description': 'New York City, Kids Therapy, Biden',
            'duration': 2415,
            'title': 'Gutfeld! - Thursday, September 29',
            'timestamp': 1664527538,
        },
        'expected_warnings': ['Ignoring subtitle tracks'],
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(f'https://video.foxnews.com/v/{video_id}', FoxNewsIE, video_id)


class FoxNewsArticleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:insider\.)?foxnews\.com/(?!v)([^/]+/)+(?P<id>[a-z-]+)'
    IE_NAME = 'foxnews:article'

    _TESTS = [{
        # data-video-id
        'url': 'http://www.foxnews.com/politics/2016/09/08/buzz-about-bud-clinton-camp-denies-claims-wore-earpiece-at-forum.html',
        'md5': '83d44e1aff1433e7a29a7b537d1700b5',
        'info_dict': {
            'id': '5116295019001',
            'ext': 'mp4',
            'title': 'Trump and Clinton asked to defend positions on Iraq War',
            'description': 'Veterans react on \'The Kelly File\'',
            'timestamp': 1473301045,
            'upload_date': '20160908',
        },
    }, {
        # iframe embed
        'url': 'http://www.foxnews.com/us/2018/03/09/parkland-survivor-kyle-kashuv-on-meeting-trump-his-app-to-prevent-another-school-shooting.amp.html?__twitter_impression=true',
        'info_dict': {
            'id': '5748266721001',
            'ext': 'flv',
            'title': 'Kyle Kashuv has a positive message for the Trump White House',
            'description': 'Marjory Stoneman Douglas student disagrees with classmates.',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 229,
            'timestamp': 1520594670,
            'upload_date': '20180309',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://insider.foxnews.com/2016/08/25/univ-wisconsin-student-group-pushing-silence-certain-words',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        video_id = self._html_search_regex(
            r'data-video-id=([\'"])(?P<id>[^\'"]+)\1',
            webpage, 'video ID', group='id', default=None)
        if video_id:
            return self.url_result(
                'http://video.foxnews.com/v/' + video_id, FoxNewsIE.ie_key())

        return self.url_result(
            next(FoxNewsIE._extract_embed_urls(url, webpage)), FoxNewsIE.ie_key())
