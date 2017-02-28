# coding=utf-8
import pprint

from provisioning import generateTrafficClasses

from initopt import *
from generatePath import *
from predicates import nullPredicate

from topology import Topology
from traffic import TrafficMatrix


import cplex
from cplex.exceptions import CplexError
import math
import copy

def setLinkCaps(topology):
    capacities = {}
    G = topology.getGraph()
    for u, v in G.edges_iter():
        print u,v
        link = (u, v)
        capacities[link] = 2000
        if u == 3 and v == 1:
            print 'test'
            #capacities[link] = 50
    return capacities

def TE():
    # ==============
    # Let's generate some example data;
    # ==============
    topo = Topology('Abilene', './data/topologies/Abilene.graphml')
    # Let's load an existing gravity traffic matrix. It's just a dict mapping ingress-egress tuples to flow volume (a float).
    trafficMatrix_1 = TrafficMatrix.load('./data/tm/Abilene.tm')
    #trafficMatrix_2 = TrafficMatrix.load('data/tm/tc-4.tm')
    trafficMatrix_2 = {}
    print trafficMatrix_1.keys()
    for key, value in trafficMatrix_1.iteritems():
        trafficMatrix_2.update({key: 7 * value})
        
    #print trafficMatrix_2

    # compute traffic classes. We will only have one class that encompasses all the traffic;
    # assume that each flow consumes 2000 units of bandwidth
    ie_path_map_1 = generatePath(trafficMatrix_1.keys(), topo, nullPredicate, "shortest", 5)
    ie_path_map_2 = generatePath(trafficMatrix_2.keys(), topo, nullPredicate, "shortest", 5)
    ie_path_map = dict(ie_path_map_1.items() + ie_path_map_2.items())
    #f = pptc_set.copy()    
    
    trafficClasses_1 = generateTrafficClasses(trafficMatrix_1.keys(), trafficMatrix_1, {'vn1':1}, {'vn1': 100})
    trafficClasses_2 = generateTrafficClasses(trafficMatrix_2.keys(), trafficMatrix_2, {'vn2':1}, {'vn2': 100}, index_base=len(trafficClasses_1))
    trafficClasses = trafficClasses_1 + trafficClasses_2
    
    v1_sum = sum(tc.demand for tc in trafficClasses_1)
    v2_sum = sum(tc.demand for tc in trafficClasses_2)
    demand_sum = sum(tc.demand for tc in trafficClasses)
    norm_list = {}
    for tc in trafficClasses:
        norm_list[tc] = tc.demand / demand_sum
    max_val = max(norm_list.values())
    for tc in trafficClasses:
        norm_list[tc] = norm_list[tc] / max_val
    

    # since our topology is "fake", provision our links and generate link capacities in our network
    linkcaps = setLinkCaps(topo)

    # these will be our link constraints: do not load links more than 50%
    linkConstrCaps = {(u, v): 1.0 for u, v in topo.links()}

    # ==============
    # Optimization
    # ==============
    pptc = initOptimization(ie_path_map, topo, trafficClasses)
    maxmin_fair_allocate(trafficClasses, linkcaps, pptc, norm_list, False)

        
    print "calculating fairness index..."

    pptc_1 = initOptimization(ie_path_map_1, topo, trafficClasses_1)
    maxmin_fair_allocate(trafficClasses_1, linkcaps, pptc_1, norm_list)

    pptc_2 = initOptimization(ie_path_map_2, topo, trafficClasses_2)
    maxmin_fair_allocate(trafficClasses_2, linkcaps, pptc_2, norm_list)

    
    s_1 = 0.0
    s_2 = 0.0
    s1_num = 0
    s2_num = 0
    for tc in pptc:
        if tc in trafficClasses_1:
            for tc1 in pptc_1:
                if tc.src == tc1.src and tc.dst == tc1.dst: 
                    print 'tc:{} tc1:{}'.format(tc.allocate_bw, tc1.allocate_bw)
                    if tc1.allocate_bw == 0:
                        tc1.allocate_bw = 0.1
                    s_1 += tc.allocate_bw / tc1.allocate_bw
                    s1_num += 1
                    break
        elif tc in trafficClasses_2:
            for tc2 in pptc_2:
                if tc.src == tc2.src and tc.dst == tc2.dst:
                    if tc2.allocate_bw == 0:
                        tc2.allocate_bw = 0.1
                    s_2 += tc.allocate_bw / tc2.allocate_bw
                    s2_num += 1
                    break
    s_1 = s_1 / s1_num
    s_2 = s_2 / s2_num
    print 's1:{} s2:{}'.format(s_1, s_2)
    


    g1 = copy.deepcopy(pptc_1)
    g2 = copy.deepcopy(pptc_2)
    
    for tc1 in pptc_1:
        if tc1.calc_flag == 1:
            continue
        for path1 in pptc_1[tc1]:
            for tc2 in pptc_2:
                if tc2.calc_flag == 1:
                    continue
                for path2 in pptc_2[tc2]:
                    links1 = path1.getLinks()
                    links2 = path2.getLinks()
                    if set(links1).intersection(links2):
                        g1[copy.deepcopy(tc2)] = copy.deepcopy(pptc_2[tc2])
                        g2[copy.deepcopy(tc1)] = copy.deepcopy(pptc_1[tc1])
                        flag = 1
                        tc2.calc_flag = 1
                        tc1.calc_flag = 1

    maxmin_fair_allocate(g1.keys(), linkcaps, g1, norm_list)
    maxmin_fair_allocate(g2.keys(), linkcaps, g2, norm_list)
   
    
    u_1 = 0.0
    u_2 = 0.0
    u1_num = 0
    u2_num = 0

    for tc1 in g1:
        for tc in pptc:
                if tc.src == tc1.src and tc.dst == tc1.dst: 
                    print 'tc:{} tc1:{}'.format(tc.allocate_bw, tc1.allocate_bw)
                    u_1 += min({tc.allocate_bw / tc1.allocate_bw, 1})
                    u1_num += 1
                    break
    for tc2 in g2:
        for tc in pptc:
            if tc.src == tc2.src and tc.dst == tc2.dst:
                u_2 += min({tc.allocate_bw / tc2.allocate_bw, 1})
                u2_num += 1
                break

    u_1 = u_1 / u1_num
    u_2 = u_2 / u2_num
    print 'u1:{} u2:{}'.format(u_1, u_2)

                
    netstat_1 = s_1 / u_1
    netstat_2 = s_2 / u_2
    
    u = (netstat_1 * v1_sum + netstat_2 * v2_sum) / (v1_sum + v2_sum)
    print u
    gfi = math.sqrt((pow(netstat_1 - u, 2) * v1_sum + pow(netstat_2 - u, 2) * v2_sum) / (v1_sum + v2_sum))
    print gfi
        
