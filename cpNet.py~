from topology import Topology
from traffic import TrafficMatrix
from generatePath import *
from initopt import *
from predicates import nullPredicate
from provisioning import generateTrafficClasses, provisionLinks

import cplex
from cplex.exceptions import CplexError
import copy
import math
import networkx

CITY_TRAFFIC_VOLUME = 100
class CpNetwork:
    def __init__(self, topo_name, topo_file):
        self.topo = Topology(topo_name, topo_file)
     
    def egress_all_maxthrough(self, fake_node_id, dst_topo):
        result = {}
        for node in dst_topo.nodes():
            nodes_num = networkx.number_of_nodes(self.topo.getGraph())
            result[(fake_node_id, node)] = nodes_num * CITY_TRAFFIC_VOLUME
        print 'total:{}'.format(nodes_num * CITY_TRAFFIC_VOLUME)
        return result
            
    def egress_volume_shortest(self, egress_nodes, dst_topo):
        values = [0] * len(egress_nodes)
        node_num = dict(zip(egress_nodes, values))
        g = self.topo.getGraph()
        for node in g.nodes():
            egress_distance_dict = {}
            for egress in egress_nodes:
                egress_distance_dict[egress] = networkx.shortest_path(g, node, egress)
            min_val = min(egress_distance_dict.itervalues())
            closest_egress = [k for k, v in egress_distance_dict.iteritems() if v == min_val]
            node_num[closest_egress[0]] += 1

        result = {}
        for egress in node_num.keys():
            for node in dst_topo.nodes():
                result[(egress, node)] = node_num[egress] * CITY_TRAFFIC_VOLUME
        return result
