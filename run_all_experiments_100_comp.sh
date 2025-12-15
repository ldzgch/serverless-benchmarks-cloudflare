# /bin/bash

# PYTHON CONTAINER

# 110
rm -rf cache && python ./sebs.py experiment invoke perf-cost --config config/110.python-container.json --output-dir results/110-python-container
python sebs.py experiment process perf-cost --config config/110.python-container.json --output-dir results/110-python-container
python plot_results.py results/110-python-container/perf-cost/result.csv --output-dir results/110-python-container/plots

# 120
rm -rf cache && python ./sebs.py experiment invoke perf-cost --config config/120.python-container.json --output-dir results/120-python-container
python sebs.py experiment process perf-cost --config config/120.python-container.json --output-dir results/120-python-container
python plot_results.py results/120-python-container/perf-cost/result.csv --output-dir results/120-python-container/plots

# 130
rm -rf cache && python ./sebs.py experiment invoke perf-cost --config config/130.python-container.json --output-dir results/130-python-container
python sebs.py experiment process perf-cost --config config/130.python-container.json --output-dir results/130-python-container
python plot_results.py results/130-python-container/perf-cost/result.csv --output-dir results/130-python-container/plots

# PYTHON NATIVE

# 110
rm -rf cache && python ./sebs.py experiment invoke perf-cost --config config/110.python-native.json --output-dir results/110-python-native
python sebs.py experiment process perf-cost --config config/110.python-native.json --output-dir results/110-python-native
python plot_results.py results/110-python-native/perf-cost/result.csv --output-dir results/110-python-native/plots

# 120
rm -rf cache && python ./sebs.py experiment invoke perf-cost --config config/120.python-native.json --output-dir results/120-python-native
python sebs.py experiment process perf-cost --config config/120.python-native.json --output-dir results/120-python-native
python plot_results.py results/120-python-native/perf-cost/result.csv --output-dir results/120-python-native/plots

# 130
rm -rf cache && python ./sebs.py experiment invoke perf-cost --config config/130.python-native.json --output-dir results/130-python-native
python sebs.py experiment process perf-cost --config config/130.python-native.json --output-dir results/130-python-native
python plot_results.py results/130-python-native/perf-cost/result.csv --output-dir results/130-python-native/plots

# NODEJS CONTAINER

# 110
rm -rf cache && python ./sebs.py experiment invoke perf-cost --config config/110.nodejs-container.json --output-dir results/110-nodejs-container
python sebs.py experiment process perf-cost --config config/110.nodejs-container.json --output-dir results/110-nodejs-container
python plot_results.py results/110-nodejs-container/perf-cost/result.csv --output-dir results/110-nodejs-container/plots

# 120
rm -rf cache && python ./sebs.py experiment invoke perf-cost --config config/120.nodejs-container.json --output-dir results/120-nodejs-container
python sebs.py experiment process perf-cost --config config/120.nodejs-container.json --output-dir results/120-nodejs-container
python plot_results.py results/120-nodejs-container/perf-cost/result.csv --output-dir results/120-nodejs-container/plots

# 130
rm -rf cache && python ./sebs.py experiment invoke perf-cost --config config/130.nodejs-container.json --output-dir results/130-nodejs-container
python sebs.py experiment process perf-cost --config config/130.nodejs-container.json --output-dir results/130-nodejs-container
python plot_results.py results/130-nodejs-container/perf-cost/result.csv --output-dir results/130-nodejs-container/plots

# NODEJS NATIVE

# 110
rm -rf cache && python ./sebs.py experiment invoke perf-cost --config config/110.nodejs-native.json --output-dir results/110-nodejs-native
python sebs.py experiment process perf-cost --config config/110.nodejs-native.json --output-dir results/110-nodejs-native
python plot_results.py results/110-nodejs-native/perf-cost/result.csv --output-dir results/110-nodejs-native/plots

# 120
rm -rf cache && python ./sebs.py experiment invoke perf-cost --config config/120.nodejs-native.json --output-dir results/120-nodejs-native
python sebs.py experiment process perf-cost --config config/120.nodejs-native.json --output-dir results/120-nodejs-native
python plot_results.py results/120-nodejs-native/perf-cost/result.csv --output-dir results/120-nodejs-native/plots

# 130
rm -rf cache && python ./sebs.py experiment invoke perf-cost --config config/130.nodejs-native.json --output-dir results/130-nodejs-native
python sebs.py experiment process perf-cost --config config/130.nodejs-native.json --output-dir results/130-nodejs-native
python plot_results.py results/130-nodejs-native/perf-cost/result.csv --output-dir results/130-nodejs-native/plots

# COMPARISON PLOTS
echo "Generating comparison plots..."
python plot_comparison.py results/*/perf-cost/result.csv --output-dir results/comparison_plots