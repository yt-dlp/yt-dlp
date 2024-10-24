import json

from .common import InfoExtractor
from ..utils import strip_or_none, traverse_obj


class BlerpIE(InfoExtractor):
    IE_NAME = 'blerp'
    _VALID_URL = r'https?://(?:www\.)?blerp\.com/soundbites/(?P<id>[0-9a-zA-Z]+)'
    _TESTS = [{
        'url': 'https://blerp.com/soundbites/6320fe8745636cb4dd677a5a',
        'info_dict': {
            'id': '6320fe8745636cb4dd677a5a',
            'title': 'Samsung Galaxy S8 Over the Horizon Ringtone 2016',
            'uploader': 'luminousaj',
            'uploader_id': '5fb81e51aa66ae000c395478',
            'ext': 'mp3',
            'tags': ['samsung', 'galaxy', 's8', 'over the horizon', '2016', 'ringtone'],
        },
    }, {
        'url': 'https://blerp.com/soundbites/5bc94ef4796001000498429f',
        'info_dict': {
            'id': '5bc94ef4796001000498429f',
            'title': 'Yee',
            'uploader': '179617322678353920',
            'uploader_id': '5ba99cf71386730004552c42',
            'ext': 'mp3',
            'tags': ['YEE', 'YEET', 'wo ha haah catchy tune yee', 'yee'],
        },
    }]

    _GRAPHQL_OPERATIONNAME = 'webBitePageGetBite'
    _GRAPHQL_QUERY = (
        '''query webBitePageGetBite($_id: MongoID!) {
            web {
                biteById(_id: $_id) {
                    ...bitePageFrag
                    __typename
                }
                __typename
            }
        }

        fragment bitePageFrag on Bite {
            _id
            title
            userKeywords
            keywords
            color
            visibility
            isPremium
            owned
            price
            extraReview
            isAudioExists
            image {
                filename
                original {
                    url
                    __typename
                }
                __typename
            }
            userReactions {
                _id
                reactions
                createdAt
                __typename
            }
            topReactions
            totalSaveCount
            saved
            blerpLibraryType
            license
            licenseMetaData
            playCount
            totalShareCount
            totalFavoriteCount
            totalAddedToBoardCount
            userCategory
            userAudioQuality
            audioCreationState
            transcription
            userTranscription
            description
            createdAt
            updatedAt
            author
            listingType
            ownerObject {
                _id
                username
                profileImage {
                    filename
                    original {
                        url
                        __typename
                    }
                    __typename
                }
                __typename
            }
            transcription
            favorited
            visibility
            isCurated
            sourceUrl
            audienceRating
            strictAudienceRating
            ownerId
            reportObject {
                reportedContentStatus
                __typename
            }
            giphy {
                mp4
                gif
                __typename
            }
            audio {
                filename
                original {
                    url
                    __typename
                }
                mp3 {
                    url
                    __typename
                }
                __typename
            }
            __typename
        }

        ''')

    def _real_extract(self, url):
        audio_id = self._match_id(url)

        data = {
            'operationName': self._GRAPHQL_OPERATIONNAME,
            'query': self._GRAPHQL_QUERY,
            'variables': {
                '_id': audio_id,
            },
        }

        headers = {
            'Content-Type': 'application/json',
        }

        json_result = self._download_json(
            'https://api.blerp.com/graphql', audio_id,
            data=json.dumps(data).encode(), headers=headers)

        bite_json = json_result['data']['web']['biteById']

        return {
            'id': bite_json['_id'],
            'url': bite_json['audio']['mp3']['url'],
            'title': bite_json['title'],
            'uploader': traverse_obj(bite_json, ('ownerObject', 'username'), expected_type=strip_or_none),
            'uploader_id': traverse_obj(bite_json, ('ownerObject', '_id'), expected_type=strip_or_none),
            'ext': 'mp3',
            'tags': list(filter(None, map(strip_or_none, (traverse_obj(bite_json, 'userKeywords', expected_type=list) or []))) or None),
        }
