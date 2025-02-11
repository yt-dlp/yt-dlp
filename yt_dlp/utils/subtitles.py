from __future__ import annotations

import re
from dataclasses import dataclass

Seconds = float


@dataclass
class Metadata:
    name: str
    value: str


@dataclass
class Subtitle:
    text: str
    start: Seconds
    end: Seconds | None = None


def parse_lrc(text):
    for line in text.split('\n'):
        times = []
        while mobj := re.fullmatch(r'\[(?P<time>((\d+:)?\d+:)?\d+(.\d+)?)\](?P<content>.*)', line):
            times.append(sum(
                float(t) * 60**i for i, t in enumerate(reversed(mobj.group('time').split(':')))))
            line = mobj.group('content')

        for t in times:
            yield Subtitle(start=t, text=line.strip())

        if not times:
            if mobj := re.fullmatch(r'\[(?P<name>[^\]:]+):(?P<value>[^\]]+)\]', line):
                yield Metadata(mobj.group('name'), mobj.group('value').strip())
            elif line.strip():
                yield ValueError(line)
