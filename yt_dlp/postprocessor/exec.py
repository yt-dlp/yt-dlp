from .common import PostProcessor
from ..utils import Popen, PostProcessingError, shell_quote, variadic


class ExecPP(PostProcessor):

    def __init__(self, downloader, exec_cmd):
        PostProcessor.__init__(self, downloader)
        self.exec_cmd = variadic(exec_cmd)

    def parse_cmd(self, cmd, info):
        tmpl, tmpl_dict = self._downloader.prepare_outtmpl(cmd, info)
        if tmpl_dict:  # if there are no replacements, tmpl_dict = {}
            return self._downloader.escape_outtmpl(tmpl) % tmpl_dict

        filepath = info.get('filepath', info.get('_filename'))
        # If video, and no replacements are found, replace {} for backard compatibility
        if filepath:
            if '{}' not in cmd:
                cmd += ' {}'
            cmd = cmd.replace('{}', shell_quote(filepath))
        return cmd

    def run(self, info):
        for tmpl in self.exec_cmd:
            cmd = self.parse_cmd(tmpl, info)
            self.to_screen(f'Executing command: {cmd}')
            _, _, return_code = Popen.run(cmd, shell=True)
            if return_code != 0:
                raise PostProcessingError(f'Command returned error code {return_code}')
        return [], info


# Deprecated
class ExecAfterDownloadPP(ExecPP):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.deprecation_warning(
            'yt_dlp.postprocessor.ExecAfterDownloadPP is deprecated '
            'and may be removed in a future version. Use yt_dlp.postprocessor.ExecPP instead')
