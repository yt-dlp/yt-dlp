import enum

from .hoodoo import Color, TermCode, Typeface, format_text
from ..utils import format_bytes, timetuple_from_msec, try_call


class Style(enum.Enum):
    DOWNLOADED_BYTES = TermCode(Color.LIGHT | Color.BLUE)
    PERCENT = TermCode(Color.LIGHT | Color.BLUE)
    ETA = TermCode(Color.YELLOW)
    SPEED = TermCode(Color.GREEN)
    ELAPSED = TermCode(Typeface.BOLD, Color.WHITE)
    TOTAL_BYTES = TermCode()
    TOTAL_BYTES_ESTIMATE = TermCode()


def apply_progress_format(progress_dict, use_color=None):
    default_template = format_and_get_default_template(progress_dict)
    if not default_template:
        return

    if use_color:
        for item in Style:
            name = f'_{item.name.lower()}_str'
            if name not in progress_dict:
                continue
            progress_dict[name] = format_text(progress_dict[name], item.value)

    progress_dict['_default_template'] = default_template % progress_dict


def format_and_get_default_template(progress_dict):
    def has_field(*field_names):
        return all(progress_dict.get(field_name) is not None for field_name in field_names)

    _format_bytes = lambda key: format_bytes(progress_dict.get(key))

    if progress_dict['status'] == 'finished':
        speed = try_call(lambda: progress_dict['total_bytes'] / progress_dict['elapsed'])
        progress_dict.update({
            'speed': speed,
            '_speed_str': format_speed(speed).strip(),
            '_total_bytes_str': format_bytes(progress_dict.get('total_bytes')),
            '_elapsed_str': format_seconds(progress_dict.get('elapsed')),
            '_percent_str': format_percent(1),
        })
        msg_template = '%(_percent_str)s'
        if has_field('total_bytes'):
            msg_template += ' of %(_total_bytes_str)s'
        if has_field('elapsed'):
            msg_template += ' in %(_elapsed_str)s'
        if has_field('speed'):
            msg_template += ' at %(_speed_str)s'

        return msg_template

    current_bytes = progress_dict.get('downloaded_bytes') or progress_dict.get('processed_bytes')

    progress_dict.update({
        '_eta_str': format_eta(progress_dict.get('eta')).strip(),
        '_speed_str': format_speed(progress_dict.get('speed')) if progress_dict.get('speed_rate') is None else format_speed_rate(progress_dict['speed_rate']),
        '_percent_str': format_percent(try_call(
            lambda: current_bytes / progress_dict['total_bytes'],
            lambda: current_bytes / progress_dict['total_bytes_estimate'],
            lambda: 0)),
        '_total_bytes_str': _format_bytes('total_bytes'),
        '_total_bytes_estimate_str': _format_bytes('total_bytes_estimate'),
        '_downloaded_bytes_str': _format_bytes('downloaded_bytes'),
        '_elapsed_str': format_seconds(progress_dict.get('elapsed')),
    })

    if progress_dict['status'] not in ('downloading', 'processing'):
        return

    msg_template = (
        '%(_percent_str)s of %(_total_bytes_str)s at %(_speed_str)s ETA %(_eta_str)s'
        if has_field('total_bytes') else
        '%(_percent_str)s of ~%(_total_bytes_estimate_str)s at %(_speed_str)s ETA %(_eta_str)s'
        if has_field('total_bytes_estimate') else
        '%(_downloaded_bytes_str)s at %(_speed_str)s (%(_elapsed_str)s)'
        if has_field('downloaded_bytes', 'elapsed') else
        '%(_downloaded_bytes_str)s at %(_speed_str)s'
        if has_field('downloaded_bytes') else
        '%(_percent_str)s at %(_speed_str)s ETA %(_eta_str)s')

    if has_field('fragment_index', 'fragment_count'):
        msg_template += ' (frag %(fragment_index)d/%(fragment_count)d)'

    elif has_field('fragment_index'):
        msg_template += ' (frag %(fragment_index)d)'

    return msg_template


def format_seconds(seconds):
    if seconds is None:
        return ' Unknown'
    time = timetuple_from_msec(int(seconds) * 1000)
    if time.hours > 99:
        return '--:--:--'
    if not time.hours:
        return f'   {time.minutes:0>2}:{time.seconds:0>2}'
    return f'{time.hours:0>2}:{time.minutes:0>2}:{time.seconds:0>2}'


def format_eta(seconds):
    if seconds is not None and seconds < 60:
        return f'{seconds}s'

    return format_seconds(seconds)


def format_percent(percent):
    return '  N/A%' if percent is None else f'{percent:>6.1%}'


def format_speed(speed):
    return ' Unknown B/s' if speed is None else f'{format_bytes(speed):>10}/s'


def format_speed_rate(rate):
    return ' ---x' if rate is None else f'{rate:>4.1f}x'
