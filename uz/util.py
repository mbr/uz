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
