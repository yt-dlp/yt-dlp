from dataclasses import dataclass


@dataclass(slots=True)
class UiContext:
    is_playlist: bool = False
    is_live: bool = False
    is_audio: bool = False
    subtitles_enabled: bool = False
    sponsorblock_enabled: bool = False


def is_audio_quality(quality: str) -> bool:
    return quality.strip().lower().startswith("audio")


def context_from_info(info: dict, quality: str, subtitles: str, sponsorblock_mode: str) -> UiContext:
    entries = info.get("entries")
    is_playlist = info.get("_type") == "playlist" or bool(entries)
    is_live = bool(info.get("is_live") or info.get("live_status") in {"is_live", "is_upcoming"})
    return UiContext(
        is_playlist=is_playlist,
        is_live=is_live,
        is_audio=is_audio_quality(quality),
        subtitles_enabled=subtitles.strip().lower() != "off",
        sponsorblock_enabled=sponsorblock_mode.strip().lower() != "off",
    )


def visible_sections(context: UiContext) -> dict[str, bool]:
    return {
        "playlist": context.is_playlist,
        "live": context.is_live,
        "subtitle_details": context.subtitles_enabled,
        "sponsorblock_details": context.sponsorblock_enabled,
        "video_container": not context.is_audio,
    }
