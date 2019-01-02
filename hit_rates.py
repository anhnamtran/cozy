#!/usr/bin/env python3

import redis
import sys
import os

redis_cli = redis.Redis(host='localhost', port=6379, db=0)

stats = redis_cli.info(section="stats")

hits = stats["keyspace_hits"]
misses = stats["keyspace_misses"]

hit_rate = float(hits) / (hits + misses)

file_name = sys.argv[1]
run_no = sys.argv[2]

hit_rates_out_dir = "exp_out/hit_rates"
file_out_dir = "{}/{}".format(hit_rates_out_dir, file_name)

if not os.path.isdir(hit_rates_out_dir):
    os.makedirs(hit_rates_out_dir)
if not os.path.isdir(file_out_dir):
    os.makedirs(file_out_dir)

with open("{}/run-{}.txt".format(file_out_dir, run_no), "w+") as f:
    f.write("Hits: {}".format(hits))
    f.write("Misses: {}".format(misses))
    f.write("Hit rate: {}".format(hit_rate))
