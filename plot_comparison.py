#!/usr/bin/env python3
"""
Compare results from multiple SeBS experiments across all benchmarks.

Usage:
    python plot_comparison.py results/*/perf-cost/result.csv
    python plot_comparison.py results/*/perf-cost/result.csv --output-dir comparison_plots
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import os
import glob
from pathlib import Path

def extract_experiment_info(csv_path):
    """Extract benchmark name, language, and deployment type from path."""
    parts = Path(csv_path).parts
    # e.g., results/110-python-container/perf-cost/result.csv
    experiment_name = parts[-3]  # e.g., "110-python-container"
    
    # Parse the experiment name
    benchmark = experiment_name.split('-')[0]  # e.g., "110"
    remainder = '-'.join(experiment_name.split('-')[1:])  # e.g., "python-container"
    
    if 'python' in remainder:
        language = 'python'
        deployment = 'container' if 'container' in remainder else 'native'
    elif 'nodejs' in remainder:
        language = 'nodejs'
        deployment = 'container' if 'container' in remainder else 'native'
    else:
        language = 'unknown'
        deployment = 'unknown'
    
    return benchmark, language, deployment

def load_all_experiments(csv_patterns):
    """Load all CSV files matching the patterns."""
    all_data = []
    
    # Expand glob patterns
    csv_files = []
    for pattern in csv_patterns:
        csv_files.extend(glob.glob(pattern))
    
    if not csv_files:
        print("Error: No CSV files found matching the patterns")
        return None
    
    print(f"Found {len(csv_files)} CSV files")
    
    for csv_path in csv_files:
        try:
            df = pd.read_csv(csv_path)
            benchmark, language, deployment = extract_experiment_info(csv_path)
            
            df['benchmark'] = benchmark
            df['language'] = language
            df['deployment'] = deployment
            df['experiment'] = f"{benchmark}-{language}-{deployment}"
            
            all_data.append(df)
            print(f"  ✓ Loaded {csv_path}: {len(df)} rows")
        except Exception as e:
            print(f"  ✗ Error loading {csv_path}: {e}")
    
    if not all_data:
        print("Error: No data loaded successfully")
        return None
    
    combined = pd.concat(all_data, ignore_index=True)
    print(f"\nTotal experiments: {combined['experiment'].nunique()}")
    print(f"Total invocations: {len(combined)}")
    
    return combined

def plot_comparisons(df, output_dir='comparison_plots'):
    """Generate comparison plots across all experiments."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Set style
    sns.set_style("whitegrid")
    sns.set_palette("husl")
    
    # Convert times to milliseconds for readability
    df['exec_time_ms'] = df['exec_time'] / 1000
    df['client_time_ms'] = df['client_time'] / 1000
    
    # 1. Mean execution time by benchmark - per experiment type
    for exp_type in df['type'].unique():
        plt.figure(figsize=(14, 7))
        type_data = df[df['type'] == exp_type]
        mean_exec = type_data.groupby(['benchmark', 'language', 'deployment'])['exec_time_ms'].mean().reset_index()
        
        for lang in sorted(mean_exec['language'].unique()):
            for deploy in sorted(mean_exec['deployment'].unique()):
                subset = mean_exec[(mean_exec['language'] == lang) & (mean_exec['deployment'] == deploy)]
                if not subset.empty:
                    label = f"{lang}-{deploy}"
                    plt.plot(subset['benchmark'], subset['exec_time_ms'], 
                            marker='o', label=label, linewidth=2, markersize=8)
        
        plt.title(f'Mean Execution Time by Benchmark - {exp_type.upper()}', fontsize=16, fontweight='bold')
        plt.xlabel('Benchmark', fontsize=13)
        plt.ylabel('Mean Execution Time (ms)', fontsize=13)
        plt.legend(fontsize=11)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/exec_time_by_benchmark_{exp_type}.png', dpi=300, bbox_inches='tight')
        print(f"✓ Saved {output_dir}/exec_time_by_benchmark_{exp_type}.png")
        plt.close()
    
    # 2. Mean execution time by language - per experiment type
    for exp_type in df['type'].unique():
        plt.figure(figsize=(14, 7))
        type_data = df[df['type'] == exp_type]
        mean_exec_lang = type_data.groupby(['benchmark', 'language', 'deployment'])['exec_time_ms'].mean().reset_index()
        
        for benchmark in sorted(mean_exec_lang['benchmark'].unique()):
            for deploy in sorted(mean_exec_lang['deployment'].unique()):
                subset = mean_exec_lang[(mean_exec_lang['benchmark'] == benchmark) & 
                                       (mean_exec_lang['deployment'] == deploy)]
                if not subset.empty:
                    label = f"{benchmark}-{deploy}"
                    plt.plot(subset['language'], subset['exec_time_ms'], 
                            marker='o', label=label, linewidth=2, markersize=8)
        
        plt.title(f'Mean Execution Time: Python vs Node.js - {exp_type.upper()}', fontsize=16, fontweight='bold')
        plt.xlabel('Language', fontsize=13)
        plt.ylabel('Mean Execution Time (ms)', fontsize=13)
        plt.legend(fontsize=10, ncol=2)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/exec_time_by_language_{exp_type}.png', dpi=300, bbox_inches='tight')
        print(f"✓ Saved {output_dir}/exec_time_by_language_{exp_type}.png")
        plt.close()
    
    # 3. Container vs Native deployment comparison - per experiment type
    for exp_type in df['type'].unique():
        plt.figure(figsize=(14, 7))
        type_data = df[df['type'] == exp_type]
        mean_deploy = type_data.groupby(['benchmark', 'language', 'deployment'])['exec_time_ms'].mean().reset_index()
        
        benchmarks = sorted(mean_deploy['benchmark'].unique())
        x = range(len(benchmarks))
        width = 0.2
        
        languages = sorted(mean_deploy['language'].unique())
        for i, lang in enumerate(languages):
            container = mean_deploy[(mean_deploy['language'] == lang) & 
                                   (mean_deploy['deployment'] == 'container')]
            native = mean_deploy[(mean_deploy['language'] == lang) & 
                                (mean_deploy['deployment'] == 'native')]
            
            container_means = [container[container['benchmark'] == b]['exec_time_ms'].mean() 
                              if not container[container['benchmark'] == b].empty else 0 
                              for b in benchmarks]
            native_means = [native[native['benchmark'] == b]['exec_time_ms'].mean() 
                           if not native[native['benchmark'] == b].empty else 0 
                           for b in benchmarks]
            
            offset = i * width * 2
            plt.plot([xi + offset for xi in x], container_means, marker='o', 
                    label=f'{lang}-container', linewidth=2, markersize=8)
            plt.plot([xi + offset for xi in x], native_means, marker='s', 
                    label=f'{lang}-native', linewidth=2, markersize=8, linestyle='--')
        
        plt.title(f'Container vs Native Deployment - {exp_type.upper()}', fontsize=16, fontweight='bold')
        plt.xlabel('Benchmark', fontsize=13)
        plt.ylabel('Mean Execution Time (ms)', fontsize=13)
        plt.xticks([xi + width for xi in x], benchmarks)
        plt.legend(fontsize=10, ncol=2)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/container_vs_native_{exp_type}.png', dpi=300, bbox_inches='tight')
        print(f"✓ Saved {output_dir}/container_vs_native_{exp_type}.png")
        plt.close()
    
    # 4. Mean client latency comparison - per experiment type
    for exp_type in df['type'].unique():
        plt.figure(figsize=(14, 7))
        type_data = df[df['type'] == exp_type]
        mean_client = type_data.groupby(['benchmark', 'language', 'deployment'])['client_time_ms'].mean().reset_index()
        
        for lang in sorted(mean_client['language'].unique()):
            for deploy in sorted(mean_client['deployment'].unique()):
                subset = mean_client[(mean_client['language'] == lang) & (mean_client['deployment'] == deploy)]
                if not subset.empty:
                    label = f"{lang}-{deploy}"
                    plt.plot(subset['benchmark'], subset['client_time_ms'], 
                            marker='o', label=label, linewidth=2, markersize=8)
        
        plt.title(f'Mean Client Latency by Benchmark - {exp_type.upper()}', fontsize=16, fontweight='bold')
        plt.xlabel('Benchmark', fontsize=13)
        plt.ylabel('Mean Client Time (ms)', fontsize=13)
        plt.legend(fontsize=11)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/client_time_by_benchmark_{exp_type}.png', dpi=300, bbox_inches='tight')
        print(f"✓ Saved {output_dir}/client_time_by_benchmark_{exp_type}.png")
        plt.close()
    
    # 5. Memory usage comparison (if available) - per experiment type
    if df['mem_used'].notna().any():
        for exp_type in df['type'].unique():
            plt.figure(figsize=(14, 7))
            type_data = df[df['type'] == exp_type]
            mean_mem = type_data.groupby(['benchmark', 'language', 'deployment'])['mem_used'].mean().reset_index()
            
            for lang in sorted(mean_mem['language'].unique()):
                for deploy in sorted(mean_mem['deployment'].unique()):
                    subset = mean_mem[(mean_mem['language'] == lang) & (mean_mem['deployment'] == deploy)]
                    if not subset.empty and subset['mem_used'].notna().any():
                        label = f"{lang}-{deploy}"
                        plt.plot(subset['benchmark'], subset['mem_used'], 
                                marker='o', label=label, linewidth=2, markersize=8)
            
            plt.title(f'Mean Memory Usage by Benchmark - {exp_type.upper()}', fontsize=16, fontweight='bold')
            plt.xlabel('Benchmark', fontsize=13)
            plt.ylabel('Mean Memory Used (MB)', fontsize=13)
            plt.legend(fontsize=11)
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(f'{output_dir}/memory_by_benchmark_{exp_type}.png', dpi=300, bbox_inches='tight')
            print(f"✓ Saved {output_dir}/memory_by_benchmark_{exp_type}.png")
            plt.close()
    
    # 6. Connection time comparison - per experiment type
    for exp_type in df['type'].unique():
        plt.figure(figsize=(14, 7))
        type_data = df[df['type'] == exp_type]
        mean_conn = type_data.groupby(['benchmark', 'language', 'deployment'])['connection_time'].mean().reset_index()
        
        for lang in sorted(mean_conn['language'].unique()):
            for deploy in sorted(mean_conn['deployment'].unique()):
                subset = mean_conn[(mean_conn['language'] == lang) & (mean_conn['deployment'] == deploy)]
                if not subset.empty:
                    label = f"{lang}-{deploy}"
                    plt.plot(subset['benchmark'], subset['connection_time'], 
                            marker='o', label=label, linewidth=2, markersize=8)
        
        plt.title(f'Mean Connection Time by Benchmark - {exp_type.upper()}', fontsize=16, fontweight='bold')
        plt.xlabel('Benchmark', fontsize=13)
        plt.ylabel('Mean Connection Time (s)', fontsize=13)
        plt.legend(fontsize=11)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/connection_time_by_benchmark_{exp_type}.png', dpi=300, bbox_inches='tight')
        print(f"✓ Saved {output_dir}/connection_time_by_benchmark_{exp_type}.png")
        plt.close()
    
    # 7. Detailed comparison: all experiments side by side - per experiment type
    for exp_type in df['type'].unique():
        plt.figure(figsize=(16, 8))
        type_data = df[df['type'] == exp_type]
        experiments = sorted(type_data['experiment'].unique())
        
        means = []
        for exp in experiments:
            exp_data = type_data[type_data['experiment'] == exp]
            means.append(exp_data['exec_time_ms'].mean() if not exp_data.empty else 0)
        
        plt.bar(range(len(experiments)), means, alpha=0.8)
        
        plt.title(f'Execution Time: All Experiments - {exp_type.upper()}', fontsize=16, fontweight='bold')
        plt.xlabel('Experiment', fontsize=13)
        plt.ylabel('Mean Execution Time (ms)', fontsize=13)
        plt.xticks(range(len(experiments)), experiments, rotation=45, ha='right')
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig(f'{output_dir}/all_experiments_comparison_{exp_type}.png', dpi=300, bbox_inches='tight')
        print(f"✓ Saved {output_dir}/all_experiments_comparison_{exp_type}.png")
        plt.close()
    
    # 8. Percentile comparison (P50, P95, P99) - per experiment type
    for exp_type in df['type'].unique():
        plt.figure(figsize=(16, 8))
        
        type_data = df[df['type'] == exp_type]
        experiments = sorted(type_data['experiment'].unique())
        
        percentiles_data = []
        for exp in experiments:
            exp_data = type_data[type_data['experiment'] == exp]['exec_time_ms']
            if not exp_data.empty:
                percentiles_data.append({
                    'experiment': exp,
                    'p50': exp_data.quantile(0.50),
                    'p95': exp_data.quantile(0.95),
                    'p99': exp_data.quantile(0.99)
                })
        
        perc_df = pd.DataFrame(percentiles_data)
        
        plt.plot(range(len(perc_df)), perc_df['p50'], marker='o', 
                label='P50', linewidth=2, markersize=6)
        plt.plot(range(len(perc_df)), perc_df['p95'], marker='s', 
                label='P95', linewidth=2, markersize=6, linestyle='--')
        plt.plot(range(len(perc_df)), perc_df['p99'], marker='^', 
                label='P99', linewidth=2, markersize=6, linestyle=':')
        
        plt.title(f'Execution Time Percentiles (P50, P95, P99) - {exp_type.upper()}', fontsize=16, fontweight='bold')
        plt.xlabel('Experiment', fontsize=13)
        plt.ylabel('Execution Time (ms)', fontsize=13)
        plt.xticks(range(len(perc_df)), perc_df['experiment'], rotation=45, ha='right')
        plt.legend(fontsize=11)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/percentiles_comparison_{exp_type}.png', dpi=300, bbox_inches='tight')
        print(f"✓ Saved {output_dir}/percentiles_comparison_{exp_type}.png")
        plt.close()
    
    # Print summary statistics
    print("\n" + "="*100)
    print("COMPARISON SUMMARY STATISTICS")
    print("="*100)
    
    for benchmark in sorted(df['benchmark'].unique()):
        print(f"\n{'='*100}")
        print(f"BENCHMARK {benchmark}")
        print(f"{'='*100}")
        
        bench_data = df[df['benchmark'] == benchmark]
        
        for exp_type in sorted(bench_data['type'].unique()):
            print(f"\n  {exp_type.upper()}:")
            print(f"  {'-'*96}")
            
            type_data = bench_data[bench_data['type'] == exp_type]
            
            for lang in sorted(type_data['language'].unique()):
                for deploy in sorted(type_data['deployment'].unique()):
                    subset = type_data[(type_data['language'] == lang) & 
                                      (type_data['deployment'] == deploy)]
                    if not subset.empty:
                        print(f"    {lang}-{deploy}:")
                        print(f"      Exec time: {subset['exec_time_ms'].mean():.2f} ms "
                              f"(±{subset['exec_time_ms'].std():.2f})")
                        print(f"      Client time: {subset['client_time_ms'].mean():.2f} ms "
                              f"(±{subset['client_time_ms'].std():.2f})")
                        if subset['mem_used'].notna().any():
                            print(f"      Memory: {subset['mem_used'].mean():.2f} MB "
                                  f"(±{subset['mem_used'].std():.2f})")
    
    print("\n" + "="*100)
    print(f"All comparison plots saved to: {os.path.abspath(output_dir)}/")
    print("="*100)

def main():
    parser = argparse.ArgumentParser(
        description='Compare SeBS perf-cost results across multiple experiments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python plot_comparison.py results/*/perf-cost/result.csv
  python plot_comparison.py results/110-*/perf-cost/result.csv --output-dir plots/comparison
  python plot_comparison.py results/*-python-*/perf-cost/result.csv
        """
    )
    parser.add_argument('csv_patterns', nargs='+', 
                       help='Glob patterns for CSV files to compare')
    parser.add_argument('--output-dir', '-o', default='comparison_plots', 
                       help='Output directory for plots (default: comparison_plots)')
    
    args = parser.parse_args()
    
    df = load_all_experiments(args.csv_patterns)
    if df is None:
        return 1
    
    plot_comparisons(df, args.output_dir)
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
