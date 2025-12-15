#!/bin/bash

# Run all benchmarks with container deployments for both Python and Node.js
# This script runs experiments for all available benchmarks, then cleans up resources

# Don't use set -e to allow cleanup to continue even if some commands fail

# Array of benchmark numbers
BENCHMARKS=(110 120 130 210 220 311 411 501 502 503 504)

# Array of languages
LANGUAGES=(python nodejs)

# Output directory
OUTPUT_DIR="results"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo "Starting serverless benchmark experiments"
echo "=========================================="
echo ""

# Outer loop: iterate over languages
for LANG in "${LANGUAGES[@]}"; do
    echo "=========================================="
    echo "Running experiments for language: $LANG"
    echo "=========================================="
    echo ""
    
    # Inner loop: iterate over benchmarks
    for BENCH in "${BENCHMARKS[@]}"; do
        CONFIG_NAME="${BENCH}.${LANG}-container"
        CONFIG_FILE="config/${CONFIG_NAME}.json"
        
        # Check if config file exists
        if [ ! -f "$CONFIG_FILE" ]; then
            echo "⚠️  Warning: Config file $CONFIG_FILE not found, skipping benchmark $BENCH for $LANG"
            echo ""
            continue
        fi
        
        echo "--------------------------------------"
        echo "Running benchmark: $CONFIG_NAME"
        echo "--------------------------------------"
        
        # Set experiment-specific output directory
        EXPERIMENT_OUTPUT_DIR="${OUTPUT_DIR}/${BENCH}-${LANG}-container"
        
        # Invoke experiment
        echo "→ Invoking experiment..."
        if ! python3 sebs.py experiment invoke perf-cost \
            --config "$CONFIG_FILE" \
            --output-dir "$EXPERIMENT_OUTPUT_DIR"; then
            echo "⚠️  Error invoking experiment, skipping to next"
            continue
        fi
        
        # Process results
        echo "→ Processing results..."
        if ! python3 sebs.py experiment process perf-cost \
            --config "$CONFIG_FILE" \
            --output-dir "$EXPERIMENT_OUTPUT_DIR"; then
            echo "⚠️  Error processing results, skipping to next"
            continue
        fi
        
        # Generate plots
        RESULT_DIR="${EXPERIMENT_OUTPUT_DIR}"
        if [ -d "$RESULT_DIR" ]; then
            echo "→ Generating plots..."
            python3 plot_results.py "$RESULT_DIR"
        else
            echo "⚠️  Warning: Result directory $RESULT_DIR not found, skipping plots"
        fi
        
        # Cleanup worker and container after this experiment
        echo "→ Cleaning up resources..."
        WORKER_NAME="sebs-${BENCH}-${LANG}-container"
        
        # Delete container application if it exists
        CONTAINER_ID=$(npx wrangler containers list 2>&1 | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for c in data:
        if c.get('name') == '${WORKER_NAME}-containerworker':
            print(c['id'])
            break
except:
    pass
" 2>/dev/null || true)
        
        if [ -n "$CONTAINER_ID" ]; then
            echo "  Deleting container: $CONTAINER_ID"
            npx wrangler containers delete "$CONTAINER_ID" > /dev/null 2>&1 || true
        fi
        
        # Delete worker
        echo "  Deleting worker: $WORKER_NAME"
        npx wrangler delete --name "$WORKER_NAME" --force > /dev/null 2>&1 || true
        
        echo "✓ Completed benchmark: $CONFIG_NAME"
        echo ""
    done
    
    echo "✓ All experiments completed for $LANG"
    echo ""
done

# Generate comparison plots across all experiments
echo "=========================================="
echo "Generating comparison plots"
echo "=========================================="

if [ -d "$OUTPUT_DIR" ]; then
    python3 plot_comparison.py "$OUTPUT_DIR"
    echo "✓ Comparison plots generated"
else
    echo "⚠️  Warning: Output directory $OUTPUT_DIR not found, skipping comparison plots"
fi

echo ""
echo "=========================================="
echo "All experiments completed!"
echo "=========================================="
