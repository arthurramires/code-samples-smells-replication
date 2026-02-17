#!/usr/bin/env python3
"""
12_dissertation_analysis.py — Análise final para a dissertação
================================================================
Gera TODAS as tabelas e figuras necessárias para os Capítulos 5, 6, 7.
Inclui:
  1. Análise descritiva temporal (Tab 6.X)
  2. Correlações Spearman por ano (Tab 6.X)
  3. Co-ocorrência por ano (Tab 6.X)
  4. Testes estatísticos (Friedman, Kruskal-Wallis, Wilcoxon)
  5. Concentração temporal de commits
  6. Figuras publication-ready (PDF, 300 DPI)
"""

import csv
import os
import sys
import glob
import statistics
import warnings
warnings.filterwarnings('ignore')

import numpy as np
from scipy import stats
from collections import defaultdict

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
def _find(pattern, fallback=""):
    m = glob.glob(pattern)
    return m[0] if m else fallback

DATA_CSV = _find("/sessions/sleepy-loving-ride/mnt/Disserta*/results/temporal/temporal_data_complete_fixed.csv")
CONC_CSV = "/sessions/sleepy-loving-ride/analysis/commit_concentration.csv"
OUTPUT_DIR = "/sessions/sleepy-loving-ride/analysis"
FIG_DIR = os.path.join(OUTPUT_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Style
plt.rcParams.update({
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.labelsize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'font.family': 'serif',
})

# -------------------------------------------------------------------
# Load Data
# -------------------------------------------------------------------
def load_data():
    rows = []
    with open(DATA_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def to_float(v, default=0):
    try:
        return float(v) if v and v.strip() else default
    except:
        return default

def to_int(v, default=0):
    try:
        return int(float(v)) if v and v.strip() else default
    except:
        return default

# -------------------------------------------------------------------
# 1. DESCRIPTIVE STATISTICS BY YEAR
# -------------------------------------------------------------------
def descriptive_by_year(rows):
    """Generate LaTeX-ready descriptive statistics table."""
    by_year = defaultdict(list)
    for r in rows:
        y = int(r['project_year'])
        by_year[y].append(r)

    metrics = [
        ('commit_count', 'CommitCount', 'int'),
        ('author_count', 'AuthorCount', 'int'),
        ('days_active', 'DaysActive', 'int'),
        ('bus_factor_number', 'BusFactor', 'float'),
        ('total_code_smells', 'CodeSmells', 'int'),
        ('total_design_smells', 'DesignSmells', 'int'),
        ('total_impl_smells', 'ImplSmells', 'int'),
    ]

    bool_metrics = [
        ('lone_wolf', 'LoneWolf'),
        ('radio_silence', 'RadioSilence'),
        ('org_silo', 'OrgSilo'),
    ]

    print("\n" + "="*80)
    print("TABLE: Descriptive Statistics by Project Year (N per year)")
    print("="*80)

    # Header
    years = sorted(by_year.keys())
    print(f"{'Metric':<20}", end="")
    for y in years:
        print(f"  Year {y} (N={len(by_year[y])})", end="")
    print()
    print("-"*80)

    results = []

    for col, label, dtype in metrics:
        row_data = {'metric': label}
        vals_all = {}
        for y in years:
            vals = [to_float(r[col]) for r in by_year[y]]
            vals_all[y] = vals
            med = statistics.median(vals)
            iqr_low = np.percentile(vals, 25)
            iqr_high = np.percentile(vals, 75)
            row_data[f'Y{y}_median'] = f"{med:.1f}"
            row_data[f'Y{y}_iqr'] = f"[{iqr_low:.1f}, {iqr_high:.1f}]"
            row_data[f'Y{y}_mean'] = f"{statistics.mean(vals):.1f}"
        print(f"{label:<20}", end="")
        for y in years:
            med = statistics.median(vals_all[y])
            print(f"  {med:>8.1f}", end="")
        print()
        results.append(row_data)

    print("-"*80)

    for col, label in bool_metrics:
        row_data = {'metric': label}
        for y in years:
            n = len(by_year[y])
            count = sum(1 for r in by_year[y] if to_int(r.get(col, 0)) == 1)
            pct = 100 * count / n if n > 0 else 0
            row_data[f'Y{y}_count'] = count
            row_data[f'Y{y}_pct'] = f"{pct:.1f}%"
        print(f"{label:<20}", end="")
        for y in years:
            n = len(by_year[y])
            count = sum(1 for r in by_year[y] if to_int(r.get(col, 0)) == 1)
            pct = 100 * count / n if n > 0 else 0
            print(f"  {pct:>7.1f}%", end="")
        print()

    # Save as CSV
    with open(os.path.join(OUTPUT_DIR, "tab_descriptive_final.csv"), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Metric', 'Stat'] + [f'Year_{y}' for y in years])
        for col, label, dtype in metrics:
            for stat_name in ['Median', 'IQR_Q1', 'IQR_Q3', 'Mean', 'Std']:
                row = [label, stat_name]
                for y in years:
                    vals = [to_float(r[col]) for r in by_year[y]]
                    if stat_name == 'Median': row.append(f"{statistics.median(vals):.2f}")
                    elif stat_name == 'IQR_Q1': row.append(f"{np.percentile(vals, 25):.2f}")
                    elif stat_name == 'IQR_Q3': row.append(f"{np.percentile(vals, 75):.2f}")
                    elif stat_name == 'Mean': row.append(f"{statistics.mean(vals):.2f}")
                    elif stat_name == 'Std': row.append(f"{statistics.stdev(vals):.2f}" if len(vals) > 1 else "0")
                w.writerow(row)
        for col, label in bool_metrics:
            row = [label, 'Prevalence(%)']
            for y in years:
                n = len(by_year[y])
                count = sum(1 for r in by_year[y] if to_int(r.get(col, 0)) == 1)
                row.append(f"{100*count/n:.1f}" if n > 0 else "0")
            w.writerow(row)

    return by_year

# -------------------------------------------------------------------
# 2. SPEARMAN CORRELATIONS BY YEAR
# -------------------------------------------------------------------
def correlations_by_year(by_year):
    """Spearman correlations between social and technical metrics."""
    years = sorted(by_year.keys())

    pairs = [
        ('bus_factor_number', 'total_code_smells', 'BusFactor × CodeSmells'),
        ('commit_count', 'total_code_smells', 'CommitCount × CodeSmells'),
        ('author_count', 'total_code_smells', 'AuthorCount × CodeSmells'),
        ('days_active', 'total_code_smells', 'DaysActive × CodeSmells'),
        ('bus_factor_number', 'total_design_smells', 'BusFactor × DesignSmells'),
        ('bus_factor_number', 'total_impl_smells', 'BusFactor × ImplSmells'),
        ('commit_count', 'total_design_smells', 'CommitCount × DesignSmells'),
        ('commit_count', 'total_impl_smells', 'CommitCount × ImplSmells'),
    ]

    print("\n" + "="*80)
    print("TABLE: Spearman Correlations by Project Year")
    print("="*80)

    all_results = []

    for col_a, col_b, label in pairs:
        row = {'pair': label}
        print(f"\n{label}:")
        for y in years:
            a = [to_float(r[col_a]) for r in by_year[y]]
            b = [to_float(r[col_b]) for r in by_year[y]]
            if len(set(a)) <= 1 or len(set(b)) <= 1:
                rho, p = float('nan'), float('nan')
            else:
                rho, p = stats.spearmanr(a, b)
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
            row[f'Y{y}_rho'] = f"{rho:.3f}" if not np.isnan(rho) else "NaN"
            row[f'Y{y}_p'] = f"{p:.4f}" if not np.isnan(p) else "NaN"
            row[f'Y{y}_sig'] = sig
            print(f"  Year {y}: ρ={rho:.3f}, p={p:.4f} {sig}")
        all_results.append(row)

    # Save
    with open(os.path.join(OUTPUT_DIR, "tab_correlations_final.csv"), 'w', newline='') as f:
        w = csv.writer(f)
        header = ['Pair']
        for y in years:
            header += [f'Y{y}_rho', f'Y{y}_p', f'Y{y}_sig']
        w.writerow(header)
        for r in all_results:
            row = [r['pair']]
            for y in years:
                row += [r.get(f'Y{y}_rho', ''), r.get(f'Y{y}_p', ''), r.get(f'Y{y}_sig', '')]
            w.writerow(row)

    return all_results

# -------------------------------------------------------------------
# 3. CO-OCCURRENCE BY YEAR (Mann-Whitney)
# -------------------------------------------------------------------
def cooccurrence_by_year(by_year):
    """Mann-Whitney tests: community smell presence vs code smell count."""
    years = sorted(by_year.keys())
    smells = [
        ('lone_wolf', 'LoneWolf'),
        ('radio_silence', 'RadioSilence'),
        ('org_silo', 'OrgSilo'),
    ]

    print("\n" + "="*80)
    print("TABLE: Co-occurrence (Mann-Whitney U) by Project Year")
    print("="*80)

    all_results = []

    for col, label in smells:
        row = {'smell': label}
        print(f"\n{label} → total_code_smells:")
        for y in years:
            present = [to_float(r['total_code_smells']) for r in by_year[y] if to_int(r.get(col, 0)) == 1]
            absent = [to_float(r['total_code_smells']) for r in by_year[y] if to_int(r.get(col, 0)) == 0]

            if len(present) >= 2 and len(absent) >= 2:
                U, p = stats.mannwhitneyu(present, absent, alternative='two-sided')
                # Effect size r = Z / sqrt(N)
                n = len(present) + len(absent)
                z = stats.norm.ppf(1 - p/2) if p > 0 else float('nan')
                r_effect = z / np.sqrt(n) if n > 0 and not np.isnan(z) else float('nan')
                sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
            else:
                U, p, r_effect, sig = float('nan'), float('nan'), float('nan'), ""

            med_p = statistics.median(present) if present else 0
            med_a = statistics.median(absent) if absent else 0

            row[f'Y{y}_n_present'] = len(present)
            row[f'Y{y}_n_absent'] = len(absent)
            row[f'Y{y}_med_present'] = f"{med_p:.1f}"
            row[f'Y{y}_med_absent'] = f"{med_a:.1f}"
            row[f'Y{y}_U'] = f"{U:.0f}" if not np.isnan(U) else "NaN"
            row[f'Y{y}_p'] = f"{p:.4f}" if not np.isnan(p) else "NaN"
            row[f'Y{y}_r'] = f"{r_effect:.3f}" if not np.isnan(r_effect) else "NaN"
            row[f'Y{y}_sig'] = sig

            print(f"  Year {y}: present={len(present)}(med={med_p:.0f}) vs absent={len(absent)}(med={med_a:.0f}), U={U:.0f}, p={p:.4f} {sig}")

        all_results.append(row)

    # Save
    with open(os.path.join(OUTPUT_DIR, "tab_cooccurrence_final.csv"), 'w', newline='') as f:
        w = csv.writer(f)
        header = ['CommunitySmell']
        for y in years:
            header += [f'Y{y}_n_present', f'Y{y}_n_absent', f'Y{y}_med_present', f'Y{y}_med_absent', f'Y{y}_U', f'Y{y}_p', f'Y{y}_r', f'Y{y}_sig']
        w.writerow(header)
        for r in all_results:
            row = [r['smell']]
            for y in years:
                row += [r.get(f'Y{y}_n_present', ''), r.get(f'Y{y}_n_absent', ''), r.get(f'Y{y}_med_present', ''), r.get(f'Y{y}_med_absent', ''), r.get(f'Y{y}_U', ''), r.get(f'Y{y}_p', ''), r.get(f'Y{y}_r', ''), r.get(f'Y{y}_sig', '')]
            w.writerow(row)

    return all_results

# -------------------------------------------------------------------
# 4. BALANCED PANEL TESTS (Friedman, Wilcoxon)
# -------------------------------------------------------------------
def balanced_panel_tests(rows):
    """Tests for temporal evolution using balanced panel."""
    print("\n" + "="*80)
    print("BALANCED PANEL ANALYSIS (repos with all 5 years)")
    print("="*80)

    # Group by repo
    by_repo = defaultdict(dict)
    for r in rows:
        repo = r['repo_name']
        y = int(r['project_year'])
        by_repo[repo][y] = r

    # Balanced panel = repos with years 1-5
    balanced = {repo: ydata for repo, ydata in by_repo.items() if set(ydata.keys()) == {1,2,3,4,5}}
    print(f"Repos in balanced panel: {len(balanced)}")

    results = {}

    # Social metrics that CAN change
    social_metrics = [
        ('commit_count', 'CommitCount'),
        ('author_count', 'AuthorCount'),
        ('bus_factor_number', 'BusFactor'),
    ]

    bool_metrics = [
        ('lone_wolf', 'LoneWolf'),
        ('radio_silence', 'RadioSilence'),
    ]

    for col, label in social_metrics:
        arrays = []
        for y in range(1, 6):
            vals = [to_float(balanced[repo][y][col]) for repo in balanced]
            arrays.append(vals)

        # Friedman test (requires variation)
        try:
            stat_f, p_f = stats.friedmanchisquare(*arrays)
            print(f"\nFriedman test for {label}: χ²={stat_f:.3f}, p={p_f:.4f}")
        except Exception as e:
            stat_f, p_f = float('nan'), float('nan')
            print(f"\nFriedman test for {label}: {e}")

        # Wilcoxon Year 1 vs Year 5
        try:
            stat_w, p_w = stats.wilcoxon(arrays[0], arrays[4])
            print(f"  Wilcoxon Y1 vs Y5: W={stat_w:.1f}, p={p_w:.4f}")
        except Exception as e:
            stat_w, p_w = float('nan'), float('nan')
            print(f"  Wilcoxon Y1 vs Y5: {e}")

        results[label] = {
            'friedman_chi2': stat_f, 'friedman_p': p_f,
            'wilcoxon_W': stat_w, 'wilcoxon_p': p_w
        }

    # Cochran's Q test for binary outcomes
    for col, label in bool_metrics:
        arrays = []
        for y in range(1, 6):
            vals = [to_int(balanced[repo][y].get(col, 0)) for repo in balanced]
            arrays.append(vals)

        # McNemar Year 1 vs Year 5
        a = np.array(arrays[0])
        b = np.array(arrays[4])
        n_01 = np.sum((a == 0) & (b == 1))  # became smell
        n_10 = np.sum((a == 1) & (b == 0))  # lost smell
        n_11 = np.sum((a == 1) & (b == 1))  # always smell
        n_00 = np.sum((a == 0) & (b == 0))  # never smell

        print(f"\n{label} Y1→Y5 transitions:")
        print(f"  0→0: {n_00}, 0→1: {n_01}, 1→0: {n_10}, 1→1: {n_11}")

        if (n_01 + n_10) > 0:
            # McNemar exact
            p_mcnemar = stats.binom_test(min(n_01, n_10), n_01 + n_10, 0.5) if hasattr(stats, 'binom_test') else float('nan')
            try:
                p_mcnemar = stats.binomtest(min(n_01, n_10), n_01 + n_10, 0.5).pvalue
            except:
                pass
            print(f"  McNemar p={p_mcnemar:.4f}")
        else:
            p_mcnemar = float('nan')
            print(f"  McNemar: no discordant pairs")

        results[label] = {'mcnemar_p': p_mcnemar, 'n_01': int(n_01), 'n_10': int(n_10), 'n_11': int(n_11), 'n_00': int(n_00)}

    # Code smells - Kruskal-Wallis across years (unpaired comparison)
    print("\n--- Code Smell comparison across years ---")
    by_year = defaultdict(list)
    for r in rows:
        y = int(r['project_year'])
        by_year[y].append(to_float(r['total_code_smells']))

    arrays_kw = [by_year[y] for y in sorted(by_year.keys())]
    try:
        H, p_kw = stats.kruskal(*arrays_kw)
        print(f"Kruskal-Wallis (CodeSmells across years): H={H:.3f}, p={p_kw:.4f}")
    except Exception as e:
        H, p_kw = float('nan'), float('nan')
        print(f"Kruskal-Wallis: {e}")

    results['CodeSmells_KW'] = {'H': H, 'p': p_kw}

    # Save
    with open(os.path.join(OUTPUT_DIR, "tab_tests_final.csv"), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Test', 'Metric', 'Statistic', 'p_value', 'Details'])
        for label, vals in results.items():
            if 'friedman_chi2' in vals:
                w.writerow(['Friedman', label, f"{vals['friedman_chi2']:.3f}", f"{vals['friedman_p']:.4f}", ''])
                w.writerow(['Wilcoxon_Y1vsY5', label, f"{vals['wilcoxon_W']:.1f}", f"{vals['wilcoxon_p']:.4f}", ''])
            elif 'mcnemar_p' in vals:
                w.writerow(['McNemar_Y1vsY5', label, '', f"{vals['mcnemar_p']:.4f}", f"0->1:{vals['n_01']}, 1->0:{vals['n_10']}"])
            elif 'H' in vals:
                w.writerow(['Kruskal-Wallis', label, f"{vals['H']:.3f}", f"{vals['p']:.4f}", ''])

    return balanced, results

# -------------------------------------------------------------------
# 5. COMMIT CONCENTRATION SUMMARY
# -------------------------------------------------------------------
def commit_concentration_summary():
    """Summarize commit concentration findings."""
    if not os.path.exists(CONC_CSV):
        print("Commit concentration CSV not found, skipping.")
        return None

    rows = []
    with open(CONC_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    print("\n" + "="*80)
    print("COMMIT CONCENTRATION SUMMARY")
    print("="*80)

    pct30 = [float(r['pct_first_30d']) for r in rows]
    pct90 = [float(r['pct_first_90d']) for r in rows]
    pct365 = [float(r['pct_first_365d']) for r in rows]
    active_days = [int(r['unique_active_days']) for r in rows]

    print(f"N = {len(rows)} repos")
    print(f"Median commits in first 30 days: {statistics.median(pct30):.1f}%")
    print(f"Median commits in first 90 days: {statistics.median(pct90):.1f}%")
    print(f"Median commits in first year:    {statistics.median(pct365):.1f}%")
    print(f"Repos with ≥80% in first 30d:    {sum(1 for p in pct30 if p>=80)}/{len(rows)} ({100*sum(1 for p in pct30 if p>=80)/len(rows):.1f}%)")
    print(f"Repos with ≥90% in first 90d:    {sum(1 for p in pct90 if p>=90)}/{len(rows)} ({100*sum(1 for p in pct90 if p>=90)/len(rows):.1f}%)")
    print(f"Median unique active days: {statistics.median(active_days)}")
    print(f"Repos active ≤7 days: {sum(1 for a in active_days if a<=7)}/{len(rows)} ({100*sum(1 for a in active_days if a<=7)/len(rows):.1f}%)")

    return rows

# -------------------------------------------------------------------
# 6. FIGURES
# -------------------------------------------------------------------
def plot_social_evolution(by_year):
    """Fig 1: Social metrics evolution across project years."""
    years = sorted(by_year.keys())

    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    fig.suptitle('Evolução das Métricas Sociais por Project Year', fontsize=14, fontweight='bold')

    # Bus Factor
    ax = axes[0, 0]
    data = [[to_float(r['bus_factor_number']) for r in by_year[y]] for y in years]
    bp = ax.boxplot(data, labels=[f'Y{y}' for y in years], patch_artist=True)
    for patch in bp['boxes']:
        patch.set_facecolor('#3498db')
        patch.set_alpha(0.6)
    ax.set_ylabel('Bus Factor')
    ax.set_title('(a) Bus Factor')
    medians = [statistics.median(d) for d in data]
    for i, m in enumerate(medians):
        ax.annotate(f'{m:.3f}', (i+1, m), textcoords="offset points", xytext=(0, 10), ha='center', fontsize=8)

    # Author Count
    ax = axes[0, 1]
    data = [[to_float(r['author_count']) for r in by_year[y]] for y in years]
    bp = ax.boxplot(data, labels=[f'Y{y}' for y in years], patch_artist=True)
    for patch in bp['boxes']:
        patch.set_facecolor('#2ecc71')
        patch.set_alpha(0.6)
    ax.set_ylabel('Author Count')
    ax.set_title('(b) Author Count')

    # Lone Wolf prevalence
    ax = axes[1, 0]
    lw_pct = [100 * sum(1 for r in by_year[y] if to_int(r.get('lone_wolf', 0)) == 1) / len(by_year[y]) for y in years]
    rs_pct = [100 * sum(1 for r in by_year[y] if to_int(r.get('radio_silence', 0)) == 1) / len(by_year[y]) for y in years]
    x = np.arange(len(years))
    w = 0.35
    bars1 = ax.bar(x - w/2, lw_pct, w, label='Lone Wolf', color='#e74c3c', alpha=0.7)
    bars2 = ax.bar(x + w/2, rs_pct, w, label='Radio Silence', color='#9b59b6', alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels([f'Y{y}' for y in years])
    ax.set_ylabel('Prevalência (%)')
    ax.set_title('(c) Community Smells')
    ax.legend()
    ax.set_ylim(0, 80)
    for bar, val in zip(bars1, lw_pct):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f'{val:.0f}%', ha='center', fontsize=8)
    for bar, val in zip(bars2, rs_pct):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f'{val:.0f}%', ha='center', fontsize=8)

    # Commit Count
    ax = axes[1, 1]
    data = [[to_float(r['commit_count']) for r in by_year[y]] for y in years]
    bp = ax.boxplot(data, labels=[f'Y{y}' for y in years], patch_artist=True)
    for patch in bp['boxes']:
        patch.set_facecolor('#f39c12')
        patch.set_alpha(0.6)
    ax.set_ylabel('Commit Count')
    ax.set_title('(d) Commit Count')

    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, 'fig_social_evolution.pdf'))
    plt.close()
    print("  Saved fig_social_evolution.pdf")

def plot_code_smells_stable(by_year):
    """Fig 2: Code smells stability across project years."""
    years = sorted(by_year.keys())

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    fig.suptitle('Estabilidade dos Code Smells ao Longo dos Project Years', fontsize=13, fontweight='bold')

    # Total code smells boxplot
    ax = axes[0]
    data = [[to_float(r['total_code_smells']) for r in by_year[y]] for y in years]
    bp = ax.boxplot(data, labels=[f'Y{y}' for y in years], patch_artist=True, showfliers=False)
    for patch in bp['boxes']:
        patch.set_facecolor('#95a5a6')
        patch.set_alpha(0.6)
    ax.set_ylabel('Total Code Smells')
    ax.set_title('(a) Distribuição por Ano')
    medians = [statistics.median(d) for d in data]
    for i, m in enumerate(medians):
        ax.annotate(f'{m:.0f}', (i+1, m), textcoords="offset points", xytext=(0, 10), ha='center', fontsize=9)

    # Design vs Implementation
    ax = axes[1]
    design = [statistics.median([to_float(r['total_design_smells']) for r in by_year[y]]) for y in years]
    impl = [statistics.median([to_float(r['total_impl_smells']) for r in by_year[y]]) for y in years]
    x = np.arange(len(years))
    ax.bar(x - 0.2, design, 0.35, label='Design Smells', color='#2c3e50', alpha=0.7)
    ax.bar(x + 0.2, impl, 0.35, label='Implementation Smells', color='#7f8c8d', alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels([f'Y{y}' for y in years])
    ax.set_ylabel('Mediana')
    ax.set_title('(b) Design vs Implementation (Mediana)')
    ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, 'fig_code_smells_stable.pdf'))
    plt.close()
    print("  Saved fig_code_smells_stable.pdf")

def plot_correlation_heatmap(by_year):
    """Fig 3: Spearman correlation heatmap across years."""
    years = sorted(by_year.keys())
    pairs = [
        ('bus_factor_number', 'total_code_smells', 'BF×CS'),
        ('commit_count', 'total_code_smells', 'CC×CS'),
        ('author_count', 'total_code_smells', 'AC×CS'),
        ('days_active', 'total_code_smells', 'DA×CS'),
    ]

    matrix = np.zeros((len(pairs), len(years)))
    p_matrix = np.zeros((len(pairs), len(years)))

    for i, (col_a, col_b, label) in enumerate(pairs):
        for j, y in enumerate(years):
            a = [to_float(r[col_a]) for r in by_year[y]]
            b = [to_float(r[col_b]) for r in by_year[y]]
            if len(set(a)) > 1 and len(set(b)) > 1:
                rho, p = stats.spearmanr(a, b)
            else:
                rho, p = 0, 1
            matrix[i, j] = rho
            p_matrix[i, j] = p

    fig, ax = plt.subplots(figsize=(7, 4))
    im = ax.imshow(matrix, cmap='RdBu_r', vmin=-0.5, vmax=0.5, aspect='auto')

    ax.set_xticks(range(len(years)))
    ax.set_xticklabels([f'Year {y}' for y in years])
    ax.set_yticks(range(len(pairs)))
    ax.set_yticklabels([p[2] for p in pairs])

    for i in range(len(pairs)):
        for j in range(len(years)):
            sig = "***" if p_matrix[i,j] < 0.001 else "**" if p_matrix[i,j] < 0.01 else "*" if p_matrix[i,j] < 0.05 else ""
            text = f"{matrix[i,j]:.2f}{sig}"
            color = 'white' if abs(matrix[i,j]) > 0.3 else 'black'
            ax.text(j, i, text, ha='center', va='center', fontsize=9, color=color)

    plt.colorbar(im, label='Spearman ρ')
    ax.set_title('Correlações Spearman: Métricas Sociais × Code Smells', fontsize=12, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, 'fig_correlation_heatmap.pdf'))
    plt.close()
    print("  Saved fig_correlation_heatmap.pdf")

