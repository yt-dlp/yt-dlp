
from __future__ import unicode_literals
import os, sys, re, json, demjson, requests, urllib2
from bs4 import BeautifulSoup
from getpass import getpass

from __main__ import logger
from __main__ import *


from parserdata      import ParserData
from downloader      import Download
from extractor       import Extractor


LOGIN_URL = "https://www.canalsurmas.es/login/"
SITE = "https://www.canalsurmas.es"
HEADERS = {
    "User-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.84 Safari/537.36",
    }


def find_c_url(url):
    url = url.replace("https://www.canalsurmas.es/videos/detail/", "")
    vid = url.split("-", 1)[0]
    return vid

def find_v_url(url):
    url = url.replace("https://www.canalsurmas.es/videos/detail/", "")
    vid = url.split("-", 1)[1]
    vid = vid.replace("/", "-")
    return vid

def find_title(url):
    html_text = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(html_text.text)
    title = soup.find("div", {"class": "single-title-detail"})
    title = title.getText()
    title = title.strip()
    return title

class ExtractorModule(Extractor):

    def __init__(self):
        pass

    def get_media_url(self, media_id):
        """
        Returns the media url from the video url
        """
        url = "https://api.interactvty.com/api/1.0/contents/" + media_id
        html_text = requests.get(url).text
        media_url = re.findall('''playlist.*?name":"(.*?)".*?content_resource.*?url":"(.*?)"''', html_text)
        #video["VIP"]
        return media_url

    def check_login(self):
        """
        Checks if the user is logged in
        """
        url = "https://www.canalsurmas.es"
        doc = Download.get(url, headers=HEADERS)
        if'name="log_nick"' in doc.text:
            is_logged = False
        else:
            is_logged = True
        return is_logged

    def login(self, username, password):
        """
        Performs the login
        """
        session = requests.session()
        logger.info("Logging in [%s]" % username)
        session.post(LOGIN_URL, verify=False, data={"log_nick": username, "log_pass": password, "log_ok": "ok"}, headers=HEADERS)
        self.username = username

    def supported_url(self, url):
        if "canalsurmas.es" in url:
            if "/detail/" in url:
                return True

    def resolve(self, url):
        """
        Resolves the given url and returns a list of streams
        """
        if not self.login_done:
            username = AddonHelper.get_setting("username")
            password = AddonHelper.get_setting("password")
            self.login(username, password)
            self.login_done = True

        c_url = ParserData.get_parameter(url)
        c_url = find_c_url(url)
        v_url = find_v_url(url)
        print "Canal: " + c_url
        print "Titulo: " + v_url


        if not self.is_logged():
            username = AddonHelper.get_setting("username")
            password = AddonHelper.get_setting("password")
            self.login(username, password)

        media_url = self.get_media_url(c_url)
        print "URL: " + media_url

        ydl = YoutubeDL()
        ydl.add_default_info_extractors()
        ydl.add_info_extractor(CanalsurmasIE(media_url))

        with ydl:
            result = ydl.extract_info(url, download=False)

        stream_url = result['url']
        print >> sys.stderr, '\033[92m' + "Canalsurmas.py: URL: " + stream_url + '\033[0m'
        return stream_url


class CanalsurmasIE(InfoExtractor):

    def __init__(self, media_url):
        self.media_url = media_url

    def find_c_url(self, url):
        url = url.replace("https://www.canalsurmas.es/videos/detail/", "")
        vid = url.split("-", 1)[0]
        return vid

    def find_v_url(self, url):
        url = url.replace("https://www.canalsurmas.es/videos/detail/", "")
        vid = url.split("-", 1)[1]
        vid = vid.replace("/", "-")
        return vid

    def find_title(self, url):
        html_text = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(html_text.text)
        title = soup.find("div", {"class": "single-title-detail"})
        title = title.getText()
        title = title.strip()
        return title

    def find_m3u8(self, url):
        html_text = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(html_text.text)
        iframe = soup.find("iframe")
        urldom = urlparse(iframe.get('src'))
        urlifr = urldom.path
        urlifr = urlifr.replace("/html5-player/embed/", "")
        urlifr = urlifr.replace("/html5-player/embed/?src=2&ruta=/hls/", "")
        urlifr = urlifr.replace("/html5-player/embed/?src=2&ruta=", "")
        urlifr = urlifr.replace("?", "")
        urlifr = urlifr.replace("&", "_")
        urlifr = urlifr + ".m3u8"
        return urlifr

    @staticmethod
    def suitable(url):
        return False if CanalsurmasIe.suitable(url) else re.match(
            r'http(s)?://(.*\.)?canalsurmas.es', url) is not None

    def _real_extract(self, url):
        print "media_url: " + self.media_url
        c_url = self.find_c_url(url)
        v_url = self.find_v_url(url)
        title = self.find_title(url)
        m3u8 = self.find_m3u8(url)

        print "Canal: " + c_url
        print "v_url: " + v_url
        print "Titulo: " + title
        print "M3U8: " + SITE + "/lista/" + m3u8

        video_url = m3u8
        video_url = SITE + "/lista/" + video_url
        print "video_url: " + video_url

        video_id = c_url + "_" + v_url

        webpage_url = url
        f4m_urls = []
        embed_urls = []
        formats = []

        for format_id, video_url in f4m_urls:
            format_dict = {
                'url': video_url,
                'format_id': format_id,
                'vcodec': 'h264',
                'ext': u'flv',
                'protocol': 'hds',
            }
            if format_id in ('400', '500'):
                format_dict['width'] = 400
                format_dict['height'] = 300
            if format_id in ('800', '1000'):
                format_dict['width'] = 800
                format_dict['height'] = 600
            formats.append(format_dict)
        self._sort_formats(formats)

        for embed_url in embed_urls:
            embed_info = self._extract_embed(embed_url)
            formats.extend(embed_info[0:])
            webpage_url = embed_info['webpage_url']

        return {
            'id': video_id,
            'url': url,
            'title': self._og_search_title(webpage),
            'formats': formats,
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
        }


    def _extract_embed(self, url):
        print "Extracting embed: " + url
        mobj = re.match(r'https?://(?:embed)?bambuser\.com/(?:.*/)?(\d+)', url)
        broadcast_id = mobj.group(1)
        broadcast_url = 'http://bambuser.com/api/broadcast/%s' % broadcast_id

        webpage = self._download_webpage(
            broadcast_url, broadcast_id,
            'Downloading embed webpage',
            'Unable to download embed webpage')

        data = parse_json(webpage, broadcast_url)

        formats = []
        for media_type, video_url in data['video'].items():
            if media_type == 'http_temp_h264_aac_ts_url':
                acodec = 'aac'
                vcodec = 'h264'
                format_id = 'ts'
            elif media_type == 'http_temp_hls_aac_url':
                acodec = 'aac'
                vcodec = 'h264'
                format_id = 'hls'

            formats.append({
                'url': video_url,
                'format_id': format_id,
                'acodec': acodec,
                'vcodec': vcodec,
            })
        self._sort_formats(formats)

        # No thumbnails for private broadcasts
        thumbnails = [] if data['public'] else None
        return {
            'id': broadcast_id,
            'is_live': True,
            'title': data.get('title', broadcast_id),
            'uploader': data.get('username'),
            'formats': formats,
            'webpage_url': url,
            'thumbnails': thumbnails,
        }
