from .common import InfoExtractor


class YnetIE(InfoExtractor):
    IE_DESC = 'Ynet article videos downloader'
    IE_NAME = 'ynet'
    _VALID_URL = r'^https?://(?:www\.)?ynet\.co\.il/.*/article/(?P<id>[a-z0-9]+)'  # add .*/article/.*
    _TESTS = [{
        'url': 'https://www.ynet.co.il/entertainment/article/by00r2ccc3',
        'playlist_count': 4,
        'info_dict': {
            'id': 'by00r2ccc3',
            'title': 'שוב הפרעות לתקשורת במחאות: עיתונאים הותקפו בהפגנה בקפלן',
            'description': 'חדשות 12 הודיעו כי במהלך הפגנת התמיכה שנערכה בתל אביב הכתב גלעד שלמור הותקף בידי מפגינים. באותו אירוע גם עיתונאי כאן איציק זוארץ נפצע בראשו מבקבוק שנזרק לעברו בעוצמה וצלם חדשות 13 חולץ מעימות אלים על ידי כוח שיטור. ארגון העיתונאים והעיתונאיות גינו את התקריות: "אין מקום לגילויי אלימות כלפי עיתונאים וצוותי תקשורת"',
        },
    }, {
        'url': 'https://www.ynet.co.il/entertainment/article/skrwop5kjg#autoplay',
        'playlist_count': 1,
        'info_dict': {
            'id': 'skrwop5kjg',
            'title': 'אם תמלאו שלושה חוקים פשוטים, תוכלו לחלוק מיקרופון עם הראפרים המובילים',
            'description': 'md5:ecf9b545401756901b889ed0564ec348',
        },
        'playlist': [{
            'info_dict': {
                'ext': 'mp4',
                'id': 'skrwop5kjg',
                'type': 'video',  # AssertionError: ['type'] is not false : Invalid fields returned by the extractor: type
                'url': 'https://vod-progressive.ynethd.com/1024/260924_rap_r7_fix_720p.mp4',
                'title': 'סצנת הפרי-סטייל בתל אביב',
                'description': 'md5:ff98fc34691f4eea960abd99f91cffed',
            },
        }],
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        videos = []

        for ld in self._yield_json_ld(webpage, video_id):
            if ld.get('@type') == 'NewsArticle':
                headline = ld.get('headline')
                description = ld.get('description')

                for e in ld.get('video'):
                    videos.append({
                        '_type': 'video',
                        'id': video_id,
                        'title': e.get('name'),
                        'description': e.get('description'),
                        'creator': e.get('author').get('name'),
                        'thumbnail': e.get('thumbnailUrl'),
                        'url': e.get('contentUrl'),
                    })

        return {
            '_type': 'playlist',
            'id': video_id,
            'title': headline,
            'description': description,
            'entries': videos,
        }
