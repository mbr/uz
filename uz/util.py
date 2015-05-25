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
