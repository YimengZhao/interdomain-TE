from topology import Topology
from cpNet import CpNetwork
from ispNet import IspNetwork
from optHelper import *

import copy

T_THROUGHPUT_LOG_DIR = "./log/tunnel_throughput.log"
TGFI_TUNNEL_LOG_DIR = "./log/tgfi_tunnel.log"
NGFI_TUNNEL_LOG_DIR = "./log/ngfi_tunnel.log"
MM_THROUGHPUT_LOG_DIR = "./log/maxmin_throughput.log"
TGFI_MM_LOG_DIR = "./log/tgfi_maxmin.log"
NGFI_MM_LOG_DIR = "./log/ngfi_maxmin.log"
MAX_THROUGHPUT_LOG_DIR = "./log/max_throughput.log"
TGFI_MAX_LOG_DIR = "./log/tgfi_max.log"
NGFI_MAX_LOG_DIR = "./log/ngfi_max.log"

#ISP_TOPO_DIR = "./data/topologies/Abilene.graphml"
ISP_TOPO_DIR = "./50.graphml"


CITY_TRAFFIC_VOLUME = 100
def bottleneck_exist(overlaplinks, ispNet):
    link_util_dict = ispNet.get_link_util()
    link_caps = ispNet.linkcaps
    

    has_bottleneck = False
    for link in overlaplinks:
        if link_util_dict[link] == link_caps[link]:
	    has_bottleneck = True
            break
    return has_bottleneck
        
def calc_network_gfi(pptc_total_dict, pptc_iso_dict, cp_num, isp_network):
    s_dict = {}
    u_dict = {}
    total_dict = {}
    iso_dict = {}
    cp_volume_dict = {}
    for i in range(cp_num):
        s_dict[i] = 0
        u_dict[i] = 0
        trafficClasses_total = pptc_total_dict[i]
        trafficClasses_iso = pptc_iso_dict[i]
        s_total = 0
        g_total = 0
        for tc_total in trafficClasses_total.keys():
            for tc_iso in trafficClasses_iso.keys():
                if tc_total.src == tc_iso.src and tc_total.dst == tc_iso.dst:
                    s_total += tc_total.allocate_bw
                    g_total += tc_iso.allocate_bw

        s_dict[i] = 1.0 * s_total / g_total
        total_dict[i] = s_total
        iso_dict[i] = g_total
	#total_dict[i] = 0
	#iso_dict[i] = 0
        cp_volume_dict[i] = sum(tc.demand for tc in trafficClasses_total.keys())

 
    for i in range(cp_num):
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
                                    for tc_iso in pptc_iso_dict[j].keys():
                                        if tc_iso.calc_flag == 1:
					    #print 'src:{} {} dst:{} {}'.format(tc_other.src, tc_iso.src, tc_other.dst, tc_iso.dst) 
                                            continue
					#print 'src:{} {} dst:{} {}'.format(tc_other.src, tc_iso.src, tc_other.dst, tc_iso.dst)
                                        if tc_other.src == tc_iso.src and tc_other.dst == tc_iso.dst:
                                            #print 'iso:{}'.format(tc_iso.allocate_bw)
                                            total_dict[i] += tc_other.allocate_bw
                                            iso_dict[i] += tc_iso.allocate_bw
                                            tc.calc_flag = 1
                                            tc_other.calc_flag = 1
                                            tc_iso.calc_flag = 1
	
	for pptc in pptc_total_dict.values():
	    for tc in pptc.keys():
	        tc.calc_flag = 0
	for pptc in pptc_iso_dict.values():
	    for tc in pptc.keys():
	        tc.calc_flag = 0
        #print 'total:{} {} {}'.format(i, total_dict[i], iso_dict[i])
	if iso_dict[i] == 0 or total_dict[i] == 0:
	    u_dict[i] = 1
	else:
            u_dict[i] = 1.0 * total_dict[i] / iso_dict[i]
        
    netstat_dict = {}
    for i in range(cp_num):
        netstat_dict[i] = s_dict[i] / u_dict[i]
        #print 'n s:{} u:{} netstat:{}'.format(s_dict[i], u_dict[i], netstat_dict[i])
    
    u = 0
    max_volume = max(cp_volume_dict.itervalues())
    cp_weight_dict = {}
    for i in range(cp_num):
        cp_weight_dict[i] = 1.0 * cp_volume_dict[i] / sum(cp_volume_dict.itervalues())

    for i in range(cp_num):
        u += netstat_dict[i] * cp_weight_dict[i]
    u = u / sum(cp_weight_dict.itervalues())

    gfi = 0
    for i in range(cp_num):
        gfi += pow(netstat_dict[i] - u, 2) * cp_weight_dict[i]
    V1 = sum(cp_weight_dict.itervalues())
    V2 = sum(pow(w, 2) for w in cp_weight_dict.itervalues())
    print cp_weight_dict.itervalues()
    print V1
    print V2
    coef = V1 / (pow(V1, 2) - V2)
    gfi = coef * gfi
    gfi = math.sqrt(gfi)
    #print 'n u:{} gfi:{}'.format(u, gfi)
    return gfi
     

