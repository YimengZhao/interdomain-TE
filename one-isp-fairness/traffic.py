# coding=utf-8
""" Implements utility classes that have to do with traffic patterns, such as
    traffic matrix, and network traffic classes (commodities)
"""
import json
import random


class TrafficMatrix(dict):
    """
    Represents a traffic matrix, extends basic dictionary type

    """

    def permute(self, rand=None):
        """
        Permute this traffic matrix randomly

        :param rand: instance of a Python :py:mod:`random` object
        """
        v = self.values()
        random.shuffle(v, rand)
        for i, k in enumerate(self.iterkeys()):
            self[k] = v[i]


    def dump(self, fname):
        """
        Save the traffic matrix to a file
        :param fname: filename to save to
        """
        with open(fname, 'w') as f:
            json.dump({"{}->{}".format(k[0], k[1]): v for k, v in self.iteritems()}, f)

    @staticmethod
    def load(fname):
        """
        Load a traffic matrix from a file
        :param fname: filename to load from
        :return: a new TrafficMatrix
        """
        with open(fname, 'r') as f:
            return TrafficMatrix({tuple(map(int, k.split('->'))): v for k, v in json.load(f).iteritems()})


class TrafficClass(object):
    """ Represents a traffic class. All members are public
    """

    # cdef public int ID, priority
    # cdef public char* name
    # cdef public double volFlows, volBytes
    # cdef public src, dst, srcIPPrefix, dstIPPrefix, srcAppPorts, dstAppPorts

    def __init__(self, network_id, ID, name, src, dst, volFlows=0, volBytes=0, priority=1,
                 srcIPPrefix=None, dstIPPrefix=None, srcAppPorts=None,
                 dstAppPorts=None, demand=None, **kwargs):
        """ Creates a new traffic class. Any keyword arguments will be made into attributes.

        :param ID: unique traffic class identifier
        :param name: traffic class name, for human readability (e.g., 'web',
            'ssh', etc.)
        :param src: nodeID that is the ingress for this traffic class
        :param dst: nodeID that is the egress for this traffic class
        :param volFlows: number of flows for this traffic class
        :param volBytes: number of bytes for this traffic class
        :param priority: traffic class priority, as an integer (higher number means higher priority)
        :param srcIPPrefix: ingress IP prefix (CIDR notation)
        :param dstIPPrefix: egress IP prefix (CIDR notation)
        :param scrAppPorts: packet application ports (source)
        :param dstAppPorts: packet application ports (destination)
        """

	self.network_id = network_id
        self.ID = ID
        self.name = name
        self.src = src
        self.dst = dst
        self.volFlows = volFlows
        self.volBytes = volBytes
        self.priority = priority
        self.srcIPPrefix = srcIPPrefix
        self.dstIPPrefix = dstIPPrefix
        self.srcAppPorts = srcAppPorts
        self.dstAppPorts = dstAppPorts
	self.demand = demand
	self.allocate_bw = 0
	self.tentative_bw = 0
	self.calc_flag = 0

        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return "TrafficClass({})".format(
            ",".join(["{}={}".format(k, v) for k, v in self.__dict__.iteritems()]))

    def __str__(self):
        return "Traffic class {} -> {}, {}, ID={}".format(self.src, self.dst,
                                                          self.name, self.ID)

    def encode(self):
        return {'TrafficClass': True}.update(self.__dict__)

    @staticmethod
    def decode(dict):
        return TrafficClass(**dict)

    def getIEPair(self):
        """
        Return the ingress-egress pair as a tuple

        :return:  ingress-egress pair
        :rtype: tuple
        """
        return self.src, self.dst

    def __key(self):
        """ Return the "identity of this object, so to speak"""
        return self.ID,

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if not isinstance(other, TrafficClass):
            return False
        else:
            return self.ID == other.ID
