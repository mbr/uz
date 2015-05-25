from collections import OrderedDict
import bz2
from datetime import datetime
import gzip
import io
from struct import unpack
from time import localtime

from backports import lzma

from .util import RandomAccessBuffer


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
    tar_flag = '--bzip2'

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
        return bz2.BZ2File(file.name)


class XZHeader(FormatHeader):
    name = 'xz'
    compression = True
    tar_flag = '--xz'

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
    tar_flag = '--gunzip'

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

    @classmethod
    def get_command(cls, action, cmd_args, parts):
        parts.pop()

        cmd = ['gunzip', '--to-stdout']

        return cmd


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

    @classmethod
    def get_command(cls, action, cmd_args, parts):
        # parts[-1] is the tar command
        parts.pop()

        assert action in ('list', 'extract')

        tar_cmd = ['tar', '--' + action]

        if cmd_args['verbose']:
            tar_cmd.append('--verbose')

        if parts:
            tar_flag = getattr(parts[-1], 'tar_flag', None)
            if tar_flag:
                parts.pop()
                tar_cmd.append(tar_flag)

        return tar_cmd


formats = [
    XZHeader,
    GZipHeader,
    BZipHeader,
    ZipHeader,
    TarHeader,
]


def get_command(nestings, action, cmd_args, filename):
    ns = nestings[:]

    cmds = []
    while ns:
        cmds.insert(0, [arg if arg is not None else filename
                        for arg in ns[-1].get_command(action, cmd_args, ns)])

    return cmds


def unravel(file):
    buf = RandomAccessBuffer(io.BufferedReader(file))

    for fmt in formats:
        hfmt = fmt.from_buf(buf)

        if hfmt:
            if hfmt.archive or not hfmt.can_open:
                return [hfmt]
            else:
                return [hfmt] + unravel(hfmt.open(file))

    return []
