from topology import Topology
from cpNet import CpNetwork
from ispNet import IspNetwork
from optHelper import *

import copy

DEFAULT_LOG_DIR = "./log/fair_default.log"
SHORTEST_LOG_DIR = "./log/fair_shortest.log"
INDEPENDENT_LOG_DIR = "./log/fair_independent.log"
NEGO_LOG_DIR = "./log/fair_negotiate.log"

def bottleneck_exist(overlaplinks, ispNet):
    link_util_dict = ispNet.get_link_util()
    link_caps = ispNet.linkcaps
    

    has_bottleneck = False
    for link in overlaplinks:
        if link_util_dict[link] == link_caps[link]:
	    has_bottleneck = True
            break
    return has_bottleneck
        
def calc_gfi(pptc_total_dict, pptc_iso_dict, cp_num, isp_network):
    s_dict = {}
    u_dict = {}
    cp_volume_dict = {}
    tc_num_dict = {}
    for i in range(cp_num):
        s_dict[i] = 0
        u_dict[i] = 0
        trafficClasses_total = pptc_total_dict[i]
        trafficClasses_iso = pptc_iso_dict[i]
        tc_num = 0
        for tc_total in trafficClasses_total.keys():
            for tc_iso in trafficClasses_iso.keys():
                if tc_total.src == tc_iso.src and tc_total.dst == tc_iso.dst:
                    if tc_iso.allocate_bw == 0:
                        tc_iso.allocate_bw = 0.1
                    s_dict[i] += tc_total.allocate_bw / tc_iso.allocate_bw
                    u_dict[i] += tc_total.allocate_bw / tc_iso.allocate_bw
                    tc_num += 1
        s_dict[i] = s_dict[i] / tc_num
        tc_num_dict[i] = tc_num
        cp_volume_dict[i] = sum(tc.demand for tc in trafficClasses_total.keys())

 
    for i in range(cp_num):
        tc_num = tc_num_dict[i]
        for tc, paths in pptc_total_dict[i].iteritems():
            if tc.calc_flag == 1:
                continue
            for path in paths:
                if tc.calc_flag == 1:
                    break
                for j in range(cp_num):
                    if i == j:
                        continue
                    else:
                        for tc_other, paths_other in pptc_total_dict[j].iteritems():
                            if tc_other.calc_flag == 1:
                                continue
                            for path_other in paths_other:
                                if tc_other.calc_flag == 1:
                                    break
                                links = path.getLinks()
                                links_other = path_other.getLinks()
                                overlap_links = set(links).intersection(links_other)
                                if overlap_links and bottleneck_exist(overlap_links, isp_network):
                                    print 'test'
                                    for tc_iso in pptc_iso_dict[j].keys():
                                        if tc_iso.calc_flag == 1:
                                            continue
					print 'src:{} {} dst:{} {}'.format(tc_other.src, tc_iso.src, tc_other.dst, tc_iso.dst)
                                        if tc_other.src == tc_iso.src and tc_other.dst == tc_iso.dst:
                                             if tc_iso.allocate_bw == 0:
                                                 tc_iso.allocate_bw = 0.1
					     print 'u:{}'.format(tc_total.allocate_bw / tc_iso.allocate_bw)
                                             u_dict[i] += tc_total.allocate_bw / tc_iso.allocate_bw
                                             tc_num += 1
                                             tc.calc_flag = 1
                                             tc_other.calc_flag = 1
                                             tc_iso.calc_flag = 1
        u_dict[i] = u_dict[i] / tc_num
       
        
    netstat_dict = {}
    for i in range(cp_num):
        netstat_dict[i] = s_dict[i] / u_dict[i]
        print 's:{} u:{} netstat:{}'.format(s_dict[i], u_dict[i], netstat_dict[i])
    
    u = 0
    for i in range(cp_num):
        u += netstat_dict[i] * cp_volume_dict[i]
    u = u / sum(cp_volume_dict.itervalues())
    
    gfi = 0
    for i in range(cp_num):
        gfi += pow(netstat_dict[i] - u, 2) * cp_volume_dict[i]
    gfi = gfi / sum(cp_volume_dict.itervalues())
    gfi = math.sqrt(gfi)
    print 'u:{} gfi:{}'.format(u, gfi)
    return gfi
                                
                            
