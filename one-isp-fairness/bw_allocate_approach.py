from topology import Topology
from cpNet import CpNetwork
from ispNet import IspNetwork
from optHelper import *
import networkx

DEFAULT_LOG_DIR = "./log/default.log"
SHORTEST_LOG_DIR = "./log/shortest.log"
INDEPENDENT_LOG_DIR = "./log/independent.log"
NEGO_LOG_DIR = "./log/negotiate.log"
OPTIMAL_LOG_DIR = "./log/optimal.log"

CP_TOPO_DIR = './data/topologies/Abilene.graphml'
ISP_TOPO_DIR = './data/topologies/Abilene.graphml'

def default_routing(cp_num):
    cpNetworks = []
    ispTopo = Topology('isp_network', ISP_TOPO_DIR)
    for i in range(cp_num):
        cpNetworks.append(CpNetwork('Abilene', CP_TOPO_DIR))

    trafficMatrix = {}
    for i in range(cp_num):
        trafficMatrix[i] = cpNetworks[i].egress_volume_shortest([0, 1], ispTopo)
        
    ispNet = IspNetwork('isp_network', ISP_TOPO_DIR)
    ispNet.linkcaps = set_link_caps(ispNet.topo)
    pptc, throughput = ispNet.calc_path_shortest(trafficMatrix)
   
    ingress_bw_dict = {}
    for i in range(cp_num):
        ingress_bw_dict[i] = {}
    for tc, paths in pptc.iteritems():
        for path in paths:
            nodes = path.getNodes()
            ingress = nodes[0]
            if ingress in ingress_bw_dict[tc.network_id]:
                ingress_bw_dict[tc.network_id][ingress] += path.bw
            else:
                ingress_bw_dict[tc.network_id][ingress] = path.bw
 
    for id, bw_dict in ingress_bw_dict.iteritems():
        print "network id:{}".format(id)
        for ingress, bw in bw_dict.iteritems():
            print '{}:{}'.format(ingress, bw)

    #log to file
    with open(DEFAULT_LOG_DIR, 'a') as f:
        f.write(str(throughput))
	f.write('\n')
        '''f.write('default routing \n')
        for id, bw_dict in ingress_bw_dict.iteritems():
            f.write('cp network id:{}, throughput:{}\n'.format(id, throughput))
            for egress, bw in bw_dict.iteritems():
                f.write('egress:{} bw:{}\n'.format(egress, bw))
        '''

def shortest_routing(cp_num):
    cpNetworks = []
    ispTopo = Topology('isp_network', ISP_TOPO_DIR)
    for i in range(cp_num):
        cpNetworks.append(CpNetwork('Abilene', CP_TOPO_DIR))

    trafficMatrix = {}
    for i in range(cp_num):
        trafficMatrix[i] = cpNetworks[i].egress_volume_shortest([0, 1], ispTopo)
        
    ispNet = IspNetwork('isp_network', ISP_TOPO_DIR)
    ispNet.linkcaps = set_link_caps(ispNet.topo)
    pptc, throughput = ispNet.calc_path_maxminfair(trafficMatrix)
   
    ingress_bw_dict = {}
    for i in range(cp_num):
        ingress_bw_dict[i] = {}
    for tc, paths in pptc.iteritems():
        for path in paths:
            nodes = path.getNodes()
            ingress = nodes[0]
            if ingress in ingress_bw_dict[tc.network_id]:
                ingress_bw_dict[tc.network_id][ingress] += path.bw
            else:
                ingress_bw_dict[tc.network_id][ingress] = path.bw
 
    for id, bw_dict in ingress_bw_dict.iteritems():
        print "network id:{}".format(id)
        for ingress, bw in bw_dict.iteritems():
            print '{}:{}'.format(ingress, bw)

    #log to file
    with open(SHORTEST_LOG_DIR, 'a') as f:
        f.write(str(throughput))
	f.write('\n')
        '''f.write('default routing \n')
        for id, bw_dict in ingress_bw_dict.iteritems():
            f.write('cp network id:{}, throughput:{}\n'.format(id, throughput))
            for egress, bw in bw_dict.iteritems():
                f.write('egress:{} bw:{}\n'.format(egress, bw))
        '''


