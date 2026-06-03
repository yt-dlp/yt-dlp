from core.subtitles import build_subdl_search_url, build_wyzie_search_url, parse_subdl_results, parse_wyzie_results


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


def test_builds_subdl_search_url_for_tv_arabic():
    url = build_subdl_search_url("tt0944947", "ar", api_key="secret", media_type="tv", season=1, episode=1)

    assert url == (
        "https://api.subdl.com/api/v1/subtitles?"
        "api_key=secret&imdb_id=tt0944947&languages=ar&type=tv&season_number=1&episode_number=1"
    )


def test_parses_subdl_results():
    results = parse_subdl_results({
        "subtitles": [{
            "url": "/subtitles/example.srt",
            "lang": "AR",
            "release_name": "Episode Arabic",
        }]
    })

    assert len(results) == 1
    assert results[0].provider == "subdl"
    assert results[0].language == "AR"
    assert results[0].url == "https://dl.subdl.com/subtitles/example.srt"
