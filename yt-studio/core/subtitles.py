from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import json

from core.qt_compat import QThread, Signal


WYZE_BASE_URL = "https://sub.wyzie.ru"


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


class SubtitleSearchWorker(QThread):
    results = Signal(list)
    error = Signal(str)
    finished = Signal()

    def __init__(self, media_id: str, language: str, api_key: str = "", opener: Callable | None = None):
        super().__init__()
        self.media_id = media_id
        self.language = language
        self.api_key = api_key
        self._opener = opener or urlopen

    def run(self):
        try:
            url = build_wyzie_search_url(self.media_id, self.language, api_key=self.api_key)
            request = Request(url, headers={"Accept": "application/json", "User-Agent": "YT-Studio/1.0"})
            with self._opener(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8", "replace"))
            self.results.emit(parse_wyzie_results(payload))
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            self.finished.emit()


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
