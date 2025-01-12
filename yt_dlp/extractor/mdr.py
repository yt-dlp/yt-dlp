import urllib.parse

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    join_nonempty,
    parse_duration,
    parse_iso8601,
    url_or_none,
    xpath_text,
)


class MDRIE(InfoExtractor):
    IE_DESC = 'MDR.DE'
    _VALID_URL = r'https?://(?:www\.)?mdr\.de/(?:.*)/[a-z-]+-?(?P<id>\d+)(?:_.+?)?\.html'

    _GEO_COUNTRIES = ['DE']

    _TESTS = [{
        # MDR regularly deletes its videos
        'url': 'http://www.mdr.de/fakt/video189002.html',
        'only_matching': True,
    }, {
        # audio
        'url': 'http://www.mdr.de/kultur/audio1312272_zc-15948bad_zs-86171fdd.html',
        'md5': '64c4ee50f0a791deb9479cd7bbe9d2fa',
        'info_dict': {
            'id': '1312272',
            'ext': 'mp3',
            'title': 'Feuilleton vom 30. Oktober 2015',
            'duration': 250,
            'uploader': 'MITTELDEUTSCHER RUNDFUNK',
        },
        'skip': '404 not found',
    }, {
        # audio with alternative playerURL pattern
        'url': 'http://www.mdr.de/kultur/videos-und-audios/audio-radio/operation-mindfuck-robert-wilson100.html',
        'info_dict': {
            'id': '100',
            'ext': 'mp4',
            'title': 'Feature: Operation Mindfuck - Robert Anton Wilson',
            'duration': 3239,
            'uploader': 'MITTELDEUTSCHER RUNDFUNK',
        },
        'skip': '404 not found',
    }, {
        'url': 'http://www.mdr.de/mediathek/mdr-videos/a/video-1334.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        data_url = self._search_regex(
            r'(?:dataURL|playerXml(?:["\'])?)\s*:\s*(["\'])(?P<url>.+?-avCustom\.xml)\1',
            webpage, 'data url', group='url').replace(r'\/', '/')

        doc = self._download_xml(
            urllib.parse.urljoin(url, data_url), video_id)

        title = xpath_text(doc, ['./title', './broadcast/broadcastName'], 'title', fatal=True)

        type_ = xpath_text(doc, './type', default=None)

        formats = []
        processed_urls = []
        for asset in doc.findall('./assets/asset'):
            for source in (
                    'download',
                    'progressiveDownload',
                    'dynamicHttpStreamingRedirector',
                    'adaptiveHttpStreamingRedirector'):
                url_el = asset.find(f'./{source}Url')
                if url_el is None:
                    continue

                video_url = url_or_none(url_el.text)
                if not video_url or video_url in processed_urls:
                    continue

                processed_urls.append(video_url)

                ext = determine_ext(video_url)
                if ext == 'm3u8':
                    formats.extend(self._extract_m3u8_formats(
                        video_url, video_id, 'mp4', entry_protocol='m3u8_native',
                        quality=1, m3u8_id='HLS', fatal=False))
                elif ext == 'f4m':
                    formats.extend(self._extract_f4m_formats(
                        video_url + '?hdcore=3.7.0&plugin=aasp-3.7.0.39.44', video_id,
                        quality=1, f4m_id='HDS', fatal=False))
                else:
                    media_type = xpath_text(asset, './mediaType', 'media type', default='MP4')
                    vbr = int_or_none(xpath_text(asset, './bitrateVideo', 'vbr'), 1000)
                    abr = int_or_none(xpath_text(asset, './bitrateAudio', 'abr'), 1000)
                    filesize = int_or_none(xpath_text(asset, './fileSize', 'file size'))

                    f = {
                        'url': video_url,
                        'format_id': join_nonempty(media_type, vbr or abr),
                        'filesize': filesize,
                        'abr': abr,
                        'vbr': vbr,
                    }

                    if vbr:
                        f.update({
                            'width': int_or_none(xpath_text(asset, './frameWidth', 'width')),
                            'height': int_or_none(xpath_text(asset, './frameHeight', 'height')),
                        })

                    if type_ == 'audio':
                        f['vcodec'] = 'none'

                    formats.append(f)

        description = xpath_text(doc, './broadcast/broadcastDescription', 'description')
        timestamp = parse_iso8601(
            xpath_text(
                doc, [
                    './broadcast/broadcastDate',
                    './broadcast/broadcastStartDate',
                    './broadcast/broadcastEndDate'],
                'timestamp', default=None))
        duration = parse_duration(xpath_text(doc, './duration', 'duration'))
        uploader = xpath_text(doc, './rights', 'uploader')

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'timestamp': timestamp,
            'duration': duration,
            'uploader': uploader,
            'formats': formats,
        }
