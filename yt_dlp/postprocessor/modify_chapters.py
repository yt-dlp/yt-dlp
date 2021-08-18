import copy
import heapq
import json
import os
import re
from collections import OrderedDict
from hashlib import sha256
from typing import (AbstractSet, Any, Dict, Iterable, List, MutableMapping, MutableSequence,
                    Optional, Pattern, Sequence, TYPE_CHECKING, Tuple)

if TYPE_CHECKING:
    from .. import YoutubeDL

from . import FFmpegPostProcessor
from .ffmpeg import FFmpegPostProcessorError
from ..compat import compat_urllib_parse_urlencode, compat_HTTPError
from ..utils import (
    float_or_none,
    PostProcessingError,
    prepend_extension,
    sanitized_Request,
    traverse_obj
)


SPONSORBLOCK_CATEGORIES = 'sponsor', 'intro', 'outro', 'interaction', 'selfpromo', 'preview', 'music_offtopic'

SPONSORBLOCK_CATEGORY_TO_CHAPTER = {
    'sponsor': 'Sponsor',
    'intro': 'Intro',
    'outro': 'Outro',
    'interaction': 'Interaction Reminder',
    'selfpromo': 'Self-Promotion',
    'preview': 'Preview/Recap',
    'music_offtopic': 'Non-Music Section'
}

# See https://ffmpeg.org/general.html#Subtitle-Formats.
SUPPORTED_SUBS = 'srt', 'ass', 'vtt'

InfoDict = MutableMapping[str, Any]
Chapter = MutableMapping[str, Any]
SponsorBlockSegment = MutableMapping[str, Any]


