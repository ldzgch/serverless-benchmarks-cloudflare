import csv
import numpy as np
import matplotlib.pyplot as plt
import datetime
import json
import sys

import numpy

DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
EXPERIMENT_NAME = sys.argv[2]

with open(sys.argv[1], "r") as jsonfile:
    data = json.load(jsonfile)

benchmarks = data["_invocations"].keys()
invocations = data["_invocations"]

avg = None

all_deltas = []

for benchmark in benchmarks:
    invocation = invocations[benchmark]
    instances = invocations[benchmark].keys()
    agg = 0
    for instance in instances:
        results = invocation[instance]
        client_begin = results["times"]["client_begin"]
        client_end = results["times"]["client_end"]

        client_begin_date = datetime.datetime.strptime(client_begin, DATE_FORMAT)
        client_end_date = datetime.datetime.strptime(client_end, DATE_FORMAT)

        begin = results["output"]["begin"]
        end = results["output"]["end"]

        delta = results["times"]["benchmark"]

        agg += delta
        all_deltas.append(delta * 1000)
    avg = agg / len(instances)
    print(all_deltas)
    print("Average remote time measurement (ms): ", avg)


# with open(
#     f"cloudflare-results/{datetime.datetime.now()}".replace(" ", "T"), "w"
# ) as file:
#     csv_file = csv.writer(file)
#     csv_file.writerow([avg])

# plt.scatter(list(range(len(all_deltas))), sorted(all_deltas))
plt.hist(sorted(all_deltas))

plt.savefig(
    f"fig/b110/{EXPERIMENT_NAME}_{datetime.datetime.now()}.png".replace(" ", "T")
)