def plot_cooccurrence_effect(by_year):
    """Fig 4: Co-occurrence effect sizes across years."""
    years = sorted(by_year.keys())

    smells = [
        ('lone_wolf', 'Lone Wolf'),
        ('radio_silence', 'Radio Silence'),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    fig.suptitle('Co-ocorrência: Community Smell → Code Smells (Mediana)', fontsize=13, fontweight='bold')

    for idx, (col, label) in enumerate(smells):
        ax = axes[idx]
        med_present = []
        med_absent = []
        p_values = []

        for y in years:
            present = [to_float(r['total_code_smells']) for r in by_year[y] if to_int(r.get(col, 0)) == 1]
            absent = [to_float(r['total_code_smells']) for r in by_year[y] if to_int(r.get(col, 0)) == 0]
            med_present.append(statistics.median(present) if present else 0)
            med_absent.append(statistics.median(absent) if absent else 0)
            if len(present) >= 2 and len(absent) >= 2:
                _, p = stats.mannwhitneyu(present, absent, alternative='two-sided')
            else:
                p = 1.0
            p_values.append(p)

        x = np.arange(len(years))
        bars1 = ax.bar(x - 0.2, med_present, 0.35, label=f'Com {label}', color='#e74c3c', alpha=0.7)
        bars2 = ax.bar(x + 0.2, med_absent, 0.35, label=f'Sem {label}', color='#3498db', alpha=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels([f'Y{y}' for y in years])
        ax.set_ylabel('Mediana Code Smells')
        ax.set_title(f'{label}')
        ax.legend()

        # Mark significant years
        for i, p in enumerate(p_values):
            if p < 0.05:
                max_h = max(med_present[i], med_absent[i])
                ax.text(i, max_h + 2, '*' if p >= 0.01 else '**' if p >= 0.001 else '***', ha='center', fontsize=12, fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, 'fig_cooccurrence_effect.pdf'))
    plt.close()
    print("  Saved fig_cooccurrence_effect.pdf")

def plot_commit_concentration(conc_data):
    """Fig 5: Commit concentration analysis."""
    if not conc_data:
        return

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    fig.suptitle('Concentração Temporal de Commits nos Code Samples', fontsize=13, fontweight='bold')

    # Histogram of % commits in first 30 days
    ax = axes[0]
    pct30 = [float(r['pct_first_30d']) for r in conc_data]
    ax.hist(pct30, bins=20, color='#3498db', alpha=0.7, edgecolor='white')
    ax.axvline(statistics.median(pct30), color='red', linestyle='--', linewidth=2, label=f'Mediana={statistics.median(pct30):.0f}%')
    ax.set_xlabel('% commits nos primeiros 30 dias')
    ax.set_ylabel('Número de repos')
    ax.set_title('(a) Concentração 30 dias')
    ax.legend(fontsize=9)

    # Unique active days
    ax = axes[1]
    active = [int(r['unique_active_days']) for r in conc_data]
    ax.hist(active, bins=30, color='#2ecc71', alpha=0.7, edgecolor='white')
    ax.axvline(statistics.median(active), color='red', linestyle='--', linewidth=2, label=f'Mediana={statistics.median(active):.0f} dias')
    ax.set_xlabel('Dias únicos com commits')
    ax.set_ylabel('Número de repos')
    ax.set_title('(b) Dias Ativos')
    ax.legend(fontsize=9)
    ax.set_xlim(0, min(100, max(active)))

    # Cumulative: % in 30, 90, 365 days
    ax = axes[2]
    thresholds = [30, 90, 365]
    for thresh, col, color in [(30, 'pct_first_30d', '#3498db'), (90, 'pct_first_90d', '#e74c3c'), (365, 'pct_first_365d', '#2ecc71')]:
        vals = sorted([float(r[col]) for r in conc_data])
        ax.plot(vals, np.linspace(0, 100, len(vals)), label=f'{thresh}d', color=color, linewidth=2)
    ax.set_xlabel('% dos commits')
    ax.set_ylabel('% dos repositórios (CDF)')
    ax.set_title('(c) CDF Cumulativa')
    ax.legend(fontsize=9)
    ax.set_xlim(0, 105)
    ax.axhline(50, color='gray', linestyle=':', alpha=0.5)

    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, 'fig_commit_concentration.pdf'))
    plt.close()
    print("  Saved fig_commit_concentration.pdf")

