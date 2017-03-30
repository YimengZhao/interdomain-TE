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

CITY_TRAFFIC_VOLUME = 14000
class CpNetwork:
    def __init__(self, topo_name, topo_file):
        self.topo = Topology(topo_name, topo_file)
	self.linkcaps = set_link_caps(self.topo)

    def egress_max_throughput(self, fake_node_id, dst_topo):
        #generate traffic matrix
        trafficMatrix = {}
        dst_topo_node_num = networkx.number_of_nodes(dst_topo._graph)
        for node in self.topo._graph.nodes():
            trafficMatrix[(node, fake_node_id)] = CITY_TRAFFIC_VOLUME * (dst_topo_node_num - 2)
            
        #generate fake topology
        self.fake_topo = copy.deepcopy(self.topo)
        self.fake_topo._graph.add_node(fake_node_id)
        #self.fake_topo._graph.add_edge(fake_node_id, 0)
        self.fake_topo._graph.add_edge(0, fake_node_id)
        #self.fake_topo._graph.add_edge(fake_node_id, 1)
        self.fake_topo._graph.add_edge(1, fake_node_id)
        
        #generate traffic classes
        ie_path_map = generatePath(trafficMatrix.keys(), self.fake_topo, nullPredicate, 'shortest', maxPaths=3)
        trafficClasses = generateTrafficClasses(0, trafficMatrix.keys(), trafficMatrix, {'a':1}, {'a':100})
        norm_list = get_norm_weight(trafficClasses)

        #optimization
        pptc = initOptimization(ie_path_map, self.fake_topo, trafficClasses)
        throughput = maxmin_fair_allocate(trafficClasses, self.linkcaps, pptc, norm_list, False)

        print 'cp net max throughput:{}'.format(throughput)
        egress_bw_dict = {}
        for tc, paths in pptc.iteritems():
            for path in paths:
                nodes = path.getNodes()
                real_egress = nodes[-2]
                if real_egress in egress_bw_dict:
                    egress_bw_dict[real_egress] += path.bw
                else:
                    egress_bw_dict[real_egress] = path.bw

        for egress, bw in egress_bw_dict.iteritems():
            print 'egress:{} bw:{}'.format(egress, bw)

        result = {}
        dst_topo_node_num = networkx.number_of_nodes(dst_topo._graph)
        for node in dst_topo.nodes():
	    if node == 0 or node == 1:
		continue
            for egress, bw in egress_bw_dict.iteritems():
                result[(egress, node)] = bw / (dst_topo_node_num - 2)

        return result

    def egress_all(self, fake_node_id, dst_topo):
        result = {}
        for node in dst_topo._graph.nodes():
	    if node == 0 or node == 1:
		continue
            nodes_num = networkx.number_of_nodes(self.topo.getGraph())
            result[(fake_node_id, node)] = nodes_num  * CITY_TRAFFIC_VOLUME
            print 'egress all src:{} dst:{} bw:{}'.format(fake_node_id, node, nodes_num * CITY_TRAFFIC_VOLUME)
        return result

    def egress_default(self, src_nodes, dst_topo):
        result = {}
	dst_nodes = dst_topo._graph.nodes()
	dst_nodes.sort()
	for src_node in src_nodes:
            for dst_node in dst_topo._graph.nodes():
	        if dst_node == dst_nodes[0] or dst_node == dst_nodes[1]:
		    continue
                result[(src_node, dst_node)] = CITY_TRAFFIC_VOLUME
                print 'egress all src:{} dst:{} bw:{}'.format(src_node, dst_node, CITY_TRAFFIC_VOLUME)
        return result

    def egress_volume_shortest(self, egress_nodes, dst_topos):
        g = self.topo.getGraph()
        egress_nodes_num = len(egress_nodes)

        node_path_dict = {}
        for node in g.nodes():
            for egress in egress_nodes:
                node_path_dict[(node, egress)] = networkx.shortest_path(g, node, egress)
                
        dst_node_num = 11
        trafficMatrix = {}
        for k in node_path_dict.keys():
            trafficMatrix[k] = CITY_TRAFFIC_VOLUME * 10
            print 'k {} value {}'.format(k, trafficMatrix[k])
        
        trafficClasses = generateTrafficClasses(0, node_path_dict.keys(), trafficMatrix, {'a':1}, {'a':100})
        pptc = {}
        for tc in trafficClasses:
            pptc[copy.deepcopy(tc)] = [Path(node_path_dict[tc.src, tc.dst])]
        norm_list = get_norm_weight(trafficClasses)
        throughput = maxmin_fair_allocate(trafficClasses, self.linkcaps, pptc, norm_list, False)

        print 'cp net shortest throughput:{}'.format(throughput)
        egress_bw_dict = {}
        for tc, paths in pptc.iteritems():
            for path in paths:
                nodes = path.getNodes()
                egress = nodes[-1]
                if egress in egress_bw_dict:
                    egress_bw_dict[egress] += path.bw
                else:
                    egress_bw_dict[egress] = path.bw

        for egress, bw in egress_bw_dict.iteritems():
            print 'egress:{} bw:{}'.format(egress, bw)

        dst_topo_node_num = networkx.number_of_nodes(dst_topos[0])
        result = {}
        for egress, dst_topo in zip(egress_bw_dict.keys(), dst_topos):
            for node in dst_topo:
                if node == 0 or node == 11 or node == 22:
                    continue
                bw = egress_bw_dict[egress]
                result[(egress, node)] = bw / 10
        
        return result

    
    def egress_ratio(self, fake_node_id, dst_topo, egress_bw_dict):
        trafficMatrix = {}
        dst_topo_node_num = networkx.number_of_nodes(dst_topo._graph)
        for node in self.topo._graph.nodes():
            trafficMatrix[(node, fake_node_id)] = CITY_TRAFFIC_VOLUME * (dst_topo_node_num - 2)

        self.fake_topo = copy.deepcopy(self.topo)
        self.fake_topo._graph.add_node(fake_node_id)
        #self.fake_topo._graph.add_edge(fake_node_id, 0)
        self.fake_topo._graph.add_edge(0, fake_node_id)
        #self.fake_topo._graph.add_edge(fake_node_id, 1)
        self.fake_topo._graph.add_edge(1, fake_node_id)

        ie_path_map = generatePath(trafficMatrix.keys(), self.fake_topo, nullPredicate, 'shortest', maxPaths=3)
        trafficClasses = generateTrafficClasses(0, trafficMatrix.keys(), trafficMatrix, {'a':1}, {'a':100})
        norm_list = get_norm_weight(trafficClasses)

        #optimization
        pptc = initOptimization(ie_path_map, self.fake_topo, trafficClasses)
        throughput = maxmin_fair_ratio_allocate(trafficClasses, self.linkcaps, pptc, norm_list, egress_bw_dict)
	print 'egress_ratio throughput:{}'.format(throughput)

        egress_bw_dict = {}
        for tc, paths in pptc.iteritems():
            for path in paths:
                nodes = path.getNodes()
                real_egress = nodes[-2]
                if real_egress in egress_bw_dict:
                    egress_bw_dict[real_egress] += path.bw
                else:
                    egress_bw_dict[real_egress] = path.bw

        for egress, bw in egress_bw_dict.iteritems():
            print 'egress:{} bw:{}'.format(egress, bw)

        result = {}
        dst_topo_node_num = networkx.number_of_nodes(dst_topo._graph)
        for node in dst_topo.nodes():
	    if node == 0 or node == 1:
		continue
            for egress, bw in egress_bw_dict.iteritems():
                result[(egress, node)] = bw / (dst_topo_node_num - 2)
        
        return result
