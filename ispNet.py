from topology import Topology
from traffic import TrafficMatrix
from generatePath import *
from initopt import *
from predicates import nullPredicate
from provisioning import generateTrafficClasses, provisionLinks

from optHelper import *

import copy
import math
import networkx

CITY_TRAFFIC_VOLUME = 100

class IspNetwork:
    def __init__(self, topo_name, topo_file, traffic_file=None):
        self.topo = Topology(topo_name, topo_file)
        if traffic_file:
            self.trafficMatrix = TrafficMatrix.load(traffic_file)


    def set_traffic(self, trafficMatrix):
        self.trafficMatrix = trafficMatrix
        self.trafficClasses = []
        self.ie_path_map = {}
        base_index = 0
        print self.topo._graph.edges()
        for key in trafficMatrix.keys():
            self.ie_path_map[key] = generatePath(self.trafficMatrix[key].keys(), self.topo, nullPredicate, "shortest", 5)
            tcs = generateTrafficClasses(key, self.trafficMatrix[key].keys(), self.trafficMatrix[key], {'a':1}, {'a':100}, index_base = base_index)
            base_index += len(tcs)
            self.trafficClasses.extend(tcs)
        #for tc in self.trafficClasses:
            #print tc
        #self.linkcaps = provisionLinks(self.topo, self.trafficClasses, 1)
        self.linkcaps = set_link_caps(self.topo)
        self.norm_list = get_norm_weight(self.trafficClasses)

    def calc_path_singleinput(self, fake_node, trafficMatrix, isp_num):
        #add fake node
        self.topo._graph.add_node(fake_node)
        self.topo._graph.add_edge(0, fake_node)
        self.topo._graph.add_edge(fake_node, 0)
        self.topo._graph.add_edge(1, fake_node)
        self.topo._graph.add_edge(fake_node, 1)
        (pptc, throughput) = self.calc_path_maxminfair(trafficMatrix)
        ingress_bw_dict = {}
        for i in range(isp_num):
            ingress_bw_dict[i] = {}
        for tc, paths in pptc.iteritems():
            for path in paths:
                nodes = path.getNodes()
                ingress = nodes[1]
                if ingress in ingress_bw_dict[tc.network_id]:
                    ingress_bw_dict[tc.network_id][ingress] += path.bw
                else:
                    ingress_bw_dict[tc.network_id][ingress] = path.bw
        return (ingress_bw_dict, throughput)

    def calc_path_maxminfair(self, trafficMatrix):
        self.set_traffic(trafficMatrix)
        ie_path_map = {}
        for pair in self.ie_path_map.itervalues():
            ie_path_map.update(pair)
        pptc = initOptimization(ie_path_map, self.topo, self.trafficClasses)
        throughput = maxmin_fair_allocate(self.trafficClasses, self.linkcaps, pptc, self.norm_list, False)
        return (pptc, throughput)

    def egress_sum_backup(self):
        pptc = initOptimization(ie_path_map, self.topo, self.trafficClasses)
        maxmin_fair_allocate(self.trafficClasses, self.linkcaps, pptc, self.norm_list, False)
        egress_dict = {}
        for tc, paths in pptc.iteritems():
            for path in paths:
                nodes = path.getNodes()
                print nodes
                
            






