import base64
import io
import itertools
import struct
import time
import urllib.parse

from .fragment import FragmentFD
from ..compat import compat_etree_fromstring
from ..networking.exceptions import HTTPError
from ..utils import fix_xml_ampersands, xpath_text


class DataTruncatedError(Exception):
    pass


class FlvReader(io.BytesIO):
    """
    Reader for Flv files
    The file format is documented in https://www.adobe.com/devnet/f4v.html
    """

    def read_bytes(self, n):
        data = self.read(n)
        if len(data) < n:
            raise DataTruncatedError(
                'FlvReader error: need %d bytes while only %d bytes got' % (
                    n, len(data)))
        return data

    # Utility functions for reading numbers and strings
    def read_unsigned_long_long(self):
        return struct.unpack('!Q', self.read_bytes(8))[0]

    def read_unsigned_int(self):
        return struct.unpack('!I', self.read_bytes(4))[0]

    def read_unsigned_char(self):
        return struct.unpack('!B', self.read_bytes(1))[0]

    def read_string(self):
        res = b''
        while True:
            char = self.read_bytes(1)
            if char == b'\x00':
                break
            res += char
        return res

    def read_box_info(self):
        """
        Read a box and return the info as a tuple: (box_size, box_type, box_data)
        """
        real_size = size = self.read_unsigned_int()
        box_type = self.read_bytes(4)
        header_end = 8
        if size == 1:
            real_size = self.read_unsigned_long_long()
            header_end = 16
        return real_size, box_type, self.read_bytes(real_size - header_end)

    def read_asrt(self):
        # version
        self.read_unsigned_char()
        # flags
        self.read_bytes(3)
        quality_entry_count = self.read_unsigned_char()
        # QualityEntryCount
        for _ in range(quality_entry_count):
            self.read_string()

        segment_run_count = self.read_unsigned_int()
        segments = []
        for _ in range(segment_run_count):
            first_segment = self.read_unsigned_int()
            fragments_per_segment = self.read_unsigned_int()
            segments.append((first_segment, fragments_per_segment))

        return {
            'segment_run': segments,
        }

    def read_afrt(self):
        # version
        self.read_unsigned_char()
        # flags
        self.read_bytes(3)
        # time scale
        self.read_unsigned_int()

        quality_entry_count = self.read_unsigned_char()
        # QualitySegmentUrlModifiers
        for _ in range(quality_entry_count):
            self.read_string()

        fragments_count = self.read_unsigned_int()
        fragments = []
        for _ in range(fragments_count):
            first = self.read_unsigned_int()
            first_ts = self.read_unsigned_long_long()
            duration = self.read_unsigned_int()
            if duration == 0:
                discontinuity_indicator = self.read_unsigned_char()
            else:
                discontinuity_indicator = None
            fragments.append({
                'first': first,
                'ts': first_ts,
                'duration': duration,
                'discontinuity_indicator': discontinuity_indicator,
            })

        return {
            'fragments': fragments,
        }

    def read_abst(self):
        # version
        self.read_unsigned_char()
        # flags
        self.read_bytes(3)

        self.read_unsigned_int()  # BootstrapinfoVersion
        # Profile,Live,Update,Reserved
        flags = self.read_unsigned_char()
        live = flags & 0x20 != 0
        # time scale
        self.read_unsigned_int()
        # CurrentMediaTime
        self.read_unsigned_long_long()
        # SmpteTimeCodeOffset
        self.read_unsigned_long_long()

        self.read_string()  # MovieIdentifier
        server_count = self.read_unsigned_char()
        # ServerEntryTable
        for _ in range(server_count):
            self.read_string()
        quality_count = self.read_unsigned_char()
        # QualityEntryTable
        for _ in range(quality_count):
            self.read_string()
        # DrmData
        self.read_string()
        # MetaData
        self.read_string()

        segments_count = self.read_unsigned_char()
        segments = []
        for _ in range(segments_count):
            box_size, box_type, box_data = self.read_box_info()
            assert box_type == b'asrt'
            segment = FlvReader(box_data).read_asrt()
            segments.append(segment)
        fragments_run_count = self.read_unsigned_char()
        fragments = []
        for _ in range(fragments_run_count):
            box_size, box_type, box_data = self.read_box_info()
            assert box_type == b'afrt'
            fragments.append(FlvReader(box_data).read_afrt())

        return {
            'segments': segments,
            'fragments': fragments,
            'live': live,
        }

    def read_bootstrap_info(self):
        total_size, box_type, box_data = self.read_box_info()
        assert box_type == b'abst'
        return FlvReader(box_data).read_abst()


def read_bootstrap_info(bootstrap_bytes):
    return FlvReader(bootstrap_bytes).read_bootstrap_info()


