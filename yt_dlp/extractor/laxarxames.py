from .common import InfoExtractor


class LaXarxaMesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?laxarxames\.cat/(?:[^/]+/)*?(player|movie-details)/(?P<id>[0-9]+)'
    _NETRC_MACHINE = 'laxarxames'
    _IS_LOGGED_IN = False
    _LOGIN_URL = 'https://www.laxarxames.cat/login'
    _TESTS = [{
        'url': 'https://www.laxarxames.cat/player/3459421',
        'md5': '0966f46c34275934c19af78f3df6e2bc',
        'info_dict': {
            'id': '3459421',
            'ext': 'mp4',
            'title': 'Resum | UA Horta — UD Viladecans',
            'type': 'video/mp4',
        },
        'skip': 'Requires login',
    }]

    def _perform_login(self, username, password):
        login = self._download_json(
            'https://api.laxarxames.cat/Authorization/SignIn', None, note='Logging in', headers={
                'X-Tenantorigin': 'https://laxarxames.cat',
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/plain, */*',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)',
                'Origin': 'https://www.laxarxames.cat',
            }, data=json.dumps({
                'Username': username,
                'Password': password,
                'Device': {
                    'PlatformCode': 'WEB',
                    'Name': 'Mac OS ()',
                },
            }).encode('utf-8'))
        )

        if not login['AuthorizationToken']:
            raise Exception('Login failed')
        else:
            self._set_cookie('www.laxarxames.cat', 'didomi_token', login['AuthorizationToken']['Token'])

    def _real_extract(self, url):
        video_id = self._match_id(url)
        authorization = self._get_cookies('https://www.laxarxames.cat/').get('didomi_token')

        if not authorization:
            self.raise_login_required()
        mediaplayinfo = self._download_json(
            'https://api.laxarxames.cat/Media/GetMediaPlayInfo',
            video_id,
            data=b'{"MediaId":%s,"StreamType":"MAIN"}' % video_id.encode(),
            headers={
                'Authorization': 'Bearer ' + authorization.value,
                'X-Tenantorigin': 'https://laxarxames.cat',
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/plain, */*',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)',
                'Origin': 'https://www.laxarxames.cat',
            }
        )

        contenturl = mediaplayinfo['ContentUrl']
        title = mediaplayinfo['Title']

        videodata = self._download_json(
            'https://edge.api.brightcove.com/playback/v1/accounts/5779379807001/videos/' + contenturl,
            video_id,
            headers={
                'Accept': 'application/json;pk=BCpkADawqM2uXEFYflHlCdYKQdRAfbdvR3tpOY9_jxup5aqCrMmJxjXtV6k9Khk7hKqFFp15BwULNmQkWBik0SJgtgqDAoni09Ezx2w4dIGs1GAjhnLMWXaeCmveEusJKQYs83DIlSUIPccu'
            }
        )

        sources = videodata['sources']

        formats = []
        for source in sources:
            url = source['src']
            type = ''
            manifest_url = None
            if 'type' in source:
                type = source['type']
                manifest_url = source['src']
            else:
                type = 'video/mp4'
            formats.append({
                'url': url,
                'type': type,
                'manifest_url': manifest_url
            })

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
        }