def calc_tunnel_gfi(pptc_total_dict, pptc_iso_dict, cp_num, isp_network):
    s_dict = {}
    u_dict = {}
    fn_dict = {}
    total_dict = {}
    iso_dict = {}
    cp_volume_dict = {}

    for i in range(cp_num):
        s_dict[i] = 0
        u_dict[i] = 0
        flow_num = 0
        trafficClasses_total = pptc_total_dict[i]
        trafficClasses_iso = pptc_iso_dict[i]
        s_total = 0
        for tc_total in trafficClasses_total.keys():
            for tc_iso in trafficClasses_iso.keys():
                if tc_total.src == tc_iso.src and tc_total.dst == tc_iso.dst:
		    print 's src:{} {} dst:{} {}'.format(tc_total.src, tc_total.allocate_bw, tc_iso.dst, tc_iso.allocate_bw)
                    s_total += tc_total.allocate_bw / tc_iso.allocate_bw
		    flow_num += 1

        s_dict[i] = 1.0 * s_total / flow_num
	print 's_dict {} f num {}'.format(s_dict[i], flow_num)
        total_dict[i] = s_total
        fn_dict[i] = flow_num
        #iso_dict[i] = g_total
	#total_dict[i] = 0
        cp_volume_dict[i] = sum(tc.demand for tc in trafficClasses_total.keys())

 
    for i in range(cp_num):
        flow_num = fn_dict[i]
	print 'start'
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
				print overlap_links
                                if overlap_links and bottleneck_exist(overlap_links, isp_network):
                                    for tc_iso in pptc_iso_dict[j].keys():
                                        if tc_iso.calc_flag == 1:
					    print 'src:{} {} dst:{} {}'.format(tc_other.src, tc_iso.src, tc_other.dst, tc_iso.dst) 
                                            continue
					print 'u src:{} {} dst:{} {}'.format(tc_other.src, tc_iso.src, tc_other.dst, tc_iso.dst)
                                        if tc_other.src == tc_iso.src and tc_other.dst == tc_iso.dst:
                                            print 'origin: {} iso:{}'.format(tc_other.allocate_bw, tc_iso.allocate_bw)
                                            total_dict[i] += tc_other.allocate_bw / tc_iso.allocate_bw
					    flow_num += 1
                                            tc.calc_flag = 1
                                            tc_other.calc_flag = 1
                                            tc_iso.calc_flag = 1
	
	for pptc in pptc_total_dict.values():
	    for tc in pptc.keys():
	        tc.calc_flag = 0
	for pptc in pptc_iso_dict.values():
	    for tc in pptc.keys():
	        tc.calc_flag = 0
        #print 'total:{} {} {}'.format(i, total_dict[i], iso_dict[i])
        u_dict[i] = 1.0 * total_dict[i] / flow_num
        
    netstat_dict = {}
    for i in range(cp_num):
        netstat_dict[i] = s_dict[i] / u_dict[i]
        print 't s:{} u:{} netstat:{}'.format(s_dict[i], u_dict[i], netstat_dict[i])
    
    u = 0
    max_volume = max(cp_volume_dict.itervalues())
    cp_weight_dict = {}
    for i in range(cp_num):
        cp_weight_dict[i] = 1.0 * cp_volume_dict[i] / sum(cp_volume_dict.itervalues())

    for i in range(cp_num):
        u += netstat_dict[i] * cp_weight_dict[i]
    u = u / sum(cp_weight_dict.itervalues())

    gfi = 0
    for i in range(cp_num):
        gfi += pow(netstat_dict[i] - u, 2) * cp_weight_dict[i]
    V1 = sum(cp_weight_dict.itervalues())
    V2 = sum(pow(w, 2) for w in cp_weight_dict.itervalues())
    coef = V1 / (pow(V1, 2) - V2)
    gfi = coef * gfi
    gfi = math.sqrt(gfi)
    print 't u:{} gfi:{}'.format(u, gfi)
    return gfi                           
                            
    

def tunnel_gfi(cp_num):
    ispNet = IspNetwork('isp_network', ISP_TOPO_DIR)
    ispNet.linkcaps = set_link_caps(ispNet.topo)

    trafficMatrix = {}
    for i in range(cp_num):
	matrix = {}
	for j in range(3):
		src_node = j		
		for dst_node in ispNet.topo._graph.nodes():
		    if dst_node == src_node:
		        continue
		    matrix[(src_node, dst_node)] = CITY_TRAFFIC_VOLUME * (cp_num - i)
	trafficMatrix[i] = matrix
        
    pptc, throughput_total = ispNet.calc_path_maxminfair(trafficMatrix)
   
    pptc_dict = {}
    for i in range(cp_num):
        pptc_dict[i] = {}
    for tc, paths in pptc.iteritems():
        pptc_dict[tc.network_id][copy.deepcopy(tc)] = copy.deepcopy(paths)
            
    pptc_iso_dict = {}
    for i in range(cp_num):
        ispNet_local = IspNetwork('isp_network', ISP_TOPO_DIR)
        tm = {}
        pptc_iso_dict[i] = {}
        tm.update({i: trafficMatrix[i]})
        pptc, throughput = ispNet_local.calc_path_maxminfair(tm)
        for tc, paths in pptc.iteritems():
            pptc_iso_dict[i][copy.deepcopy(tc)] = copy.deepcopy(paths)

    network_gfi = calc_network_gfi(pptc_dict, pptc_iso_dict, cp_num, ispNet)
    tunnel_gfi = calc_tunnel_gfi(pptc_dict, pptc_iso_dict, cp_num, ispNet)

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
    with open(T_THROUGHPUT_LOG_DIR, 'a') as f:
	f.write(str(throughput_total))
	f.write('\n')
    with open(TGFI_TUNNEL_LOG_DIR, 'a') as f:
        f.write(str(tunnel_gfi))
	f.write('\n')
    with open(NGFI_TUNNEL_LOG_DIR, 'a') as f:
        f.write(str(network_gfi))
	f.write('\n')