def build_fragments_list(boot_info):
    """ Return a list of (segment, fragment) for each fragment in the video """
    res = []
    segment_run_table = boot_info['segments'][0]
    fragment_run_entry_table = boot_info['fragments'][0]['fragments']
    first_frag_number = fragment_run_entry_table[0]['first']
    fragments_counter = itertools.count(first_frag_number)
    for segment, fragments_count in segment_run_table['segment_run']:
        # In some live HDS streams (e.g. Rai), `fragments_count` is
        # abnormal and causing out-of-memory errors. It's OK to change the
        # number of fragments for live streams as they are updated periodically
        if fragments_count == 4294967295 and boot_info['live']:
            fragments_count = 2
        for _ in range(fragments_count):
            res.append((segment, next(fragments_counter)))

    if boot_info['live']:
        res = res[-2:]

    return res


def write_unsigned_int(stream, val):
    stream.write(struct.pack('!I', val))


def write_unsigned_int_24(stream, val):
    stream.write(struct.pack('!I', val)[1:])


def write_flv_header(stream):
    """Writes the FLV header to stream"""
    # FLV header
    stream.write(b'FLV\x01')
    stream.write(b'\x05')
    stream.write(b'\x00\x00\x00\x09')
    stream.write(b'\x00\x00\x00\x00')


def write_metadata_tag(stream, metadata):
    """Writes optional metadata tag to stream"""
    SCRIPT_TAG = b'\x12'
    FLV_TAG_HEADER_LEN = 11

    if metadata:
        stream.write(SCRIPT_TAG)
        write_unsigned_int_24(stream, len(metadata))
        stream.write(b'\x00\x00\x00\x00\x00\x00\x00')
        stream.write(metadata)
        write_unsigned_int(stream, FLV_TAG_HEADER_LEN + len(metadata))


def remove_encrypted_media(media):
    return list(filter(lambda e: 'drmAdditionalHeaderId' not in e.attrib
                                 and 'drmAdditionalHeaderSetId' not in e.attrib,
                       media))


def _add_ns(prop, ver=1):
    return '{http://ns.adobe.com/f4m/%d.0}%s' % (ver, prop)


def get_base_url(manifest):
    base_url = xpath_text(
        manifest, [_add_ns('baseURL'), _add_ns('baseURL', 2)],
        'base URL', default=None)
    if base_url:
        base_url = base_url.strip()
    return base_url


