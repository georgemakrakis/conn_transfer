import matplotlib.pyplot as plt
import csv
import numpy as np
from datetime import datetime

x, y = np.loadtxt('avg_spawn_time.csv', delimiter=',')
plt.plot(x, y, color = 'orange', linestyle = 'dashed',
         marker = 'o', markeredgecolor = 'black', markerfacecolor= 'black',label = "Average spawn time")

#x, y = np.genfromtxt('avg_spawn_time.csv', delimiter=',', unpack=True)

#x, y = np.loadtxt('migration_latency.txt', delimiter=',')

#plt.plot(x, y, color = 'orange', linestyle = 'dashed',
#         marker = 'o', markeredgecolor = 'black', markerfacecolor= 'black',label = "migration")

#x1, y1 = np.loadtxt('no-migration_latency.txt', delimiter=',')

#plt.plot(x1, y1, color = 'blue', linestyle = 'dashed',
#         marker = 'o', markeredgecolor = 'black', markerfacecolor= 'black',label = "no migration")


#plt.xticks(rotation = 25)
plt.xlabel('Containers')
plt.ylabel('seconds')

#plt.xlabel('Connections')
#plt.ylabel('Seconds')
#plt.title('Average time to spawn containers', fontsize = 20)

#plt.grid()
plt.legend()

now = datetime.now()
plt.savefig(f"line_avg_spawn_{now.strftime('%m_%d_%Y-%H-%M-%S')}.png")
#plt.savefig(f"line_migration_no-migration_{now.strftime('%m_%d_%Y-%H-%M-%S')}.png")

plt.show()