def plot_smell_types_by_year(by_year):
    """Fig 6: Top smell types composition."""
    years = sorted(by_year.keys())

    # Collect all smell type columns
    design_cols = [c for c in by_year[1][0].keys() if c.startswith('design_')]
    impl_cols = [c for c in by_year[1][0].keys() if c.startswith('impl_')]

    # Get top types across all years (by total)
    all_sums = {}
    for col in design_cols + impl_cols:
        total = 0
        for y in years:
            total += sum(to_float(r.get(col, 0)) for r in by_year[y])
        if total > 0:
            all_sums[col] = total

    top_types = sorted(all_sums.keys(), key=lambda x: all_sums[x], reverse=True)[:8]

    fig, ax = plt.subplots(figsize=(10, 5))

    bottom = np.zeros(len(years))
    colors = plt.cm.Set3(np.linspace(0, 1, len(top_types)))

    for i, col in enumerate(top_types):
        vals = []
        for y in years:
            total_smells = sum(to_float(r.get(col, 0)) for r in by_year[y])
            vals.append(total_smells)
        label = col.replace('design_', 'D: ').replace('impl_', 'I: ').replace('_', ' ')
        ax.bar(range(len(years)), vals, bottom=bottom, label=label, color=colors[i], alpha=0.8)
        bottom += np.array(vals)

    ax.set_xticks(range(len(years)))
    ax.set_xticklabels([f'Year {y}' for y in years])
    ax.set_ylabel('Contagem Total')
    ax.set_title('Composição dos Top 8 Tipos de Smells por Project Year', fontsize=13, fontweight='bold')
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, 'fig_smell_composition_detail.pdf'))
    plt.close()
    print("  Saved fig_smell_composition_detail.pdf")

