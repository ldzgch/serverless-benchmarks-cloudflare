import json
import sys

storage_file = sys.argv[1]
experiment_file = sys.argv[2]
with open(experiment_file) as f:
    ex_data = json.load(f)

with open(storage_file) as f:
    sto_data = json.load(f)

ex_data["deployment"].get("local")

["local"]["storage"] = sto_data

with open(experiment_file, "w") as f:
    json.dump(ex_data)
