import base64
import binascii
import datetime as dt
import hashlib
import hmac
import json
import os
import urllib.parse

from .common import InfoExtractor
from ..utils import ExtractorError, int_or_none
from ..utils.traversal import get_first, traverse_obj


class GoPlayIE(InfoExtractor):
    _VALID_URL = r'https?://(www\.)?goplay\.be/video/([^/?#]+/[^/?#]+/|)(?P<id>[^/#]+)'

    _NETRC_MACHINE = 'goplay'

    _TESTS = [{
        'url': 'https://www.goplay.be/video/de-slimste-mens-ter-wereld/de-slimste-mens-ter-wereld-s22/de-slimste-mens-ter-wereld-s22-aflevering-1',
        'info_dict': {
            'id': '2baa4560-87a0-421b-bffc-359914e3c387',
            'ext': 'mp4',
            'title': 'De Slimste Mens ter Wereld - S22 - Aflevering 1',
            'description': r're:In aflevering 1 nemen Daan Alferink, Tess Elst en Xander De Rycke .{66}',
            'series': 'De Slimste Mens ter Wereld',
            'episode': 'Wordt aangekondigd',
            'season_number': 22,
            'episode_number': 1,
            'season': 'Season 22',
        },
        'params': {'skip_download': True},
        'skip': 'This video is only available for registered users',
    }, {
        'url': 'https://www.goplay.be/video/1917',
        'info_dict': {
            'id': '40cac41d-8d29-4ef5-aa11-75047b9f0907',
            'ext': 'mp4',
            'title': '1917',
            'description': r're:Op het hoogtepunt van de Eerste Wereldoorlog krijgen twee jonge .{94}',
        },
        'params': {'skip_download': True},
        'skip': 'This video is only available for registered users',
    }, {
        'url': 'https://www.goplay.be/video/de-mol/de-mol-s11/de-mol-s11-aflevering-1#autoplay',
        'info_dict': {
            'id': 'ecb79672-92b9-4cd9-a0d7-e2f0250681ee',
            'ext': 'mp4',
            'title': 'De Mol - S11 - Aflevering 1',
            'description': r're:Tien kandidaten beginnen aan hun verovering van Amerika en ontmoeten .{102}',
            'episode': 'Episode 1',
            'series': 'De Mol',
            'season_number': 11,
            'episode_number': 1,
            'season': 'Season 11',
        },
        'params': {'skip_download': True},
        'skip': 'This video is only available for registered users',
    }]

    _id_token = None

    def _perform_login(self, username, password):
        self.report_login()
        aws = AwsIdp(ie=self, pool_id='eu-west-1_dViSsKM5Y', client_id='6s1h851s8uplco5h6mqh1jac8m')
        self._id_token, _ = aws.authenticate(username=username, password=password)

    def _real_initialize(self):
        if not self._id_token:
            raise self.raise_login_required(method='password')

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        nextjs_data = self._search_nextjs_v13_data(webpage, display_id)
        meta = get_first(nextjs_data, (
            lambda k, v: k in ('video', 'meta') and v['path'] == urllib.parse.urlparse(url).path))

        video_id = meta['uuid']
        info_dict = traverse_obj(meta, {
            'title': ('title', {str}),
            'description': ('description', {str.strip}),
        })

        if traverse_obj(meta, ('program', 'subtype')) != 'movie':
            for season_data in traverse_obj(nextjs_data, (..., 'playlists', ..., {dict})):
                episode_data = traverse_obj(season_data, ('videos', lambda _, v: v['videoId'] == video_id, any))
                if not episode_data:
                    continue

                season_number = traverse_obj(season_data, ('season', {int_or_none}))
                info_dict.update({
                    'episode': traverse_obj(episode_data, ('episodeTitle', {str})),
                    'episode_number': traverse_obj(episode_data, ('episodeNumber', {int_or_none})),
                    'season_number': season_number,
                    'series': self._search_regex(
                        fr'^(.+)? - S{season_number} - ', info_dict.get('title'), 'series', default=None),
                })
                break

        api = self._download_json(
            f'https://api.goplay.be/web/v1/videos/long-form/{video_id}',
            video_id, headers={
                'Authorization': f'Bearer {self._id_token}',
                **self.geo_verification_headers(),
            })

        if 'manifestUrls' in api:
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                api['manifestUrls']['hls'], video_id, ext='mp4', m3u8_id='HLS')

        else:
            if 'ssai' not in api:
                raise ExtractorError('expecting Google SSAI stream')

            ssai_content_source_id = api['ssai']['contentSourceID']
            ssai_video_id = api['ssai']['videoID']

            dai = self._download_json(
                f'https://dai.google.com/ondemand/dash/content/{ssai_content_source_id}/vid/{ssai_video_id}/streams',
                video_id, data=b'{"api-key":"null"}',
                headers={'content-type': 'application/json'})

            periods = self._extract_mpd_periods(dai['stream_manifest'], video_id)

            # skip pre-roll and mid-roll ads
            periods = [p for p in periods if '-ad-' not in p['id']]

            formats, subtitles = self._merge_mpd_periods(periods)

        info_dict.update({
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
        })
        return info_dict


