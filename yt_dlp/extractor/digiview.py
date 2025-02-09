from .youtube import YoutubeIE
from ..utils import int_or_none, urlencode_postdata


class DigiviewIE(YoutubeIE):
    IE_DESC = 'Digiview'
    IE_NAME = 'digiview'
    _VALID_URL = r'https?://(?:www\.)?ladigitale\.dev/digiview/#/v/(?P<id>[0-9a-f]+)'
    _TESTS = [
        {
            # normal video
            'url': 'https://ladigitale.dev/digiview/#/v/67a8e50aee2ec',
            'info_dict': {
                'title': 'Big Buck Bunny 60fps 4K - Official Blender Foundation Short Film',
            },
        },
        {
            # cut video
            'url': 'https://ladigitale.dev/digiview/#/v/67a8e51d0dd58',
            'info_dict': {
                'title': 'Big Buck Bunny 60fps 4K - Official Blender Foundation Short Film',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage_data = self._download_json(
            'https://ladigitale.dev/digiview/inc/recuperer_video.php', video_id,
            data=urlencode_postdata({'id': video_id}))

        youtube_ie = YoutubeIE()
        youtube_ie.set_downloader(self._downloader)
        info = youtube_ie._real_extract(webpage_data['videoId'])

        # replace the YouTube metadata by the Digiview one
        info['title'] = webpage_data.get('titre') or info['title']
        info['description'] = webpage_data.get('description') or info['description']

        ffmpeg_args = []

        start_time = int_or_none(webpage_data.get('debut'))
        if start_time is not None and start_time != 0:
            ffmpeg_args.extend(['-ss', str(start_time)])

        end_time = int_or_none(webpage_data.get('fin'))
        if end_time is not None and end_time != info['duration']:
            ffmpeg_args.extend(['-t', str(end_time - (start_time or 0))])

        if ffmpeg_args and self._downloader:
            # cut the video if specified in the Digiview webpage
            ppargs = self._downloader.params.get('postprocessor_args')
            ppargs.setdefault('merger', []).extend(ffmpeg_args)

        return info
