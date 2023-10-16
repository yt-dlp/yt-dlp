import datetime
import hashlib
import hmac

from .common import InfoExtractor
from ..compat import compat_urllib_parse_urlencode


class AWSIE(InfoExtractor):  # XXX: Conventionally, base classes should end with BaseIE/InfoExtractor
    _AWS_ALGORITHM = 'AWS4-HMAC-SHA256'
    _AWS_REGION = 'us-east-1'

    def _aws_execute_api(self, aws_dict, video_id, query=None):
        query = query or {}
        amz_date = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        date = amz_date[:8]
        headers = {
            'Accept': 'application/json',
            'Host': self._AWS_PROXY_HOST,
            'X-Amz-Date': amz_date,
            'X-Api-Key': self._AWS_API_KEY
        }
        session_token = aws_dict.get('session_token')
        if session_token:
            headers['X-Amz-Security-Token'] = session_token

        def aws_hash(s):
            return hashlib.sha256(s.encode('utf-8')).hexdigest()

        # Task 1: http://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html
        canonical_querystring = compat_urllib_parse_urlencode(query)
        canonical_headers = ''
        for header_name, header_value in sorted(headers.items()):
            canonical_headers += '%s:%s\n' % (header_name.lower(), header_value)
        signed_headers = ';'.join([header.lower() for header in sorted(headers.keys())])
        canonical_request = '\n'.join([
            'GET',
            aws_dict['uri'],
            canonical_querystring,
            canonical_headers,
            signed_headers,
            aws_hash('')
        ])

        # Task 2: http://docs.aws.amazon.com/general/latest/gr/sigv4-create-string-to-sign.html
        credential_scope_list = [date, self._AWS_REGION, 'execute-api', 'aws4_request']
        credential_scope = '/'.join(credential_scope_list)
        string_to_sign = '\n'.join([self._AWS_ALGORITHM, amz_date, credential_scope, aws_hash(canonical_request)])

        # Task 3: http://docs.aws.amazon.com/general/latest/gr/sigv4-calculate-signature.html
        def aws_hmac(key, msg):
            return hmac.new(key, msg.encode('utf-8'), hashlib.sha256)

        def aws_hmac_digest(key, msg):
            return aws_hmac(key, msg).digest()

        def aws_hmac_hexdigest(key, msg):
            return aws_hmac(key, msg).hexdigest()

        k_signing = ('AWS4' + aws_dict['secret_key']).encode('utf-8')
        for value in credential_scope_list:
            k_signing = aws_hmac_digest(k_signing, value)

        signature = aws_hmac_hexdigest(k_signing, string_to_sign)

        # Task 4: http://docs.aws.amazon.com/general/latest/gr/sigv4-add-signature-to-request.html
        headers['Authorization'] = ', '.join([
            '%s Credential=%s/%s' % (self._AWS_ALGORITHM, aws_dict['access_key'], credential_scope),
            'SignedHeaders=%s' % signed_headers,
            'Signature=%s' % signature,
        ])

        return self._download_json(
            'https://%s%s%s' % (self._AWS_PROXY_HOST, aws_dict['uri'], '?' + canonical_querystring if canonical_querystring else ''),
            video_id, headers=headers)
