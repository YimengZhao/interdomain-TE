from topology import Topology
from cpNet import CpNetwork
from ispNet import IspNetwork

CP_NUM = 2
LOG_FILE_DIR = "./log.log"

def default_routing():
    cpNetworks = []
    ispTopo = Topology('isp_network', './data/topologies/simple.graphml')
    for i in range(CP_NUM):
        cpNetworks.append(CpNetwork('Abilene', './data/topologies/Abilene.graphml'))

    trafficMatrix = {}
    for i in range(CP_NUM):
        trafficMatrix[i] = cpNetworks[i].egress_volume_shortest([0, 1], ispTopo)
        
    ispNet = IspNetwork('isp_network', './data/topologies/simple.graphml')
    pptc, throughput = ispNet.calc_path_maxminfair(trafficMatrix)
    ingress_bw_dict = {}
    for i in range(CP_NUM):
        ingress_bw_dict[i] = {}
    for tc, path in pptc.iteritems():
        ingress = tc.src
        if ingress in ingress_bw_dict[tc.network_id]:
            ingress_bw_dict[tc.network_id][ingress] += tc.allocate_bw
        else:
            ingress_bw_dict[tc.network_id][ingress] = tc.allocate_bw

    #log to file
    with open(LOG_FILE_DIR, 'a') as f:
        f.write('default routing \n')
        for id, bw_dict in ingress_bw_dict.iteritems():
            f.write('cp network id:{}, throughput:{}\n'.format(id, throughput))
            for egress, bw in bw_dict.iteritems():
                f.write('egress:{} bw:{}\n'.format(egress, bw))
        

def independent_routing():
    cpNets = []
    ispTopo = Topology('isp_network', './data/topologies/simple.graphml')
    for i in range(CP_NUM):
        cpNets.append(CpNetwork('Abilene', './data/topologies/Abilene.graphml'))

    trafficMatrix = {}
    for i in range(CP_NUM):
        trafficMatrix[i] = cpNets[i].egress_all_maxthrough(10000, ispTopo)

    ispNet = IspNetwork('isp_network', './data/topologies/simple.graphml')
    egress_bw_dict, throughput = ispNet.calc_path_singleinput(10000, trafficMatrix, CP_NUM)

    with open(LOG_FILE_DIR, 'a' ) as f:
        f.write('independent routing\n')
        for id, bw_dict in egress_bw_dict.iteritems():
            f.write('isp network id:{}, throughput:{}\n'.format(id, throughput))
            for egress, bw in bw_dict.iteritems():
                f.write('egress:{} bw:{}\n'.format(egress, bw))