def plot_sensitivity_no_magic(by_year):
    """Fig 7: Sensitivity analysis excluding Magic Number."""
    years = sorted(by_year.keys())

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    fig.suptitle('Análise de Sensibilidade: Excluindo Magic Number', fontsize=13, fontweight='bold')

    # Correlations with and without Magic Number
    ax = axes[0]
    rho_with = []
    rho_without = []

    for y in years:
        cc = [to_float(r['commit_count']) for r in by_year[y]]
        cs_full = [to_float(r['total_code_smells']) for r in by_year[y]]
        cs_no_mn = [to_float(r['total_code_smells']) - to_float(r.get('impl_Magic_Number', 0)) for r in by_year[y]]

        rho1, _ = stats.spearmanr(cc, cs_full)
        rho2, _ = stats.spearmanr(cc, cs_no_mn)
        rho_with.append(rho1)
        rho_without.append(rho2)

    x = np.arange(len(years))
    ax.bar(x - 0.2, rho_with, 0.35, label='Com Magic Number', color='#3498db', alpha=0.7)
    ax.bar(x + 0.2, rho_without, 0.35, label='Sem Magic Number', color='#e74c3c', alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels([f'Y{y}' for y in years])
    ax.set_ylabel('Spearman ρ')
    ax.set_title('(a) CommitCount × CodeSmells')
    ax.legend(fontsize=9)
    ax.axhline(0, color='gray', linestyle='-', alpha=0.3)

    # Box plot of code smells without Magic Number
    ax = axes[1]
    data_full = [[to_float(r['total_code_smells']) for r in by_year[y]] for y in years]
    data_no_mn = [[to_float(r['total_code_smells']) - to_float(r.get('impl_Magic_Number', 0)) for r in by_year[y]] for y in years]

    positions = np.arange(len(years))
    bp1 = ax.boxplot(data_full, positions=positions - 0.2, widths=0.35, patch_artist=True, showfliers=False)
    bp2 = ax.boxplot(data_no_mn, positions=positions + 0.2, widths=0.35, patch_artist=True, showfliers=False)
    for patch in bp1['boxes']:
        patch.set_facecolor('#3498db')
        patch.set_alpha(0.5)
    for patch in bp2['boxes']:
        patch.set_facecolor('#e74c3c')
        patch.set_alpha(0.5)
    ax.set_xticks(positions)
    ax.set_xticklabels([f'Y{y}' for y in years])
    ax.set_ylabel('Code Smells')
    ax.set_title('(b) Distribuição com/sem Magic Number')
    ax.legend([bp1['boxes'][0], bp2['boxes'][0]], ['Todos', 'Sem Magic Number'], fontsize=9)

    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, 'fig_sensitivity_magic_number.pdf'))
    plt.close()
    print("  Saved fig_sensitivity_magic_number.pdf")

