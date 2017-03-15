# coding=utf-8

import networkx as nx

from paths import Path

def generatePathsPerIE(source, sink, topology, predicate, cutoff,
                       maxPaths, modifyFunc=None,
                       raiseOnEmpty=True):
    """
    Generates all simple paths between source and sink using a given predicate.

    :param source: the start node (source)
    :param sink: the end node (sink)
    :param topology: the topology on which we are operating
    :param predicate: the predicate that defines a valid path, must be a
       python callable that accepts a path and a topology, returns a boolean
    :param cutoff: the maximum length of a path.
        Helps to avoid unnecessarily long paths.
    :param maxPaths: maximum number of paths paths to return, by default no limit.
    :param modifyFunc: a custom function may be passed to convert a list of
        nodes, to a different type of path.

        For example, when choosing middleboxes, we use :py:func:`~predicates.useMboxModifier`
        to expand a list of switches into all possible combinations of middleboxes
    :param raiseOnEmpty: whether to raise an exception if no valid paths are detected.
        Set to True by default.
    :raise NoPathsException: if no paths are found
    :returns: a list of path objects
    :rtype: list
    """
    G = topology.getGraph()
    paths = []
    num = 0
    #maxPaths = 1
    for p in nx.all_simple_paths(G, source, sink):
        if modifyFunc is None:
            if predicate(p, topology):
                paths.append(Path(p))
                num += 1
        else:
            np = modifyFunc(p, num, topology)
            if isinstance(np, list):
                for innerp in np:
                    if predicate(innerp, topology):
                        paths.append(innerp)
                        num += 1
            else:
                if predicate(np, topology):
                    paths.append(np)
                    num += 1
    if not paths:
        if raiseOnEmpty:
	    print 'no paths between {} and {}'.format(source, sink)
            raise exceptions.NoPathsException("No paths between {} and {}".format(source, sink))
    paths.sort(key=lambda x: x.getNodesNum(), reverse=False)
    paths = paths[0:maxPaths]
    return paths

def generatePath(ie_pairs, topology, predicate, cutoff, maxPaths=3, modifyFunc=None, raiseOnEmpty=True):
    pptc_set = {}
    for ie in ie_pairs:
        i, e = ie
        pptc_set[ie] = generatePathsPerIE(i, e, topology, predicate, cutoff, maxPaths, modifyFunc, raiseOnEmpty)
    return pptc_set

def generatePathsPerTrafficClass(topology, trafficClasses, predicate, cutoff,
                                 maxPaths=3, modifyFunc=None,
                                 raiseOnEmpty=True):
    """
    Generate all simple paths for each traffic class

    :param topology: topology to work with
    :param trafficClasses: a list of traffic classes for which paths should be generated
    :param predicate: predicate to use, must be a valid preciate callable
    :param cutoff:  the maximum length of a path.
    :param maxPaths: maximum number of paths paths to return, by default no limit.
    :param modifyFunc: a custom function may be passed to convert a list of
        nodes, to a different type of path.

        For example, when choosing middleboxes, we use :py:func:`~predicates.useMboxModifier`
        to expand a list of switches into all possible combinations of middleboxes
    :param raiseOnEmpty: whether to raise an exception if no valid paths are detected.
        Set to True by default.
    :raise NoPathsException: if no paths are found for a trafficClass
    :returns: a mapping of traffic classes to a list of path objects
    :rtype: dict
    """
    result = {}
    for t in trafficClasses:
        result[t] = generatePathsPerIE(t.src, t.dst, topology, predicate, cutoff, maxPaths,
                                       modifyFunc, raiseOnEmpty)
    return result
