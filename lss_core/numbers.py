"""Parsing numbers from SPEC and MCA text without ``eval``.

The readers used ``eval`` on every number in the file: slow (about 16 ms
per 4096-channel spectrum) and it executes whatever text the file holds.
``spec_number`` gives the same result as ``eval`` for every numeric
literal that appears in these files: an ``int`` for integers, a ``float``
otherwise. Anything that is not a plain number raises ``ValueError``, as
``eval`` raised for it (the readers catch that).
"""
import re

_INT = re.compile(r'[+-]?\d+\Z')
_FLOAT = re.compile(r'[+-]?(?:\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)\Z')


def spec_number(token):
    if _INT.match(token):
        return int(token)
    if _FLOAT.match(token):
        return float(token)
    raise ValueError('not a number: %r' % (token,))


def spec_numbers(tokens):
    return [spec_number(t) for t in tokens]
