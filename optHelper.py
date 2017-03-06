import cplex
from cplex.exceptions import CplexError
import math

from provisioning import computeBackgroundLoad


def set_link_caps(topo):
    capacities = {}
    G = topo._graph
    for u, v in G.edges_iter():
        link = (u, v)
        capacities[link] = 8000
        if u == 10000 and v == 0 or u == 10000 and v == 1 or u == 0 and v == 10000 or u == 1 and v == 10000:
            capacities[link] = 1000000000000000
    return capacities
      
def get_norm_weight(trafficClasses):
    demand_sum = sum(tc.demand for tc in trafficClasses)
    norm_list = {}
    for tc in trafficClasses:
        norm_list[tc] = tc.demand * 1.0 / demand_sum
    max_val = max(norm_list.values())
    for tc in trafficClasses:
        norm_list[tc] = norm_list[tc] / max_val
    return norm_list

def maxmin_fair_ratio_allocate(trafficClasses, linkcaps, pptc, norm_list, egress_bw_dict):
    a = 2
    U = 5
    max_demand = max(tc.demand for tc in trafficClasses)
    round_num = 2 * int(math.ceil(math.log(max_demand/U, a)))

    throughput = 0
    f = {}
    for i in range(round_num):
        b_low = math.pow(a, i) * U
	if i == 0:
	    b_low = 0
        b_high = math.pow(a, i+1) * U

        (ret, tmp_throughput) = MCF_ratio(linkcaps, b_low, b_high, f, pptc, norm_list, egress_bw_dict)
        if ret == 0:
            throughput = 0
            for tc in pptc:
                print 'tentative:{} demand:{} high:{}'.format(tc.tentative_bw, tc.demand, b_high)
                if tc.tentative_bw < min(tc.demand, b_high) or i == round_num-1:
                    tc.allocate_bw = tc.tentative_bw
                    f[tc] = pptc[tc]
                throughput += tc.allocate_bw
            print "max min ratio throughput:{}".format(throughput)
    return throughput

def maxmin_fair_allocate(trafficClasses, linkcaps, pptc, norm_list, is_max=False):
    a = 2
    U = 5
    max_demand = max(tc.demand for tc in trafficClasses)
    roundNum = 2 * int(math.ceil(math.log(max_demand/U, a)))
    f = {}

    throughput = 0
    for i in range(roundNum):
        print "{} round".format(i)
        b_low = math.pow(a, i) * U 
	if i == 0:
	    b_low = 0
        b_high = math.pow(a, i+1) * U

        if is_max:
            b_low = 0
            b_high = 1000000000

        (ret, tmp_throughput) = MCF(linkcaps, b_low, b_high, f, pptc, norm_list, is_max)
        print 'ret:{}'.format(ret)
        if ret == 0:
            for tc in pptc:
                print 'tc:{},src:{},dst:{},tentative:{},demand:{},high:{}'.format(tc.name, tc.src,tc.dst,tc.tentative_bw,tc.demand,b_high)
                #for path in pptc[tc]:
                #print "paths:",path.getNodes(), "bw:",path.bw
                if tc.tentative_bw < min(tc.demand, b_high * norm_list[tc]) or i == roundNum - 1:
                    tc.allocate_bw = tc.tentative_bw
                    f[tc] = pptc[tc]

            print "throughput:{}".format(throughput)
	    throughput = tmp_throughput
            #return
    return throughput

