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

CITY_TRAFFIC_VOLUME = 10

class IspNetwork:
    def __init__(self, topo_name, topo_file, traffic_file=None):
        self.topo = Topology(topo_name, topo_file)
        if traffic_file:
            self.trafficMatrix = TrafficMatrix.load(traffic_file)


    def set_traffic(self, trafficMatrix, topo, path_num=3):
        self.trafficMatrix = trafficMatrix
        self.trafficClasses = []
        self.ie_path_map = {}
        base_index = 0
        for key in trafficMatrix.keys():
            self.ie_path_map[key] = generatePath(self.trafficMatrix[key].keys(), topo, nullPredicate, "shortest", maxPaths=path_num)
            tcs = generateTrafficClasses(key, self.trafficMatrix[key].keys(), self.trafficMatrix[key], {'a':1}, {'a':100}, index_base = base_index)
            base_index += len(tcs)
            self.trafficClasses.extend(tcs)
        #for tc in self.trafficClasses:
            #print tc
        #self.linkcaps = provisionLinks(self.topo, self.trafficClasses, 1)
        self.linkcaps = set_link_caps(self.topo)
        self.norm_list = get_norm_weight(self.trafficClasses)
        print 'normal_list:'
        print self.norm_list.values()

    def calc_path_singleinput(self, fake_node, trafficMatrix, cp_num):
        #add fake node
        self.fake_topo = copy.deepcopy(self.topo)
        self.fake_topo._graph.add_node(fake_node)
        #self.topo._graph.add_edge(0, fake_node)
        self.fake_topo._graph.add_edge(fake_node, 0)
        #self.topo._graph.add_edge(1, fake_node)
        self.fake_topo._graph.add_edge(fake_node, 1)
        
        (pptc, throughput) = self.calc_path_maxminfair(trafficMatrix, self.fake_topo)
        ingress_bw_dict = {}
        for i in range(cp_num):
            ingress_bw_dict[i] = {}
        print 'single input'
        for tc, paths in pptc.iteritems():
            for path in paths:
                nodes = path.getNodes()
                print 'nodes:{}'.format(nodes)
                print 'bw:{}'.format(path.bw)
                ingress = nodes[1]
                if ingress in ingress_bw_dict[tc.network_id]:
                    ingress_bw_dict[tc.network_id][ingress] += path.bw
                else:
                    ingress_bw_dict[tc.network_id][ingress] = path.bw
        return (ingress_bw_dict, throughput)


    def calc_path_maxminfair(self, trafficMatrix, topo = None):
        if topo == None:
            topo = self.topo
        self.set_traffic(trafficMatrix, topo, path_num = 3)
        ie_path_map = {}
        for path_map in self.ie_path_map.itervalues():
            ie_path_map.update(path_map)
        '''print 'testing'
        for ie, paths in ie_path_map.iteritems():
            print ie
            for path in paths:
                print path.getNodes()'''
        pptc = initOptimization(ie_path_map, topo, self.trafficClasses)
	self.linkcaps[(0,2)] = 10
	self.linkcaps[(2,0)] = 10
	self.linkcaps[(0,1)] = 10
	self.linkcaps[(1,0)] = 10
        throughput = maxmin_fair_allocate(self.trafficClasses, self.linkcaps, pptc, self.norm_list, False)
        return (pptc, throughput)


    def calc_path_shortest(self, trafficMatrix):
        self.set_traffic(trafficMatrix, self.topo, path_num = 1)
        ie_path_map = {}
        for path_map in self.ie_path_map.itervalues():
            ie_path_map.update(path_map)
        pptc = initOptimization(ie_path_map, self.topo, self.trafficClasses)
	self.linkcaps[(0,2)] = 10
	self.linkcaps[(2,0)] = 10
	self.linkcaps[(0,1)] = 10
	self.linkcaps[(1,0)] = 10
        throughput = maxmin_fair_allocate(self.trafficClasses, self.linkcaps, pptc, self.norm_list, False)
        return (pptc, throughput)

		
	    






