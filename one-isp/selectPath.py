# coding=utf-8
""" Module implements different path pruning strategies
"""
from collections import defaultdict
import random
import functools


_RANDOM = ['random', 'rand']
_SHORTEST = ['shortest', 'short', 'kshortest', 'k-shortest', 'kshort',
             'k-short']


def chooserand(pptc, numPaths):
    """ Chooses a number of paths uniformly at random

    :param pptc: paths per commodity
    :param numPaths: number of paths to pick per commodity
    :return: the new (chosen) paths per each commodity
    :rtype: dict
    """
    newppk = {}
    for comm in pptc:
        if len(pptc[comm]) > numPaths:
            newppk[comm] = random.sample(pptc[comm], numPaths)
        else:
            newppk[comm] = pptc[comm]
    return newppk


def sortPathsPerCommodity(pptc, key=None, inplace=True):
    """
    Sort paths per commodity

    :param pptc: paths per traffic class
    :param key: criteria to sort by. If none, path length is used
    :param inplace: sort in place. If False, new sorted ppk is returned.
    :return: New ppk if *inplace=False* otherwise None
    """
    if key is None:
        key = len
    if inplace:
        for tc in pptc:
            pptc[tc].sort(key=len)
    else:
        newppk = {}
        for tc in pptc:
            newppk[tc] = sorted(pptc[tc], key=key)
        return newppk


def kShortestPaths(pptc, numPaths, needsSorting=True, inplace=True):
    """ Chooses K shortest paths
    :param pptc: paths per commodity
    :param numPaths: number of paths to choose (k) per commodity
    :param needsSorting: whether we need to sort the paths first
    :param inplace: if *needsSorting* is True, whether to sort the ppk in
        place or make a copy
    :return: the new (chosen) paths per commodity
    :rtype: dict
    """
    newppk = None
    if needsSorting:
        newppk = sortPathsPerCommodity(pptc, key=len, inplace=inplace)
    if newppk is None:
        newppk = pptc
    result = {}
    for comm in pptc:
        result[comm] = newppk[comm][:numPaths]
    return result


def filterPaths(pptc, func):
    """
    Filter paths using a function.

    :param pptc: paths per traffic class
    :param func: function to be applied to each path
    :return: new paths per commodity with paths for which *func* returned a
        true value
    """
    assert (hasattr(func, '__call__'))
    result = defaultdict(lambda: [])
    for tc in pptc:
        for path in pptc[tc]:
            if func(path):
                result[tc].append(path)
    return result


def getSelectFunction(strName, kwargs=None):
    """
    Return the path selection function based on name.
    Allows passing of additional keyword arguments, so that the returned function can satisfy the following signature::
        function(pptc, selectNumber)

    :param strName: the name of the function
    :param kwargs: a dictionary of keyword arguements to be passed to the function
    :return: the callable object with
    :raise: InvalidConfigException
        if the name passed in is not supported

    Supported names so far: 'random' and 'shortest' For example::

        f = getSelectFunction('random')
        pptc = f(pptc, 5)

    will give you 5 paths per traffic class, randomly chosen

    """
    if kwargs is None:
        kwargs = {}
    if strName.lower() in _RANDOM:
        return functools.partial(chooserand, **kwargs)
    elif strName.lower() in _SHORTEST:
        return functools.partial(kShortestPaths, **kwargs)
    else:
        raise InvalidConfigException("Unknown select method")
