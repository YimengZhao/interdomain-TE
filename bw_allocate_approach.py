from topology import Topology
from cpNet import CpNetwork
from ispNet import IspNetwork


DEFAULT_LOG_DIR = "./log/default.log"
INDEPENDENT_LOG_DIR = "./log/independent.log"
NEGO_LOG_DIR = "./log/negotiate.log"

def default_routing(cp_num):
    cpNetworks = []
    ispTopo = Topology('isp_network', './data/topologies/simple.graphml')
    for i in range(cp_num):
        cpNetworks.append(CpNetwork('Abilene', './data/topologies/Abilene.graphml'))

    trafficMatrix = {}
    for i in range(cp_num):
        trafficMatrix[i] = cpNetworks[i].egress_volume_shortest([0, 1], ispTopo)
        
    ispNet = IspNetwork('isp_network', './data/topologies/simple.graphml')
    pptc, throughput = ispNet.calc_path_maxminfair(trafficMatrix)
    ingress_bw_dict = {}
    for i in range(cp_num):
        ingress_bw_dict[i] = {}
    for tc, path in pptc.iteritems():
        ingress = tc.src
        if ingress in ingress_bw_dict[tc.network_id]:
            ingress_bw_dict[tc.network_id][ingress] += tc.allocate_bw
        else:
            ingress_bw_dict[tc.network_id][ingress] = tc.allocate_bw

    #log to file
    with open(DEFAULT_LOG_DIR, 'a') as f:
        f.write(str(throughput))
	f.write('\n')
        #f.write('default routing \n')
        #for id, bw_dict in ingress_bw_dict.iteritems():
            #f.write('cp network id:{}, throughput:{}\n'.format(id, throughput))
            #for egress, bw in bw_dict.iteritems():
                #f.write('egress:{} bw:{}\n'.format(egress, bw))
        

def independent_routing(cp_num):
    cpNets = []
    ispTopo = Topology('isp_network', './data/topologies/simple.graphml')
    for i in range(cp_num):
        cpNets.append(CpNetwork('Abilene', './data/topologies/Abilene.graphml'))

    trafficMatrix = {}
    for i in range(cp_num):
        trafficMatrix[i] = cpNets[i].egress_max_throughput(10000, ispTopo)

    ispNet = IspNetwork('isp_network', './data/topologies/simple.graphml')
    egress_bw_dict, throughput = ispNet.calc_path_singleinput(10000, trafficMatrix, cp_num)

    with open(INDEPENDENT_LOG_DIR, 'a' ) as f:
	f.write(str(throughput))
	f.write('\n')
        #f.write('independent routing\n')
        #for id, bw_dict in egress_bw_dict.iteritems():
            #f.write('isp network id:{}, throughput:{}\n'.format(id, throughput))
            #for egress, bw in bw_dict.iteritems():
                #f.write('egress:{} bw:{}\n'.format(egress, bw))


def negotiate_routing(cp_num):
    cpNets = []
    ispTopo = Topology('isp_network', './data/topologies/simple.graphml')
    for i in range(cp_num):
        cpNets.append(CpNetwork('Abilene', './data/topologies/Abilene.graphml'))

    trafficMatrix = {}
    for i in range(cp_num):
        trafficMatrix[i] = cpNets[i].egress_all(10000, ispTopo)

    ispNet = IspNetwork('isp_network', './data/topologies/Abilene.graphml')
    egress_bw_dict, throughput = ispNet.calc_path_singleinput(10000, trafficMatrix, cp_num)
    print 'isp throughput:{}'.format(throughput)

    trafficMatrix = {}
    for id, bw_dict in egress_bw_dict.iteritems():
        trafficMatrix[id] = cpNets[id].egress_ratio(10000, ispTopo, bw_dict)

    pptc, throughput = ispNet.calc_path_maxminfair(trafficMatrix)
    
    with open(NEGO_LOG_DIR, 'a') as f:
	f.write(str(throughput))
	f.write('\n')
        #f.write('negotiate routing\n')
        #f.write('throughput:{}'.format(throughput))
