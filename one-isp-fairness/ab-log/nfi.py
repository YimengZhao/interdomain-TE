import numpy as np
import matplotlib.pyplot as plt

import mpltex

#@mpltex.acs_decorator

maxmin_data = np.loadtxt('./ngfi_maxmin.log')
max_data = np.loadtxt('./ngfi_max.log')
#network_data = np.loadtxt('./network_algo.log')
tunnel_data = np.loadtxt('./ngfi_tunnel.log')

linestyles = mpltex.linestyle_generator()
line_width = 0
marker_size = 15

x = np.arange(2, 11)
plt.plot(x, maxmin_data, label = 'Max-min Fair', markersize=marker_size, linewidth=line_width, **linestyles.next())
plt.plot(x, max_data, label = 'MCF', markersize=marker_size, linewidth=line_width, **linestyles.next())
#plt.plot(x, network_data, label = "DP-CP", markersize=marker_size, linewidth=line_width, **linestyles.next())
plt.plot(x, tunnel_data, label = "DP-T", markersize=marker_size, linewidth=line_width, **linestyles.next())

plt.xlabel('Number of CPs')
plt.ylabel('NFI')
plt.legend(loc='upper left')
#plt.ylim([0, 0.5])
#fig.tight_layout(pad=0.1)
#fig.savefig('./throughput')

plt.rcParams.update({'font.size' : 18})

plt.show()
