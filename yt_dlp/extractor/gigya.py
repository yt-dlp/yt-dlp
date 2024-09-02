from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    urlencode_postdata,
)


class GigyaBaseIE(InfoExtractor):
    def _gigya_login(self, auth_data):
        auth_info = self._download_json(
            'https://accounts.eu1.gigya.com/accounts.login', None,
            note='Logging in', errnote='Unable to log in',
            data=urlencode_postdata(auth_data))

        error_message = auth_info.get('errorDetails') or auth_info.get('errorMessage')
        if error_message:
            raise ExtractorError(
                f'Unable to login: {error_message}', expected=True)
        return auth_info