def independent_routing(cp_num):
    cpNets = []
    ispTopo = Topology('isp_network', ISP_TOPO_DIR)
    for i in range(cp_num):
        cpNets.append(CpNetwork('Abilene', CP_TOPO_DIR))

    trafficMatrix = {}
    for i in range(cp_num):
        trafficMatrix[i] = cpNets[i].egress_max_throughput(10000, ispTopo)

    ispNet = IspNetwork('isp_network', ISP_TOPO_DIR)
    ispNet.linkcaps = set_link_caps(ispNet.topo)
    pptc, throughput = ispNet.calc_path_maxminfair(trafficMatrix)

    ingress_bw_dict = {}
    for i in range(cp_num):
        ingress_bw_dict[i] = {}
    for tc, paths in pptc.iteritems():
        for path in paths:
            nodes = path.getNodes()
            ingress = nodes[0]
            if ingress in ingress_bw_dict[tc.network_id]:
                ingress_bw_dict[tc.network_id][ingress] += path.bw
            else:
                ingress_bw_dict[tc.network_id][ingress] = path.bw
 
    for id, bw_dict in ingress_bw_dict.iteritems():
        print 'network id:{}'.format(id)
        for ingress, bw in bw_dict.iteritems():
            print '{}:{}'.format(ingress, bw)

    with open(INDEPENDENT_LOG_DIR, 'a' ) as f:
	f.write(str(throughput))
	f.write('\n')
        '''f.write('independent routing\n')
        for id, bw_dict in ingress_bw_dict.iteritems():
            f.write('isp network id:{}, throughput:{}\n'.format(id, throughput))
            for ingress, bw in bw_dict.iteritems():
                f.write('egress:{} bw:{}\n'.format(ingress, bw))
'''

def negotiate_routing(cp_num):
    cpNets = []
    ispTopo = Topology('isp_network', ISP_TOPO_DIR)
    for i in range(cp_num):
        cpNets.append(CpNetwork('Abilene', CP_TOPO_DIR))

    trafficMatrix = {}
    for i in range(cp_num):
        trafficMatrix[i] = cpNets[i].egress_all(10000, ispTopo)

    ispNet = IspNetwork('isp_network', ISP_TOPO_DIR)
    ispNet.linkcaps = set_link_caps(ispNet.topo)
    egress_bw_dict, throughput = ispNet.calc_path_singleinput(10000, trafficMatrix, cp_num)
    link_utils = ispNet.get_link_util()
    for link, util in link_utils.iteritems():
	print 'link {} util {}'.format(link, util)

    '''with open(NEGO_LOG_DIR, 'a') as f:
        f.write('first isp throughput:{}\n'.format(throughput))
        for id, bw_dict in egress_bw_dict.iteritems():
            f.write('cp network:{}\n'.format(id))
            for egress, bw in bw_dict.iteritems():
                f.write('egress:{} bw:{}\n'.format(egress, bw))'''


    trafficMatrix = {}
    for id, bw_dict in egress_bw_dict.iteritems():
        trafficMatrix[id] = cpNets[id].egress_ratio(10000, ispTopo, bw_dict)

    pptc, throughput = ispNet.calc_path_maxminfair(trafficMatrix)
    
    ingress_bw_dict = {}
    for i in range(cp_num):
        ingress_bw_dict[i] = {}
    for tc, paths in pptc.iteritems():
        for path in paths:
            nodes = path.getNodes()
            ingress = nodes[0]
            if ingress in ingress_bw_dict[tc.network_id]:
                ingress_bw_dict[tc.network_id][ingress] += path.bw
            else:
                ingress_bw_dict[tc.network_id][ingress] = path.bw

    for id, bw_dict in ingress_bw_dict.iteritems():
        print 'network id:{}'.format(id)
        for ingress, bw in bw_dict.iteritems():
            print '{}:{}'.format(ingress, bw)

    with open(NEGO_LOG_DIR, 'a' ) as f:
	f.write(str(throughput))
	f.write('\n')
        '''for id, bw_dict in ingress_bw_dict.iteritems():
            f.write('isp network id:{}, throughput:{}\n'.format(id, throughput))
            for ingress, bw in bw_dict.iteritems():
                f.write('egress:{} bw:{}\n'.format(ingress, bw))
'''

