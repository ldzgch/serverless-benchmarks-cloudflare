# /bin/bash


run_it () {
	rm -rf cache && python ./sebs.py experiment invoke perf-cost --config config/$1.python-native.json --output-dir results/"$1"-python-native
	python sebs.py experiment process perf-cost --config config/$1.python-native.json --output-dir results/"$1"-python-native
	python plot_results.py results/"$1"-python-native/perf-cost/result.csv --output-dir results/"$1"-python-native/plots
}

# PYTHON NATIVE

run_it 210


# COMPARISON PLOTS
echo "Generating comparison plots..."
python plot_comparison.py results/*/perf-cost/result.csv --output-dir results/comparison_plots
