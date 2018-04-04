import numpy as np
import matplotlib.pyplot as plt

import mpltex

#@mpltex.acs_decorator

maxmin_data = np.loadtxt('./maxmin_throughput.log')
max_data = np.loadtxt('./max_throughput.log')
#network_data = np.loadtxt('./network_throughput.log')
tunnel_data = np.loadtxt('./tunnel_throughput.log')

maxmin_data = [x/10 for x in maxmin_data]
max_data = [x/10 for x in max_data]
tunnel_data = [x/10 for x in tunnel_data]

linestyles = mpltex.linestyle_generator()
line_width = 0
marker_size = 15

x = np.arange(2, 11)
plt.plot(x, maxmin_data, label = 'Max-min Fair', markersize=marker_size, linewidth=line_width, **linestyles.next())
plt.plot(x, max_data, label = 'MCF', markersize=marker_size, linewidth=line_width, **linestyles.next())
#plt.plot(x, network_data, label = "DP-CP", markersize=marker_size, linewidth=line_width, **linestyles.next())
plt.plot(x, tunnel_data, label = "WBA", markersize=marker_size, linewidth=line_width, **linestyles.next())

plt.xlabel('Number of CPs')
plt.ylabel('Total Rates')
plt.legend(loc='upper left')
plt.ylim([0, 1900])
#fig.tight_layout(pad=0.1)
#fig.savefig('./throughput')

plt.rcParams.update({'font.size' : 18})

plt.show()
