import matplotlib.pyplot as plt
import numpy as np

from datetime import datetime

#conns_list = [10, 100, 200]
conns_list = [10, 20, 30, 40, 50, 60 ,70, 80 ,90, 100]

#checkpoint_restore = "restore"
checkpoint_restore = "checkpoint"

final_data_10 = []
final_data_100 = []
final_data_200 = []

data_dict = {}

for num in conns_list:
    final_data = []
    #data_dict = {}
    try:
        with open(f"{checkpoint_restore}_{num}.txt") as data:
            for each_line in data:
                try:
                    if each_line != '\n':
                        line = each_line.replace("\n", "").strip()
                        final_data.append(float(line))
                except ValueError:
                    pass

        data_dict[f"{num}"] = np.asarray(final_data)
        #fig, ax = plt.subplots()
        #plt.xlabel("Connections")
        #plt.ylabel("Seconds")
        #plt.figure(figsize =(10, 7))
        #ax.boxplot(data_dict.values()) # With outliers
        ##ax.boxplot(data_dict.values(), showfliers=False)
        #ax.set_xticklabels(data_dict.keys())

        ## Creating plot
        ## plt.boxplot(final_data)

        #now = datetime.now()
        ##plt.savefig(f"box_checkpoint_{now.strftime('%m_%d_%Y-%H:%M:%S')}.png")
        #fig.savefig(f"box_plots/box_{checkpoint_restore}_{num}_{now.strftime('%m_%d_%Y-%H:%M:%S')}.png")
        ##fig.savefig(f"box_plots/box_{checkpoint_restore}_ALL_{now.strftime('%m_%d_%Y-%H:%M:%S')}.png")

        ## show plot
        ##plt.show()

    except:
        print(f"Exception while in {num}")

data_dict[f"{num}"] = np.asarray(final_data)
fig, ax = plt.subplots()
plt.xlabel("Connections")
plt.ylabel("Seconds")
plt.figure(figsize =(10, 7))
#ax.boxplot(data_dict.values()) # With outliers
ax.boxplot(data_dict.values(), showfliers=False)
ax.set_xticklabels(data_dict.keys())

# Creating plot
# plt.boxplot(final_data)

now = datetime.now()
##plt.savefig(f"box_checkpoint_{now.strftime('%m_%d_%Y-%H:%M:%S')}.png")
fig.savefig(f"box_plots/box_{checkpoint_restore}_{num}_{now.strftime('%m_%d_%Y-%H:%M:%S')}.png")
##fig.savefig(f"box_plots/box_{checkpoint_restore}_ALL_{now.strftime('%m_%d_%Y-%H:%M:%S')}.png")

# show plot
#plt.show()