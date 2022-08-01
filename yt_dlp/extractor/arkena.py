from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    parse_iso8601,
    parse_qs,
    try_get,
)


class ArkenaIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                        https?://
                            (?:
                                video\.(?:arkena|qbrick)\.com/play2/embed/player\?|
                                play\.arkena\.com/(?:config|embed)/avp/v\d/player/media/(?P<id>[^/]+)/[^/]+/(?P<account_id>\d+)
                            )
                        '''
    # See https://support.arkena.com/display/PLAY/Ways+to+embed+your+video
    _EMBED_REGEX = [r'<iframe[^>]+src=(["\'])(?P<url>(?:https?:)?//play\.arkena\.com/embed/avp/.+?)\1']
    _TESTS = [{
        'url': 'https://video.qbrick.com/play2/embed/player?accountId=1034090&mediaId=d8ab4607-00090107-aab86310',
        'md5': '97f117754e5f3c020f5f26da4a44ebaf',
        'info_dict': {
            'id': 'd8ab4607-00090107-aab86310',
            'ext': 'mp4',
            'title': 'EM_HT20_117_roslund_v2.mp4',
            'timestamp': 1608285912,
            'upload_date': '20201218',
            'duration': 1429.162667,
            'subtitles': {
                'sv': 'count:3',
            },
        },
    }, {
        'url': 'https://play.arkena.com/embed/avp/v2/player/media/b41dda37-d8e7-4d3f-b1b5-9a9db578bdfe/1/129411',
        'only_matching': True,
    }, {
        'url': 'https://play.arkena.com/config/avp/v2/player/media/b41dda37-d8e7-4d3f-b1b5-9a9db578bdfe/1/129411/?callbackMethod=jQuery1111023664739129262213_1469227693893',
        'only_matching': True,
    }, {
        'url': 'http://play.arkena.com/config/avp/v1/player/media/327336/darkmatter/131064/?callbackMethod=jQuery1111002221189684892677_1469227595972',
        'only_matching': True,
    }, {
        'url': 'http://play.arkena.com/embed/avp/v1/player/media/327336/darkmatter/131064/',
        'only_matching': True,
    }, {
        'url': 'http://video.arkena.com/play2/embed/player?accountId=472718&mediaId=35763b3b-00090078-bf604299&pageStyling=styled',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        account_id = mobj.group('account_id')

        # Handle http://video.arkena.com/play2/embed/player URL
        if not video_id:
            qs = parse_qs(url)
            video_id = qs.get('mediaId', [None])[0]
            account_id = qs.get('accountId', [None])[0]
            if not video_id or not account_id:
                raise ExtractorError('Invalid URL', expected=True)

        media = self._download_json(
            'https://video.qbrick.com/api/v1/public/accounts/%s/medias/%s' % (account_id, video_id),
            video_id, query={
                # https://video.qbrick.com/docs/api/examples/library-api.html
                'fields': 'asset/resources/*/renditions/*(height,id,language,links/*(href,mimeType),type,size,videos/*(audios/*(codec,sampleRate),bitrate,codec,duration,height,width),width),created,metadata/*(title,description),tags',
            })
        metadata = media.get('metadata') or {}
        title = metadata['title']

        duration = None
        formats = []
        thumbnails = []
        subtitles = {}
        for resource in media['asset']['resources']:
            for rendition in (resource.get('renditions') or []):
                rendition_type = rendition.get('type')
                for i, link in enumerate(rendition.get('links') or []):
                    href = link.get('href')
                    if not href:
                        continue
                    if rendition_type == 'image':
                        thumbnails.append({
                            'filesize': int_or_none(rendition.get('size')),
                            'height': int_or_none(rendition.get('height')),
                            'id': rendition.get('id'),
                            'url': href,
                            'width': int_or_none(rendition.get('width')),
                        })
                    elif rendition_type == 'subtitle':
                        subtitles.setdefault(rendition.get('language') or 'en', []).append({
                            'url': href,
                        })
                    elif rendition_type == 'video':
                        f = {
                            'filesize': int_or_none(rendition.get('size')),
                            'format_id': rendition.get('id'),
                            'url': href,
                        }
                        video = try_get(rendition, lambda x: x['videos'][i], dict)
                        if video:
                            if not duration:
                                duration = float_or_none(video.get('duration'))
                            f.update({
                                'height': int_or_none(video.get('height')),
                                'tbr': int_or_none(video.get('bitrate'), 1000),
                                'vcodec': video.get('codec'),
                                'width': int_or_none(video.get('width')),
                            })
                            audio = try_get(video, lambda x: x['audios'][0], dict)
                            if audio:
                                f.update({
                                    'acodec': audio.get('codec'),
                                    'asr': int_or_none(audio.get('sampleRate')),
                                })
                        formats.append(f)
                    elif rendition_type == 'index':
                        mime_type = link.get('mimeType')
                        if mime_type == 'application/smil+xml':
                            formats.extend(self._extract_smil_formats(
                                href, video_id, fatal=False))
                        elif mime_type == 'application/x-mpegURL':
                            formats.extend(self._extract_m3u8_formats(
                                href, video_id, 'mp4', 'm3u8_native',
                                m3u8_id='hls', fatal=False))
                        elif mime_type == 'application/hds+xml':
                            formats.extend(self._extract_f4m_formats(
                                href, video_id, f4m_id='hds', fatal=False))
                        elif mime_type == 'application/dash+xml':
                            formats.extend(self._extract_f4m_formats(
                                href, video_id, f4m_id='hds', fatal=False))
                        elif mime_type == 'application/vnd.ms-sstr+xml':
                            formats.extend(self._extract_ism_formats(
                                href, video_id, ism_id='mss', fatal=False))
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': metadata.get('description'),
            'timestamp': parse_iso8601(media.get('created')),
            'thumbnails': thumbnails,
            'subtitles': subtitles,
            'duration': duration,
            'tags': media.get('tags'),
            'formats': formats,
        }
