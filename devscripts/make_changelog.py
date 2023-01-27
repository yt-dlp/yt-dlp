from __future__ import annotations

import enum
import json
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_AUTHOR = "pukkandan"
AUTHOR_INDICATOR = "Authored by: "
COMMIT_SEPARATOR = "---"

USER_BASE_URL = "https://github.com"
REPO_BASE_URL = "https://github.com/yt-dlp/yt-dlp"

# fmt: off
MESSAGE_RE = re.compile(r"(?:\[(?P<prefix>[\w\/:]+)\] )?(?P<message>.+?)(?: \(#(?P<issue>\d+)\))?")
# fmt: on

OVERRIDE_PATH = Path(__file__).parent / "changelog_override.json"
CONTRIBUTORS_PATH = Path(__file__).parent.parent / "CONTRIBUTORS"


class CommitGroup(enum.Enum):
    IMPORTANT = ...
    CORE = None
    DOWNLOADER = "Downloader"
    EXTRACTOR = "Extractor"
    MISC = "Misc."

    @classmethod
    def _missing_(cls, value: str):
        return {
            "": CommitGroup.CORE,
            "aes": CommitGroup.CORE,
            "build": CommitGroup.CORE,
            "cache": CommitGroup.CORE,
            "cookies": CommitGroup.CORE,
            "dependencies": CommitGroup.CORE,
            "jsinterp": CommitGroup.CORE,
            "plugins": CommitGroup.CORE,
            "update": CommitGroup.CORE,
            "utils": CommitGroup.CORE,
            "cleanup": CommitGroup.MISC,
            "downloader": CommitGroup.DOWNLOADER,
            "extractor": CommitGroup.EXTRACTOR,
        }.get(value, cls.MISC)


@dataclass
class CommitInfo:
    prefix: str | None
    details: str | None
    message: str
    issue: str | None
    commit: Commit

    def key(self):
        return (self.prefix or "", self.details or "", self.message)


@dataclass
class Commit:
    hash: str | None
    short: str
    authors: list[str]


class Changelog:
    def __init__(self, groups: dict[CommitGroup, list[CommitInfo]]):
        self.groups = groups

    @classmethod
    def from_commits(cls, commits: list[Commit]):
        return cls(cls.group_commits(commits))

    def __str__(self):
        return "\n".join(self._format_groups(self.groups))

    def _format_groups(self, groups: dict[CommitGroup, list[CommitInfo]]):
        yield "## Changelog"

        for item in CommitGroup:
            group = groups[item]
            if group:
                yield self.format_module(item.value, group)

    def format_module(self, name: str | None, group: Iterable[CommitInfo]):
        result = f"### {name} changes\n" if name else ""
        return result + "\n".join(self._format_group(group))

    def _format_group(self, group: Iterable[CommitInfo]):
        current = ""
        indent = ""
        for item in sorted(group, key=CommitInfo.key):
            details = item.details or item.prefix
            if details != current:
                yield f"- {details}"
                current = details
                indent = "    "

            yield f"{indent}- {self.format_single_change(item)}"

    def format_single_change(self, commit_info: CommitInfo):
        message = (
            f"[{commit_info.message}]({REPO_BASE_URL}/commit/{commit_info.commit.hash})"
            if commit_info.commit.hash
            else commit_info.message
        )
        # fmt: off
        authors = ", ".join(f"[{author}]({USER_BASE_URL}/{author})" for author in commit_info.commit.authors)
        if commit_info.issue:
            issue = f"[#{commit_info.issue}]({REPO_BASE_URL}/issues/{commit_info.issue})"
            return f"{message} ({issue}) by {authors}"
        # fmt: on
        return f"{message} by {authors}"

    @staticmethod
    def group_commits(commits: Iterable[Commit]) -> dict[CommitGroup, list[CommitInfo]]:
        groups = defaultdict(list)
        for commit in commits:
            if commit.short.startswith("Release "):
                continue

            match = MESSAGE_RE.fullmatch(commit.short)
            assert match is not None, f"Error in short commit message: {commit.short!r}"
            prefix, message, issue = match.groups()
            if prefix == "version":
                # Skip version bump commit
                continue
            prefix, _, detail = (prefix or "").lower().partition("/")
            detail, _, sub_detail = detail.partition(":")
            if sub_detail:
                message = f"`{sub_detail}`: {message}"
            group = CommitGroup(prefix)
            groups[group].append(
                CommitInfo(prefix, detail or None, message, issue, commit)
            )

        return groups


