from core.subtitles import build_wyzie_search_url, parse_wyzie_results


def test_builds_wyzie_subtitle_search_url_for_arabic_imdb_id():
    url = build_wyzie_search_url("tt15940132", "ar")

    assert url == "https://sub.wyzie.ru/search?id=tt15940132&format=srt&language=ar"


def test_builds_wyzie_subtitle_search_url_with_api_key():
    url = build_wyzie_search_url("tt15940132", "en", api_key="secret")

    assert url == "https://sub.wyzie.ru/search?id=tt15940132&format=srt&language=en&api_key=secret"


def test_parses_wyzie_subtitle_results():
    results = parse_wyzie_results([
        {
            "url": "https://example.com/sub.srt",
            "language": "en",
            "source": "opensubtitles",
            "display": "War Machine English",
            "format": "srt",
        }
    ])

    assert len(results) == 1
    assert results[0].provider == "opensubtitles"
    assert results[0].language == "en"
    assert results[0].display == "War Machine English"
    assert results[0].url == "https://example.com/sub.srt"
