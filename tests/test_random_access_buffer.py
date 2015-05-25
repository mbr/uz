from io import BytesIO, BufferedReader

import pytest
from uz.util import RandomAccessBuffer


@pytest.fixture
def val():
    return 'abcdefghijklmnopqrstuvwxyz' * 1000


@pytest.fixture
def stream(val):
    return BufferedReader(BytesIO(val))


@pytest.fixture
def rabuf(stream):
    return RandomAccessBuffer(stream)


def test_full_slice(rabuf, val):
    assert rabuf[:] == val


def test_read_twice(rabuf):
    assert rabuf[0:3] == 'abc'
    assert rabuf[0:3] == 'abc'


def test_random_read(rabuf):
    assert rabuf[0:6] == 'abcdef'
    assert rabuf[3] == 'd'
    assert rabuf[-2] == 'y'
    assert rabuf[28:30] == 'cd'


def test_slices(rabuf, val):
    assert rabuf[:2] == 'ab'
    assert rabuf[20:] == 'uvwxyz' + 'abcdefghijklmnopqrstuvwxyz' * 999
    assert rabuf[:-2] == ('abcdefghijklmnopqrstuvwxyz' * 999 +
                          'abcdefghijklmnopqrstuvwx')
    assert rabuf[:] == val
    assert rabuf[:2] == 'ab'
