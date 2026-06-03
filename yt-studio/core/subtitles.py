from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import json

from core.qt_compat import QThread, Signal


WYZE_BASE_URL = "https://sub.wyzie.ru"
SUBDL_BASE_URL = "https://api.subdl.com/api/v1/subtitles"


@dataclass(slots=True)
class SubtitleResult:
    provider: str
    language: str
    display: str
    url: str
    format: str = "srt"


def build_wyzie_search_url(media_id: str, language: str = "", subtitle_format: str = "srt", api_key: str = "") -> str:
    query = {"id": media_id, "format": subtitle_format}
    if language:
        query["language"] = language
    if api_key:
        query["api_key"] = api_key
    return f"{WYZE_BASE_URL}/search?{urlencode(query)}"


def build_subdl_search_url(
    media_id: str,
    language: str = "",
    api_key: str = "",
    media_type: str = "",
    season: int | None = None,
    episode: int | None = None,
) -> str:
    query = {"api_key": api_key}
    if media_id.startswith("tt"):
        query["imdb_id"] = media_id
    else:
        query["tmdb_id"] = media_id
    if language:
        query["languages"] = language
    if media_type:
        query["type"] = media_type
    if season:
        query["season_number"] = str(season)
    if episode:
        query["episode_number"] = str(episode)
    return f"{SUBDL_BASE_URL}?{urlencode(query)}"


def parse_wyzie_results(payload) -> list[SubtitleResult]:
    if isinstance(payload, dict):
        items = payload.get("subtitles") or payload.get("results") or []
    else:
        items = payload or []
    results = []
    for item in items:
        url = item.get("url") or item.get("download_url")
        if not url:
            continue
        language = item.get("language") or item.get("lang") or ""
        display = item.get("display") or item.get("name") or item.get("release") or item.get("source") or url
        results.append(
            SubtitleResult(
                provider=item.get("source") or item.get("provider") or "wyzie",
                language=language,
                display=display,
                url=url,
                format=item.get("format") or "srt",
            )
        )
    return results


def parse_subdl_results(payload) -> list[SubtitleResult]:
    items = payload.get("subtitles") if isinstance(payload, dict) else payload
    results = []
    for item in items or []:
        url = item.get("url")
        if url and url.startswith("/"):
            url = f"https://dl.subdl.com{url}"
        if not url:
            continue
        language = item.get("lang") or item.get("language") or ""
        display = item.get("release_name") or item.get("name") or item.get("author") or url
        results.append(SubtitleResult("subdl", language, display, url, item.get("format") or "srt"))
    return results


class SubtitleSearchWorker(QThread):
    results = Signal(list)
    error = Signal(str)
    finished = Signal()

    def __init__(
        self,
        media_id: str,
        language: str,
        wyzie_api_key: str = "",
        subdl_api_key: str = "",
        media_type: str = "",
        season: int | None = None,
        episode: int | None = None,
        opener: Callable | None = None,
    ):
        super().__init__()
        self.media_id = media_id
        self.language = language
        self.wyzie_api_key = wyzie_api_key
        self.subdl_api_key = subdl_api_key
        self.media_type = media_type
        self.season = season
        self.episode = episode
        self._opener = opener or urlopen

    def run(self):
        try:
            results = []
            errors = []
            if self.wyzie_api_key:
                try:
                    results.extend(self._fetch_json_results(
                        build_wyzie_search_url(self.media_id, self.language, api_key=self.wyzie_api_key),
                        parse_wyzie_results))
                except Exception as exc:
                    errors.append(f"Wyzie: {exc}")
            if self.subdl_api_key:
                try:
                    results.extend(self._fetch_json_results(
                        build_subdl_search_url(
                            self.media_id,
                            self.language,
                            api_key=self.subdl_api_key,
                            media_type=self.media_type,
                            season=self.season,
                            episode=self.episode,
                        ),
                        parse_subdl_results))
                except Exception as exc:
                    errors.append(f"SubDL: {exc}")
            if not self.wyzie_api_key and not self.subdl_api_key:
                raise RuntimeError("Add a Wyzie or SubDL subtitle API key in CONFIG first.")
            if not results and errors:
                raise RuntimeError("; ".join(errors))
            self.results.emit(results)
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            self.finished.emit()

    def _fetch_json_results(self, url: str, parser: Callable):
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "YT-Studio/1.0"})
        with self._opener(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
        return parser(payload)


class SubtitleDownloadWorker(QThread):
    downloaded = Signal(str)
    error = Signal(str)
    finished = Signal()

    def __init__(self, result: SubtitleResult, output_path: Path, opener: Callable | None = None):
        super().__init__()
        self.result = result
        self.output_path = output_path
        self._opener = opener or urlopen

    def run(self):
        try:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            request = Request(self.result.url, headers={"User-Agent": "YT-Studio/1.0"})
            with self._opener(request, timeout=60) as response:
                self.output_path.write_bytes(response.read())
            self.downloaded.emit(str(self.output_path))
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            self.finished.emit()
