import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    orderedSet,
    unescapeHTML,
)


class StanfordOpenClassroomIE(InfoExtractor):
    IE_NAME = 'stanfordoc'
    IE_DESC = 'Stanford Open ClassRoom'
    _VALID_URL = r'https?://openclassroom\.stanford\.edu(?P<path>/?|(/MainFolder/(?:HomePage|CoursePage|VideoPage)\.php([?]course=(?P<course>[^&]+)(&video=(?P<video>[^&]+))?(&.*)?)?))$'
    _TEST = {
        'url': 'http://openclassroom.stanford.edu/MainFolder/VideoPage.php?course=PracticalUnix&video=intro-environment&speed=100',
        'md5': '544a9468546059d4e80d76265b0443b8',
        'info_dict': {
            'id': 'PracticalUnix_intro-environment',
            'ext': 'mp4',
            'title': 'Intro Environment',
        }
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)

        if mobj.group('course') and mobj.group('video'):  # A specific video
            course = mobj.group('course')
            video = mobj.group('video')
            info = {
                'id': course + '_' + video,
                'uploader': None,
                'upload_date': None,
            }

            baseUrl = 'http://openclassroom.stanford.edu/MainFolder/courses/' + course + '/videos/'
            xmlUrl = baseUrl + video + '.xml'
            mdoc = self._download_xml(xmlUrl, info['id'])
            try:
                info['title'] = mdoc.findall('./title')[0].text
                info['url'] = baseUrl + mdoc.findall('./videoFile')[0].text
            except IndexError:
                raise ExtractorError('Invalid metadata XML file')
            return info
        elif mobj.group('course'):  # A course page
            course = mobj.group('course')
            info = {
                'id': course,
                '_type': 'playlist',
                'uploader': None,
                'upload_date': None,
            }

            coursepage = self._download_webpage(
                url, info['id'],
                note='Downloading course info page',
                errnote='Unable to download course info page')

            info['title'] = self._html_search_regex(
                r'<h1>([^<]+)</h1>', coursepage, 'title', default=info['id'])

            info['description'] = self._html_search_regex(
                r'(?s)<description>([^<]+)</description>',
                coursepage, 'description', fatal=False)

            links = orderedSet(re.findall(r'<a href="(VideoPage\.php\?[^"]+)">', coursepage))
            info['entries'] = [self.url_result(
                'http://openclassroom.stanford.edu/MainFolder/%s' % unescapeHTML(l)
            ) for l in links]
            return info
        else:  # Root page
            info = {
                'id': 'Stanford OpenClassroom',
                '_type': 'playlist',
                'uploader': None,
                'upload_date': None,
            }
            info['title'] = info['id']

            rootURL = 'http://openclassroom.stanford.edu/MainFolder/HomePage.php'
            rootpage = self._download_webpage(rootURL, info['id'],
                                              errnote='Unable to download course info page')

            links = orderedSet(re.findall(r'<a href="(CoursePage\.php\?[^"]+)">', rootpage))
            info['entries'] = [self.url_result(
                'http://openclassroom.stanford.edu/MainFolder/%s' % unescapeHTML(l)
            ) for l in links]
            return info
