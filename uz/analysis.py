from collections import OrderedDict
import bz2
from datetime import datetime
import gzip
from struct import unpack
from time import localtime

from backports import lzma


class FormatHeader(object):
    name = u'Unnamed header format'
    compression = False
    archive = False

    def __init__(self, extras=None):
        self.extras = extras or OrderedDict()

    @classmethod
    def from_buf(self, buf):
        raise RuntimeError

    def __unicode__(self):
        buf = [self.name]

        extras = getattr(self, 'extras', None)
        if extras:
            buf.append('(')
            buf.append(u', '.join('{0[0]}={0[1]!r}'.format(i)
                                  for i in extras.items()))
            buf.append(')')

        return u''.join(buf)

    @property
    def can_open(self):
        return callable(getattr(self, 'open', None))

    def __str__(self):
        return unicode(self).encode('utf8')


class BZipHeader(FormatHeader):
    name = 'BZip'
    compression = True

    @classmethod
    def from_buf(cls, buf):
        if buf[:2] == b'BZ':
            hfmt = cls()
            if buf[2] == b'h':
                hfmt.extras['version'] = '2 (Huffman)'
            elif buf[2] == b'0':
                hfmt.extras['version'] = '1'
            else:
                return  # invalid header

            hfmt.extras['blocksize'] = '{}00 kB'.format(buf[3])
            return hfmt

    @classmethod
    def open(cls, file):
        return bz2.open(file.name)


class XZHeader(FormatHeader):
    name = 'xz'
    compression = True

    @classmethod
    def from_buf(cls, buf):
        if buf[:6] == b'\xfd7zXZ\x00':
            hfmt = cls()
            return hfmt

    @classmethod
    def open(cls, file):
        return lzma.open(file.name)


class GZipHeader(FormatHeader):
    name = 'gzip'
    compression = True

    @classmethod
    def from_buf(cls, buf):
        if buf[:2] == b'\x1F\x8B':
            hfmt = cls()
            hfmt.extras['compression_method'] = {
                b'\x00': 'store',
                b'\x01': 'compress',
                b'\x02': 'pack',
                b'\x03': 'lzh',
                b'\x08': 'deflate',
            }.get(buf[2], 'unknown')

            lt = localtime(unpack('<I', buf[4:8])[0])
            hfmt.extras['timestamp'] = datetime(*lt[:6]).isoformat()

            return hfmt

    @classmethod
    def open(cls, file):
        return gzip.open(file.name)


class ZipHeader(FormatHeader):
    name = 'zipfile'
    compression = True
    archive = True

    @classmethod
    def from_buf(cls, buf):
        if buf[:4] == b'\x50\x4B\x03\x04':
            hfmt = cls()

            (hfmt.extras['min_version'],
             _,
             hfmt.extras['compression_method']
             ) = unpack('<HHH', buf[4:10])

            return hfmt


class TarHeader(FormatHeader):
    name = 'tarfile'
    compression = False
    archive = True

    @classmethod
    def from_buf(cls, buf):
        if buf[257:263] == b'ustar ':
            hfmt = cls()
            hfmt.extras['version'] = unpack('<H', buf[263:265])[0]
            return hfmt


class SmartBuffer(object):
    def __init__(self, reader):
        self.reader = reader
        self.buffer = b''

    def __getitem__(self, sl):
        max_pos = sl + 1 if isinstance(sl, int) else sl.stop

        buflen = len(self.buffer)
        if buflen < max_pos:
            self.buffer += self.reader.read(max_pos - buflen)
        return self.buffer[sl]


formats = [
    XZHeader,
    GZipHeader,
    BZipHeader,
    ZipHeader,
    TarHeader,
]


def unravel(file):
    buf = SmartBuffer(file)

    for fmt in formats:
        hfmt = fmt.from_buf(buf)

        if hfmt:
            if hfmt.archive or not hfmt.can_open:
                return [hfmt]
            else:
                return [hfmt] + unravel(hfmt.open(file))

    return []
