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
        capacities[link] = 30
        if u == 3 and v == 2:
            capacities[link] = 50
        if u == 5 and v == 6:
            print 'test'
            capacities[link] = 50
    return capacities

def TE():
    # ==============
    # Let's generate some example data;
    # ==============
    topo = Topology('Abilene', 'data/topologies/simple-flex.graphml')
    # Let's load an existing gravity traffic matrix. It's just a dict mapping ingress-egress tuples to flow volume (a float).
    trafficMatrix_1 = TrafficMatrix.load('data/tm/tc-3.tm')
    trafficMatrix_2 = TrafficMatrix.load('data/tm/tc-4.tm')


    # compute traffic classes. We will only have one class that encompasses all the traffic;
    # assume that each flow consumes 2000 units of bandwidth
    ie_path_map_1 = generatePath(trafficMatrix_1.keys(), topo, nullPredicate, "shortest", 5)
    ie_path_map_2 = generatePath(trafficMatrix_2.keys(), topo, nullPredicate, "shortest", 5)
    ie_path_map = dict(ie_path_map_1.items() + ie_path_map_2.items())
    #f = pptc_set.copy()    
    
    trafficClasses_1 = generateTrafficClasses(trafficMatrix_1.keys(), trafficMatrix_1, {'vn1':1}, {'vn1': 100})
    trafficClasses_2 = generateTrafficClasses(trafficMatrix_2.keys(), trafficMatrix_2, {'vn2':1}, {'vn2': 100}, index_base=len(trafficClasses_1))
    for tc in trafficClasses_2:
        print tc
    trafficClasses = trafficClasses_1 + trafficClasses_2
    for tc in trafficClasses:
        print tc
        print "ID:",tc.ID,";name:",tc.name,"src:",tc.src,";dst:",tc.dst,";flows:",tc.volFlows,";byte:",tc.volBytes


    # since our topology is "fake", provision our links and generate link capacities in our network
    linkcaps = setLinkCaps(topo)

    # these will be our link constraints: do not load links more than 50%
    linkConstrCaps = {(u, v): 1.0 for u, v in topo.links()}

    # ==============
    # Optimization
    # ==============
    pptc = initOptimization(ie_path_map, topo, trafficClasses)
    maxmin_fair_allocate(trafficClasses, linkcaps, pptc, False)

      
        
def maxmin_fair_allocate(trafficClasses, linkcaps, pptc, is_max=False):
    a = 2
    U = 2
    max_demand = max(tc.demand for tc in trafficClasses)
    roundNum = int(math.ceil(math.log(max_demand/U, a)))
    print "test:{},{}".format(max_demand, roundNum)
    f = {}
    for i in range(roundNum):
        print "{} round".format(i)
        b_low = math.pow(a, i) * U
        b_high = math.pow(a, i+1) * U
        
        if is_max:
            b_low = 0
            b_high = 1000000000

        (ret, throughput) = MCF(linkcaps, b_low, b_high, f, pptc)
        if ret == 0:
            for tc in pptc:
                print 'tc:{},src:{},dst:{},tentative:{},demand:{},high:{}'.format(tc.name, tc.src,tc.dst,tc.tentative_bw,tc.demand,b_high)
                for path in pptc[tc]:
                    print "paths:",path.getNodes(), "bw:",path.bw
                if tc.tentative_bw < min(tc.demand, b_high) or i == roundNum - 1:
                    tc.allocate_bw = tc.tentative_bw
                    f[tc] = pptc[tc]
            
            print "throughput:{}".format(throughput)
    

def MCF(linkcaps, b_low, b_high, flow_group, pptc):
    try:
        prob = cplex.Cplex()

        #set objective
        obj = []
        multi = []
        for tc in pptc:
            for path in pptc[tc]:
                var_name = 'bpc_{}_{}_{}_{}'.format(tc.name, path.getNodes(), tc.src, tc.dst)
                obj.append(var_name)
                if tc.dst == 3:
                    multi.append(1)
                else:
                    multi.append(1)

        prob.variables.add(obj = multi, lb = [0.0]*len(obj), names = obj)
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
