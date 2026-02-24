#!/usr/bin/env python3
"""
Comprehensive statistical analysis script for Master's dissertation:
Co-occurrence of Code Smells and Community Smells in Java code samples

Dataset 1 (Cross-sectional): 377 repositories
Dataset 2 (Temporal): 208 repositories, 800 snapshots, 5 years
"""

import csv
import os
import sys
from collections import defaultdict
from pathlib import Path
from math import isnan, sqrt
import warnings

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import seaborn as sns
from scipy import stats
from scipy.stats import spearmanr, mannwhitneyu, kruskal, friedmanchisquare, chi2_contingency
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

warnings.filterwarnings('ignore')

# Configuration
OUTPUT_DIR = Path('/sessions/sleepy-loving-ride/analysis')
FIGURES_DIR = OUTPUT_DIR / 'figures'
DATA_DIR = Path('/sessions/sleepy-loving-ride/mnt/mestrado-pipeline/data/consolidated')

# Create directories
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Style configuration
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 10
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['ps.fonttype'] = 42

# Color palette
COLORS = {
    'primary': '#1f77b4',
    'secondary': '#ff7f0e',
    'success': '#2ca02c',
    'danger': '#d62728',
    'warning': '#ff9896',
    'info': '#9467bd',
    'light': '#c7c7c7',
    'dark': '#2c3e50'
}

def read_csv_to_dicts(filepath):
    """Read CSV file and return list of dicts."""
    data = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return []
            for row in reader:
                data.append(row)
        print(f"Loaded {len(data)} rows from {filepath}")
        return data
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return []

def safe_float(val, default=np.nan):
    """Safely convert value to float."""
    if val is None or val == '' or val == 'nan' or val == 'NaN':
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def safe_int(val, default=None):
    """Safely convert value to int."""
    if val is None or val == '':
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default

def get_numeric_values(data, column_name, skip_nan=True):
    """Extract numeric values from a column, optionally skipping NaNs."""
    values = []
    for row in data:
        val = safe_float(row.get(column_name))
        if skip_nan and isnan(val):
            continue
        values.append(val)
    return values

def get_row_numeric_values(row, columns, skip_nan=True):
    """Extract numeric values from specific columns in a row."""
    values = []
    for col in columns:
        val = safe_float(row.get(col))
        if skip_nan and isnan(val):
            return None
        values.append(val)
    return values

def descriptive_stats(values, label=""):
    """Calculate descriptive statistics."""
    values = [v for v in values if not isnan(v)]
    if not values:
        return None

    stats_dict = {
        'n': len(values),
        'mean': np.mean(values),
        'median': np.median(values),
        'std': np.std(values),
        'min': np.min(values),
        'max': np.max(values),
        'q25': np.percentile(values, 25),
        'q75': np.percentile(values, 75),
    }
    return stats_dict

def print_descriptive_stats(title, stats_dict):
    """Pretty print descriptive statistics."""
    if stats_dict is None:
        print(f"{title}: No data")
        return
    print(f"\n{title}")
    print(f"  N={stats_dict['n']}")
    print(f"  Mean={stats_dict['mean']:.2f}, Median={stats_dict['median']:.2f}, Std={stats_dict['std']:.2f}")
    print(f"  Min={stats_dict['min']:.2f}, Max={stats_dict['max']:.2f}")
    print(f"  Q25={stats_dict['q25']:.2f}, Q75={stats_dict['q75']:.2f}")

def rank_biserial(U, n1, n2):
    """Calculate rank-biserial correlation."""
    if n1 == 0 or n2 == 0:
        return np.nan
    return 1 - (2 * U) / (n1 * n2)

def save_figure(fig, name):
    """Save figure in both PDF and PNG formats."""
    pdf_path = FIGURES_DIR / f"{name}.pdf"
    png_path = FIGURES_DIR / f"{name}.png"
    fig.savefig(pdf_path, bbox_inches='tight', format='pdf')
    fig.savefig(png_path, bbox_inches='tight', format='png', dpi=300)
    print(f"Saved {pdf_path} and {png_path}")
    plt.close(fig)

def write_csv_table(filename, headers, rows):
    """Write data to CSV file."""
    filepath = OUTPUT_DIR / filename
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Saved {filepath}")

# ============================================================================
# PART A: CROSS-SECTIONAL ANALYSIS
# ============================================================================

