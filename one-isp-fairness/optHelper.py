import cplex
from cplex.exceptions import CplexError
import math

from provisioning import computeBackgroundLoad

a = 2
U = 2

def set_link_caps(topo):
    capacities = {}
    G = topo._graph
    for u, v in G.edges_iter():
        link = (u, v)
	capacities[link] = 2000
	'''if u % 3 == 0:
            capacities[link] = 1000
	elif u% 4 == 0:
	    capacities[link] = 500
	elif u % 5 == 0:
	    capacities[link] = 1200
	else:
	    capacities[link] = 1500'''
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

def get_network_norm_weight(trafficClasses):
    tc_dict = {}
    demand_sum = sum(tc.demand for tc in trafficClasses)
    for tc in trafficClasses:
	if tc.network_id not in tc_dict:
	    tc_dict[tc.network_id] = 0
	tc_dict[tc.network_id] += tc.demand * 1.0 / demand_sum
    norm_list = tc_dict.values()
    return norm_list


def maxmin_fair_ratio_allocate(trafficClasses, linkcaps, pptc, norm_list, egress_bw_dict):
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
    print 'normlist'
    print norm_list.values()
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
            (ret, throughput) = MCF(linkcaps, b_low, b_high, f, pptc, norm_list, is_max)
	    for tc in pptc:
		tc.allocate_bw = tc.tentative_bw
	    return throughput

        (ret, tmp_throughput) = MCF(linkcaps, b_low, b_high, f, pptc, norm_list, is_max)
        print 'ret:{}'.format(ret)
        if ret == 0:
            for tc in pptc:
                print 'tc:{}-{},src:{},dst:{},tentative:{},demand:{},high:{}'.format(tc.network_id, tc.ID, tc.src,tc.dst,tc.tentative_bw,tc.demand,b_high*norm_list[tc])
                #for path in pptc[tc]:
                #print "paths:",path.getNodes(), "bw:",path.bw
                if tc.tentative_bw < min(tc.demand, b_high * norm_list[tc]) or i == roundNum - 1:
                    tc.allocate_bw = tc.tentative_bw
                    f[tc] = pptc[tc]

            print "throughput:{}".format(throughput)
	    throughput = tmp_throughput
            #return
    return throughput



def MCF_network(linkcaps, pptc, norm_list, lamda, is_max=False):
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

        #set demand constraints
        for tc in pptc:
            var_group = []
            for path in pptc[tc]:
                var_name = 'bpc_{}_{}_{}_{}'.format(tc.ID, path.getNodes(), tc.src, tc.dst)
                var_group.append(var_name)

            prob.linear_constraints.add(lin_expr=[cplex.SparsePair(ind=var_group, val=[1.0]*len(var_group))], senses=["L"], rhs=[tc.demand], names=["demand-{}".format(path.getNodes())])

        #set network constraints
	tc_var_dict = {}
	all_var = []
        for tc in pptc:
	    if tc.network_id not in tc_var_dict:
		tc_var_dict[tc.network_id] = []
	    for path in pptc[tc]:
		var_name = 'bpc_{}_{}_{}_{}'.format(tc.ID, path.getNodes(), tc.src, tc.dst)
		tc_var_dict[tc.network_id].append(var_name)
		all_var.append(var_name)
	
	for network_id, var_list in tc_var_dict.iteritems():
	    other_var = []
	    for var in all_var:
		if var not in var_list:
		    other_var.append(var)
	    var_group = var_list + other_var
	    multi = [1.0 - norm_list[network_id]] * len(var_list) + [-1.0 * norm_list[network_id]] * len(other_var)
	    prob.linear_constraints.add(lin_expr=[cplex.SparsePair(ind=var_group, val=multi)], senses=["L"], rhs=[lamda], names=["u{}-{}".format(tc.src, tc.dst)])
	    prob.linear_constraints.add(lin_expr=[cplex.SparsePair(ind=var_group, val=multi)], senses=["G"], rhs=[-1.0 * lamda], names=["l{}-{}".format(tc.src, tc.dst)])


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
                if r != 0:
			print 'network:{},{}:{}'.format(tc.network_id, var_name, r)
                tc.tentative_bw += r
		tc.allocate_bw += r
                path.bw = r

        return (0, prob.solution.get_objective_value())

    except CplexError as exc:
        print exc
        return (exc.args, 0)

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
	print 'in group'
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
                    var_group = []
                    for path in pptc[tc]:
                        var_name = 'bpc_{}_{}_{}_{}'.format(tc.ID, path.getNodes(), tc.src, tc.dst)
                        var_group.append(var_name)

                    prob.linear_constraints.add(lin_expr=[cplex.SparsePair(ind=var_group, val=[1.0]*len(var_group))], senses=["L"], rhs=[upper_bound], names=["u{}-{}".format(tc.src, tc.dst)])
                    prob.linear_constraints.add(lin_expr=[cplex.SparsePair(ind=var_group, val=[1.0]*len(var_group))], senses=["G"], rhs=[lower_bound], names=['l{}-{}'.format(tc.src, tc.dst)])
		else:
		    var_group = []
                    for path in pptc[tc]:
                        var_name = 'bpc_{}_{}_{}_{}'.format(tc.ID, path.getNodes(), tc.src, tc.dst)
                        var_group.append(var_name)
                    prob.linear_constraints.add(lin_expr=[cplex.SparsePair(ind=var_group, val=[1.0]*len(var_group))], senses=["L"], rhs=[tc.demand], names=["u{}-{}".format(tc.src, tc.dst)])
		


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
                #if r != 0:
		print 'network:{},{}:{}'.format(tc.network_id, var_name, r)
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
	multi = [0.9] * len(obj_1) + [-0.1] * len(obj_2)
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
