# /bin/bash


run_it () {
	rm -rf cache && python ./sebs.py experiment invoke perf-cost --config config/$1.python-aws.json --output-dir results/"$1"-python-aws
	python sebs.py experiment process perf-cost --config config/$1.python-aws.json --output-dir results/"$1"-python-aws
	python plot_results.py results/"$1"-python-aws/perf-cost/result.csv --output-dir results/"$1"-python-aws/plots
}

# PYTHON NATIVE

run_it 501
run_it 502
run_it 503
run_it 504


# COMPARISON PLOTS
echo "Generating comparison plots..."
python plot_comparison.py results/*/perf-cost/result.csv --output-dir results/comparison_plots
