from gfi_approach import *

if __name__ == "__main__":
    #default_gfi(14)
    #independent_routing(2)
    #negotiate_routing(2)
    #shortest_gfi(2)
    for i in range(1, 15):
        #default_gfi(i)
        #shortest_gfi(i)
        #independent_gfi(i)
        negotiate_gfi(i)

