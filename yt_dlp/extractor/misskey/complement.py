from .misskey import MisskeyIE
from ...compat import compat_str


class BaseMisskeyComplement(object):
    """
    This class (Complement) is used for extending support for more formats,
    added by a specific instance.
    """
    _INSTANCE_RE = r''

    def _extract_formats(self, ie: MisskeyIE, video_id: compat_str, file) -> list:
        """
        Return list of formats which is not available in standard extraction.
        Sorting is done in MisskeyIE, so you don't have to do that in it.
        """
        raise Exception('Implement this in subclasses')


class MisskeyIoComplement(BaseMisskeyComplement):
    _INSTANCE_RE = r'^misskey\.io$'

    def _extract_formats(self, ie: MisskeyIE, video_id: compat_str, file) -> list:
        mimetype = file.get('type')
        if not mimetype or not mimetype.startswith('video/'):
            return []
        embed_url = 'https://s3encode.arkjp.net/?video=%s' % file.get('url')
        embed_webpage = ie._download_webpage(
            embed_url, video_id, note='Downloading embed webpage',
            headers={
                'Referer': 'https://misskey.io/',
            })
        vdeliv_embed_id = ie._search_regex(
            r'<iframe src="https://iframe\.videodelivery\.net/([a-zA-Z0-9]+)"',
            embed_webpage, 'videodeliver embed URL', group=1)
        vdeliv_mpd_url = f'https://videodelivery.net/{vdeliv_embed_id}/manifest/video.mpd?parentOrigin=https%3A%2F%2Fs3encode.arkjp.net'

        return ie._extract_mpd_formats(vdeliv_mpd_url, video_id, mpd_id='mpd', fatal=False)


_COMPLEMENTS = [MisskeyIoComplement]

__all__ = ['_COMPLEMENTS']