def maxmin_gfi(cp_num):
    ispNet = IspNetwork('isp_network', ISP_TOPO_DIR)
    ispNet.linkcaps = set_link_caps(ispNet.topo)

    trafficMatrix = {}
    for i in range(cp_num):
	matrix = {}
	for j in range(3):
		src_node = j		
		for dst_node in ispNet.topo._graph.nodes():
		    if dst_node == src_node:
		        continue
		    matrix[(src_node, dst_node)] = CITY_TRAFFIC_VOLUME * (cp_num - i)
	trafficMatrix[i] = matrix
        
    pptc, throughput_total = ispNet.calc_path_maxminfair(trafficMatrix, network_level=False, weighted=False)

   
    pptc_dict = {}
    for i in range(cp_num):
        pptc_dict[i] = {}
    for tc, paths in pptc.iteritems():
        pptc_dict[tc.network_id][copy.deepcopy(tc)] = copy.deepcopy(paths)
            
    pptc_iso_dict = {}
    for i in range(cp_num):
        ispNet_local = IspNetwork('isp_network', ISP_TOPO_DIR)
        tm = {}
        pptc_iso_dict[i] = {}
        tm.update({i: trafficMatrix[i]})
        pptc, throughput = ispNet_local.calc_path_maxminfair(tm)
        for tc, paths in pptc.iteritems():
            pptc_iso_dict[i][copy.deepcopy(tc)] = copy.deepcopy(paths)

    network_gfi = calc_network_gfi(pptc_dict, pptc_iso_dict, cp_num, ispNet)
    tunnel_gfi = calc_tunnel_gfi(pptc_dict, pptc_iso_dict, cp_num, ispNet)


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
    with open(MM_THROUGHPUT_LOG_DIR, 'a') as f:
	f.write(str(throughput_total))
	f.write('\n')
    with open(NGFI_MM_LOG_DIR, 'a') as f:
        f.write(str(network_gfi))
	f.write('\n')
    with open(TGFI_MM_LOG_DIR, 'a') as f:
        f.write(str(tunnel_gfi))
	f.write('\n')


def max_gfi(cp_num):
    ispNet = IspNetwork('isp_network', ISP_TOPO_DIR)
    ispNet.linkcaps = set_link_caps(ispNet.topo)

    trafficMatrix = {}
    for i in range(cp_num):
	matrix = {}
	for j in range(3):
		src_node = j		
		for dst_node in ispNet.topo._graph.nodes():
		    if dst_node == src_node:
		        continue
		    matrix[(src_node, dst_node)] = CITY_TRAFFIC_VOLUME * (cp_num - i)
	trafficMatrix[i] = matrix

    

    pptc, throughput_total = ispNet.calc_path_maxminfair(trafficMatrix, network_level=False, weighted=False, max_throughput=True)

   
    pptc_dict = {}
    for i in range(cp_num):
        pptc_dict[i] = {}
    for tc, paths in pptc.iteritems():
        pptc_dict[tc.network_id][copy.deepcopy(tc)] = copy.deepcopy(paths)
            
    pptc_iso_dict = {}
    for i in range(cp_num):
        ispNet_local = IspNetwork('isp_network', ISP_TOPO_DIR)
        tm = {}
        pptc_iso_dict[i] = {}
        tm.update({i: trafficMatrix[i]})
        pptc, throughput = ispNet_local.calc_path_maxminfair(tm)
        for tc, paths in pptc.iteritems():
            pptc_iso_dict[i][copy.deepcopy(tc)] = copy.deepcopy(paths)

    network_gfi = calc_network_gfi(pptc_dict, pptc_iso_dict, cp_num, ispNet)
    tunnel_gfi = calc_tunnel_gfi(pptc_dict, pptc_iso_dict, cp_num, ispNet)


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
    with open(MAX_THROUGHPUT_LOG_DIR, 'a') as f:
	f.write(str(throughput_total))
	f.write('\n')
    with open(TGFI_MAX_LOG_DIR, 'a') as f:
        f.write(str(tunnel_gfi))
	f.write('\n')
    with open(NGFI_MAX_LOG_DIR, 'a') as f:
        f.write(str(network_gfi))
	f.write('\n')