def optimal_routing(cp_num):
    cpNets = []
    node_num = 0
    union_graph = networkx.DiGraph()
    for i in range(cp_num):
	net = CpNetwork('Abilene', CP_TOPO_DIR)
	mapping = dict(zip(net.topo._graph.nodes(), [x + i * 11 for x in networkx.nodes_iter(net.topo._graph)]))
	net.topo._graph = networkx.relabel_nodes(net.topo._graph, mapping)
	node_num += networkx.number_of_nodes(net.topo._graph)
	cpNets.append(net)
        union_graph = networkx.union(union_graph, net.topo._graph)

    ispNet = IspNetwork('isp_network', ISP_TOPO_DIR)
    mapping = dict(zip(ispNet.topo._graph.nodes(), [x + node_num for x in networkx.nodes_iter(ispNet.topo._graph)]))
    ispNet.topo._graph = networkx.relabel_nodes(ispNet.topo._graph, mapping)
   	
    trafficMatrix = {}
    for i in range(cp_num):
        trafficMatrix[i] = cpNets[i].egress_default(networkx.nodes_iter(cpNets[i].topo._graph), ispNet.topo)
	
    ispNet.topo._graph = networkx.union(ispNet.topo._graph, union_graph)
    ispNet.linkcaps = set_link_caps(ispNet.topo) 
    for i in range(cp_num):
	node_1 = i * 11
	node_2 = i * 11 + 1
	node_3 = cp_num * 11
	node_4 = cp_num * 11 + 1
	ispNet.topo._graph.add_edge(node_1, node_3)
	ispNet.topo._graph.add_edge(node_2, node_4)
	ispNet.linkcaps[(node_1, node_3)] = 10000000
	ispNet.linkcaps[(node_2, node_4)] = 10000000

    node = cp_num * 11
    ispNet.linkcaps[(node, node+1)] = 10
    ispNet.linkcaps[(node+1, node)] = 10
    ispNet.linkcaps[(node, node+2)] = 10
    ispNet.linkcaps[(node+2, node)] = 10

    print ispNet.topo._graph.edges()
    pptc, throughput = ispNet.calc_path_maxminfair(trafficMatrix)

    ingress_bw_dict = {}
    for i in range(cp_num):
        ingress_bw_dict[i] = {}
    for tc, paths in pptc.iteritems():
        for path in paths:
            nodes = path.getNodes()
            ingress = nodes[0]
            if ingress in ingress_bw_dict[tc.network_id]:
                ingress_bw_dict[tc.network_id][ingress] += path.bw
            else:
                ingress_bw_dict[tc.network_id][ingress] = path.bw
 
    for id, bw_dict in ingress_bw_dict.iteritems():
        print 'network id:{}'.format(id)
        for ingress, bw in bw_dict.iteritems():
            print '{}:{}'.format(ingress, bw)

    with open(OPTIMAL_LOG_DIR, 'a' ) as f:
	f.write(str(throughput))
	f.write('\n')
        '''f.write('independent routing\n')
        for id, bw_dict in ingress_bw_dict.iteritems():
            f.write('isp network id:{}, throughput:{}\n'.format(id, throughput))
            for ingress, bw in bw_dict.iteritems():
                f.write('egress:{} bw:{}\n'.format(ingress, bw))
'''
