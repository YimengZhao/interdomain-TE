from topology import Topology
from cpNet import CpNetwork
from ispNet import IspNetwork
from optHelper import *
import networkx

DEFAULT_LOG_DIR = './log/default.log'


CP_TOPO_DIR = './data/topologies/Abilene.graphml'
ISP_TOPO_DIR = './data/topologies/simple.graphml'

def default_test(cp_num, isp_num):
    cpNetworks = []
    for i in range(cp_num):
        cpNetworks.append(CpNetwork('Abilene', CP_TOPO_DIR))

    trafficMatrix = {}
    ispNetworks = []
    union_ISP = networkx.DiGraph()
    dst_topos = []
    for i in range(isp_num):
        net = IspNetwork('isp_network', ISP_TOPO_DIR)
        mapping = dict(zip(net.topo._graph.nodes(), [x + i * 11 for x in networkx.nodes_iter(net.topo._graph)]))
        net.topo._graph = networkx.relabel_nodes(net.topo._graph, mapping)
        ispNetworks.append(net)
        dst_topos.append(net.topo._graph)
        #union_ISP = networkx.union(union_ISP, net.topo._graph)

    for i in range(cp_num):
        trafficMatrix[i] = cpNetworks[i].egress_volume_shortest([0, 1, 2], dst_topos)
        
            
    with open(DEFAULT_LOG_DIR, 'a') as f:
        for i in range(isp_num):
            ispNetworks[i].linkcaps = set_link_caps(ispNetworks[i].topo)
            pptc, throughput = ispNetworks[i].calc_path_shortest(trafficMatrix, i)
            #isp_pptc.append(pptc)

            cp_bw_total = {}
            for tc, paths in pptc.iteritems():
                cp_id = tc.network_id
                for path in paths:
                    if cp_id in cp_bw_total:
                        cp_bw_total[cp_id] += path.bw
                    else:
                        cp_bw_total[cp_id] = path.bw
                        
            for cp_id in cp_bw_total.keys():
                f.write('cp {} isp {} get bw {}'.format(cp_id, i, cp_bw_total[cp_id]))
                f.write('\n')

                
            
        
