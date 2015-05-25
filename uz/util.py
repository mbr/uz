class ReadView(object):
    def __init__(self, buf, offset=0, limit=None):
        if not isinstance(offset, int) or not isinstance(limit, int):
            raise ValueError('an integer is required')

        if limit < 0 or offset < 0:
            raise ValueError('value must be positive')

        if offset >= len(buf) or limit > len(buf):
            raise ValueError('value out of range')

        if limit < offset:
            raise ValueError('limit must be >= offset')

        self.limit = limit
        self.offset = offset
        self.buf = buf
        self.pos = offset

    def _get_pos(self):
        return self.pos + self.offset

    def __len__(self):
        return self.limit - self.offset

    def read(self, n=-1):
        if not isinstance(n, int):
            raise TypeError('an integer is required')

        buflen = len(self)
        pos = self._get_pos()
        maxread = buflen - pos
        newpos = self.pos + n

        self.pos += n
        return self.buf[pos:pos+n]

    def tell(self):
        return self._get_pos()

    def seek(self, offset, whence=0):
        if not isinstance(offset, int) or not isinstance(whence, int):
            raise TypeError('an integer is required')

        if whence == 0 and not offset > 0:
            raise ValueError('offset must be >= 0')

        if whence == 0:
            newpos = offset
        elif whence == 1:
            newpos = self.pos + offset
        elif whence == 2:
            newpos = len(self.buf) + offset
        else:
            raise ValueError('invalid value for whence')

        if newpos < 0 or newpos >= len(self.buf):
            raise ValueError('invalid offset')

        self.pos = newpos

    def seekable(self):
        return True


class RandomAccessBuffer(object):
    def __init__(self, reader):
        self.reader = reader
        self.buffer = b''
        self.pos = 0

    def _read_until(self, n):
        buflen = len(self.buffer)
        if buflen < n:
            buf = self.reader.read(n - buflen)
            self.buffer += buf
            return buf
        return ''

    def __getitem__(self, sl):
        max_pos = sl + 1 if isinstance(sl, int) else sl.stop

        self._read_until(max_pos)

        return self.buffer[sl]

    def read(self, n=None):
        if n is None:
            # read remainder
            buf = self.reader.read()
            self.buffer += buf

            return buf

        self.pos += n
        self._read_until(self.pos)

        return self.buffer[self.pos-n:self.pos]

    def seek(self, pos):
        self.pos = pos

    def tell(self):
        return self.pos
