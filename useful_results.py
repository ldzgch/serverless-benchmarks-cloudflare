import csv
import numpy as np
import matplotlib.pyplot as plt
import datetime
import json
import sys

import numpy

DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

with open(sys.argv[1], "r") as jsonfile:
    data = json.load(jsonfile)

benchmarks = data["_invocations"].keys()
invocations = data["_invocations"]

experiment_type = sys.argv[1].split("/")[-1].split("_")[0]

avg = None


for benchmark in benchmarks:
    all_deltas = []
    invocation = invocations[benchmark]
    instances = invocations[benchmark].keys()
    agg = 0
    n_cold_starts = 0
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
        all_deltas.append(delta / 1000)
    avg = agg / len(instances)
    print(all_deltas)
    print("Average remote time measurement (ms): ", avg)

    # with open(
    #     f"cloudflare-results/{datetime.datetime.now()}".replace(" ", "T"), "w"
    # ) as file:
    #     csv_file = csv.writer(file)
    #     csv_file.writerow([avg])

    # plt.scatter(list(range(len(all_deltas))), sorted(all_deltas))
    # plt.savefig(
    #     f"cloudflare-results/fig/{'.'.join(benchmark.split('-')[:2])}/dot_{benchmark.split('-')[2]}_{experiment_type}_{len(instances)}_{datetime.datetime.now()}.png".replace(
    #         " ", "T"
    #     )
    # )

    plt.clf()

    language = benchmark.split("-")[-2]

    benchmark_split = benchmark.split("-")
    benchmark_name = f"{benchmark_split[0]}.{'-'.join(benchmark_split[1:-2])}"
    n_cold_starts = 0

    cold_instance_deltas = []
    warm_instance_deltas = []

    if benchmark_name == "060.cold-start":
        for instance in instances:
            if invocation[instance]["output"]["result"]["output"]["is_cold_start"]:
                n_cold_starts += 1
                cold_instance_deltas.append(
                    invocation[instance]["times"]["benchmark"] / 1000
                )
            else:
                warm_instance_deltas.append(
                    invocation[instance]["times"]["benchmark"] / 1000
                )

    cold_delta_array = np.array(cold_instance_deltas)

    warm_delta_array = np.array(warm_instance_deltas)

    print(f"Warm/Cold: {np.mean(warm_delta_array)} / {np.mean(cold_delta_array)}")
    print(
        f"Warm/Cold intervals: [{np.min(warm_delta_array)}-{np.max(warm_delta_array)}] / [{np.min(cold_delta_array)}-{np.max(cold_delta_array)}]"
    )

    plt.title(
        f"{benchmark} {language.upper()} with {experiment_type} (cold: {n_cold_starts})"
    )
    plt.xlabel("Remote time (ms)")
    plt.ylabel("# invocations")

    plt.hist(sorted(all_deltas), bins=(np.arange(0, max(all_deltas), 1)))
    plt.savefig(
        f"cloudflare-results/fig/{benchmark_name}/{language}_{experiment_type}_{len(instances)}_{datetime.datetime.now()}.png".replace(
            " ", "T"
        )
    )
