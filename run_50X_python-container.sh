# /bin/bash


run_it () {
	rm -rf cache && python ./sebs.py experiment invoke perf-cost --config config/$1.python-container.json --output-dir results/"$1"-python-container
	python sebs.py experiment process perf-cost --config config/$1.python-container.json --output-dir results/"$1"-python-container
	python plot_results.py results/"$1"-python-container/perf-cost/result.csv --output-dir results/"$1"-python-container/plots
}

# PYTHON NATIVE

# 501

#run_it 501
#run_it 502
run_it 503
#run_it 504


# COMPARISON PLOTS
echo "Generating comparison plots..."
python plot_comparison.py results/*/perf-cost/result.csv --output-dir results/comparison_plots