def default_gfi(cp_num):
    cpNetworks = []
    ispTopo = Topology('isp_network', './data/topologies/simple.graphml')
    for i in range(cp_num):
        cpNetworks.append(CpNetwork('Abilene', './data/topologies/Abilene.graphml'))

    trafficMatrix = {}
    for i in range(cp_num):
        trafficMatrix[i] = cpNetworks[i].egress_volume_shortest([0, 1], ispTopo)
        
    ispNet = IspNetwork('isp_network', './data/topologies/simple.graphml')
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
        print "test network id:{}".format(id)
        for ingress, bw in bw_dict.iteritems():
            print '{}:{}'.format(ingress, bw)

    pptc_dict = {}
    for i in range(cp_num):
        pptc_dict[i] = {}
    for tc, paths in pptc.iteritems():
        pptc_dict[tc.network_id][copy.deepcopy(tc)] = copy.deepcopy(paths)
            
    pptc_iso_dict = {}
    for i in range(cp_num):
        ispNet_local = IspNetwork('isp_network', './data/topologies/simple.graphml')
	tm = {}
        pptc_iso_dict[i] = {}
	tm.update({i: trafficMatrix[i]})
        pptc, throughput = ispNet_local.calc_path_shortest(tm)
	for tc, paths in pptc.iteritems():
            pptc_iso_dict[i][copy.deepcopy(tc)] = copy.deepcopy(paths)

    gfi = calc_gfi(pptc_dict, pptc_iso_dict, cp_num, ispNet)

    #log to file
    with open(DEFAULT_LOG_DIR, 'a') as f:
        f.write(str(gfi))
	f.write('\n')
        #f.write('default routing \n')
        '''for id, bw_dict in ingress_bw_dict.iteritems():
            f.write('cp network id:{}, throughput:{}\n'.format(id, throughput))
            for egress, bw in bw_dict.iteritems():
                f.write('egress:{} bw:{}\n'.format(egress, bw))
        '''

def shortest_gfi(cp_num):
    cpNetworks = []
    ispTopo = Topology('isp_network', './data/topologies/simple.graphml')
    for i in range(cp_num):
        cpNetworks.append(CpNetwork('Abilene', './data/topologies/Abilene.graphml'))

    trafficMatrix = {}
    for i in range(cp_num):
        trafficMatrix[i] = cpNetworks[i].egress_volume_shortest([0, 1], ispTopo)
        
    ispNet = IspNetwork('isp_network', './data/topologies/simple.graphml')
    pptc, throughput = ispNet.calc_path_maxminfair(trafficMatrix)
   
    pptc_dict = {}
    for i in range(cp_num):
        pptc_dict[i] = {}
    for tc, paths in pptc.iteritems():
        pptc_dict[tc.network_id][copy.deepcopy(tc)] = copy.deepcopy(paths)
            
    pptc_iso_dict = {}
    for i in range(cp_num):
        ispNet_local = IspNetwork('isp_network', './data/topologies/simple.graphml')
        tm = {}
        pptc_iso_dict[i] = {}
        tm.update({i: trafficMatrix[i]})
        pptc, throughput = ispNet_local.calc_path_shortest(tm)
        for tc, paths in pptc.iteritems():
            print tc
            print paths
            pptc_iso_dict[i][copy.deepcopy(tc)] = copy.deepcopy(paths)

    gfi = calc_gfi(pptc_dict, pptc_iso_dict, cp_num, ispNet)

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
        f.write(str(gfi))
	f.write('\n')
        '''f.write('default routing \n')
        for id, bw_dict in ingress_bw_dict.iteritems():
            f.write('cp network id:{}, throughput:{}\n'.format(id, throughput))
            for egress, bw in bw_dict.iteritems():
                f.write('egress:{} bw:{}\n'.format(egress, bw))
        '''


