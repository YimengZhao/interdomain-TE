# coding=utf-8
from __future__ import division

import itertools
from collections import defaultdict

import networkx
import numpy
import six

from traffic import TrafficClass, TrafficMatrix
from paths import Path

def generateIEpairs(topology):
    """
    Default way of generating ingress-egress pairs. Generates all possible n*(n-1) node combinations

    :param topology: the topology to work with
    :type topology: sol.optimization.topology.topology
    :return: list of ingress-egress pairs (as tuples)
    """
    return [pair for pair in
            itertools.product([n for n in topology.nodes()], repeat=2)
            if pair[0] != pair[1]]



def generateTrafficClasses(network_id, iepairs, trafficMatrix, classFractionDict,
                           classBytesDict=None, asdict=False, index_base=0):
    """
    Generate traffic classes from given ingress-egress pairs and traffic matrix

    :param iepairs: list of ingress-egress pairs (as tuples)
    :param trafficMatrix: the traffic matrix object
    :param classFractionDict: a dictionary mapping class name to a fraction of traffic (in flows).
        Must sum up to 1.
        Example::

            classFractionDict = {'web': .6, 'ssh': .2, 'voip': .2}

        .. note::

            This does assume that the split is even across all ingress-egress pairs

    :param classBytesDict: dictionary mapping class name to an average flow size in bytes.
        That is::

            classBytesDict = {'web': 100, 'ssh': 200, 'voip': 200}

        means that each web flow is 100 bytes, each ssh flow is 200 bytes and so on.
    :return: a list of traffic classes
    """
    #assert sum(classFractionDict.values()) == 1
    trafficClasses = []
    if asdict:
        trafficClasses = defaultdict(lambda: [])
    index = 1
    index += index_base
    print len(iepairs)
    for ie in iepairs:
        i, e = ie
        print ie
	print trafficMatrix.keys()
        for classname, fraction in classFractionDict.iteritems():
            volflows = fraction * trafficMatrix[ie]
            if classBytesDict is not None:
                volbytes = volflows * classBytesDict[classname]
	    print 'network id: {}, i, {}, e, {}'.format(network_id, i, e)
            tc = TrafficClass(network_id, index, classname, i, e, volflows, volbytes, demand=volflows)
            if asdict:
                trafficClasses[classname].append(tc)
            else:
                trafficClasses.append(tc)
            index += 1
    return trafficClasses


def computeBackgroundLoad(topology, trafficClasses):
        ind = 0
        paths = {}
        allsp = networkx.all_pairs_shortest_path(topology.getGraph())
        for tc in trafficClasses:
            i, e = tc.getIEPair()
            paths[(i, e)] = Path(allsp[i][e], ind)
            ind += 1
        loads = {}
        for u, v in topology.links():
            link = (u, v)
            loads[link] = 0
        for tc in trafficClasses:
            path = paths[tc.getIEPair()]
            for link in path.getLinks():
                l = tc.volBytes
                loads[link] += l
        return loads


def provisionLinks(topology, trafficClasses, overprovision=2, setAttr=False):
    """ Provision the links in the topology based on the traffic classes.
    Computes shortest path routing for given traffic classes, uses the maximum
    load, scaled by *overprovision*, as the link capacity
    :param topology: topology of interest
    :param trafficClasses: list of traffic classes
    :param overprovision: the multiplier by which to overprovision the links
    :param setAttr: if True the topology graph will be modified to set
        the link *capacity* attribute for each link.
    :returns: mapping of links to their capacities
    :rtype: dict
    """

    bg = computeBackgroundLoad(topology, trafficClasses)

    maxBackground = max(bg.values())
    capacities = {}
    G = topology.getGraph()
    for u, v in G.edges_iter():
        # print u,v
        link = (u, v)
        mult = 1.0
        if 'capacitymult' in G.edge[u][v]:
            mult = G.edge[u][v]['capacitymult']
        capacities[link] = overprovision * maxBackground * mult
        if setAttr:
            G.edge[u][v]['capacity'] = capacities[link]
    return capacities

def computeMaxIngressLoad(trafficClasses, tcCost):
    """
    Compute the maximum load assuming all the processing would be done at
    ingress nodes

    :param trafficClasses: list of traffic classes
    :param tcCost: a mapping of traffic class to the processing cost (for a
        particular resource)

    :returns: max ingress load
    """

    loads = defaultdict(lambda: 0)
    for tc in trafficClasses:
        loads[tc.src] += (tc.volFlows * tcCost[tc])
    return float(max(loads.values()))