# Taken from https://github.com/add-ons/plugin.video.viervijfzes/blob/master/resources/lib/viervijfzes/auth_awsidp.py
# Released into Public domain by https://github.com/michaelarnauts

class InvalidLoginException(ExtractorError):
    """ The login credentials are invalid """


class AuthenticationException(ExtractorError):
    """ Something went wrong while logging in """


class AwsIdp:
    """ AWS Identity Provider """

    def __init__(self, ie, pool_id, client_id):
        """
        :param InfoExtrator ie: The extractor that instantiated this class.
        :param str pool_id:     The AWS user pool to connect to (format: <region>_<poolid>).
                                E.g.: eu-west-1_aLkOfYN3T
        :param str client_id:   The client application ID (the ID of the application connecting)
        """

        self.ie = ie

        self.pool_id = pool_id
        if '_' not in self.pool_id:
            raise ValueError('Invalid pool_id format. Should be <region>_<poolid>.')

        self.client_id = client_id
        self.region = self.pool_id.split('_')[0]
        self.url = f'https://cognito-idp.{self.region}.amazonaws.com/'

        # Initialize the values
        # https://github.com/aws/amazon-cognito-identity-js/blob/master/src/AuthenticationHelper.js#L22
        self.n_hex = (
            'FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1'
            '29024E088A67CC74020BBEA63B139B22514A08798E3404DD'
            'EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245'
            'E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED'
            'EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D'
            'C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F'
            '83655D23DCA3AD961C62F356208552BB9ED529077096966D'
            '670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B'
            'E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9'
            'DE2BCBF6955817183995497CEA956AE515D2261898FA0510'
            '15728E5A8AAAC42DAD33170D04507A33A85521ABDF1CBA64'
            'ECFB850458DBEF0A8AEA71575D060C7DB3970F85A6E1E4C7'
            'ABF5AE8CDB0933D71E8C94E04A25619DCEE3D2261AD2EE6B'
            'F12FFA06D98A0864D87602733EC86A64521F2B18177B200C'
            'BBE117577A615D6C770988C0BAD946E208E24FA074E5AB31'
            '43DB5BFCE0FD108E4B82D120A93AD2CAFFFFFFFFFFFFFFFF')

        # https://github.com/aws/amazon-cognito-identity-js/blob/master/src/AuthenticationHelper.js#L49
        self.g_hex = '2'
        self.info_bits = bytearray('Caldera Derived Key', 'utf-8')

        self.big_n = self.__hex_to_long(self.n_hex)
        self.g = self.__hex_to_long(self.g_hex)
        self.k = self.__hex_to_long(self.__hex_hash('00' + self.n_hex + '0' + self.g_hex))
        self.small_a_value = self.__generate_random_small_a()
        self.large_a_value = self.__calculate_a()

    def authenticate(self, username, password):
        """ Authenticate with a username and password. """
        # Step 1: First initiate an authentication request
        auth_data_dict = self.__get_authentication_request(username)
        auth_data = json.dumps(auth_data_dict).encode()
        auth_headers = {
            'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth',
            'Accept-Encoding': 'identity',
            'Content-Type': 'application/x-amz-json-1.1',
        }
        auth_response_json = self.ie._download_json(
            self.url, None, data=auth_data, headers=auth_headers,
            note='Authenticating username', errnote='Invalid username')
        challenge_parameters = auth_response_json.get('ChallengeParameters')

        if auth_response_json.get('ChallengeName') != 'PASSWORD_VERIFIER':
            raise AuthenticationException(auth_response_json['message'])

        # Step 2: Respond to the Challenge with a valid ChallengeResponse
        challenge_request = self.__get_challenge_response_request(challenge_parameters, password)
        challenge_data = json.dumps(challenge_request).encode()
        challenge_headers = {
            'X-Amz-Target': 'AWSCognitoIdentityProviderService.RespondToAuthChallenge',
            'Content-Type': 'application/x-amz-json-1.1',
        }
        auth_response_json = self.ie._download_json(
            self.url, None, data=challenge_data, headers=challenge_headers,
            note='Authenticating password', errnote='Invalid password')

        if 'message' in auth_response_json:
            raise InvalidLoginException(auth_response_json['message'])
        return (
            auth_response_json['AuthenticationResult']['IdToken'],
            auth_response_json['AuthenticationResult']['RefreshToken'],
        )

    def __get_authentication_request(self, username):
        """

        :param str username:    The username to use

        :return: A full Authorization request.
        :rtype: dict
        """
        return {
            'AuthParameters': {
                'USERNAME': username,
                'SRP_A': self.__long_to_hex(self.large_a_value),
            },
            'AuthFlow': 'USER_SRP_AUTH',
            'ClientId': self.client_id,
        }

    def __get_challenge_response_request(self, challenge_parameters, password):
        """ Create a Challenge Response Request object.

        :param dict[str,str|imt] challenge_parameters:  The parameters for the challenge.
        :param str password:                            The password.

        :return: A valid and full request data object to use as a response for a challenge.
        :rtype: dict
        """
        user_id = challenge_parameters['USERNAME']
        user_id_for_srp = challenge_parameters['USER_ID_FOR_SRP']
        srp_b = challenge_parameters['SRP_B']
        salt = challenge_parameters['SALT']
        secret_block = challenge_parameters['SECRET_BLOCK']

        timestamp = self.__get_current_timestamp()

        # Get a HKDF key for the password, SrpB and the Salt
        hkdf = self.__get_hkdf_key_for_password(
            user_id_for_srp,
            password,
            self.__hex_to_long(srp_b),
            salt,
        )
        secret_block_bytes = base64.standard_b64decode(secret_block)

        # the message is a combo of the pool_id, provided SRP userId, the Secret and Timestamp
        msg = \
            bytearray(self.pool_id.split('_')[1], 'utf-8') + \
            bytearray(user_id_for_srp, 'utf-8') + \
            bytearray(secret_block_bytes) + \
            bytearray(timestamp, 'utf-8')
        hmac_obj = hmac.new(hkdf, msg, digestmod=hashlib.sha256)
        signature_string = base64.standard_b64encode(hmac_obj.digest()).decode('utf-8')
        return {
            'ChallengeResponses': {
                'USERNAME': user_id,
                'TIMESTAMP': timestamp,
                'PASSWORD_CLAIM_SECRET_BLOCK': secret_block,
                'PASSWORD_CLAIM_SIGNATURE': signature_string,
            },
            'ChallengeName': 'PASSWORD_VERIFIER',
            'ClientId': self.client_id,
        }

    def __get_hkdf_key_for_password(self, username, password, server_b_value, salt):
        """ Calculates the final hkdf based on computed S value, and computed U value and the key.

        :param str username:        Username.
        :param str password:        Password.
        :param int server_b_value:  Server B value.
        :param int salt:            Generated salt.

        :return Computed HKDF value.
        :rtype: object
        """

        u_value = self.__calculate_u(self.large_a_value, server_b_value)
        if u_value == 0:
            raise ValueError('U cannot be zero.')
        username_password = '{}{}:{}'.format(self.pool_id.split('_')[1], username, password)
        username_password_hash = self.__hash_sha256(username_password.encode())

        x_value = self.__hex_to_long(self.__hex_hash(self.__pad_hex(salt) + username_password_hash))
        g_mod_pow_xn = pow(self.g, x_value, self.big_n)
        int_value2 = server_b_value - self.k * g_mod_pow_xn
        s_value = pow(int_value2, self.small_a_value + u_value * x_value, self.big_n)
        return self.__compute_hkdf(
            bytearray.fromhex(self.__pad_hex(s_value)),
            bytearray.fromhex(self.__pad_hex(self.__long_to_hex(u_value))),
        )

    def __compute_hkdf(self, ikm, salt):
        """ Standard hkdf algorithm

        :param {Buffer} ikm Input key material.
        :param {Buffer} salt Salt value.
        :return {Buffer} Strong key material.
        """

        prk = hmac.new(salt, ikm, hashlib.sha256).digest()
        info_bits_update = self.info_bits + bytearray(chr(1), 'utf-8')
        hmac_hash = hmac.new(prk, info_bits_update, hashlib.sha256).digest()
        return hmac_hash[:16]

    def __calculate_u(self, big_a, big_b):
        """ Calculate the client's value U which is the hash of A and B

        :param int big_a:   Large A value.
        :param int big_b:   Server B value.

        :return Computed U value.
        :rtype: int
        """

        u_hex_hash = self.__hex_hash(self.__pad_hex(big_a) + self.__pad_hex(big_b))
        return self.__hex_to_long(u_hex_hash)

    def __generate_random_small_a(self):
        """ Helper function to generate a random big integer

        :return a random value.
        :rtype: int
        """
        random_long_int = self.__get_random(128)
        return random_long_int % self.big_n

    def __calculate_a(self):
        """ Calculate the client's public value A = g^a%N with the generated random number a

        :return Computed large A.
        :rtype: int
        """

        big_a = pow(self.g, self.small_a_value, self.big_n)
        # safety check
        if (big_a % self.big_n) == 0:
            raise ValueError('Safety check for A failed')
        return big_a

    @staticmethod
    def __long_to_hex(long_num):
        return f'{long_num:x}'

    @staticmethod
    def __hex_to_long(hex_string):
        return int(hex_string, 16)

    @staticmethod
    def __hex_hash(hex_string):
        return AwsIdp.__hash_sha256(bytearray.fromhex(hex_string))

    @staticmethod
    def __hash_sha256(buf):
        """AuthenticationHelper.hash"""
        digest = hashlib.sha256(buf).hexdigest()
        return (64 - len(digest)) * '0' + digest

    @staticmethod
    def __pad_hex(long_int):
        """ Converts a Long integer (or hex string) to hex format padded with zeroes for hashing

        :param int|str long_int:    Number or string to pad.

        :return Padded hex string.
        :rtype: str
        """

        if not isinstance(long_int, str):
            hash_str = AwsIdp.__long_to_hex(long_int)
        else:
            hash_str = long_int
        if len(hash_str) % 2 == 1:
            hash_str = f'0{hash_str}'
        elif hash_str[0] in '89ABCDEFabcdef':
            hash_str = f'00{hash_str}'
        return hash_str

    @staticmethod
    def __get_random(nbytes):
        random_hex = binascii.hexlify(os.urandom(nbytes))
        return AwsIdp.__hex_to_long(random_hex)

    @staticmethod
    def __get_current_timestamp():
        """ Creates a timestamp with the correct English format.

        :return: timestamp in format 'Sun Jan 27 19:00:04 UTC 2019'
        :rtype: str
        """

        # We need US only data, so we cannot just do a strftime:
        # Sun Jan 27 19:00:04 UTC 2019
        months = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

        time_now = dt.datetime.now(dt.timezone.utc)
        format_string = f'{days[time_now.weekday()]} {months[time_now.month]} {time_now.day} %H:%M:%S UTC %Y'
        return time_now.strftime(format_string)

    def __str__(self):
        return 'AWS IDP Client for:\nRegion: {}\nPoolId: {}\nAppId:  {}'.format(
            self.region, self.pool_id.split('_')[1], self.client_id,
        )
