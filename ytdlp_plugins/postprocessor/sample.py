# ⚠ Don't use relative imports
from yt_dlp.postprocessor.common import PostProcessor


# ℹ️ See the docstring of yt_dlp.postprocessor.common.PostProcessor
class SamplePluginPP(PostProcessor):
    def __init__(self, downloader=None, **kwargs):
        # ⚠ Only kwargs can be passed from the CLI, and all argument values will be string
        # Also, "downloader", "when" and "key" are reserved names
        super().__init__(downloader)
        self._kwargs = kwargs

    # ℹ️ See docstring of yt_dlp.postprocessor.common.PostProcessor.run
    def run(self, info):
        if info.get('_type', 'video') != 'video':  # PP was called for playlist
            self.to_screen(f'Post-processing playlist {info.get("id")!r} with {self._kwargs}')
        elif info.get('filepath'):  # PP was called after download (default)
            filepath = info.get('filepath')
            self.to_screen(f'Post-processed {filepath!r} with {self._kwargs}')
        elif info.get('requested_downloads'):  # PP was called after_video
            filepaths = [f.get('filepath') for f in info.get('requested_downloads')]
            self.to_screen(f'Post-processed {filepaths!r} with {self._kwargs}')
        else:  # PP was called before actual download
            filepath = info.get('_filename')
            self.to_screen(f'Pre-processed {filepath!r} with {self._kwargs}')
        return [], info  # return list_of_files_to_delete, info_dict
