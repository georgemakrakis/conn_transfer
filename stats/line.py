import matplotlib.pyplot as plt
import csv
import numpy as np
from datetime import datetime

x, y = np.loadtxt('avg_spawn_time.csv', delimiter=',')
#x, y = np.genfromtxt('avg_spawn_time.csv', delimiter=',', unpack=True)

plt.plot(x, y, color = 'orange', linestyle = 'dashed',
         marker = 'o',label = "Average spawn time")

plt.xticks(rotation = 25)
plt.xlabel('Containers')
plt.ylabel('seconds')
plt.title('Average time to spawn containers', fontsize = 20)
plt.grid()
plt.legend()

now = datetime.now()
plt.savefig(f"line_avg_spawn_{now.strftime('%m_%d_%Y-%H-%M-%S')}.png")

plt.show()