def get_commits(start, end):
    # fmt: off
    command = ["git", "log", f"--format=%H%n%s%n%b%n{COMMIT_SEPARATOR}", f"{start}..{end}"]
    # fmt: on
    result = subprocess.run(command, stdout=subprocess.PIPE, text=True)
    lines = iter(result.stdout.splitlines(False))
    for line in lines:
        commit_hash = line
        short = next(lines)

        authors = [DEFAULT_AUTHOR]
        line = next(lines)
        while line != COMMIT_SEPARATOR:
            if line.startswith(AUTHOR_INDICATOR):
                authors = line.removeprefix(AUTHOR_INDICATOR).split(", ")

            line = next(lines)

        yield Commit(commit_hash, short, authors)


def fix_commits(commits: Iterable[Commit], info=lambda x: None):
    with OVERRIDE_PATH.open("r") as file:
        override = json.load(file)

    commit_lookup = {commit.hash: commit for commit in commits}
    for commit_hash, data in override["change"].items():
        if commit_hash not in commit_lookup:
            continue
        short, authors = data["short"], data["authors"]
        old_commit = commit_lookup[commit_hash]
        old_short, old_authors = old_commit.short, old_commit.authors
        info(
            f"Changed {commit_hash[:7]} from {old_short!r} ({old_authors}) to {short!r} ({authors})"
        )
        commit_lookup[commit_hash] = Commit(commit_hash, short, authors)

    for commit_hash in override["remove"]:
        commit_lookup.pop(commit_hash, None)
        info(f"Removed commit {commit_hash[:7]} from changes")

    for data in override["add"].get(args.start) or ():
        short, authors = data["short"], data["authors"]
        info(f"Added {short!r} ({authors}) as a change")
        yield Commit(None, short, authors)

    yield from commit_lookup.values()


def update_contributors(commits: list[Commit]):
    contributors = set()
    with CONTRIBUTORS_PATH.open() as file:
        for line in filter(None, map(str.strip, file)):
            author, _, _ = line.partition(" (")
            authors = author.split("/")
            contributors.update(authors)

    new_contributors = {}
    for commit in commits:
        for author in commit.authors:
            if author in contributors:
                continue
            contributors.add(author)
            new_contributors[author] = None

    new_contributors = list(reversed(new_contributors))
    with CONTRIBUTORS_PATH.open("a") as file:
        for contributor in new_contributors:
            file.write(f"{contributor}\n")

    return new_contributors


if __name__ == "__main__":
    import argparse

    # fmt: off
    parser = argparse.ArgumentParser(description="Create a changelog from git range")
    parser.add_argument("start", help="The hash or tag to start from")
    parser.add_argument("end", default="HEAD", nargs="?", help="The hash or tag to end on (default: HEAD)")
    parser.add_argument("-i", "--info", action="store_true", help="Print additional info about the operations")
    parser.add_argument("-c", "--contributors", action="store_true", help="Update CONTRIBUTORS file")
    # fmt: on
    args = parser.parse_args()
    if args.info:
        import sys

        info = lambda x: print(x, file=sys.stderr)
    else:
        info = lambda x: None

    commits = get_commits(args.start, args.end)
    commits = list(fix_commits(commits, info))
    info(f"Loaded {len(commits)} commits")

    if args.contributors:
        new_contributors = update_contributors(commits)
        info(f"Added these new contributors: {new_contributors}")

    print(Changelog.from_commits(commits))
