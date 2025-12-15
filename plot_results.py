#!/usr/bin/env python3
"""
Plot results from SeBS perf-cost experiments.

Usage:
    python plot_results.py results/110-python-container/perf-cost/result.csv
    python plot_results.py results/110-python-container/perf-cost/result.csv --output-dir my_plots
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import os

def plot_perf_cost(csv_path, output_dir='plots'):
    """
    Generate plots from SeBS perf-cost experiment CSV results.
    
    Args:
        csv_path: Path to result.csv file
        output_dir: Directory to save plots (default: 'plots')
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Read data
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} invocations from {csv_path}")
    print(f"Experiment types: {df['type'].unique()}")
    print(f"Memory configurations: {df['memory'].unique()}")
    
    # Set style
    sns.set_style("whitegrid")
    sns.set_palette("husl")
    
    # 1. Execution time distribution
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df, x='type', y='exec_time', hue='type', legend=False)
    plt.title('Execution Time Distribution by Experiment Type', fontsize=14, fontweight='bold')
    plt.ylabel('Execution Time (μs)', fontsize=12)
    plt.xlabel('Experiment Type', fontsize=12)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/exec_time_boxplot.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved {output_dir}/exec_time_boxplot.png")
    plt.close()
    
    # 2. Memory usage distribution
    if df['mem_used'].notna().any():
        plt.figure(figsize=(12, 6))
        sns.violinplot(data=df, x='type', y='mem_used', hue='type', legend=False)
        plt.title('Memory Usage Distribution', fontsize=14, fontweight='bold')
        plt.ylabel('Memory Used (MB)', fontsize=12)
        plt.xlabel('Experiment Type', fontsize=12)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/memory_usage.png', dpi=300, bbox_inches='tight')
        print(f"✓ Saved {output_dir}/memory_usage.png")
        plt.close()
    else:
        print("⚠ No memory data available, skipping memory plot")
    
    # 3. End-to-end latency (client time)
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df, x='type', y='client_time', hue='type', legend=False)
    plt.title('End-to-End Latency (Client-side)', fontsize=14, fontweight='bold')
    plt.ylabel('Client Time (μs)', fontsize=12)
    plt.xlabel('Experiment Type', fontsize=12)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/client_latency.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved {output_dir}/client_latency.png")
    plt.close()
    
    # 4. Connection time overhead
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df, x='type', y='connection_time', hue='type', legend=False)
    plt.title('HTTP Connection Time Overhead', fontsize=14, fontweight='bold')
    plt.ylabel('Connection Time (s)', fontsize=12)
    plt.xlabel('Experiment Type', fontsize=12)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/connection_time.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved {output_dir}/connection_time.png")
    plt.close()
    
    # 5. Comparison: exec vs client time
    plt.figure(figsize=(14, 6))
    
    # Convert to milliseconds for better readability
    df_plot = df.copy()
    df_plot['exec_time_ms'] = df_plot['exec_time'] / 1000
    df_plot['client_time_ms'] = df_plot['client_time'] / 1000
    
    plt.subplot(1, 2, 1)
    sns.boxplot(data=df_plot, x='type', y='exec_time_ms', hue='type', legend=False)
    plt.title('Execution Time', fontsize=12, fontweight='bold')
    plt.ylabel('Time (ms)', fontsize=11)
    plt.xlabel('Experiment Type', fontsize=11)
    
    plt.subplot(1, 2, 2)
    sns.boxplot(data=df_plot, x='type', y='client_time_ms', hue='type', legend=False)
    plt.title('End-to-End Latency', fontsize=12, fontweight='bold')
    plt.ylabel('Time (ms)', fontsize=11)
    plt.xlabel('Experiment Type', fontsize=11)
    
    plt.suptitle('Execution Time vs End-to-End Latency', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/time_comparison.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved {output_dir}/time_comparison.png")
    plt.close()
    
    # 6. Line plot: Execution time over invocations
    for exp_type in df['type'].unique():
        df_type = df[df['type'] == exp_type].copy()
        df_type = df_type.reset_index(drop=True)
        df_type['invocation'] = df_type.index
        df_type['exec_time_ms'] = df_type['exec_time'] / 1000
        
        plt.figure(figsize=(12, 6))
        plt.plot(df_type['invocation'], df_type['exec_time_ms'], marker='o', markersize=3, linewidth=1.5, alpha=0.7)
        plt.title(f'Execution Time Over Invocations - {exp_type.upper()}', fontsize=14, fontweight='bold')
        plt.xlabel('Invocation Number', fontsize=12)
        plt.ylabel('Execution Time (ms)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/exec_time_line_{exp_type}.png', dpi=300, bbox_inches='tight')
        print(f"✓ Saved {output_dir}/exec_time_line_{exp_type}.png")
        plt.close()
    
    # 7. Line plot: Client time over invocations
    for exp_type in df['type'].unique():
        df_type = df[df['type'] == exp_type].copy()
        df_type = df_type.reset_index(drop=True)
        df_type['invocation'] = df_type.index
        df_type['client_time_ms'] = df_type['client_time'] / 1000
        
        plt.figure(figsize=(12, 6))
        plt.plot(df_type['invocation'], df_type['client_time_ms'], marker='o', markersize=3, linewidth=1.5, alpha=0.7, color='orange')
        plt.title(f'Client Latency Over Invocations - {exp_type.upper()}', fontsize=14, fontweight='bold')
        plt.xlabel('Invocation Number', fontsize=12)
        plt.ylabel('Client Time (ms)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/client_time_line_{exp_type}.png', dpi=300, bbox_inches='tight')
        print(f"✓ Saved {output_dir}/client_time_line_{exp_type}.png")
        plt.close()
    
    # 8. Line plot: Memory usage over invocations
    if df['mem_used'].notna().any():
        for exp_type in df['type'].unique():
            df_type = df[df['type'] == exp_type].copy()
            df_type = df_type.reset_index(drop=True)
            df_type['invocation'] = df_type.index
            
            if df_type['mem_used'].notna().any():
                plt.figure(figsize=(12, 6))
                plt.plot(df_type['invocation'], df_type['mem_used'], marker='o', markersize=3, linewidth=1.5, alpha=0.7, color='green')
                plt.title(f'Memory Usage Over Invocations - {exp_type.upper()}', fontsize=14, fontweight='bold')
                plt.xlabel('Invocation Number', fontsize=12)
                plt.ylabel('Memory Used (MB)', fontsize=12)
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.savefig(f'{output_dir}/memory_line_{exp_type}.png', dpi=300, bbox_inches='tight')
                print(f"✓ Saved {output_dir}/memory_line_{exp_type}.png")
                plt.close()
    
    # 9. Line plot: Connection time over invocations
    for exp_type in df['type'].unique():
        df_type = df[df['type'] == exp_type].copy()
        df_type = df_type.reset_index(drop=True)
        df_type['invocation'] = df_type.index
        
        plt.figure(figsize=(12, 6))
        plt.plot(df_type['invocation'], df_type['connection_time'], marker='o', markersize=3, linewidth=1.5, alpha=0.7, color='red')
        plt.title(f'Connection Time Over Invocations - {exp_type.upper()}', fontsize=14, fontweight='bold')
        plt.xlabel('Invocation Number', fontsize=12)
        plt.ylabel('Connection Time (s)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/connection_time_line_{exp_type}.png', dpi=300, bbox_inches='tight')
        print(f"✓ Saved {output_dir}/connection_time_line_{exp_type}.png")
        plt.close()
    
    # Print summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    
    summary_cols = ['exec_time', 'client_time', 'connection_time']
    if df['mem_used'].notna().any():
        summary_cols.append('mem_used')
    
    for exp_type in df['type'].unique():
        print(f"\n{exp_type.upper()} Experiment:")
        print("-" * 80)
        subset = df[df['type'] == exp_type][summary_cols]
        print(subset.describe().round(2))
    
    print("\n" + "="*80)
    print(f"All plots saved to: {os.path.abspath(output_dir)}/")
    print("="*80)

def main():
    parser = argparse.ArgumentParser(
        description='Plot SeBS perf-cost experiment results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python plot_results.py results/110-python-container/perf-cost/result.csv
  python plot_results.py results/*/perf-cost/result.csv --output-dir all_plots
        """
    )
    parser.add_argument('csv_file', help='Path to result.csv file')
    parser.add_argument('--output-dir', '-o', default='plots', 
                       help='Output directory for plots (default: plots)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv_file):
        print(f"Error: CSV file not found: {args.csv_file}")
        return 1
    
    plot_perf_cost(args.csv_file, args.output_dir)
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
