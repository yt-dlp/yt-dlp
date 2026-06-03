from core.ui_state import context_from_info, is_audio_quality, visible_sections


def test_detects_playlist_live_and_audio_contextual_sections():
    context = context_from_info(
        {
            "_type": "playlist",
            "is_live": True,
            "entries": [{"id": "one"}],
        },
        quality="Audio MP3",
        subtitles="English",
        sponsorblock_mode="Skip sponsors",
    )

    sections = visible_sections(context)

    assert is_audio_quality("Audio MP3") is True
    assert sections["playlist"] is True
    assert sections["live"] is True
    assert sections["subtitle_details"] is True
    assert sections["sponsorblock_details"] is True
    assert sections["video_container"] is False


def test_hides_contextual_sections_for_plain_video_defaults():
    context = context_from_info(
        {
            "_type": "video",
            "is_live": False,
        },
        quality="1080p",
        subtitles="Off",
        sponsorblock_mode="Off",
    )

    sections = visible_sections(context)

    assert sections["playlist"] is False
    assert sections["live"] is False
    assert sections["subtitle_details"] is False
    assert sections["sponsorblock_details"] is False
    assert sections["video_container"] is True
