from StringIO import StringIO

import pytest
from uz.util import RandomAccessBuffer


@pytest.fixture
def val():
    return 'abcdefghijklmnopqrstuvwxyz' * 1000


@pytest.fixture
def sbuf(val):
    return StringIO(val)


@pytest.fixture
def rabuf(sbuf):
    return RandomAccessBuffer(sbuf)


def test_straight_read(rabuf, val):
    assert rabuf.read() == val


def test_read_twice(rabuf):
    assert rabuf.read(3) == 'abc'
    assert rabuf[0:3] == 'abc'


def test_seek(rabuf):
    rabuf.seek(3)

    assert rabuf.read(3) == 'def'

    assert rabuf[0:6] == 'abcdef'