def MCF(linkcaps, b_low, b_high, flow_group, pptc, norm_list, is_max):
    try:
        prob = cplex.Cplex()

        #set objective
        obj = []
        for tc in pptc:
            for path in pptc[tc]:
                print path.getNodes()
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
            prob.linear_constraints.add(lin_expr=[cplex.SparsePair(ind=var_group, val=[1.0]*len(var_group))], senses=["E"], rhs=[tc.tentative_bw], names=["inflow-{}".format(path.getNodes())])

        #set flows that is not in flow_group
        for tc in pptc:
            if tc not in flow_group:
                upper_bound = min(tc.demand, b_high * norm_list[tc])
                lower_bound = min(tc.demand, b_low * norm_list[tc])

                if is_max == False:
                    #upper_bound = upper_bound * norm_list[tc]
                    #lower_bound = lower_bound * norm_list[tc]
                    print 'upper bound:{}'.format(upper_bound)
                    print 'lower bound:{}'.format(lower_bound)
                    var_group = []
                    for path in pptc[tc]:
                        var_name = 'bpc_{}_{}_{}_{}'.format(tc.ID, path.getNodes(), tc.src, tc.dst)
                        var_group.append(var_name)
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
            prob.linear_constraints.add(lin_expr=[cplex.SparsePair(ind=link_cap_var, val=[1.0] * len(link_cap_var))], senses=["L"], rhs=[cap], names=['link-{}-{}'.format(link, path.getNodes)])


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
		print '{}:{}'.format(var_name, r)
                tc.tentative_bw += r
                path.bw = r

        return (0, prob.solution.get_objective_value())

    except CplexError as exc:
        print exc
        return (exc.args, 0)


def MCF_ratio(linkcaps, b_low, b_high, flow_group, pptc, norm_list, egress_bw_dict):
    try:
        prob = cplex.Cplex()

        #set objective
	obj_1 = []
        path_bw_vars = []
        egress_var_dict = {}
        for tc, paths in pptc.iteritems():
            for path in paths:
                nodes = path.getNodes()
                egress = nodes[-2]
                var_name = 'bpc_{}_{}_{}_{}'.format(tc.ID, path.getNodes(), tc.src, tc.dst)
		obj_1.append(var_name)
                if egress in egress_var_dict:
                    egress_var_dict[egress].append(var_name)
                else:
                    egress_var_dict[egress] = [var_name]
                path_bw_vars.append(var_name)

	obj_2=[]
        for egress in egress_var_dict.keys():
            var_name = 'x_{}'.format(egress)
            obj_2.append(var_name)
            
        obj = []
	obj = obj_1 + obj_2
	multi = [1] * len(obj_1) + [-0.1] * len(obj_2)
        prob.variables.add(obj = multi, lb = [0.0]*len(obj), names = obj)
        prob.objective.set_sense(prob.objective.sense.maximize)

        #set path bw variables
        #prob.variables.add(names = path_bw_vars, lb = [0.0]*len(path_bw_vars))

        #set x constraints
        for egress in egress_bw_dict:
            var_group = ['x_{}'.format(egress)]
            coefficient_u = [1.0]
            coefficient_l = [1.0]
            var_group.extend(egress_var_dict[egress])
            coefficient_u.extend([1.0] * len(egress_var_dict[egress]))
            coefficient_l.extend([-1.0] * len(egress_var_dict[egress]))
	    
            prob.linear_constraints.add(lin_expr=[cplex.SparsePair(ind=var_group, val=coefficient_u)], senses=["G"], rhs=[egress_bw_dict[egress]])
            prob.linear_constraints.add(lin_expr=[cplex.SparsePair(ind=var_group, val=coefficient_l)], senses=['G'], rhs=[-1.0 * egress_bw_dict[egress]])

        #set flows that is already in flow_group
        for tc in flow_group:
            var_group = []
            for path in flow_group[tc]:
                var_name = 'bpc_{}_{}_{}_{}'.format(tc.ID, path.getNodes(), tc.src, tc.dst)
                var_group.append(var_name)
            prob.linear_constraints.add(lin_expr=[cplex.SparsePair(ind=var_group, val=[1.0]*len(var_group))], senses=["E"], rhs=[tc.tentative_bw])

        #set flows that is not in flow_group
        for tc in pptc:
            if tc not in flow_group:
                upper_bound = min(tc.demand, b_high * norm_list[tc])
                lower_bound = min(tc.demand, b_low * norm_list[tc])

                is_max = False
                if is_max == False:
                    upper_bound = upper_bound * norm_list[tc]
                    lower_bound = lower_bound * norm_list[tc]
                    var_group = []
                    for path in pptc[tc]:
                        var_name = 'bpc_{}_{}_{}_{}'.format(tc.ID, path.getNodes(), tc.src, tc.dst)
                        var_group.append(var_name)
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
	        print '{}:{}'.format(var_name, r)
                tc.tentative_bw += r
                path.bw = r

        return (0, prob.solution.get_objective_value())

    except CplexError as exc:
        print exc
        return (exc.args, 0)
