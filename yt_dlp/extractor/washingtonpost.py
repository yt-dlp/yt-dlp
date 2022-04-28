import re

from .common import InfoExtractor

from ..utils import traverse_obj


class WashingtonPostIE(InfoExtractor):
    IE_NAME = 'washingtonpost'
    _VALID_URL = r'(?:washingtonpost:|https?://(?:www\.)?washingtonpost\.com/(?:video|posttv)/(?:[^/]+/)*)(?P<id>[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})'
    _EMBED_URL = r'https?://(?:www\.)?washingtonpost\.com/video/c/embed/[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}'
    _TESTS = [{
        'url': 'https://www.washingtonpost.com/video/c/video/480ba4ee-1ec7-11e6-82c2-a7dcb313287d',
        'md5': '6f537e1334b714eb15f9563bd4b9cdfa',
        'info_dict': {
            'id': '480ba4ee-1ec7-11e6-82c2-a7dcb313287d',
            'ext': 'mp4',
            'title': 'Egypt finds belongings, debris from plane crash',
            'description': 'md5:a17ceee432f215a5371388c1f680bd86',
            'upload_date': '20160520',
            'timestamp': 1463775187,
        },
    }, {
        'url': 'https://www.washingtonpost.com/video/world/egypt-finds-belongings-debris-from-plane-crash/2016/05/20/480ba4ee-1ec7-11e6-82c2-a7dcb313287d_video.html',
        'only_matching': True,
    }, {
        'url': 'https://www.washingtonpost.com/posttv/world/iraq-to-track-down-antiquities-after-islamic-state-museum-rampage/2015/02/28/7c57e916-bf86-11e4-9dfb-03366e719af8_video.html',
        'only_matching': True,
    }]

    @classmethod
    def _extract_urls(cls, webpage):
        return re.findall(
            r'<iframe[^>]+\bsrc=["\'](%s)' % cls._EMBED_URL, webpage)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            'arcpublishing:wapo:' + video_id, 'ArcPublishing', video_id)


class WashingtonPostArticleIE(InfoExtractor):
    IE_NAME = 'washingtonpost:article'
    _VALID_URL = r'https?://(?:www\.)?washingtonpost\.com/(?:[^/]+/)*(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'http://www.washingtonpost.com/sf/national/2014/03/22/sinkhole-of-bureaucracy/',
        'info_dict': {
            'id': 'sinkhole-of-bureaucracy',
            'title': 'Sinkhole of bureaucracy',
        },
        'playlist': [{
            'md5': '7ccf53ea8cbb77de5f570242b3b21a59',
            'info_dict': {
                'id': 'fc433c38-b146-11e3-b8b3-44b1d1cd4c1f',
                'ext': 'mp4',
                'title': 'Breaking Points: The Paper Mine',
                'duration': 1290,
                'description': 'Overly complicated paper pushing is nothing new to government bureaucracy. But the way federal retirement applications are filed may be the most outdated. David Fahrenthold explains.',
                'timestamp': 1395440416,
                'upload_date': '20140321',
                'thumbnail': r're:https://[^\.]+.cloudfront\.net/PAPERMINESplash\.jpg',
            },
        }, {
            'md5': '7ccf53ea8cbb77de5f570242b3b21a59',
            'info_dict': {
                'id': '41255e28-b14a-11e3-b8b3-44b1d1cd4c1f',
                'ext': 'mp4',
                'title': 'The town bureaucracy sustains',
                'description': 'Underneath the friendly town of Boyers is a sea of government paperwork. In a disused limestone mine, hundreds of locals now track, file and process retirement applications for the federal government. We set out to find out what it\'s like to do paperwork 230 feet underground.',
                'duration': 2220,
                'timestamp': 1395441819,
                'upload_date': '20140321',
                'thumbnail': r're:https://[^\.]+.cloudfront\.net/BoyersSplash\.jpeg',
            },
        }],
    }, {
        'url': 'http://www.washingtonpost.com/blogs/wonkblog/wp/2014/12/31/one-airline-figured-out-how-to-make-sure-its-airplanes-never-disappear/',
        'info_dict': {
            'id': 'one-airline-figured-out-how-to-make-sure-its-airplanes-never-disappear',
            'title': 'One airline figured out how to make sure its airplanes never disappear',
        },
        'playlist': [{
            'md5': 'a7c1b5634ba5e57a6a82cdffa5b1e0d0',
            'info_dict': {
                'id': '0e4bb54c-9065-11e4-a66f-0ca5037a597d',
                'ext': 'mp4',
                'description': 'Washington Post transportation reporter Ashley Halsey III explains why a plane\'s black box needs to be recovered from a crash site instead of having its information streamed in real time throughout the flight.',
                'upload_date': '20141230',
                'timestamp': 1419972442,
                'title': 'Why black boxes don’t transmit data in real time',
            }
        }],
        'skip': 'Doesnt have a video anymore',
    }, {
        'url': 'https://www.washingtonpost.com/nation/2021/08/05/dixie-river-fire-california-climate/',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if WashingtonPostIE.suitable(url) else super(WashingtonPostArticleIE, cls).suitable(url)

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id)

        title = self._og_search_title(webpage)

        uuids = re.findall(r'''(?x)
            (?:
                <div\s+class="posttv-video-embed[^>]*?data-uuid=|
                data-video-uuid=
            )"([^"]+)"''', webpage)

        if not uuids:
            json_data = self._search_nextjs_data(webpage, page_id)
            for content_element in traverse_obj(json_data, ('props', 'pageProps', 'globalContent', 'content_elements')):
                if content_element.get('type') == 'video':
                    uuids.append(content_element.get('_id'))

        entries = [self.url_result('washingtonpost:%s' % uuid, 'WashingtonPost', uuid) for uuid in uuids]

        return {
            '_type': 'playlist',
            'entries': entries,
            'id': page_id,
            'title': title,
        }
