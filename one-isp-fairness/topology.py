# coding=utf-8
""" Implements the topology for SOL optimization

"""
from os.path import sep

import networkx as nx
from networkx.readwrite import graphml


class Topology(object):
    """
    Class that stores the topology graph and provides helper functions (e.g., middlebox manipulation)

    """

    def __init__(self, name, graph=None):
        """ Create a new empty topology

        :param name: The topology name
        :param graph: Either a
            #) :py:mod:`networkx` graph that represents the topology
            #) filename of a graphml file to load the graph from
            #) None, in which case an empty directed graph is created

        """
        self.name = name
        if graph is not None:
            if isinstance(graph, str):
                self.loadGraph(graph)
            else:
                self._graph = graph
        else:
            self._graph = nx.DiGraph()

    def getNumNodes(self, service=None):
        """ Returns the number of nodes in this topology

        :param service: only count nodes that provide a particular service (
            e.g., 'switch', 'ids', 'fw', etc.)
        """
        if service is None:
            return self._graph.number_of_nodes()
        else:
            return len([n for n in self._graph.nodes_iter()
                        if 'services' in self._graph.node[n] and
                        service in self._graph.node[n]['services']])

    def getGraph(self):
        """ Return the topology graph

        :return: :py:mod:`networkx` topology directed graph
        """
        return self._graph

    def setGraph(self, graph):
        """ Set the graph

        :param graph: :py:mod:`networkx` directed graph
        """
        self._graph = graph

    def writeGraph(self, dirName, fName=None):
        """
        Writes out the graph in GraphML format

        :param dirName: directory to write to
        :param fName: file name to use. If None, topology name with a
            '.graphml' suffix is used
        """
        n = self.name + '.graphml' if fName is None else fName
        graphml.write_graphml(
            self._graph, dirName + sep + n)

    def loadGraph(self, fName):
        """ Loads the topology graph from a file in GraphML format

        :param fName: the name of the file to read from
        """
        self._graph = graphml.read_graphml(fName, int).to_directed()

    # @staticmethod
    # def load(fname):
    #     G = graphml.read_graphml(fname, int)
    #     return Topology(G.graph.get('name', 'NoName'), G)

    def getServiceTypes(self, node):
        """
        Returns the list of services a particular node provides

        :param node: the node id of interest
        :return: a list of available services at this node (e.g., 'switch',
            'ids')
        """
        return self._graph.node[node]['services'].split(';')

    def setServiceTypes(self, node, serviceTypes):
        """
        Set the service types for this node

        :param node: the node id of interest
        :param serviceTypes: a list of strings denoting the services
        :type serviceTypes: list
        """
        if isinstance(serviceTypes, str):
            self._graph.node[node]['services'] = serviceTypes
        elif isinstance(serviceTypes, list):
            self._graph.node[node]['services'] = ';'.join(serviceTypes)
        else:
            raise AttributeError('Wrong type of serviceTypes, use a list')

    def addServiceType(self, node, serviceType):
        """
        Add a single service type to the given node

        :param node: the node id of interest
        :param serviceType: the service to add (e.g., 'switch', 'ids')
        :type serviceType: str
        """
        if 'services' in self._graph.node[node]:
            types = self._graph.node[node]['services'].split(';') + [
                serviceType]
        else:
            types = [serviceType]
        self._graph.node[node]['services'] = ';'.join(types)

    def nodes(self, data=False):
        """

        :return: Iterator over topology nodes as tuples of the form (nodeID, nodeData)
        """
        return self._graph.nodes_iter(data=data)

    def edges(self, data=False):
        """

        :return: Iterator over topology edge tuples (nodeID1, nodeID2, edgeData)
        """
        return self._graph.edges_iter(data=data)

    links = edges  # Method alias here

    def __repr__(self):
        return "{}(name={})".format(self.__class__, self.name)

    def hasMiddlebox(self, node):
        """
        Check if the given node has a middlebox attached to it

        :param node: node ID to check
        :return: True or False
        """
        try:
            return self._graph.node[node]['hasMbox']
        except KeyError:
            return False

    hasMbox = hasMiddlebox

    def setMiddlebox(self, node, val=True):
        """
        Indicate whether a middlebox is attached to a given node

        :param node: node ID
        :param val: True or False
        """
        self._graph.node[node]['hasMbox'] = val

    setMbox = setMiddlebox




