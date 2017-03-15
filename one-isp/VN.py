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
class IspNetwork:
    def __init__(self, topo_name, topo_file):
        self.topo = Topology(topo_name, topo_file)
     
    def egress_all(self, fake_node, dst_topo):
        result = {}
        for node in dst_topo.nodes():
            nodes_num = networkx.number_of_nodes(self.topo.getGraph())
            result[(fake_node, node)] = nodes_num * CITY_TRAFFIC_VOLUME
        print 'total:{}'.format(nodes_num * CITY_TRAFFIC_VOLUME)
        return result
            
    def egress_volume(self, egress_nodes, dst_topo):
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

class CpNetwork:
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
        self.linkcaps = self.setLinkCaps()
        self.norm_list = self.getNormWeight()

    def calc_path_sum(self, fake_node, trafficMatrix, isp_num):
        #add fake node
        self.topo._graph.add_node(fake_node)
        self.topo._graph.add_edge(0, fake_node)
        self.topo._graph.add_edge(fake_node, 0)
        self.topo._graph.add_edge(1, fake_node)
        self.topo._graph.add_edge(fake_node, 1)
        pptc = self.calc_path_sp(trafficMatrix)
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
        return ingress_bw_dict

    def calc_path_sp(self, trafficMatrix):
        self.set_traffic(trafficMatrix)
        ie_path_map = {}
        for pair in self.ie_path_map.itervalues():
            ie_path_map.update(pair)
        pptc = initOptimization(ie_path_map, self.topo, self.trafficClasses)
        maxmin_fair_allocate(self.trafficClasses, self.linkcaps, pptc, self.norm_list, False)
        return pptc

      
    def getNormWeight(self):
        print [tc.demand for tc in self.trafficClasses]
        demand_sum = sum(tc.demand for tc in self.trafficClasses)
        norm_list = {}
        for tc in self.trafficClasses:
            norm_list[tc] = tc.demand * 1.0 / demand_sum
        print norm_list.values()
        max_val = max(norm_list.values())
        for tc in self.trafficClasses:
            norm_list[tc] = norm_list[tc] / max_val
        return norm_list

    def setLinkCaps(self):
        capacities = {}
        G = self.topo._graph
        for u, v in G.edges_iter():
            link = (u, v)
            capacities[link] = 20000
            if u == 10000 and v == 0 or u == 10000 and v == 1:
                print 'test'
                capacities[link] = 10000000
        return capacities

    def egress_sum_backup(self):
        pptc = initOptimization(ie_path_map, self.topo, self.trafficClasses)
        maxmin_fair_allocate(self.trafficClasses, self.linkcaps, pptc, self.norm_list, False)
        egress_dict = {}
        for tc, paths in pptc.iteritems():
            for path in paths:
                nodes = path.getNodes()
                print nodes
                
            

def maxmin_fair_allocate(trafficClasses, linkcaps, pptc, norm_list, is_max=False):
    a = 2
    U = 10
    max_demand = max(tc.demand for tc in trafficClasses)
    roundNum = int(math.ceil(math.log(max_demand/U, a)))
    f = {}

    for i in range(roundNum):
        print "{} round".format(i)
        b_low = math.pow(a, i) * U 
        b_high = math.pow(a, i+1) * U

        if is_max:
            b_low = 0
            b_high = 1000000000

        (ret, throughput) = MCF(linkcaps, b_low, b_high, f, pptc, norm_list, is_max)
        if ret == 0:
            for tc in pptc:
                #print 'tc:{},src:{},dst:{},tentative:{},demand:{},high:{}'.format(tc.name, tc.src,tc.dst,tc.tentative_bw,tc.demand,b_high)
                #for path in pptc[tc]:
                #print "paths:",path.getNodes(), "bw:",path.bw
                if tc.tentative_bw < min(tc.demand, b_high) or i == roundNum - 1:
                    tc.allocate_bw = tc.tentative_bw
                    f[tc] = pptc[tc]

            print "throughput:{}".format(throughput)
            #return

def MCF(linkcaps, b_low, b_high, flow_group, pptc, norm_list, is_max):
    try:
        prob = cplex.Cplex()

        #set objective
        obj = []
        for tc in pptc:
            for path in pptc[tc]:
                var_name = 'bpc_{}_{}_{}_{}'.format(tc.ID, path.getNodes(), tc.src, tc.dst)
                obj.append(var_name)

        prob.variables.add(obj = [1.0]*len(obj), lb = [0.0]*len(obj), names = obj)
        prob.objective.set_sense(prob.objective.sense.maximize)

        #set flows that is already in flow_group
        for tc in flow_group:
            var_group = []
            for path in flow_group[tc]:
                var_name = 'bpc_{}_{}_{}_{}'.format(tc.ID, path.getNodes(), tc.src, tc.dst)
                var_group.append(var_name)
                prob.linear_constraints.add(lin_expr=[cplex.SparsePair(ind=var_group, val=[1.0]*len(var_group))], senses=["E"], rhs=[tc.allocate_bw])

        #set flows that is not in flow_group
        for tc in pptc:
            if tc not in flow_group:
                upper_bound = min(tc.demand, b_high)
                lower_bound = min(tc.demand, b_low)

                if is_max == False:
                    upper_bound = upper_bound * norm_list[tc]
                    lower_bound = lower_bound * norm_list[tc]
                    print norm_list[tc]
                    print is_max
                    print 'upper bound:{}'.format(upper_bound)
                    print 'lower bound:{}'.format(lower_bound)
                    var_group = []
                    for path in pptc[tc]:
                        var_name = 'bpc_{}_{}_{}_{}'.format(tc.ID, path.getNodes(), tc.src, tc.dst)
                        var_group.append(var_name)
                        print var_group
                        print 'upper ',upper_bound
                        print 'lower ',lower_bound
                        prob.linear_constraints.add(lin_expr=[cplex.SparsePair(ind=var_group, val=[1.0]*len(var_group))], senses=["L"], rhs=[upper_bound], names=["u{}-{}".format(tc.src, tc.dst)])
                        prob.linear_constraints.add(lin_expr=[cplex.SparsePair(ind=var_group, val=[1.0]*len(var_group))], senses=["G"], rhs=[lower_bound], names=['l{}-{}'.format(tc.src, tc.dst)])


        #set link capacity constraint
        for link in linkcaps:
            print link
            u, v = link
            cap = linkcaps[link]
            link_cap_var = []
            if cap > 0:
                for tc in pptc:
                    for path in pptc[tc]:
                        if link in path.getLinks():
                            #print path.getNodes()
                            var_name = 'bpc_{}_{}_{}_{}'.format(tc.ID, path.getNodes(), tc.src, tc.dst)
                            link_cap_var.append(var_name)
                            #print link_cap_var, ' cap:', cap
                            prob.linear_constraints.add(lin_expr=[cplex.SparsePair(ind=link_cap_var, val=[1.0] * len(link_cap_var))], senses=["L"], rhs=[cap])


        prob.solve()
        print("Solution status = ", prob.solution.get_status())
        print("Obj ", prob.solution.get_objective_value())

        numrows = prob.linear_constraints.get_num()
        numcols = prob.variables.get_num()


        for tc, paths in pptc.iteritems():
            tc.tentative_bw = 0
            for path in paths:
                var_name = 'bpc_{}_{}_{}_{}'.format(tc.ID, path.getNodes(), tc.src, tc.dst)
                r = prob.solution.get_values(var_name)
                tc.tentative_bw += r
                path.bw = r

        return (0, prob.solution.get_objective_value())

    except CplexError as exc:
        print exc
        return (exc.args, 0)





