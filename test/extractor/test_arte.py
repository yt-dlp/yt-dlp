import pytest

from yt_dlp.extractor.arte import ArteTVIE


ACCESSIBLE_TESTS = [
    ({'fr': [{'url': 'https://arte-cmafhls.akamaized.net/am/cmaf/103000/103500/103522-000-A/230804153206/medias/103522-000-A_st_VF-FRA.m3u8', 'ext': 'vtt', 'protocol': 'm3u8_native'}]}, 'fr'),
    ({'fr': [{'url': 'https://arte-cmafhls.akamaized.net/am/cmaf/103000/103500/103522-000-A/230804153206/medias/103522-000-A_st_VF-MAL.m3u8', 'ext': 'vtt', 'protocol': 'm3u8_native'}]}, 'fr-acc'),
]


@pytest.mark.parametrize('original_subs,expected_locale', ACCESSIBLE_TESTS)
def test_extract_accessible_subtitles(original_subs, expected_locale):
    extractor = ArteTVIE()

    subs = extractor._contvert_accessible_subs_locale(original_subs)

    assert len(subs) == 1
    assert expected_locale in subs
    assert subs[expected_locale] == original_subs['fr']
