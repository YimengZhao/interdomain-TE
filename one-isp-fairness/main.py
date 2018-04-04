#from fairness_ratio import *
from fairness import *

if __name__ == "__main__":
    #tunnel_gfi(5)
    #max_gfi(5)
    #max_gfi(3)
    for i in range(2, 11):
	tunnel_gfi(i)
	maxmin_gfi(i)
	max_gfi(i)