class F4mFD(FragmentFD):
    """
    A downloader for f4m manifests or AdobeHDS.
    """

    def _get_unencrypted_media(self, doc):
        media = doc.findall(_add_ns('media'))
        if not media:
            self.report_error('No media found')
        if not self.params.get('allow_unplayable_formats'):
            for e in (doc.findall(_add_ns('drmAdditionalHeader'))
                      + doc.findall(_add_ns('drmAdditionalHeaderSet'))):
                # If id attribute is missing it's valid for all media nodes
                # without drmAdditionalHeaderId or drmAdditionalHeaderSetId attribute
                if 'id' not in e.attrib:
                    self.report_error('Missing ID in f4m DRM')
            media = remove_encrypted_media(media)
        if not media:
            self.report_error('Unsupported DRM')
        return media

    def _get_bootstrap_from_url(self, bootstrap_url):
        bootstrap = self.ydl.urlopen(bootstrap_url).read()
        return read_bootstrap_info(bootstrap)

    def _update_live_fragments(self, bootstrap_url, latest_fragment):
        fragments_list = []
        retries = 30
        while (not fragments_list) and (retries > 0):
            boot_info = self._get_bootstrap_from_url(bootstrap_url)
            fragments_list = build_fragments_list(boot_info)
            fragments_list = [f for f in fragments_list if f[1] > latest_fragment]
            if not fragments_list:
                # Retry after a while
                time.sleep(5.0)
                retries -= 1

        if not fragments_list:
            self.report_error('Failed to update fragments')

        return fragments_list

    def _parse_bootstrap_node(self, node, base_url):
        # Sometimes non empty inline bootstrap info can be specified along
        # with bootstrap url attribute (e.g. dummy inline bootstrap info
        # contains whitespace characters in [1]). We will prefer bootstrap
        # url over inline bootstrap info when present.
        # 1. http://live-1-1.rutube.ru/stream/1024/HDS/SD/C2NKsS85HQNckgn5HdEmOQ/1454167650/S-s604419906/move/four/dirs/upper/1024-576p.f4m
        bootstrap_url = node.get('url')
        if bootstrap_url:
            bootstrap_url = urllib.parse.urljoin(
                base_url, bootstrap_url)
            boot_info = self._get_bootstrap_from_url(bootstrap_url)
        else:
            bootstrap_url = None
            bootstrap = base64.b64decode(node.text)
            boot_info = read_bootstrap_info(bootstrap)
        return boot_info, bootstrap_url

    def real_download(self, filename, info_dict):
        man_url = info_dict['url']
        requested_bitrate = info_dict.get('tbr')
        self.to_screen(f'[{self.FD_NAME}] Downloading f4m manifest')

        urlh = self.ydl.urlopen(self._prepare_url(info_dict, man_url))
        man_url = urlh.url
        # Some manifests may be malformed, e.g. prosiebensat1 generated manifests
        # (see https://github.com/ytdl-org/youtube-dl/issues/6215#issuecomment-121704244
        # and https://github.com/ytdl-org/youtube-dl/issues/7823)
        manifest = fix_xml_ampersands(urlh.read().decode('utf-8', 'ignore')).strip()

        doc = compat_etree_fromstring(manifest)
        formats = [(int(f.attrib.get('bitrate', -1)), f)
                   for f in self._get_unencrypted_media(doc)]
        if requested_bitrate is None or len(formats) == 1:
            # get the best format
            formats = sorted(formats, key=lambda f: f[0])
            rate, media = formats[-1]
        else:
            rate, media = next(filter(
                lambda f: int(f[0]) == requested_bitrate, formats))

        # Prefer baseURL for relative URLs as per 11.2 of F4M 3.0 spec.
        man_base_url = get_base_url(doc) or man_url

        base_url = urllib.parse.urljoin(man_base_url, media.attrib['url'])
        bootstrap_node = doc.find(_add_ns('bootstrapInfo'))
        boot_info, bootstrap_url = self._parse_bootstrap_node(
            bootstrap_node, man_base_url)
        live = boot_info['live']
        metadata_node = media.find(_add_ns('metadata'))
        if metadata_node is not None:
            metadata = base64.b64decode(metadata_node.text)
        else:
            metadata = None

        fragments_list = build_fragments_list(boot_info)
        test = self.params.get('test', False)
        if test:
            # We only download the first fragment
            fragments_list = fragments_list[:1]
        total_frags = len(fragments_list)
        # For some akamai manifests we'll need to add a query to the fragment url
        akamai_pv = xpath_text(doc, _add_ns('pv-2.0'))

        ctx = {
            'filename': filename,
            'total_frags': total_frags,
            'live': bool(live),
        }

        self._prepare_frag_download(ctx)

        dest_stream = ctx['dest_stream']

        if ctx['complete_frags_downloaded_bytes'] == 0:
            write_flv_header(dest_stream)
            if not live:
                write_metadata_tag(dest_stream, metadata)

        base_url_parsed = urllib.parse.urlparse(base_url)

        self._start_frag_download(ctx, info_dict)

        frag_index = 0
        while fragments_list:
            seg_i, frag_i = fragments_list.pop(0)
            frag_index += 1
            if frag_index <= ctx['fragment_index']:
                continue
            name = 'Seg%d-Frag%d' % (seg_i, frag_i)
            query = []
            if base_url_parsed.query:
                query.append(base_url_parsed.query)
            if akamai_pv:
                query.append(akamai_pv.strip(';'))
            if info_dict.get('extra_param_to_segment_url'):
                query.append(info_dict['extra_param_to_segment_url'])
            url_parsed = base_url_parsed._replace(path=base_url_parsed.path + name, query='&'.join(query))
            try:
                success = self._download_fragment(ctx, url_parsed.geturl(), info_dict)
                if not success:
                    return False
                down_data = self._read_fragment(ctx)
                reader = FlvReader(down_data)
                while True:
                    try:
                        _, box_type, box_data = reader.read_box_info()
                    except DataTruncatedError:
                        if test:
                            # In tests, segments may be truncated, and thus
                            # FlvReader may not be able to parse the whole
                            # chunk. If so, write the segment as is
                            # See https://github.com/ytdl-org/youtube-dl/issues/9214
                            dest_stream.write(down_data)
                            break
                        raise
                    if box_type == b'mdat':
                        self._append_fragment(ctx, box_data)
                        break
            except HTTPError as err:
                if live and (err.status == 404 or err.status == 410):
                    # We didn't keep up with the live window. Continue
                    # with the next available fragment.
                    msg = 'Fragment %d unavailable' % frag_i
                    self.report_warning(msg)
                    fragments_list = []
                else:
                    raise

            if not fragments_list and not test and live and bootstrap_url:
                fragments_list = self._update_live_fragments(bootstrap_url, frag_i)
                total_frags += len(fragments_list)
                if fragments_list and (fragments_list[0][1] > frag_i + 1):
                    msg = 'Missed %d fragments' % (fragments_list[0][1] - (frag_i + 1))
                    self.report_warning(msg)

        return self._finish_frag_download(ctx, info_dict)
