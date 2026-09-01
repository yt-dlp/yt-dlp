import threading
import weakref


_POLICIES = weakref.WeakKeyDictionary()
_POLICIES_LOCK = threading.Lock()


def get_video_detail(universal_data):
    if not isinstance(universal_data, dict):
        return {}
    video_detail = (
        universal_data.get('webapp.video-detail')
        or universal_data.get('webapp.reflow.video.detail')
        or {})
    return video_detail if isinstance(video_detail, dict) else {}


def get_video_data(video_detail):
    if not isinstance(video_detail, dict):
        return {}
    item_info = video_detail.get('itemInfo')
    item_struct = item_info.get('itemStruct') if isinstance(item_info, dict) else None
    return item_struct if isinstance(item_struct, dict) else {}


def get_video_status(video_detail):
    if not isinstance(video_detail, dict):
        return None
    try:
        return int(video_detail.get('statusCode'))
    except (TypeError, ValueError):
        return None


def has_playable_video(video_detail):
    video = get_video_data(video_detail).get('video', {})
    return isinstance(video, dict) and bool(video.get('playAddr'))


class TikTokWebpagePolicy:
    def __init__(self, targets):
        self._targets = list(dict.fromkeys(targets))
        self._lock = threading.Lock()

    def candidates(self):
        with self._lock:
            return tuple(self._targets)

    def succeeded(self, target):
        self._move(target, 0)

    def failed(self, target):
        self._move(target, -1)

    def _move(self, target, index):
        with self._lock:
            self._targets.remove(target)
            if index < 0:
                self._targets.append(target)
            else:
                self._targets.insert(index, target)


def get_tiktok_webpage_policy(ydl):
    with _POLICIES_LOCK:
        policy = _POLICIES.get(ydl)
        if policy is not None:
            return policy
        targets = [target for target, _ in ydl._get_available_impersonate_targets()] or [True]
        policy = TikTokWebpagePolicy(targets)
        _POLICIES[ydl] = policy
        return policy
