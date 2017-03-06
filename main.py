from bw_allocate_approach import *

if __name__ == "__main__":
    #default_routing(2)
    #independent_routing(2)
    #negotiate_routing(2)
    for i in range(1, 15):
        default_routing(i)
        shortest_routing(i)
        independent_routing(i)
        negotiate_routing(i)

