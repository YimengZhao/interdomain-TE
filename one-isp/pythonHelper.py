# coding=utf-8
""" Various utility functions

.. note::
    Some code copied from other projects, might not be related
"""
import functools
import itertools
import warnings
from collections import defaultdict


def tup2str(t):
    """ Convert tuple to string

    :param t: the tuple
    """
    return '_'.join(map(str, t))


def str2tup(s, d='_'):
    """ Convert string to tuple

    :param s: string
    :param d: delimiter
    :return: tuple
    """
    return tuple(s.split(d))


# Self-nesting dict
Tree = lambda: defaultdict(Tree)


def deprecated(func):
    """
    A deprecated decorator. For convenience.

    :param func:
    :return:
        This is a decorator which can be used to mark functions
        as deprecated. It will result in a warning being emitted
        when the function is used.
    """

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.warn_explicit(
            "Call to deprecated function {}.".format(func.__name__),
            category=DeprecationWarning,
            filename=func.func_code.co_filename,
            lineno=func.func_code.co_firstlineno + 1
        )
        return func(*args, **kwargs)

    return new_func


class alwaysOneDict(object):
    """ Dictionary that returns one for any key. Only supports *get* operation """

    def __getitem__(self, key):
        return 1.


def listEq(a, b):
    return len(a) == len(b) and all([x == y for x, y in itertools.izip(a, b)])
