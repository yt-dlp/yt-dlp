import os

from .common import PostProcessor
from ..compat import compat_os_name
from ..utils import (
    PostProcessingError,
    XAttrMetadataError,
    XAttrUnavailableError,
    hyphenate_date,
    write_xattr,
)


class XAttrMetadataPP(PostProcessor):
    """Set extended attributes on downloaded file (if xattr support is found)

    More info about extended attributes for media:
        http://freedesktop.org/wiki/CommonExtendedAttributes/
        http://www.freedesktop.org/wiki/PhreedomDraft/
        http://dublincore.org/documents/usageguide/elements.shtml

    TODO:
        * capture youtube keywords and put them in 'user.dublincore.subject' (comma-separated)
        * figure out which xattrs can be used for 'duration', 'thumbnail', 'resolution'
    """

    XATTR_MAPPING = {
        'user.xdg.referrer.url': 'webpage_url',
        # 'user.xdg.comment': 'description',
        'user.dublincore.title': 'title',
        'user.dublincore.date': 'upload_date',
        'user.dublincore.description': 'description',
        'user.dublincore.contributor': 'uploader',
        'user.dublincore.format': 'format',
    }

    def run(self, info):
        mtime = os.stat(info['filepath']).st_mtime
        self.to_screen('Writing metadata to file\'s xattrs')
        try:
            for xattrname, infoname in self.XATTR_MAPPING.items():
                value = info.get(infoname)
                if value:
                    if infoname == 'upload_date':
                        value = hyphenate_date(value)
                    write_xattr(info['filepath'], xattrname, value.encode())

        except XAttrUnavailableError as e:
            raise PostProcessingError(str(e))
        except XAttrMetadataError as e:
            if e.reason == 'NO_SPACE':
                self.report_warning(
                    'There\'s no disk space left, disk quota exceeded or filesystem xattr limit exceeded. '
                    'Some extended attributes are not written')
            elif e.reason == 'VALUE_TOO_LONG':
                self.report_warning('Unable to write extended attributes due to too long values.')
            else:
                tip = ('You need to use NTFS' if compat_os_name == 'nt'
                       else 'You may have to enable them in your "/etc/fstab"')
                raise PostProcessingError(f'This filesystem doesn\'t support extended attributes. {tip}')

        self.try_utime(info['filepath'], mtime, mtime)
        return [], info
