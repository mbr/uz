from collections import OrderedDict
import bz2
from datetime import datetime
import io
from struct import unpack
from time import localtime

from backports import lzma

from .util import (RandomAccessBuffer, DecompressingReader, GzipReader,
                   BufferView)


class FormatHeader(object):
    name = u'Unnamed header format'
    compression = False
    archive = False
    streamable = True

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

    def strip_ending(self, filename):
        if not filename.endswith(self.file_ending):
            raise ValueError('{}: {!r} does not end with {}'.format(
                self.__class__.__name__,
                filename,
                self.file_ending
            ))

        return filename[:-len(self.file_ending)]

    def __str__(self):
        return unicode(self).encode('utf8')


class ArchiveHeader(FormatHeader):
    archive = True


class BZipHeader(FormatHeader):
    name = 'BZip'
    compression = True
    tar_flag = '--bzip2'
    file_ending = '.bz2'

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
    def get_command(cls, action, cmd_args, parts):
        parts.pop()

        cmd = ['bunzip2', '--stdout']

        return cmd

    @classmethod
    def open(cls, file):
        return DecompressingReader(bz2.BZ2Decompressor().decompress, file)


class XZHeader(FormatHeader):
    name = 'xz'
    compression = True
    tar_flag = '--xz'
    file_ending = '.xz'

    @classmethod
    def from_buf(cls, buf):
        if buf[:6] == b'\xfd7zXZ\x00':
            hfmt = cls()
            return hfmt

    @classmethod
    def get_command(cls, action, cmd_args, parts):
        parts.pop()

        cmd = ['xz', '--decompress', '--stdout']

        return cmd

    @classmethod
    def open(cls, file):
        return DecompressingReader(lzma.LZMADecompressor().decompress, file)


class GZipHeader(FormatHeader):
    name = 'gzip'
    compression = True
    tar_flag = '--gunzip'
    file_ending = '.gz'

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
    def get_command(cls, action, cmd_args, parts):
        parts.pop()

        cmd = ['gunzip', '--to-stdout']

        return cmd

    @classmethod
    def open(cls, file):
        return GzipReader(file)


class ZipHeader(ArchiveHeader):
    name = 'zipfile'
    compression = True
    streamable = False
    file_ending = '.zip'

    @classmethod
    def from_buf(cls, buf):
        if buf[:4] == b'\x50\x4B\x03\x04':
            hfmt = cls()

            (hfmt.extras['min_version'],
             _,
             hfmt.extras['compression_method']
             ) = unpack('<HHH', buf[4:10])

            return hfmt

    def get_command(cls, action, cmd_args, parts):
        parts.pop()

        zip_cmd = ['unzip']

        if action == 'list':
            zip_cmd.append('-l')

        zip_cmd.append(None)

        return zip_cmd


class TarHeader(ArchiveHeader):
    name = 'tarfile'
    compression = False
    file_ending = '.tar'

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


class RARHeader(ArchiveHeader):
    name = 'rarfile'
    compression = True
    streamable = False
    file_ending = '.rar'

    HEADER_V4 = b'\x52\x61\x72\x21\x1A\x07\x00'
    HEADER_V5 = b'\x52\x61\x72\x21\x1A\x07\x01\x00'

    @classmethod
    def from_buf(cls, buf):
        if buf[:len(cls.HEADER_V4)] == cls.HEADER_V4:
            hfmt = cls()
            hfmt.extras['format_version'] = '4.x'
        elif buf[:len(cls.HEADER_V5)] == cls.HEADER_V5:
            hfmt = cls()
            hfmt.extras['format_version'] = '4.x'
        else:
            return None

        return hfmt

    def get_command(cls, action, cmd_args, parts):
        parts.pop()

        rar_cmd = ['unrar', '-ierr', '-p-', '-o+', '-y']

        if action == 'list':
            if cmd_args['verbose']:
                rar_cmd.append('v')
            else:
                rar_cmd.append('l')
        else:
            rar_cmd.append('x')

        rar_cmd.append(None)

        return rar_cmd


class SevenZipHeader(ArchiveHeader):
    name = '7zfile'
    compression = True
    streamable = False
    file_ending = '.7z'

    HEADER = b'\x37\x7A\xBC\xAF\x27\x1C'

    @classmethod
    def from_buf(cls, buf):
        if buf[:len(cls.HEADER)] == cls.HEADER:
            return cls()

    def get_command(cls, action, cmd_args, parts):
        parts.pop()

        sz_cmd = ['7z']

        if action == 'list':
            sz_cmd.append('l')
        else:
            sz_cmd.append('x')

        sz_cmd.append(None)

        return sz_cmd


formats = [
    XZHeader,
    GZipHeader,
    BZipHeader,
    ZipHeader,
    TarHeader,
    RARHeader,
    SevenZipHeader,
]


def get_command(nestings, action, cmd_args, filename):
    ns = nestings[:]

    cmds = []
    while ns:
        cmds.insert(0, [arg if arg is not None else filename
                        for arg in ns[-1].get_command(action, cmd_args, ns)])

    return cmds


def get_filename(nestings, filename):
    ns = nestings[:]

    while ns:
        filename = ns.pop(0).strip_ending(filename)

    return filename


def unravel(file):
    buf = RandomAccessBuffer(io.BufferedReader(file))

    for fmt in formats:
        hfmt = fmt.from_buf(buf)

        if hfmt:
            if hfmt.archive or not hfmt.can_open:
                return [hfmt]
            else:
                return [hfmt] + unravel(hfmt.open(BufferView(buf)))

    return []
