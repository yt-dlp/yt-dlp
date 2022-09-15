from __future__ import unicode_literals

from ..blowfish import blowfish_cbc_decrypt
from .common import FileDownloader
from ..utils import sanitized_Request, sanitize_open
from ..compat import compat_struct_pack
import time


def writeid3v1(fo, info_dict):
    data = compat_struct_pack("3s" "30s" "30s" "30s" "4s" "28s" "BB" "B",
                              b"TAG",
                              info_dict["track"].encode('utf-8'),
                              info_dict["artist"].encode('utf-8'),
                              info_dict["album"].encode('utf-8'),
                              b"",   # year
                              b"",   # comment
                              0, int(info_dict["track_number"] or 0),  # tracknum
                              255)   # genre
    fo.write(data)


def writeid3v2(fo, info_dict, ydl):
    def make28bit(x):
        return ((x << 3) & 0x7F000000) | ((x << 2) & 0x7F0000) | ((x << 1) & 0x7F00) | (x & 127)

    def maketag(tag, content):
        return compat_struct_pack(">4sLH", tag, len(content), 0) + content

    def makeutf8(txt):
        return b"\x03" + (txt.encode('utf-8'))

    def makepic(data):
        imgframe = (b"\x00",          # text encoding
                    b"image/jpeg\x00",     # mime type
                    b"\x00",               # picture type: 'other'
                    b"\x00",               # description
                    data)
        return b''.join(imgframe)

    id3 = [
        maketag(b"TRCK", makeutf8("%02s" % str(info_dict["track_number"]))),  # decimal, no term NUL
        maketag(b"TIT2", makeutf8(info_dict["track"])),     # tern NUL ?
        maketag(b"TPE1", makeutf8(info_dict["artist"])),    # tern NUL ?
        maketag(b"TALB", makeutf8(info_dict["album"])),     # tern NUL ?
    ]
    try:
        fh = ydl.urlopen(info_dict["thumbnail"])
        id3.append(maketag(b"APIC", makepic(fh.read())))
    except Exception:
        pass

    id3data = b"".join(id3)

    hdr = compat_struct_pack(">3s" "H" "B" "L",
                             b"ID3",
                             0x400,   # version
                             0x00,    # flags
                             make28bit(len(id3data)))

    fo.write(hdr)
    fo.write(id3data)


def decryptfile(fh, key, fo, progressupdate):
    """
    Decrypt data from file <fh>, and write to file <fo>.
    decrypt using blowfish with <key>.
    Only every third 2048 byte block is encrypted.
    """
    i = 0
    byte_counter = 0
    while True:
        data = fh.read(2048)
        if not data:
            break

        if (i % 3) == 0 and len(data) == 2048:
            data = blowfish_cbc_decrypt(data, key, b"\x00\x01\x02\x03\x04\x05\x06\x07")
        fo.write(data)
        i += 1

        byte_counter += len(data)

        if (i % 16) == 0:
            progressupdate(byte_counter)


class DeezerFD(FileDownloader):
    def real_download(self, filename, info_dict):
        url = info_dict['url']
        request = sanitized_Request(url, None, {})
        data = self.ydl.urlopen(request)
        tstart = time.time()
        data_len = int(data.info().get('Content-length', 0))

        def progressupdate(byte_counter):
            self._hook_progress({
                'filename': filename,
                'status': 'downloading',
                'downloaded_bytes': byte_counter,
                'total_bytes': data_len,
                'eta': self.calc_eta(tstart, time.time(), data_len, byte_counter),
                'speed': self.calc_speed(tstart, time.time(), byte_counter),
            }, info_dict)

        def progressfinished():
            self._hook_progress({
                'filename': filename,
                'status': 'finished',
                'downloaded_bytes': data_len,
                'total_bytes': data_len,
            }, info_dict)

        stream, realfilename = sanitize_open(filename, "wb")
        try:
            decryptfile(data, info_dict['key'], stream, progressupdate)
            progressfinished()
        finally:
            if realfilename != '-':
                stream.close()