class ModifyChaptersPP(FFmpegPostProcessor):
    def __init__(
            self, downloader: 'YoutubeDL', remove_chapters_pattern: Optional[Pattern[str]] = None,
            force_keyframes=False, use_sponsorblock=False,
            sponsorblock_query: AbstractSet[str] = frozenset(SPONSORBLOCK_CATEGORIES),
            sponsorblock_cut: AbstractSet[str] = frozenset(SPONSORBLOCK_CATEGORIES),
            sponsorblock_force=False, sponsorblock_hide_video_id=True,
            sponsorblock_api='https://sponsor.ajay.app'):
        FFmpegPostProcessor.__init__(self, downloader)
        self._remove_chapters_pattern = remove_chapters_pattern
        self._force_keyframes = force_keyframes
        self._use_sponsorblock = use_sponsorblock
        self._sponsorblock_query = sponsorblock_query
        self._sponsorblock_cut = sponsorblock_cut
        self._sponsorblock_force = sponsorblock_force
        self._sponsorblock_hide_video_id = sponsorblock_hide_video_id
        # Force HTTPS if protocol is omitted, unsecure HTTP must be requested explicitly.
        self._sponsorblock_api = (sponsorblock_api if re.match('^https?://', sponsorblock_api)
                                  else 'https://' + sponsorblock_api)

    def run(self, info: InfoDict) -> Tuple[List[str], InfoDict]:
        video_file: str = info['filepath']
        # When cut is requested, simple info['chapters'] update is insufficient.
        if not os.path.exists(video_file) and (
                self._remove_chapters_pattern or self._sponsorblock_cut):
            return [], info

        # Chapter will be flagged for removal, which can fail. Deep copy to make sure
        # original chapters are not flagged.
        chapters: Optional[MutableSequence[Chapter]] = copy.deepcopy(info.get('chapters', None))
        if not chapters and not self._use_sponsorblock:
            return [], info

        duration = self._get_video_duration(video_file)
        sponsor_chapters = self._get_sponsor_chapters(info, duration)
        if not sponsor_chapters and not (chapters and self._remove_chapters_pattern):
            return [], info

        if chapters and self._remove_chapters_pattern:
            for c in chapters:
                if 'title' in c and self._remove_chapters_pattern.match(c['title']):
                    c['remove'] = True
        if not chapters:
            chapters = [{'start_time': 0, 'end_time': duration, 'title': info['title']}]
        chapters += sponsor_chapters

        new_chapters, cuts, has_sponsors = self._remove_marked_arrange_sponsors(chapters)
        if not cuts:
            info['chapters'] = new_chapters
            self._downloader.write_info_json(info, override=True)
            if has_sponsors:
                # Tell FFmpegMetadataPP to add chapters even
                # if --add-metadata was not requested explicitly.
                info['__has_sponsor_chapters'] = True
            return [], info

        real_download, cut_warn = info.get('__real_download', False), False
        files_to_remove: List[str] = []

        def move_to_uncut(file: str) -> str:
            nonlocal cut_warn
            uncut_file = prepend_extension(file, 'uncut')
            if real_download or not os.path.exists(uncut_file):
                if not real_download and not cut_warn:
                    cut_warn = True
                    self.report_warning('Removing chapters multiple times may cut out '
                                        'unintended parts of the video')
                os.rename(file, uncut_file)
            files_to_remove.append(uncut_file)
            return uncut_file

        files_to_cut = [(move_to_uncut(video_file), video_file)]
        # get(..., {}) is broken: sometimes a literal None is stored under this key.
        for lang, sub in (info.get('requested_subtitles') or {}).items():
            sub_file = sub.get('filepath')
            # The file might have been removed by --embed-subs.
            if not sub_file or not os.path.exists(sub_file):
                continue
            ext: str = sub['ext']
            if ext not in SUPPORTED_SUBS:
                self.report_warning('Cannot remove chapters from external subtitles '
                                    f'of type ".{ext}". They are now out of sync.')
                continue
            files_to_cut.append((move_to_uncut(sub_file), sub_file))

        if self._try_remove_chapters(files_to_cut, cuts, duration):
            info['chapters'] = new_chapters
            self._downloader.write_info_json(info, override=True)
            return files_to_remove, info
        # Revert everything.
        for uncut, original in files_to_cut:
            os.rename(uncut, original)
        return [], info

    def _get_video_duration(self, video_file: str) -> float:
        # In contrast to info['duration'], ffprobe reports real duration,
        # thus providing protection against cutting the same pieces twice
        # (see duration_match in _get_sponsor_chapters below).
        duration = float_or_none(
            traverse_obj(self.get_metadata_object(video_file), ['format', 'duration']))
        if duration is None:
            raise PostProcessingError('Cannot determine the video duration')
        return duration

    def _get_sponsor_chapters(self, info: InfoDict, duration: float) -> List[Chapter]:
        if not self._use_sponsorblock:
            return []
        if info['extractor_key'].lower() != 'youtube':
            self.to_screen('Skipping SponsorBlock since it is not a YouTube video')
            return []
        # When cut is requested, simple info['chapters'] update is insufficient.
        if not info.get('__real_download', False) and (
                self._sponsorblock_cut and not self._sponsorblock_force):
            self.report_warning(
                'Skipping SponsorBlock since the video was already downloaded. '
                'Use --sponsorblock-force to SponsorBlock anyway')
            return []

        segments = (self._get_sponsor_segments_hiding_id if self._sponsorblock_hide_video_id
                    else self._get_sponsor_segments_revealing_id)(info['id'])

        def duration_filter(s: SponsorBlockSegment):
            start_end: MutableSequence[float] = s['segment']
            # Ignore milliseconds difference at the start.
            if start_end[0] <= 1:
                start_end[0] = 0
            # Ignore milliseconds difference at the end.
            # Never allow the segment to exceed the video.
            if duration - start_end[1] <= 1:
                start_end[1] = duration
            # SponsorBlock duration may be absent or it may deviate from the real one.
            return s['videoDuration'] == 0 or abs(duration - s['videoDuration']) <= 1

        duration_match = [s for s in segments if duration_filter(s)]
        if len(duration_match) != len(segments):
            warning = 'Some SponsorBlock segments are from a video of different duration'
            warning += (', maybe from an old version of this video' if not self._sponsorblock_force
                        else '. Looks like SponsorBlock has already run')
            self.report_warning(warning)

        def to_chapter(s: SponsorBlockSegment) -> Chapter:
            (start, end), cat = s['segment'], s['category']
            c = {'start_time': start, 'end_time': end, 'categories': [(cat, start, end)]}
            if cat in self._sponsorblock_cut:
                c['remove'] = True
            return c

        sponsor_chapters = [to_chapter(s) for s in duration_match]
        if not sponsor_chapters:
            self.to_screen('No skippable segments were found by SponsorBlock')
        return sponsor_chapters

    def _get_sponsor_segments_revealing_id(self, video_id: str) -> Sequence[SponsorBlockSegment]:
        url = f'{self._sponsorblock_api}/api/skipSegments?' + compat_urllib_parse_urlencode({
            'videoID': video_id,
            'categories': json.dumps(tuple(self._sponsorblock_query)),
            'service': 'YouTube'
        })
        return self._get_json(url)

    def _get_sponsor_segments_hiding_id(self, video_id: str) -> Sequence[SponsorBlockSegment]:
        hash = sha256(video_id.encode('ascii')).hexdigest()
        # SponsorBlock API recommends using first 4 hash characters.
        url = f'{self._sponsorblock_api}/api/skipSegments/{hash[:4]}?' + (
            compat_urllib_parse_urlencode({
                'categories': json.dumps(tuple(self._sponsorblock_query)),
                'service': 'YouTube'
            }))
        for d in self._get_json(url):
            if d['videoID'] == video_id:
                return d['segments']
        return []

    def _get_json(self, url: str) -> Any:
        try:
            self.write_debug(f'SponsorBlock query: {url}')
            rsp = self._downloader.urlopen(sanitized_Request(url))
            return json.loads(rsp.read().decode(rsp.info().get_param('charset') or 'utf-8'))
        except compat_HTTPError as e:
            if e.code == 404:
                return []
            raise PostProcessingError('Error communicating with SponsorBlock API') from e

    def _remove_marked_arrange_sponsors(
            self, chapters: MutableSequence[Chapter]) -> Tuple[List[Chapter], List[Chapter], bool]:
        # Store cuts separately, since adjacent and overlapping cuts must be merged.
        cuts: List[Chapter] = []

        overlap_warn = False

        def warn_sponsors_overlap():
            nonlocal overlap_warn
            if overlap_warn:
                return
            overlap_warn = True
            self.report_warning(
                'Some SponsorBlock segments overlap. '
                'Usually it means that there are many conflicting submissions. '
                'You may want to review them, and upvote or downvote appropriately')

        def append_cut(c: Chapter) -> int:
            assert 'remove' in c
            last_to_cut = cuts[-1] if cuts else None
            if last_to_cut and last_to_cut['end_time'] >= c['start_time']:
                if 'categories' in c:
                    if 'categories' in last_to_cut:
                        warn_sponsors_overlap()
                    else:
                        last_to_cut['categories'] = c['categories']
                last_to_cut['end_time'] = max(last_to_cut['end_time'], c['end_time'])
            else:
                cuts.append(c)
            return len(cuts) - 1

        def excess_duration(c: Chapter) -> float:
            # Cuts that are completely within the chapter reduce chapters' duration.
            # Since cuts can overlap, excess duration may be less that the sum of cuts' durations.
            # To avoid that, chapter stores the index to the fist cut within the chapter,
            # instead of storing excess duration. append_cut ensures that subsequent cuts (if any)
            # will be merged with previous ones (if necessary).
            cut_idx, excess = c.pop('cut_idx', len(cuts)), 0
            while cut_idx < len(cuts):
                cut = cuts[cut_idx]
                if cut['start_time'] >= c['end_time']:
                    break
                if cut['end_time'] > c['start_time']:
                    if 'categories' in cut and 'categories' in c:
                        warn_sponsors_overlap()
                    excess += min(cut['end_time'], c['end_time'])
                    excess -= max(cut['start_time'], c['start_time'])
                cut_idx += 1
            return excess

        # same_titles tracks chapters having the same title to disambiguate them later,
        # e.g. multiple 'Sponsor' chapters will be renamed to 'Sponsor - 1', 'Sponsor - 2', etc.
        same_titles: Dict[str, List[Chapter]] = {}
        new_chapters: List[Chapter] = []
        has_sponsors = False

        def append_chapter(c: Chapter):
            nonlocal has_sponsors
            assert 'remove' not in c
            length = c['end_time'] - c['start_time'] - excess_duration(c)
            if length <= 0:
                # Chapter is completely covered by cuts or sponsors.
                return
            start = new_chapters[-1]['end_time'] if new_chapters else 0
            c.update(start_time=start, end_time=start + length)
            if 'categories' in c:
                has_sponsors = True
                cats = [cat for cat, _, _ in c['categories']]
                # Overlapping sponsor chapters will have a title that looks like
                # '[SponsorBlock]: Sponsor/Interaction Remainder/Self-Promotion',
                # in the order in which the categories were encountered.
                # OrderedDict removes duplicates preserving the order.
                c['title'] = '[SponsorBlock]: ' + '/'.join(OrderedDict(
                    zip(cats, map(SPONSORBLOCK_CATEGORY_TO_CHAPTER.__getitem__, cats))).values())
                del c['categories']
            # According to InfoExtractor docs, chapter title is optional.
            same_titles.setdefault(c.setdefault('title', 'Untitled'), []).append(c)
            new_chapters.append(c)

        # Turn into a priority queue, index is a tie breaker.
        # Plain stack sorted by start_time is not enough: after splitting the chapter,
        # the part returned to the stack is not guaranteed to have start_time
        # less than or equal to the that of the stack's head.
        chapters = [(c['start_time'], i, c) for i, c in enumerate(chapters)]
        heapq.heapify(chapters)

        _, cur_i, cur_chapter = heapq.heappop(chapters)
        while chapters:
            _, i, c = heapq.heappop(chapters)
            # Non-overlapping chapters or cuts can be appended directly. However,
            # adjacent non-overlapping cuts must be merged, which is handled by append_cut.
            if cur_chapter['end_time'] <= c['start_time']:
                (append_chapter if 'remove' not in cur_chapter else append_cut)(cur_chapter)
                cur_i, cur_chapter = i, c
                continue

            both_sponsors = 'categories' in cur_chapter and 'categories' in c
            if both_sponsors:
                warn_sponsors_overlap()

            # Eight possibilities for overlapping chapters: (cut, cut), (cut, sponsor),
            # (cut, normal), (sponsor, cut), (normal, cut), (sponsor, sponsor),
            # (sponsor, normal), and (normal, sponsor). There is no (normal, normal):
            # normal chapters are assumed not to overlap.
            if 'remove' in cur_chapter:
                # (cut, cut): adjust end_time.
                if 'remove' in c:
                    cur_chapter['end_time'] = max(cur_chapter['end_time'], c['end_time'])
                # (cut, sponsor/normal): chop the beginning of the later chapter
                # (if it's not completely hidden by the cut). Push to the priority queue
                # to restore sorting by start_time: with beginning chopped, c may actually
                # start later than the remaining chapters from the queue.
                elif cur_chapter['end_time'] < c['end_time']:
                    c['start_time'] = cur_chapter['end_time']
                    heapq.heappush(chapters, (c['start_time'], i, c))
            # (sponsor/normal, cut).
            elif 'remove' in c:
                # Chop the end of the current chapter if the cut is not contained within it.
                # Chopping the end doesn't break start_time sorting, no PQ push is necessary.
                if cur_chapter['end_time'] <= c['end_time']:
                    cur_chapter['end_time'] = c['start_time']
                    append_chapter(cur_chapter)
                    cur_i, cur_chapter = i, c
                    continue
                # Current chapter contains the cut within it. If the current chapter is
                # a sponsor chapter, check whether the categories before and after the cut differ.
                if 'categories' in cur_chapter:
                    after_c = dict(cur_chapter, start_time=c['end_time'], categories=[])
                    cur_cats = []
                    for cat_start_end in cur_chapter['categories']:
                        if cat_start_end[1] < c['start_time']:
                            cur_cats.append(cat_start_end)
                        if cat_start_end[2] > c['end_time']:
                            after_c['categories'].append(cat_start_end)
                    cur_chapter['categories'] = cur_cats
                    if cur_chapter['categories'] != after_c['categories']:
                        # Categories before and after the cut differ: push the after part to PQ.
                        heapq.heappush(chapters, (after_c['start_time'], cur_i, after_c))
                        cur_chapter['end_time'] = c['start_time']
                        append_chapter(cur_chapter)
                        cur_i, cur_chapter = i, c
                        continue
                # Either sponsor categories before and after the cut are the same or
                # we're dealing with a normal chapter. Just register an outstanding cut:
                # subsequent append_chapter will reduce the duration.
                cur_chapter.setdefault('cut_idx', append_cut(c))
            # (sponsor, sponsor): merge categories and adjust end_time.
            elif both_sponsors:
                cur_chapter['categories'].extend(c['categories'])
                cur_chapter['end_time'] = max(cur_chapter['end_time'], c['end_time'])
            # (sponsor, normal): if a normal chapter is not completely overlapped,
            # chop the beginning of it and push it to PQ.
            elif 'categories' in cur_chapter:
                if cur_chapter['end_time'] < c['end_time']:
                    c['start_time'] = cur_chapter['end_time']
                    heapq.heappush(chapters, (c['start_time'], i, c))
            # (normal, sponsor)
            else:
                assert 'categories' in c
                # If a sponsor chapter splits the normal one,
                # push the part after the sponsor to PQ.
                if cur_chapter['end_time'] > c['end_time']:
                    after_c = dict(cur_chapter, start_time=c['end_time'])
                    heapq.heappush(chapters, (after_c['start_time'], cur_i, after_c))
                # Sponsor chapter must inherit the cuts that the normal chapter
                # has accumulated within it.
                if 'cut_idx' in cur_chapter:
                    c['cut_idx'] = cur_chapter['cut_idx']
                cur_chapter['end_time'] = c['start_time']
                append_chapter(cur_chapter)
                cur_i, cur_chapter = i, c
        (append_chapter if 'remove' not in cur_chapter else append_cut)(cur_chapter)

        # Make sure split chapters have unique names.
        for cs in same_titles.values():
            if len(cs) > 1:
                for i, c in enumerate(cs, 1):
                    c['title'] += f' - {i}'
        return new_chapters, cuts, has_sponsors

    def _try_remove_chapters(self, in_out_files: Iterable[Tuple[str, str]],
                             chapters_to_remove: Iterable[Chapter], duration: float) -> bool:
        concat_opts = self._make_concat_opts(chapters_to_remove, duration)
        for in_file, out_file in in_out_files:
            force_keyframes = (self._force_keyframes
                               and out_file.rpartition('.')[-1] not in SUPPORTED_SUBS)
            if force_keyframes:
                in_file = self.force_keyframes(
                    in_file, (s[t] for s in chapters_to_remove for t in ['start_time', 'end_time']))

            try:
                self.to_screen(f'Removing parts of {in_file}')
                self.concat_files([in_file] * len(concat_opts), out_file, concat_opts)
            except FFmpegPostProcessorError:
                msg = 'FFmpeg was unable to cut chapters from the video '
                if not self.get_param('verbose', False):
                    msg += '(use -v to see the details). '
                msg += 'You can try to download a different format'
                if not self._force_keyframes:
                    msg += ' or re-encode with --remove-chapters-force-keyframes'
                self.report_warning(msg)
                return False

            if force_keyframes:
                os.remove(in_file)
        return True

    @staticmethod
    def _make_concat_opts(chapters_to_remove: Iterable[Chapter],
                          duration: float) -> List[Dict[str, str]]:
        opts: List[Dict[str, str]] = [{}]
        for s in chapters_to_remove:
            # Do not create 0 duration chunk at the beginning.
            if s['start_time'] == 0:
                opts[-1]['inpoint'] = f'{s["end_time"]:.6f}'
                continue
            opts[-1]['outpoint'] = f'{s["start_time"]:.6f}'
            # Do not create 0 duration chunk at the end.
            if s['end_time'] != duration:
                opts.append({'inpoint': f'{s["end_time"]:.6f}'})
        return opts