def plot_transition_sankey_simple(by_year):
    """Fig 8: Transitions of community smells Y1 → Y5."""
    # Build transition data for balanced panel repos
    by_repo = defaultdict(dict)
    for y in by_year:
        for r in by_year[y]:
            by_repo[r['repo_name']][y] = r

    balanced = {repo: ydata for repo, ydata in by_repo.items() if set(ydata.keys()) >= {1, 5}}

    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    fig.suptitle('Transições de Community Smells: Year 1 → Year 5', fontsize=13, fontweight='bold')

    for idx, (col, label) in enumerate([('lone_wolf', 'Lone Wolf'), ('radio_silence', 'Radio Silence')]):
        ax = axes[idx]
        # Count transitions
        transitions = {'0→0': 0, '0→1': 0, '1→0': 0, '1→1': 0}
        for repo, ydata in balanced.items():
            v1 = to_int(ydata[1].get(col, 0))
            v5 = to_int(ydata[5].get(col, 0))
            transitions[f'{v1}→{v5}'] += 1

        labels = list(transitions.keys())
        values = list(transitions.values())
        colors_t = ['#2ecc71', '#e74c3c', '#3498db', '#f39c12']

        bars = ax.bar(labels, values, color=colors_t, alpha=0.7, edgecolor='white')
        ax.set_title(label)
        ax.set_ylabel('Número de repos')
        for bar, val in zip(bars, values):
            n_total = sum(values)
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{val}\n({100*val/n_total:.0f}%)', ha='center', fontsize=9)

    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, 'fig_transitions_y1_y5.pdf'))
    plt.close()
    print("  Saved fig_transitions_y1_y5.pdf")

# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------
def main():
    print("="*80)
    print("ANÁLISE FINAL PARA A DISSERTAÇÃO")
    print("="*80)
    print(f"Data file: {DATA_CSV}")

    rows = load_data()
    print(f"Total snapshots: {len(rows)}")
    print(f"Unique repos: {len(set(r['repo_name'] for r in rows))}")

    # 1. Descriptive stats
    by_year = descriptive_by_year(rows)

    # 2. Correlations
    corr_results = correlations_by_year(by_year)

    # 3. Co-occurrence
    cooc_results = cooccurrence_by_year(by_year)

    # 4. Balanced panel tests
    balanced, test_results = balanced_panel_tests(rows)

    # 5. Commit concentration
    conc_data = commit_concentration_summary()

    # 6. Figures
    print("\n" + "="*80)
    print("GENERATING FIGURES")
    print("="*80)
    plot_social_evolution(by_year)
    plot_code_smells_stable(by_year)
    plot_correlation_heatmap(by_year)
    plot_cooccurrence_effect(by_year)
    if conc_data:
        plot_commit_concentration(conc_data)
    plot_smell_types_by_year(by_year)
    plot_sensitivity_no_magic(by_year)
    plot_transition_sankey_simple(by_year)

    print("\n" + "="*80)
    print("ALL DONE!")
    print(f"Tables saved to: {OUTPUT_DIR}/tab_*.csv")
    print(f"Figures saved to: {FIG_DIR}/fig_*.pdf")
    print("="*80)

if __name__ == "__main__":
    main()
