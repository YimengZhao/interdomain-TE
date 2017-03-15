# coding=utf-8
import networkx

from generatePath import generatePathsPerTrafficClass
from selectPath import getSelectFunction
from predicates import nullPredicate
from generatePath import generatePathsPerIE
import copy

def initOptimization(ie_path_map, topology, trafficClasses, predicate=nullPredicate, selectStrategy='shortest', selectNumber=5):
    """
    A kick start function for the optimization

    Generates the paths for the traffic classes, automatically selects the paths based on given numbers and strategy,
    and by default adds the decision variables

    :param topology: topology we are working with
    :param trafficClasses: a list of traffic classes
    :param predicate: the predicate to verify path validity
    :param selectStrategy: way to select paths ('random', 'shortest'...)
    :param selectNumber: number of paths per traffic class to choose
    :param modifyFunc: the path modifier function
    :param backend: the optimization backend
    :return: a tuple containing the :py:class:`~sol.optimization.optbase.Optimization` object and paths per traffic class
        (in the form of a dictionary)
    """
    result = {}
    for t in trafficClasses:
	if (t.src, t.dst) in ie_path_map:
		print ie_path_map[(t.src, t.dst)]
        result[copy.deepcopy(t)] = copy.deepcopy(ie_path_map[(t.src, t.dst)])
    return result



        
    
