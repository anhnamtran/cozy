#!/usr/bin/env python3
from matplotlib import pyplot as plt
import sys
import os

lines = open("data.txt", "r").read().split('\n')
times = list(map(float, lines[:-1]))

for i in range(1, len(times)):
    idx = len(times) - i
    times[idx] = times[idx] - times[idx - 1]

ys = times[1:]
xs = list(range(1, len(ys) + 1))

plt.xlabel("nth improvement")
plt.ylabel("time used (s)")
plt.plot(xs, ys)

fig_name = sys.argv[1]
run_no = sys.argv[2]

if not os.path.isdir("plots/{}".format(fig_name)):
    os.makedirs("plots/{}".format(fig_name))

plt.savefig("plots/{}/run-{}.png".format(fig_name, run_no))
#plt.show()