def analyze_cross_sectional(data):
    """Perform cross-sectional analysis on 377 repositories."""
    print("\n" + "="*80)
    print("PART A: CROSS-SECTIONAL ANALYSIS (N=377)")
    print("="*80)

    # 1. DESCRIPTIVE STATISTICS FOR TECHNICAL METRICS
    print("\n--- 1. DESCRIPTIVE STATISTICS FOR TECHNICAL METRICS ---")

    technical_columns = [
        'num_classes', 'num_methods', 'total_LOC', 'mean_WMC', 'mean_CC', 'max_CC', 'smell_density'
    ]

    tech_stats = {}
    for col in technical_columns:
        values = get_numeric_values(data, col)
        stats_obj = descriptive_stats(values)
        tech_stats[col] = stats_obj
        print_descriptive_stats(f"  {col}", stats_obj)

    # 2. CODE SMELL DISTRIBUTION
    print("\n--- 2. CODE SMELL DISTRIBUTION ---")

    # Count total code smells by type
    smell_types = defaultdict(int)
    total_code_smells = get_numeric_values(data, 'total_code_smells')
    total_design_smells = get_numeric_values(data, 'total_design_smells')
    total_impl_smells = get_numeric_values(data, 'total_impl_smells')

    stats_obj = descriptive_stats(total_code_smells)
    print_descriptive_stats("  Total Code Smells", stats_obj)

    stats_obj = descriptive_stats(total_design_smells)
    print_descriptive_stats("  Total Design Smells", stats_obj)

    stats_obj = descriptive_stats(total_impl_smells)
    print_descriptive_stats("  Total Implementation Smells", stats_obj)

    # Get top 10 smell types
    smell_columns = [col for col in data[0].keys() if col not in [
        'repo_id', 'repository', 'num_classes', 'num_methods', 'total_LOC',
        'mean_WMC', 'mean_CC', 'max_CC', 'smell_density', 'v', 'CommitCount',
        'DaysActive', 'AuthorCount', 'TimezoneCount', 'NumberPRs', 'NumberIssues',
        'BusFactorNumber', 'lone_wolf', 'radio_silence', 'org_silo',
        'total_code_smells', 'total_design_smells', 'total_impl_smells',
        'commitCentrality_Community Count', 'commitCentrality_Density'
    ]]

    for smell_col in smell_columns:
        count = sum(1 for row in data if safe_float(row.get(smell_col, 0)) > 0)
        if count > 0:
            smell_types[smell_col] = count

    # Sort and get top 10
    top_10_smells = sorted(smell_types.items(), key=lambda x: x[1], reverse=True)[:10]
    print("\n  Top 10 Code Smell Types:")
    for smell, count in top_10_smells:
        print(f"    {smell}: {count} repos")

    # Generate fig_top10_smells.pdf
    fig, ax = plt.subplots(figsize=(10, 6))
    smell_names = [s[0] for s in top_10_smells]
    smell_counts = [s[1] for s in top_10_smells]

    bars = ax.barh(smell_names, smell_counts, color=COLORS['primary'])
    ax.set_xlabel('Número de Repositórios', fontsize=11, weight='bold')
    ax.set_ylabel('Tipo de Code Smell', fontsize=11, weight='bold')
    ax.set_title('Top 10 Code Smells por Frequência', fontsize=12, weight='bold')
    ax.invert_yaxis()

    for i, (bar, count) in enumerate(zip(bars, smell_counts)):
        ax.text(count, i, f' {count}', va='center', fontsize=9)

    ax.grid(axis='x', alpha=0.3)
    save_figure(fig, 'fig_top10_smells')

    # 3. SOCIAL METRICS DESCRIPTIVES & COMMUNITY SMELLS
    print("\n--- 3. SOCIAL METRICS DESCRIPTIVES & COMMUNITY SMELLS ---")

    social_columns = [
        'CommitCount', 'DaysActive', 'AuthorCount', 'TimezoneCount', 'NumberPRs', 'NumberIssues'
    ]

    social_stats = {}
    for col in social_columns:
        values = get_numeric_values(data, col)
        stats_obj = descriptive_stats(values)
        social_stats[col] = stats_obj
        print_descriptive_stats(f"  {col}", stats_obj)

    # Community smells prevalence
    community_smells = ['lone_wolf', 'radio_silence', 'org_silo']
    print("\n  Community Smell Prevalence:")

    community_counts = {}
    for smell in community_smells:
        count = sum(1 for row in data if safe_int(row.get(smell, 0)) == 1)
        pct = 100 * count / len(data)
        community_counts[smell] = (count, pct)
        print(f"    {smell}: {count} repos ({pct:.1f}%)")

    # Generate fig_community_smells.pdf
    fig, ax = plt.subplots(figsize=(8, 5))
    smell_names = ['Lone Wolf', 'Radio Silence', 'Org Silo']
    smell_pcts = [community_counts[s][1] for s in community_smells]

    bars = ax.bar(smell_names, smell_pcts, color=[COLORS['danger'], COLORS['warning'], COLORS['info']])
    ax.set_ylabel('Prevalência (%)', fontsize=11, weight='bold')
    ax.set_title('Prevalência de Community Smells (N=377)', fontsize=12, weight='bold')
    ax.set_ylim(0, max(smell_pcts) * 1.15)

    for bar, pct in zip(bars, smell_pcts):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{pct:.1f}%', ha='center', va='bottom', fontsize=10, weight='bold')

    ax.grid(axis='y', alpha=0.3)
    save_figure(fig, 'fig_community_smells')

    # 4. COOCCURRENCE HEATMAP
    print("\n--- 4. COOCCURRENCE HEATMAP ---")

    # Create binary matrix for community smells and code smell types
    cooccurrence_matrix = defaultdict(lambda: defaultdict(int))

    for row in data:
        for smell in community_smells:
            if safe_int(row.get(smell, 0)) == 1:
                for code_smell_type in ['design', 'impl', 'total']:
                    # Check if this type of smell exists
                    if code_smell_type == 'design':
                        val = safe_float(row.get('total_design_smells'))
                    elif code_smell_type == 'impl':
                        val = safe_float(row.get('total_impl_smells'))
                    else:
                        val = safe_float(row.get('total_code_smells'))

                    if not isnan(val) and val > 0:
                        cooccurrence_matrix[smell][code_smell_type] += 1

    # Create figure
    fig, ax = plt.subplots(figsize=(8, 5))

    smell_labels = ['Lone Wolf', 'Radio Silence', 'Org Silo']
    code_smell_labels = ['Design Smells', 'Implementation Smells', 'Total Code Smells']

    matrix = np.zeros((3, 3))
    for i, smell in enumerate(community_smells):
        for j, code_type in enumerate(['design', 'impl', 'total']):
            matrix[i, j] = cooccurrence_matrix[smell][code_type]

    im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto')
    ax.set_xticks(np.arange(3))
    ax.set_yticks(np.arange(3))
    ax.set_xticklabels(code_smell_labels, rotation=45, ha='right')
    ax.set_yticklabels(smell_labels)
    ax.set_title('Coocorrência entre Community e Code Smells', fontsize=12, weight='bold')

    # Add text annotations
    for i in range(3):
        for j in range(3):
            text = ax.text(j, i, int(matrix[i, j]),
                          ha="center", va="center", color="black", fontsize=11, weight='bold')

    plt.colorbar(im, ax=ax, label='Número de Repositórios')
    save_figure(fig, 'fig_cooccurrence')

    # 5. SPEARMAN CORRELATIONS
    print("\n--- 5. SPEARMAN CORRELATIONS ---")

    technical_corr_cols = [
        'total_code_smells', 'total_design_smells', 'total_impl_smells',
        'Magic_Number', 'Long_Parameter_List', 'Complex_Method', 'Long_Method',
        'Unutilized_Abstraction', 'Deficient_Encapsulation', 'God_Class'
    ]

    social_corr_cols = [
        'CommitCount', 'AuthorCount', 'DaysActive', 'TimezoneCount', 'BusFactorNumber',
        'lone_wolf', 'radio_silence', 'org_silo', 'NumberPRs', 'NumberIssues',
        'commitCentrality_Community Count', 'commitCentrality_Density'
    ]

    correlations = []
    significant_correlations = []

    for tech_col in technical_corr_cols:
        for social_col in social_corr_cols:
            # Get valid pairs
            pairs = []
            for row in data:
                tech_val = safe_float(row.get(tech_col))
                social_val = safe_float(row.get(social_col))
                if not isnan(tech_val) and not isnan(social_val):
                    pairs.append((tech_val, social_val))

            if len(pairs) < 3:
                continue

            x, y = zip(*pairs)
            rho, p_val = spearmanr(x, y)
            n = len(pairs)

            sig_marker = '***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else ''

            corr_record = {
                'tech_col': tech_col,
                'social_col': social_col,
                'rho': rho,
                'p_val': p_val,
                'n': n,
                'sig': sig_marker
            }
            correlations.append(corr_record)

            if p_val < 0.05:
                significant_correlations.append(corr_record)
                print(f"  {tech_col} x {social_col}: rho={rho:.3f}, p={p_val:.4f}{sig_marker}, N={n}")

    # Write correlations to CSV
    headers = ['Technical Variable', 'Social Variable', 'Rho', 'P-value', 'Significance', 'N']
    rows = []
    for corr in significant_correlations:
        rows.append([
            corr['tech_col'],
            corr['social_col'],
            f"{corr['rho']:.4f}",
            f"{corr['p_val']:.6f}",
            corr['sig'],
            corr['n']
        ])
    write_csv_table('spearman_correlations_significant.csv', headers, rows)

    # Generate heatmap for significant correlations
    if significant_correlations:
        # Create a subset matrix for heatmap
        unique_techs = sorted(list(set(c['tech_col'] for c in significant_correlations)))
        unique_socials = sorted(list(set(c['social_col'] for c in significant_correlations)))

        heatmap_matrix = np.zeros((len(unique_techs), len(unique_socials)))
        significance_matrix = np.empty((len(unique_techs), len(unique_socials)), dtype=object)

        for corr in significant_correlations:
            i = unique_techs.index(corr['tech_col'])
            j = unique_socials.index(corr['social_col'])
            heatmap_matrix[i, j] = corr['rho']
            significance_matrix[i, j] = corr['sig']

        fig, ax = plt.subplots(figsize=(14, 8))
        im = ax.imshow(heatmap_matrix, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)

        ax.set_xticks(np.arange(len(unique_socials)))
        ax.set_yticks(np.arange(len(unique_techs)))
        ax.set_xticklabels(unique_socials, rotation=45, ha='right', fontsize=9)
        ax.set_yticklabels(unique_techs, fontsize=9)

        # Add text annotations
        for i in range(len(unique_techs)):
            for j in range(len(unique_socials)):
                if heatmap_matrix[i, j] != 0:
                    sig = significance_matrix[i, j]
                    text = f"{heatmap_matrix[i, j]:.2f}{sig}"
                    ax.text(j, i, text, ha="center", va="center",
                           color="white" if abs(heatmap_matrix[i, j]) > 0.5 else "black",
                           fontsize=8, weight='bold')

        ax.set_title('Correlações de Spearman (Significantes, p<0.05)', fontsize=12, weight='bold')
        plt.colorbar(im, ax=ax, label='Rho')
        save_figure(fig, 'fig_heatmap_spearman')

    # Generate scatter plot: BusFactor vs Code Smells
    print("\n  Generating BusFactor vs Code Smells scatter plot...")
    pairs = []
    for row in data:
        bf = safe_float(row.get('BusFactorNumber'))
        smells = safe_float(row.get('total_code_smells'))
        if not isnan(bf) and not isnan(smells):
            pairs.append((bf, smells))

    if len(pairs) > 2:
        x, y = zip(*pairs)
        rho, p_val = spearmanr(x, y)

        fig, ax = plt.subplots(figsize=(9, 6))
        ax.scatter(x, y, alpha=0.5, color=COLORS['primary'], edgecolors='black', linewidth=0.5)

        # Add regression line
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(x), max(x), 100)
        ax.plot(x_line, p(x_line), "r--", linewidth=2, label=f'Linear fit')

        ax.set_xlabel('Bus Factor Number', fontsize=11, weight='bold')
        ax.set_ylabel('Total Code Smells', fontsize=11, weight='bold')
        ax.set_title(f'Bus Factor vs Code Smells (rho={rho:.3f}, p={p_val:.4f})',
                    fontsize=12, weight='bold')
        ax.legend()
        ax.grid(alpha=0.3)
        save_figure(fig, 'fig_scatter_busfactor_smells')

    # 6. MANN-WHITNEY U TESTS
    print("\n--- 6. MANN-WHITNEY U TESTS ---")

    mann_whitney_results = []

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()

    plot_idx = 0

    for smell_idx, smell in enumerate(community_smells):
        for smell_var_idx, smell_var in enumerate(['total_code_smells', 'total_impl_smells']):
            # Split data by community smell presence
            present = []
            absent = []

            for row in data:
                smell_val = safe_int(row.get(smell, 0))
                code_smell_val = safe_float(row.get(smell_var))

                if not isnan(code_smell_val):
                    if smell_val == 1:
                        present.append(code_smell_val)
                    else:
                        absent.append(code_smell_val)

            if len(present) > 0 and len(absent) > 0:
                U, p_val = mannwhitneyu(present, absent, alternative='two-sided')
                r_rb = rank_biserial(U, len(present), len(absent))

                median_present = np.median(present)
                median_absent = np.median(absent)

                result = {
                    'community_smell': smell,
                    'code_smell_var': smell_var,
                    'U': U,
                    'p_val': p_val,
                    'rank_biserial': r_rb,
                    'median_present': median_present,
                    'median_absent': median_absent,
                    'n_present': len(present),
                    'n_absent': len(absent)
                }
                mann_whitney_results.append(result)

                sig = '***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else 'ns'
                print(f"  {smell} x {smell_var}:")
                print(f"    U={U:.0f}, p={p_val:.4f}{sig}, r_rb={r_rb:.3f}")
                print(f"    Median present={median_present:.0f}, absent={median_absent:.0f}")

                # Create boxplot
                ax = axes[plot_idx]
                data_to_plot = [absent, present]
                bp = ax.boxplot(data_to_plot, labels=['Absent', 'Present'], patch_artist=True)

                for patch, color in zip(bp['boxes'], [COLORS['light'], COLORS['danger']]):
                    patch.set_facecolor(color)

                ax.set_ylabel('Total Code Smells' if smell_var == 'total_code_smells' else 'Implementation Smells',
                             fontsize=10, weight='bold')
                ax.set_title(f'{smell.capitalize()} vs {smell_var.replace("_", " ").title()}',
                            fontsize=10, weight='bold')
                ax.text(0.5, 0.95, f'p={p_val:.4f}{sig}', transform=ax.transAxes,
                       ha='center', va='top', fontsize=9, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
                ax.grid(axis='y', alpha=0.3)

                plot_idx += 1

    # Hide unused subplots
    for idx in range(plot_idx, 6):
        axes[idx].axis('off')

    plt.tight_layout()
    save_figure(fig, 'fig_boxplot_mann_whitney')

    # Write Mann-Whitney results to CSV
    headers = ['Community Smell', 'Code Smell Variable', 'U Statistic', 'P-value', 'Rank-Biserial',
               'Median Present', 'Median Absent', 'N Present', 'N Absent']
    rows = []
    for result in mann_whitney_results:
        rows.append([
            result['community_smell'],
            result['code_smell_var'],
            f"{result['U']:.1f}",
            f"{result['p_val']:.6f}",
            f"{result['rank_biserial']:.4f}",
            f"{result['median_present']:.1f}",
            f"{result['median_absent']:.1f}",
            result['n_present'],
            result['n_absent']
        ])
    write_csv_table('mann_whitney_tests.csv', headers, rows)

    # 7. PARTIAL CORRELATIONS (controlling for AuthorCount)
    print("\n--- 7. PARTIAL CORRELATIONS (controlling for AuthorCount) ---")

    partial_corr_pairs = [
        ('org_silo', 'total_code_smells'),
        ('lone_wolf', 'total_code_smells'),
        ('BusFactorNumber', 'total_code_smells')
    ]

    partial_results = []

    for var1, var2 in partial_corr_pairs:
        # Get valid triplets
        triplets = []
        for row in data:
            v1 = safe_float(row.get(var1))
            v2 = safe_float(row.get(var2))
            v3 = safe_float(row.get('AuthorCount'))

            if not isnan(v1) and not isnan(v2) and not isnan(v3):
                triplets.append((v1, v2, v3))

        if len(triplets) < 4:
            continue

        v1_vals, v2_vals, v3_vals = zip(*triplets)

        # Calculate partial correlation using residuals
        # Regress var1 on AuthorCount
        z1 = np.polyfit(v3_vals, v1_vals, 1)
        p1 = np.poly1d(z1)
        residuals1 = np.array(v1_vals) - p1(np.array(v3_vals))

        # Regress var2 on AuthorCount
        z2 = np.polyfit(v3_vals, v2_vals, 1)
        p2 = np.poly1d(z2)
        residuals2 = np.array(v2_vals) - p2(np.array(v3_vals))

        # Correlation of residuals
        partial_rho, partial_p = spearmanr(residuals1, residuals2)

        sig = '***' if partial_p < 0.001 else '**' if partial_p < 0.01 else '*' if partial_p < 0.05 else 'ns'

        partial_results.append({
            'var1': var1,
            'var2': var2,
            'partial_rho': partial_rho,
            'partial_p': partial_p,
            'n': len(triplets),
            'sig': sig
        })

        print(f"  {var1} vs {var2} | AuthorCount:")
        print(f"    Partial rho={partial_rho:.3f}, p={partial_p:.4f}{sig}, N={len(triplets)}")

    # 8. K-MEANS CLUSTERING
    print("\n--- 8. K-MEANS CLUSTERING ---")

    # Prepare data for clustering
    cluster_cols = ['total_code_smells', 'CommitCount', 'AuthorCount', 'commitCentrality_Density', 'BusFactorNumber', 'DaysActive']

    cluster_data = []
    cluster_indices = []

    for idx, row in enumerate(data):
        vals = get_row_numeric_values(row, cluster_cols)
        if vals is not None:
            cluster_data.append(vals)
            cluster_indices.append(idx)

    if len(cluster_data) > 10:
        X = np.array(cluster_data)

        # Remove outliers (±2 std)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        mask = np.ones(len(X_scaled), dtype=bool)
        for col in range(X_scaled.shape[1]):
            col_data = X_scaled[:, col]
            mean, std = np.mean(col_data), np.std(col_data)
            mask &= np.abs((col_data - mean) / (std + 1e-8)) <= 2

        X_filtered = X[mask]
        indices_filtered = [cluster_indices[i] for i in range(len(X)) if mask[i]]

        if len(X_filtered) > 10:
            X_scaled_filtered = scaler.fit_transform(X_filtered)

            # Elbow method to find optimal k
            inertias = []
            silhouette_scores = []
            k_range = range(2, min(11, len(X_filtered) // 3))

            for k in k_range:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                kmeans.fit(X_scaled_filtered)
                inertias.append(kmeans.inertia_)
                silhouette_scores.append(silhouette_score(X_scaled_filtered, kmeans.labels_))

            # Use silhouette score to select optimal k
            optimal_k = list(k_range)[np.argmax(silhouette_scores)]
            print(f"  Optimal k={optimal_k} (silhouette={max(silhouette_scores):.3f})")

            # Fit final model
            kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X_scaled_filtered)

            # Characterize clusters
            print(f"  Cluster Characterization:")
            for cluster_id in range(optimal_k):
                cluster_mask = labels == cluster_id
                cluster_size = np.sum(cluster_mask)
                print(f"    Cluster {cluster_id} (n={cluster_size}):")

                for col_idx, col_name in enumerate(cluster_cols):
                    cluster_vals = X_filtered[cluster_mask, col_idx]
                    print(f"      {col_name}: mean={np.mean(cluster_vals):.2f}, median={np.median(cluster_vals):.2f}")

            # Generate cluster visualization
            fig, axes = plt.subplots(1, 2, figsize=(14, 5))

            # Plot 1: Code Smells vs Commits
            ax = axes[0]
            scatter = ax.scatter(X_filtered[:, 1], X_filtered[:, 0], c=labels, cmap='viridis',
                                alpha=0.6, s=50, edgecolors='black', linewidth=0.5)
            ax.set_xlabel('Commit Count', fontsize=11, weight='bold')
            ax.set_ylabel('Total Code Smells', fontsize=11, weight='bold')
            ax.set_title('Clusters: Code Smells vs Commits', fontsize=12, weight='bold')
            ax.grid(alpha=0.3)
            plt.colorbar(scatter, ax=ax, label='Cluster')

            # Plot 2: Bus Factor vs Density
            ax = axes[1]
            scatter = ax.scatter(X_filtered[:, 4], X_filtered[:, 3], c=labels, cmap='viridis',
                                alpha=0.6, s=50, edgecolors='black', linewidth=0.5)
            ax.set_xlabel('Bus Factor Number', fontsize=11, weight='bold')
            ax.set_ylabel('Commit Centrality Density', fontsize=11, weight='bold')
            ax.set_title('Clusters: Bus Factor vs Density', fontsize=12, weight='bold')
            ax.grid(alpha=0.3)
            plt.colorbar(scatter, ax=ax, label='Cluster')

            plt.tight_layout()
            save_figure(fig, 'fig_clusters')

    return {
        'tech_stats': tech_stats,
        'social_stats': social_stats,
        'community_counts': community_counts,
        'top_10_smells': top_10_smells,
        'correlations': correlations,
        'mann_whitney': mann_whitney_results
    }

# ============================================================================
# PART B: TEMPORAL ANALYSIS
# ============================================================================

def analyze_temporal(data):
    """Perform temporal analysis on 208 repositories across 5 years."""
    print("\n" + "="*80)
    print("PART B: TEMPORAL ANALYSIS (N=208, 5 years, 800 snapshots)")
    print("="*80)

    # Group by year
    by_year = defaultdict(list)
    for row in data:
        year = safe_int(row.get('project_year', 1))
        if year and 1 <= year <= 5:
            by_year[year].append(row)

    print(f"\nData by year:")
    for year in sorted(by_year.keys()):
        print(f"  Year {year}: {len(by_year[year])} snapshots")

    # 9. TEMPORAL DESCRIPTIVES BY YEAR
    print("\n--- 9. TEMPORAL DESCRIPTIVES BY YEAR ---")

    temporal_cols = [
        'commit_count', 'author_count', 'bus_factor_number',
        'total_code_smells', 'total_design_smells', 'total_impl_smells'
    ]

    temporal_table = []

    for year in sorted(by_year.keys()):
        year_data = by_year[year]

        row = [year, len(year_data)]

        for col in temporal_cols:
            values = get_numeric_values(year_data, col)
            if values:
                row.append(f"{np.median(values):.1f}")
            else:
                row.append("N/A")

        # Community smells
        lone_wolf_count = sum(1 for r in year_data if safe_int(r.get('lone_wolf', 0)) == 1)
        lone_wolf_pct = 100 * lone_wolf_count / len(year_data)

        radio_silence_count = sum(1 for r in year_data if safe_int(r.get('radio_silence', 0)) == 1)
        radio_silence_pct = 100 * radio_silence_count / len(year_data)

        row.append(f"{lone_wolf_pct:.1f}%")
        row.append(f"{radio_silence_pct:.1f}%")

        temporal_table.append(row)

        print(f"\n  Year {year} (N={len(year_data)}):")
        for col in temporal_cols:
            values = get_numeric_values(year_data, col)
            if values:
                print(f"    {col}: median={np.median(values):.1f}")
        print(f"    Lone Wolf: {lone_wolf_pct:.1f}%")
        print(f"    Radio Silence: {radio_silence_pct:.1f}%")

    # Write temporal table
    headers = ['Year', 'N'] + temporal_cols + ['Lone Wolf %', 'Radio Silence %']
    write_csv_table('temporal_descriptives_by_year.csv', headers, temporal_table)

    # 10. SPEARMAN CORRELATIONS BY YEAR
    print("\n--- 10. SPEARMAN CORRELATIONS BY YEAR ---")

    temporal_corr_pairs = [
        ('commit_count', 'total_code_smells'),
        ('author_count', 'total_code_smells'),
        ('days_active', 'total_code_smells'),
        ('bus_factor_number', 'total_code_smells')
    ]

    corr_by_year = defaultdict(lambda: defaultdict(dict))

    for year in sorted(by_year.keys()):
        year_data = by_year[year]

        for var1, var2 in temporal_corr_pairs:
            pairs = []
            for row in year_data:
                v1 = safe_float(row.get(var1))
                v2 = safe_float(row.get(var2))
                if not isnan(v1) and not isnan(v2):
                    pairs.append((v1, v2))

            if len(pairs) >= 3:
                x, y = zip(*pairs)
                rho, p_val = spearmanr(x, y)
                sig = '***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else ''

                corr_by_year[var1][var2][year] = {
                    'rho': rho,
                    'p_val': p_val,
                    'sig': sig,
                    'n': len(pairs)
                }

                print(f"  Year {year} - {var1} x {var2}: rho={rho:.3f}, p={p_val:.4f}{sig}, N={len(pairs)}")

    # Generate heatmap for temporal correlations
    fig, axes = plt.subplots(1, len(temporal_corr_pairs), figsize=(16, 4))
    if len(temporal_corr_pairs) == 1:
        axes = [axes]

    for plot_idx, (var1, var2) in enumerate(temporal_corr_pairs):
        ax = axes[plot_idx]

        # Build matrix
        years = sorted(by_year.keys())
        matrix = np.zeros((1, len(years)))

        for col_idx, year in enumerate(years):
            if year in corr_by_year[var1][var2]:
                matrix[0, col_idx] = corr_by_year[var1][var2][year]['rho']

        im = ax.imshow(matrix, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)
        ax.set_xticks(np.arange(len(years)))
        ax.set_xticklabels(years)
        ax.set_yticks([0])
        ax.set_yticklabels([f"{var1}\nvs\n{var2}"], fontsize=9)
        ax.set_title(f'{var1.replace("_", " ").title()}\nvs\n{var2.replace("_", " ").title()}',
                    fontsize=10, weight='bold')

        # Add text
        for col_idx, year in enumerate(years):
            if year in corr_by_year[var1][var2]:
                rho = corr_by_year[var1][var2][year]['rho']
                sig = corr_by_year[var1][var2][year]['sig']
                ax.text(col_idx, 0, f"{rho:.2f}{sig}", ha="center", va="center",
                       color="white" if abs(rho) > 0.5 else "black", fontsize=9, weight='bold')

    plt.tight_layout()
    save_figure(fig, 'fig_correlation_heatmap')

    # 11. MANN-WHITNEY BY YEAR (Community Smells)
    print("\n--- 11. MANN-WHITNEY TESTS BY YEAR ---")

    mann_whitney_by_year = []

    fig, axes = plt.subplots(2, 5, figsize=(16, 8))
    plot_idx = 0

    for smell_idx, smell in enumerate(['radio_silence', 'lone_wolf']):
        for year in sorted(by_year.keys()):
            year_data = by_year[year]

            # Split by smell presence
            present = []
            absent = []

            for row in year_data:
                smell_val = safe_int(row.get(smell, 0))
                code_smell = safe_float(row.get('total_code_smells'))

                if not isnan(code_smell):
                    if smell_val == 1:
                        present.append(code_smell)
                    else:
                        absent.append(code_smell)

            if len(present) > 0 and len(absent) > 0:
                U, p_val = mannwhitneyu(present, absent, alternative='two-sided')

                result = {
                    'smell': smell,
                    'year': year,
                    'U': U,
                    'p_val': p_val,
                    'n_present': len(present),
                    'n_absent': len(absent),
                    'median_present': np.median(present),
                    'median_absent': np.median(absent)
                }
                mann_whitney_by_year.append(result)

                # Boxplot
                ax = axes[smell_idx, year - 1]
                bp = ax.boxplot([absent, present], labels=['Absent', 'Present'], patch_artist=True)

                for patch, color in zip(bp['boxes'], [COLORS['light'], COLORS['danger']]):
                    patch.set_facecolor(color)

                sig = '***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else 'ns'
                ax.set_title(f'Year {year} - {smell.replace("_", " ").title()}\n{sig}', fontsize=10, weight='bold')
                ax.set_ylabel('Total Code Smells', fontsize=9)
                ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    save_figure(fig, 'fig_cooccurrence_effect')

    # 12. SOCIAL EVOLUTION FIGURES
    print("\n--- 12. SOCIAL EVOLUTION FIGURES ---")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Bus Factor by year
    ax = axes[0, 0]
    bus_factor_by_year = [get_numeric_values(by_year[y], 'bus_factor_number') for y in sorted(by_year.keys())]
    bp = ax.boxplot(bus_factor_by_year, labels=sorted(by_year.keys()), patch_artist=True)
    for patch in bp['boxes']:
        patch.set_facecolor(COLORS['primary'])
    ax.set_xlabel('Ano do Projeto', fontsize=10, weight='bold')
    ax.set_ylabel('Bus Factor Number', fontsize=10, weight='bold')
    ax.set_title('Evolução do Bus Factor', fontsize=11, weight='bold')
    ax.grid(axis='y', alpha=0.3)

    # Author Count by year
    ax = axes[0, 1]
    author_by_year = [get_numeric_values(by_year[y], 'author_count') for y in sorted(by_year.keys())]
    bp = ax.boxplot(author_by_year, labels=sorted(by_year.keys()), patch_artist=True)
    for patch in bp['boxes']:
        patch.set_facecolor(COLORS['secondary'])
    ax.set_xlabel('Ano do Projeto', fontsize=10, weight='bold')
    ax.set_ylabel('Author Count', fontsize=10, weight='bold')
    ax.set_title('Evolução de Autores', fontsize=11, weight='bold')
    ax.grid(axis='y', alpha=0.3)

    # Community Smells prevalence by year
    ax = axes[1, 0]
    years = sorted(by_year.keys())
    lone_wolf_pcts = []
    radio_silence_pcts = []

    for year in years:
        lw_count = sum(1 for r in by_year[year] if safe_int(r.get('lone_wolf', 0)) == 1)
        rs_count = sum(1 for r in by_year[year] if safe_int(r.get('radio_silence', 0)) == 1)
        lone_wolf_pcts.append(100 * lw_count / len(by_year[year]))
        radio_silence_pcts.append(100 * rs_count / len(by_year[year]))

    ax.plot(years, lone_wolf_pcts, marker='o', label='Lone Wolf', color=COLORS['danger'], linewidth=2)
    ax.plot(years, radio_silence_pcts, marker='s', label='Radio Silence', color=COLORS['warning'], linewidth=2)
    ax.set_xlabel('Ano do Projeto', fontsize=10, weight='bold')
    ax.set_ylabel('Prevalência (%)', fontsize=10, weight='bold')
    ax.set_title('Evolução de Community Smells', fontsize=11, weight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_xticks(years)

    # Commit Count by year
    ax = axes[1, 1]
    commit_by_year = [get_numeric_values(by_year[y], 'commit_count') for y in sorted(by_year.keys())]
    bp = ax.boxplot(commit_by_year, labels=sorted(by_year.keys()), patch_artist=True)
    for patch in bp['boxes']:
        patch.set_facecolor(COLORS['success'])
    ax.set_xlabel('Ano do Projeto', fontsize=10, weight='bold')
    ax.set_ylabel('Commit Count', fontsize=10, weight='bold')
    ax.set_title('Evolução de Commits', fontsize=11, weight='bold')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    save_figure(fig, 'fig_social_evolution')

    # Code Smells stability
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Total distribution by year
    ax = axes[0]
    code_smells_by_year = [get_numeric_values(by_year[y], 'total_code_smells') for y in sorted(by_year.keys())]
    bp = ax.boxplot(code_smells_by_year, labels=sorted(by_year.keys()), patch_artist=True)
    for patch in bp['boxes']:
        patch.set_facecolor(COLORS['info'])
    ax.set_xlabel('Ano do Projeto', fontsize=10, weight='bold')
    ax.set_ylabel('Total Code Smells', fontsize=10, weight='bold')
    ax.set_title('Distribuição Total de Code Smells por Ano', fontsize=11, weight='bold')
    ax.grid(axis='y', alpha=0.3)

    # Design vs Implementation medians
    ax = axes[1]
    years_list = sorted(by_year.keys())
    design_medians = []
    impl_medians = []

    for year in years_list:
        design_vals = get_numeric_values(by_year[year], 'total_design_smells')
        impl_vals = get_numeric_values(by_year[year], 'total_impl_smells')
        design_medians.append(np.median(design_vals) if design_vals else 0)
        impl_medians.append(np.median(impl_vals) if impl_vals else 0)

    x = np.arange(len(years_list))
    width = 0.35
    ax.bar(x - width/2, design_medians, width, label='Design Smells', color=COLORS['danger'])
    ax.bar(x + width/2, impl_medians, width, label='Implementation Smells', color=COLORS['warning'])
    ax.set_xlabel('Ano do Projeto', fontsize=10, weight='bold')
    ax.set_ylabel('Mediana de Smells', fontsize=10, weight='bold')
    ax.set_title('Design vs Implementation Smells - Mediana por Ano', fontsize=11, weight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(years_list)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    save_figure(fig, 'fig_code_smells_stable')

    # 13. KRUSKAL-WALLIS TEST (Code Smells across years)
    print("\n--- 13. KRUSKAL-WALLIS TEST ---")

    code_smells_groups = [get_numeric_values(by_year[y], 'total_code_smells') for y in sorted(by_year.keys())]
    H, p_val = kruskal(*code_smells_groups)
    sig = '***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else 'ns'

    print(f"  Code Smells across years:")
    print(f"    H={H:.3f}, p={p_val:.4f}{sig}")

    # 14. FRIEDMAN TEST (Balanced panel)
    print("\n--- 14. FRIEDMAN TEST (Balanced panel only) ---")

    # Find repos with all 5 years
    repo_years = defaultdict(set)
    repo_data = defaultdict(lambda: defaultdict(dict))

    for row in data:
        repo = row.get('repo_name', '')
        year = safe_int(row.get('project_year', 1))
        if repo and year:
            repo_years[repo].add(year)
            repo_data[repo][year] = row

    balanced_repos = [repo for repo, years in repo_years.items() if years == {1, 2, 3, 4, 5}]
    print(f"  Balanced panel: {len(balanced_repos)} repos with all 5 years")

    if len(balanced_repos) >= 5:
        for metric in ['commit_count', 'author_count', 'bus_factor_number']:
            # Build matrix for Friedman test (repos x years)
            matrix = []
            for repo in balanced_repos:
                row = []
                for year in sorted(range(1, 6)):
                    val = safe_float(repo_data[repo][year].get(metric))
                    row.append(val if not isnan(val) else np.median([
                        safe_float(repo_data[repo][year].get(metric))
                        for y in range(1, 6)
                        if not isnan(safe_float(repo_data[repo][year].get(metric)))
                    ]))
                matrix.append(row)

            matrix = np.array(matrix)
            T, p_val = friedmanchisquare(*matrix.T)
            sig = '***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else 'ns'

            print(f"  {metric}:")
            print(f"    T={T:.3f}, p={p_val:.4f}{sig}")

    # 15. TRANSITIONS Y1 → Y5
    print("\n--- 15. TRANSITIONS YEAR 1 → YEAR 5 ---")

    transitions = {'lone_wolf': {}, 'radio_silence': {}}

    for smell in ['lone_wolf', 'radio_silence']:
        # Build transition matrix
        transitions_matrix = defaultdict(lambda: defaultdict(int))

        for repo in balanced_repos:
            y1_val = safe_int(repo_data[repo][1].get(smell, 0))
            y5_val = safe_int(repo_data[repo][5].get(smell, 0))

            transitions_matrix[y1_val][y5_val] += 1

        # Extract counts
        t00 = transitions_matrix[0][0]
        t01 = transitions_matrix[0][1]
        t10 = transitions_matrix[1][0]
        t11 = transitions_matrix[1][1]

        transitions[smell] = {
            '0_to_0': t00,
            '0_to_1': t01,
            '1_to_0': t10,
            '1_to_1': t11
        }

        # McNemar test
        if (t01 + t10) > 0:
            mcnemar_stat = ((t01 - t10) ** 2) / (t01 + t10)
            mcnemar_p = 1 - stats.chi2.cdf(mcnemar_stat, 1)
            sig = '***' if mcnemar_p < 0.001 else '**' if mcnemar_p < 0.01 else '*' if mcnemar_p < 0.05 else 'ns'

            print(f"  {smell}:")
            print(f"    0→0: {t00}, 0→1: {t01}, 1→0: {t10}, 1→1: {t11}")
            print(f"    McNemar χ²={mcnemar_stat:.3f}, p={mcnemar_p:.4f}{sig}")
        else:
            print(f"  {smell}:")
            print(f"    0→0: {t00}, 0→1: {t01}, 1→0: {t10}, 1→1: {t11}")
            print(f"    No transitions (invariant)")

    # Generate transitions visualization
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax_idx, smell in enumerate(['lone_wolf', 'radio_silence']):
        ax = axes[ax_idx]

        trans = transitions[smell]
        matrix = np.array([
            [trans['0_to_0'], trans['0_to_1']],
            [trans['1_to_0'], trans['1_to_1']]
        ])

        im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto')
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(['Ausente Y5', 'Presente Y5'], fontsize=10)
        ax.set_yticklabels(['Ausente Y1', 'Presente Y1'], fontsize=10)
        ax.set_title(f'Transições: {smell.replace("_", " ").title()}', fontsize=11, weight='bold')

        # Add text
        for i in range(2):
            for j in range(2):
                text = ax.text(j, i, int(matrix[i, j]),
                              ha="center", va="center", color="black", fontsize=12, weight='bold')

        plt.colorbar(im, ax=ax, label='Número de Repositórios')

    plt.tight_layout()
    save_figure(fig, 'fig_transitions_y1_y5')

    print("\n--- Temporal analysis complete ---")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("="*80)
    print("COMPREHENSIVE STATISTICAL ANALYSIS")
    print("Co-occurrence of Code Smells and Community Smells in Java Code")
    print("="*80)

    # Load datasets
    print("\nLoading datasets...")

    cross_sectional_file = DATA_DIR / 'consolidated_full_v1v2.csv'
    temporal_file = Path('/sessions/sleepy-loving-ride/temporal_v1.csv')

    cross_sectional_data = read_csv_to_dicts(str(cross_sectional_file))
    temporal_data = read_csv_to_dicts(str(temporal_file))

    if not cross_sectional_data:
        print(f"ERROR: Could not load cross-sectional data from {cross_sectional_file}")
        sys.exit(1)

    if not temporal_data:
        print(f"WARNING: Could not load temporal data from {temporal_file}")

    # Run analyses
    cross_sectional_results = analyze_cross_sectional(cross_sectional_data)

    if temporal_data:
        analyze_temporal(temporal_data)

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print(f"Figures saved to: {FIGURES_DIR}")
    print(f"Tables saved to: {OUTPUT_DIR}")
    print("="*80)

if __name__ == '__main__':
    main()
