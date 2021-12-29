# coding: utf-8

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
        filepath = info.get('filepath')
        if filepath:  # PP was called after download (default)
            self.to_screen(f'Post-processed {filepath!r} with {self._kwargs}')
        else:  # PP was called before actual download
            filepath = info.get('_filename')
            self.to_screen(f'Pre-processed {filepath!r} with {self._kwargs}')
        return [], info  # return list_of_files_to_delete, info_dict
