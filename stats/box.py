import matplotlib.pyplot as plt
import numpy as np

from datetime import datetime

final_data = []
try:
    with open("checkpoint.txt") as data:
        for each_line in data:
            try:
                if each_line != '\n':
                    line = each_line.replace("\n", "").strip()
                    final_data.append(float(line))

            except ValueError:
                pass
except:
    pass

#print(final_data)
final_data = np.asarray(final_data)

#data = np.loadtxt("restore.txt")

fig = plt.figure(figsize =(10, 7))

# Creating plot
plt.boxplot(final_data)

now = datetime.now()
plt.savefig(f"box_checkpoint_{now.strftime('%m_%d_%Y-%H:%M:%S')}.png")

# show plot
plt.show()