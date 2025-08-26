"""PUBLIC API"""

from __future__ import annotations

import base64
import contextlib
import enum
import re
import urllib.parse

from yt_dlp.extractor.youtube.pot.provider import PoTokenContext, PoTokenRequest
from yt_dlp.utils import traverse_obj

__all__ = ['WEBPO_CLIENTS', 'ContentBindingType', 'get_webpo_content_binding']

WEBPO_CLIENTS = (
    'WEB',
    'MWEB',
    'TVHTML5',
    'WEB_EMBEDDED_PLAYER',
    'WEB_CREATOR',
    'WEB_REMIX',
    'TVHTML5_SIMPLY',
    'TVHTML5_SIMPLY_EMBEDDED_PLAYER',
)


class ContentBindingType(enum.Enum):
    VISITOR_DATA = 'visitor_data'
    DATASYNC_ID = 'datasync_id'
    VIDEO_ID = 'video_id'
    VISITOR_ID = 'visitor_id'


def get_webpo_content_binding(
    request: PoTokenRequest,
    webpo_clients=WEBPO_CLIENTS,
    bind_to_visitor_id=False,
) -> tuple[str | None, ContentBindingType | None]:

    client_name = traverse_obj(request.innertube_context, ('client', 'clientName'))
    if not client_name or client_name not in webpo_clients:
        return None, None

    if request.context == PoTokenContext.GVS or client_name in ('WEB_REMIX', ):
        if request.is_authenticated:
            return request.data_sync_id, ContentBindingType.DATASYNC_ID
        else:
            if bind_to_visitor_id:
                visitor_id = _extract_visitor_id(request.visitor_data)
                if visitor_id:
                    return visitor_id, ContentBindingType.VISITOR_ID
            return request.visitor_data, ContentBindingType.VISITOR_DATA

    elif request.context in (PoTokenContext.PLAYER, PoTokenContext.SUBS):
        return request.video_id, ContentBindingType.VIDEO_ID

    return None, None


def _extract_visitor_id(visitor_data):
    if not visitor_data:
        return None

    # Attempt to extract the visitor ID from the visitor_data protobuf
    # xxx: ideally should use a protobuf parser
    with contextlib.suppress(Exception):
        visitor_id = base64.urlsafe_b64decode(
            urllib.parse.unquote_plus(visitor_data))[2:13].decode()
        # check that visitor id is all letters and numbers
        if re.fullmatch(r'[A-Za-z0-9_-]{11}', visitor_id):
            return visitor_id

    return None
