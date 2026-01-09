# /bin/bash


run_it () {
	python scripts/local_update_storage.py storage_object.json config/$1.python-local.json
	
	rm -rf cache && python ./sebs.py experiment invoke perf-cost --config config/$1.python-local.json --output-dir results/"$1"-python-local
	python sebs.py experiment process perf-cost --config config/$1.python-local.json --output-dir results/"$1"-python-local
	python plot_results.py results/"$1"-python-local/perf-cost/result.csv --output-dir results/"$1"-python-local/plots
}

# PYTHON LOCAL

./sebs.py storage start object config/storage.json --output-json storage_object.json


run_it 501

./sebs.py storage stop object storage_object.json
rm storage_object.json


# COMPARISON PLOTS
echo "Generating comparison plots..."
python plot_comparison.py results/*/perf-cost/result.csv --output-dir results/comparison_plots