def maxmin_fair_allocate(trafficClasses, linkcaps, pptc, norm_list, is_max=False):
    a = 2
    U = 2 
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
                var_name = 'bpc_{}_{}_{}_{}'.format(tc.name, path.getNodes(), tc.src, tc.dst)
                obj.append(var_name)

        prob.variables.add(obj = [1.0]*len(obj), lb = [0.0]*len(obj), names = obj)
        prob.objective.set_sense(prob.objective.sense.maximize)
    
        #set flows that is already in flow_group
        for tc in flow_group:
            var_group = []
            for path in flow_group[tc]:
                var_name = 'bpc_{}_{}_{}_{}'.format(tc.name, path.getNodes(), tc.src, tc.dst)
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
                    var_name = 'bpc_{}_{}_{}_{}'.format(tc.name, path.getNodes(), tc.src, tc.dst)
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
                            var_name = 'bpc_{}_{}_{}_{}'.format(tc.name, path.getNodes(), tc.src, tc.dst)
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
                var_name = 'bpc_{}_{}_{}_{}'.format(tc.name, path.getNodes(), tc.src, tc.dst)
                r = prob.solution.get_values(var_name)
                tc.tentative_bw += r
                path.bw = r

        return (0, prob.solution.get_objective_value())

    except CplexError as exc:
        print exc.args[2]
        return (exc.args[2], 0)
        

if __name__ == "__main__":
    TE()
