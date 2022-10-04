import json

from .common import TokenGenerator


class NFLTokenGenerator(TokenGenerator):
    _AUTHORIZATION = None

    def generate(ie, anvack, mcp_id):
        if not NFLTokenGenerator._AUTHORIZATION:
            reroute = ie._download_json(
                'https://api.nfl.com/v1/reroute', mcp_id,
                data=b'grant_type=client_credentials',
                headers={'X-Domain-Id': 100})
            NFLTokenGenerator._AUTHORIZATION = '%s %s' % (reroute.get('token_type') or 'Bearer', reroute['access_token'])
        return ie._download_json(
            'https://api.nfl.com/v3/shield/', mcp_id, data=json.dumps({
                'query': '''{
  viewer {
    mediaToken(anvack: "%s", id: %s) {
      token
    }
  }
}''' % (anvack, mcp_id),
            }).encode(), headers={
                'Authorization': NFLTokenGenerator._AUTHORIZATION,
                'Content-Type': 'application/json',
            })['data']['viewer']['mediaToken']['token']
