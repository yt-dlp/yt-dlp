from yt_dlp.postprocessor.common import PostProcessor


class NormalPluginPP(PostProcessor):
    def __init__(self, downloader=None, **kwargs):
        super().__init__(downloader)
        self._kwargs = kwargs

    def run(self, info):
        if info.get('_type', 'video') != 'video':
            self.to_screen(f'Post-processing playlist {info.get("id")!r} with {self._kwargs}')
        elif info.get('filepath'):
            filepath = info.get('filepath')
            self.to_screen(f'Post-processed {filepath!r} with {self._kwargs}')
        elif info.get('requested_downloads'):
            filepaths = [f.get('filepath') for f in info.get('requested_downloads')]
            self.to_screen(f'Post-processed {filepaths!r} with {self._kwargs}')
        else:
            filepath = info.get('_filename')
            self.to_screen(f'Pre-processed {filepath!r} with {self._kwargs}')
        return [], info
