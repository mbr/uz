from datetime import datetime
from functools import partial
import io
from struct import unpack, calcsize
import zlib


class RandomAccessBuffer(object):
    """Allow random read access over a stream.

    :param reader: A buffered reader (must have a .read() method that returns
                   exactly n bytes upon read, provided there are enough left).
    """
    def __init__(self, reader):
        self.reader = reader
        self.buffer = b''

    def _read_until(self, newpos):
        if newpos is None:
            buf = self.reader.read()
        elif len(self.buffer) >= newpos:
            # already have what we need
            return
        else:
            buf = self.reader.read(newpos - len(self.buffer))

        self.buffer = buf if not self.buffer else self.buffer + buf
        return buf

    def __getitem__(self, pos):
        if isinstance(pos, int):
            if pos < 0:
                until = None
            else:
                until = pos + 1
        elif isinstance(pos, slice):
            until = pos.stop
        else:
            raise TypeError('index must be integer or slice')

        self._read_until(until)

        return self.buffer[pos]


class BufferView(io.RawIOBase):
    def __init__(self, buffer, pos=0):
        super(BufferView)
        self.buf = buffer
        self.pos = pos

    def readable(self):
        return True

    def readinto(self, b):
        # ensure enough data is available
        self.buf._read_until(self.pos + len(b))

        end = min(self.pos + len(b), len(self.buf.buffer))
        chunk = self.buf.buffer[self.pos:end]
        self.pos += len(chunk)

        b[:len(chunk)] = chunk
        return len(chunk)


class DecompressingReader(io.RawIOBase):
    def __init__(self, decompress, source, bufsize=4096):
        super(DecompressingReader, self).__init__()
        self.source = source
        self.decompress = decompress
        self.bufsize = bufsize
        self._dbuf = None

    def readable(self):
        return True

    def readinto(self, b):
        blen = len(b)
        while True:
            if self._dbuf:
                chunk = self._dbug
                break

            rbuf = self.source.read(self.bufsize)
            if not rbuf:
                return 0

            chunk = self.decompress(rbuf)
            if chunk:
                break

        rv, self._dbug = chunk[:blen], chunk[blen:]
        b[:len(rv)] = rv
        return len(rv)


class GzipReader(io.RawIOBase):
    # implementation according to https://tools.ietf.org/html/rfc1952
    _HEADER = '<BBBBIBB'

    def __init__(self, input_stream):
        super(GzipReader, self).__init__()
        self.input_stream = input_stream
        self.initialized = False

    def readable(self):
        return True

    def _read_n(self, n):
        buf = self.input_stream.read(n)
        if len(buf) != n:
            raise IOError('Unexpected EOF while decompressing. Is the input '
                          'stream buffered?')
        return buf

    def readinto(self, b):
        if not self.initialized:
            self.read_header()
            self.initialized = True

        blen = len(b)

        if self._zlibdec.unconsumed_tail:
            chunk = self._zlibdec.decompress(
                self._zlibdec.unconsumed_tail, blen
            )
        else:
            # a crappy heuristic, but a rather safe one
            raw = self.input_stream.read(blen)
            if not raw:
                chunk = b''

            chunk = self._zlibdec.decompress(raw, blen)

        b[:len(chunk)] = chunk
        return len(chunk)

    def read_header(self):
        buf = self._read_n(calcsize(self._HEADER))

        id1, id2, cm, flg, mtime, xfl, os = unpack(self._HEADER, buf)

        if (id1, id2) != (31, 139):
            raise IOError('Did not find valid gzip header')

        if cm != 0x08:
            raise NotImplementedError(
                'Unknown compression method 0x{:02x} (only deflate is '
                'supported.'.format(cm))

        if flg & 0b11100000:
            raise NotImplementedError(
                'Unsupported flags found: {:08b}'.format(flg)
            )

        FTEXT = flg & 1               # file is "probably" ascii text
        FHCRC = flg & (1 << 1)        # crc checksum (ignored; see rfc)
        FEXTRA = flg & (1 << 2)       # completely ignored
        FNAME = flg & (1 << 3)        # original filename
        FCOMMENT = flg & (1 << 4)     # latin-1 comment

        self.gzip_MTIME = datetime.fromtimestamp(mtime)
        self.gzip_FTEXT = bool(FTEXT)

        # xfl ignored
        self.gzip_OS = {
            0: 'FAT filesystem (MS-DOS, OS/2, NT/Win32)',
            1: 'Amiga',
            2: 'VMS (or OpenVMS)',
            3: 'Unix',
            4: 'VM/CMS',
            5: 'Atari TOS',
            6: 'HPFS filesystem (OS/2, NT)',
            7: 'Macintosh',
            8: 'Z-System',
            9: 'CP/M',
            10: 'TOPS-20',
            11: 'NTFS filesystem (NT)',
            12: 'QDOS',
            13: 'Acorn RISCOS',
            255: 'unknown',
        }.get(os, 'invalid')

        if FEXTRA:
            xlen = unpack('<H', self._read_n(2))[0]
            self._read_n(xlen)

        def read_str0():
            return b''.join(
                c for c in iter(partial(self._read_n, 1), b'\x00')
            )

        self.gzip_NAME = self.gzip_COMMENT = self.gzip_CRC = None
        if FNAME:
            self.gzip_NAME = read_str0()

        if FCOMMENT:
            self.gzip_COMMENT = read_str0()

        if FHCRC:
            # skip crc
            self.gzip_CRC = self._read_n(2)

        # negative window size supresses headers
        self._zlibdec = zlib.decompressobj(-zlib.MAX_WBITS)
