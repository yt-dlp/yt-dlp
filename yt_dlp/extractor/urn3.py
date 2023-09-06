from datetime import datetime
from ..networking import HEADRequest
from ..networking.exceptions import TransportError
from ..utils import js_to_json
from urllib.parse import urlparse
from .common import InfoExtractor, ExtractorError
from box import Box, BoxList


class URN3IE(InfoExtractor):
    IE_DESC = 'Harvard Library, Digital Collections'
    _VALID_URL = r"""https?://nrs.harvard.edu/(urn|URN)-3:FHCL(.HOUGH|):[0-9]+"""
    _TESTS = [{
        'url': 'https://nrs.harvard.edu/urn-3:FHCL:2453393',
    }]
    info = Box(extractor="URN3", series={})

    def _getChanInfo(self, sets: Box):
        all_collections = self._download_json(
            'https://api.lib.harvard.edu/v2/collections.json',
            'Fetching channel metadata for',
            sets.set.setSpec,
            query={'limit': 100},
        )

        for chan in [
            Box(c) for c in all_collections
            if c['systemId'] == int(sets.set.systemId)
        ]:
            self.info.channel = Box(
                id=f"{self.info.urn.split(':')[0]}_{sets.set.systemId}",
                title=sets.set.setName,
                title_short=sets.set.setSpec,
                description=chan.setDescription,
                thumbnails=[Box(
                    preference=1,
                    url=chan.thumbnailUrn,
                )],
                url=chan.collectionUrn,
            )
            self.info.channel.id = self.info.channel.id.lower()
            self.info.channel_id = self.info.channel.id
            self.info.channel_url = self.info.channel.url
            self.info.channel_title = sets.set.setName
            self.info.channel_title_short = sets.set.setSpec
            self._baseUrl = sets.set.baseUrl

    def _getId(self, mod: Box) -> None:
        for e in mod.extension:
            if (hasattr(e, "DRSMetadata") and e.DRSMetadata.inDRS):
                if e.DRSMetadata.uriType in ("SDS", "SDS_VIDEO"):
                    # self.info.id = e.DRSMetadata.drsFileId
                    self.info.id = self.info.urn
                    self.info.url = e.DRSMetadata.fileDeliveryURL
                    self.info.insertionDate = datetime.fromisoformat(
                        e.DRSMetadata.insertionDate
                    )
                    self.info.upload_date = self.info.insertionDate.strftime(
                        '%Y%m%d'
                    )
                elif (e.DRSMetadata.uriType == "PDS" and
                        hasattr(e.DRSMetadata, 'metsLabel')):
                    self.info.metsLabel = e.DRSMetadata.metsLabel

    def _isrecord_valid(self, mod: Box) -> Box | None:
        isvalid = False
        for e in mod.extension:
            if (hasattr(e, 'sets') and e.sets is not None):
                isvalid = True
                self._getChanInfo(e.sets)
                break

        return mod if isvalid else None

    def _getName(self, mod: Box) -> None:
        if hasattr(mod, 'name'):
            for name in mod.name:
                if isinstance(name.role, BoxList):
                    for role in name.role:
                        if role.roleTerm == "Interviewee":
                            self.info.interviewee = name.namePart
                        if role.roleTerm == "Interviewer":
                            self.info.interviewer = name.namePart
                elif name.role.roleTerm == "Interviewee":
                    self.info.interviewee = name.namePart
                elif name.role.roleTerm == "Interviewer":
                    self.info.interviewer = name.namePart

    def _getNotes(self, mod: Box) -> None:
        if not hasattr(mod, 'note'):
            return

        for note in mod.note:
            if note.type == 'gender':
                self.info.gender = note.text
            if note.type == 'biographical/historical':
                self.info.significance = f"{note.type}: {note.text}"

    def _getSeasonEpisode(self, mod: Box) -> None:
        recordIdentifier = mod.recordInfo.recordIdentifier.text
        recordIdentifier_split = recordIdentifier.split('.')
        self.info.season = recordIdentifier_split[0]

    def _getTitleInfo(self, mod: Box) -> None:
        self.info.title = mod.titleInfo.title

        if not hasattr(mod.titleInfo, 'partNumber'):
            return

        self.info.channel.type = 'serial'
        self.info.series.title = self.info.title
        self.info.series.part = f"{mod.titleInfo.partNumber}"
        self.info.title += f" {mod.titleInfo.partNumber}"

    def _getCategories(self, mod: Box) -> None:
        self.info.categories = []

        if hasattr(mod, 'genre'):
            self.info.genre = mod.genre
            self.info.categories += [mod.genre]

        if not hasattr(mod, 'subject'):
            return

        self.info.topics = [
            s.topic for s in mod.subject if hasattr(s, 'topic')
        ]

    def _getGeoChrono(self, mod: Box) -> None:
        if hasattr(mod, 'location'):
            for loc in [loc for loc in mod.location
                        if hasattr(loc, 'url')]:
                for url in [u.text for u in loc.url if
                            u.text.startswith(self._baseUrl)]:
                    self.info.more_info = url

        if not hasattr(mod, 'originInfo') or mod.originInfo is None:
            return

        if hasattr(mod.originInfo, 'place'):
            self.info.location = mod.originInfo.place.placeTerm
        if hasattr(mod.originInfo, 'dateCaptured'):
            self.info.date_captured = mod.originInfo.dateCaptured

    def _getLang(self, mod: Box) -> None:
        if not hasattr(mod.language.languageTerm, 'type'):
            return
        if mod.language.languageTerm.type == 'text':
            self.info.language = mod.language.languageTerm.text

    def _real_extract(self, url):
        self.info.original_url = self.info.url = url

        self.info.urn = url.split('/')[-1]
        harvard = Box(
            self._download_json(
                'https://api.lib.harvard.edu/v2/items.json',
                'Fetching metadata for', self.info.urn,
                query={'urn': self.info.urn},
            )['items']
        )
        mods = None
        if isinstance(harvard.mods, BoxList):
            mods = harvard.mods
        elif isinstance(harvard.mods, Box):
            mods = [harvard.mods]
        else:
            raise ExtractorError(
                f"No proper metadata for {self.info.original_url}"
            )

        for i in [m for m in mods if self._isrecord_valid(m)]:
            self._getId(i)
            self._getName(i)
            self._getNotes(i)
            self._getSeasonEpisode(i)
            self._getTitleInfo(i)
            self._getCategories(i)
            self._getGeoChrono(i)
            self._getLang(i)

        if not hasattr(self.info, 'id'):
            raise ExtractorError(f"No media found for {self.info.originl_url}")

        self._find_entries()

        return self.info

    def _follow_redirect(self) -> str:
        """Follow and Report information extraction."""
        url = self.info.url
        while (urlparse(url).netloc != "mps.lib.harvard.edu"):
            try:
                next = self._request_webpage(
                    HEADRequest(url),
                    video_id=self.info.id,
                    note=f"Resolving {self.info.url} to final URL",
                    errnote='Could not resolve final URL'
                )
            except TransportError:
                raise
            else:
                if isinstance(next, bool):
                    raise ExtractorError(f"Redirect err for {self.info.url}")
                url = next.url
        return url

    def _find_entries(self):
        # url = self._follow_redirect()
        webpage = self._download_webpage(self.info.url, self.info.id)

        jwplayer_data = self._find_jwplayer_data(webpage, self.info.id,
                                                 transform_source=js_to_json)
        if jwplayer_data is None:
            return

        playlist = [i['file'] for i in jwplayer_data['playlist']]
        jwplayer_extract = self._parse_jwplayer_data(
            jwplayer_data=jwplayer_data,
            video_id=self.info.id,
            require_title=False
        )
        if not isinstance(jwplayer_extract, dict):
            return

        self.info.entries = []

        # jwplayer_extract['_type'] == None
        self.info._type = 'multi_video'
        entries = jwplayer_extract.get('entries')
        if entries is None:
            jwplayer_extract.update({
                'channel': self.info.channel.title_short,
                'channel_id': self.info.channel.id,
                'channel_url': self.info.channel.url,
                'genre': self.info.genre,
                'id': self.info.id,
                'interviewee': self.info.interviewee,
                'interviewer': self.info.interviewer,
                'location': self.info.location,
                'original_url': self.info.original_url,
                'playlist_title': self.info.title,
                'playlist_id': self.info.id,
                'release_year': self.info.insertionDate.year,
                'title': self.info.title,
                'url': playlist[0],
                'upload_date': self.info.upload_date, } |
                ({'metsLabel': self.info.metsLabel} if hasattr(self.info,
                                                               'metsLabel')
                    else {})
                                    )
            self.info.entries = [jwplayer_extract]
            return

        # jwplayer_extract['_type'] == playlist
        for e in entries:
            idx = playlist.index(e['formats'][0]['manifest_url'])
            e.update({
                'channel': self.info.channel.title_short,
                'channel_id': self.info.channel.id,
                'channel_url': self.info.channel.url,
                'genre': self.info.genre,
                'id': f"{e['id']}-{idx}",
                'interviewee': self.info.interviewee,
                'interviewer': self.info.interviewer,
                'location': self.info.location,
                'original_url': self.info.original_url,
                'playlist_title': self.info.title,
                'playlist_id': e['id'],
                'release_year': self.info.insertionDate.year,
                'title': self.info.title,
                'upload_date': self.info.upload_date, } |
                ({'metsLabel': self.info.metsLabel} if hasattr(self.info,
                                                               'metsLabel')
                    else {}))
            self.info.entries += [e]
            self.info.protocol = e['formats'][0]['protocol']