def independent_gfi(cp_num):
    cpNets = []
    ispTopo = Topology('isp_network', './data/topologies/simple.graphml')
    for i in range(cp_num):
        cpNets.append(CpNetwork('Abilene', './data/topologies/Abilene.graphml'))

    trafficMatrix = {}
    for i in range(cp_num):
        trafficMatrix[i] = cpNets[i].egress_max_throughput(10000, ispTopo)

    ispNet = IspNetwork('isp_network', './data/topologies/simple.graphml')
    pptc, throughput = ispNet.calc_path_maxminfair(trafficMatrix)

    pptc_dict = {}
    for i in range(cp_num):
        pptc_dict[i] = {}
    for tc, paths in pptc.iteritems():
        pptc_dict[tc.network_id][copy.deepcopy(tc)] = copy.deepcopy(paths)
            
    pptc_iso_dict = {}
    for i in range(cp_num):
        ispNet_local = IspNetwork('isp_network', './data/topologies/simple.graphml')
        tm = {}
        pptc_iso_dict[i] = {}
        tm.update({i: trafficMatrix[i]})
        pptc, throughput = ispNet_local.calc_path_shortest(tm)
        for tc, paths in pptc.iteritems():
            print tc
            print paths
            pptc_iso_dict[i][copy.deepcopy(tc)] = copy.deepcopy(paths)

    gfi = calc_gfi(pptc_dict, pptc_iso_dict, cp_num, ispNet)

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
	f.write(str(gfi))
	f.write('\n')
        '''f.write('independent routing\n')
        for id, bw_dict in ingress_bw_dict.iteritems():
            f.write('isp network id:{}, throughput:{}\n'.format(id, throughput))
            for ingress, bw in bw_dict.iteritems():
                f.write('egress:{} bw:{}\n'.format(ingress, bw))
'''

def negotiate_gfi(cp_num):
    cpNets = []
    ispTopo = Topology('isp_network', './data/topologies/simple.graphml')
    for i in range(cp_num):
        cpNets.append(CpNetwork('Abilene', './data/topologies/Abilene.graphml'))

    trafficMatrix = {}
    for i in range(cp_num):
        trafficMatrix[i] = cpNets[i].egress_all(10000, ispTopo)
    
    ispNet = IspNetwork('isp_network', './data/topologies/simple.graphml')
    egress_bw_dict, throughput = ispNet.calc_path_singleinput(10000, trafficMatrix, cp_num)

    '''with open(NEGO_LOG_DIR, 'a') as f:
        f.write('first isp throughput:{}\n'.format(throughput))
        for id, bw_dict in egress_bw_dict.iteritems():
            f.write('cp network:{}\n'.format(id))
            for egress, bw in bw_dict.iteritems():
                f.write('egress:{} bw:{}\n'.format(egress, bw))
'''

    trafficMatrix = {}
    for id, bw_dict in egress_bw_dict.iteritems():
        trafficMatrix[id] = cpNets[id].egress_ratio(10000, ispTopo, bw_dict)

    pptc, throughput = ispNet.calc_path_maxminfair(trafficMatrix)
    
    pptc_dict = {}
    for i in range(cp_num):
        pptc_dict[i] = {}
    for tc, paths in pptc.iteritems():
        pptc_dict[tc.network_id][copy.deepcopy(tc)] = copy.deepcopy(paths)
            
    pptc_iso_dict = {}
    for i in range(cp_num):
        ispNet_local = IspNetwork('isp_network', './data/topologies/simple.graphml')
        tm = {}
        pptc_iso_dict[i] = {}
        tm.update({i: trafficMatrix[i]})
        pptc, throughput = ispNet_local.calc_path_shortest(tm)
        for tc, paths in pptc.iteritems():
            pptc_iso_dict[i][copy.deepcopy(tc)] = copy.deepcopy(paths)

    gfi = calc_gfi(pptc_dict, pptc_iso_dict, cp_num, ispNet)

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
	f.write(str(gfi))
	f.write('\n')
        '''for id, bw_dict in ingress_bw_dict.iteritems():
            f.write('isp network id:{}, throughput:{}\n'.format(id, throughput))
            for ingress, bw in bw_dict.iteritems():
                f.write('egress:{} bw:{}\n'.format(ingress, bw))
'''
