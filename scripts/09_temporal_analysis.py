#!/usr/bin/env python3
"""
09_temporal_analysis.py — Análise dos Dados Temporais por Project Year
=====================================================================
Dissertação: Coocorrência Evolutiva de Code Smells e Community Smells
             em Code Samples Java

Este script analisa os dados extraídos por 08_temporal_extraction.py,
gerando:
  - Tabelas descritivas por project year
  - Evolução temporal de Code Smells e Community Smells
  - Testes estatísticos (Friedman, Wilcoxon) para mudanças entre anos
  - Figuras para a dissertação (Capítulo 6 - Resultados, RQ2)
  - Análise de coocorrência por project year

Uso:
  python 09_temporal_analysis.py --input temporal_data.csv \
      --output-dir analysis/ --fig-dir texto-quali/cap6/

Autor: Arthur Bueno (dissertação de mestrado)
"""

import argparse
import csv
import os
import sys
import warnings
from collections import defaultdict
from typing import Optional

import numpy as np

warnings.filterwarnings('ignore')

# Tentativa de imports opcionais
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("[WARN] pandas não encontrado. Instale com: pip install pandas")

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("[WARN] matplotlib não encontrado. Figuras não serão geradas.")

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("[WARN] scipy não encontrado. Testes estatísticos serão omitidos.")


# ============================================================
# 1. CARGA E PREPARAÇÃO DOS DADOS
# ============================================================
def load_temporal_data(input_path: str) -> 'pd.DataFrame':
    """Carrega e prepara os dados temporais."""
    df = pd.read_csv(input_path)

    # Converter colunas numéricas
    numeric_cols = [c for c in df.columns if any(c.startswith(p) for p in
                    ['total_', 'design_', 'impl_', 'commit_count', 'author_count',
                     'bus_factor', 'pr_count', 'issue_count', 'days_active',
                     'timezone_count', 'lone_wolf', 'radio_silence', 'org_silo'])]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Garantir project_year é inteiro
    df['project_year'] = pd.to_numeric(df['project_year'], errors='coerce').astype(int)

    print(f"Dados carregados: {len(df)} linhas, {df['repo_name'].nunique()} repos")
    print(f"Project years: {sorted(df['project_year'].unique())}")
    print(f"Repos por project year:")
    for y in sorted(df['project_year'].unique()):
        n = len(df[df['project_year'] == y])
        print(f"  Year {y}: {n} repos")

    return df


# ============================================================
# 2. ESTATÍSTICAS DESCRITIVAS POR PROJECT YEAR
# ============================================================
def descriptive_stats_by_year(df: 'pd.DataFrame', output_dir: str):
    """Gera tabelas descritivas por project year."""
    print("\n" + "=" * 60)
    print("2. ESTATÍSTICAS DESCRITIVAS POR PROJECT YEAR")
    print("=" * 60)

    metrics = {
        'total_code_smells': 'Total Code Smells',
        'total_design_smells': 'Design Smells',
        'total_impl_smells': 'Impl. Smells',
        'commit_count': 'Commits',
        'author_count': 'Authors',
        'bus_factor_number': 'Bus Factor',
        'pr_count': 'PRs',
        'issue_count': 'Issues',
        'lone_wolf': 'Lone Wolf',
        'radio_silence': 'Radio Silence',
    }

    rows = []
    for year in sorted(df['project_year'].unique()):
        year_df = df[df['project_year'] == year]
        row = {'project_year': year, 'n_repos': len(year_df)}

        for col, label in metrics.items():
            if col in year_df.columns:
                vals = year_df[col].dropna()
                if len(vals) > 0:
                    row[f'{col}_mean'] = round(vals.mean(), 2)
                    row[f'{col}_median'] = round(vals.median(), 2)
                    row[f'{col}_std'] = round(vals.std(), 2)
                    row[f'{col}_q25'] = round(vals.quantile(0.25), 2)
                    row[f'{col}_q75'] = round(vals.quantile(0.75), 2)

                    # Para indicadores binários, reportar prevalência
                    if col in ['lone_wolf', 'radio_silence', 'org_silo']:
                        row[f'{col}_prevalence'] = round(vals.sum() / len(vals) * 100, 1)

        rows.append(row)
        print(f"\n  Year {year} (n={len(year_df)}):")
        for col, label in metrics.items():
            if f'{col}_median' in row:
                print(f"    {label}: median={row[f'{col}_median']}, "
                      f"mean={row[f'{col}_mean']}, std={row[f'{col}_std']}")

    # Salvar
    stats_df = pd.DataFrame(rows)
    stats_path = os.path.join(output_dir, "temporal_descriptive_stats.csv")
    stats_df.to_csv(stats_path, index=False)
    print(f"\n  Salvo: {stats_path}")

    return stats_df


# ============================================================
# 3. EVOLUÇÃO TEMPORAL DE SMELLS
# ============================================================
def evolution_analysis(df: 'pd.DataFrame', output_dir: str, fig_dir: str):
    """Analisa a evolução de smells ao longo dos project years."""
    print("\n" + "=" * 60)
    print("3. EVOLUÇÃO TEMPORAL")
    print("=" * 60)

    # ---- 3a. Repos com dados em TODOS os anos (painel balanceado) ----
    years = sorted(df['project_year'].unique())
    repo_year_counts = df.groupby('repo_name')['project_year'].count()
    balanced_repos = repo_year_counts[repo_year_counts == len(years)].index.tolist()

    print(f"\n  Repos com todos os {len(years)} years (painel balanceado): {len(balanced_repos)}")

    if len(balanced_repos) < 10:
        # Tentar com menos anos
        for min_years in range(len(years) - 1, 1, -1):
            balanced = repo_year_counts[repo_year_counts >= min_years].index.tolist()
            if len(balanced) >= 20:
                print(f"  Usando painel com ≥{min_years} years: {len(balanced)} repos")
                balanced_repos = balanced
                years = sorted(df[df['repo_name'].isin(balanced)]['project_year'].unique())[:min_years]
                break

    balanced_df = df[df['repo_name'].isin(balanced_repos)]

    # ---- 3b. Variação de smells entre anos consecutivos ----
    print("\n  Variação mediana entre project years:")
    for i in range(len(years) - 1):
        y1, y2 = years[i], years[i + 1]
        d1 = balanced_df[balanced_df['project_year'] == y1].set_index('repo_name')
        d2 = balanced_df[balanced_df['project_year'] == y2].set_index('repo_name')
        common = d1.index.intersection(d2.index)

        if 'total_code_smells' in d1.columns and len(common) > 0:
            diff = d2.loc[common, 'total_code_smells'] - d1.loc[common, 'total_code_smells']
            print(f"    Year {y1} → {y2}: Δ median={diff.median():.1f}, "
                  f"mean={diff.mean():.1f}, "
                  f"↑ {(diff > 0).sum()}/{len(common)}, "
                  f"↓ {(diff < 0).sum()}/{len(common)}, "
                  f"= {(diff == 0).sum()}/{len(common)}")

    # ---- 3c. Testes estatísticos ----
    if HAS_SCIPY and len(balanced_repos) >= 10:
        print("\n  Testes estatísticos:")

        # Friedman test (comparação entre múltiplos anos pareados)
        if len(years) >= 3 and 'total_code_smells' in balanced_df.columns:
            groups = []
            for y in years:
                vals = balanced_df[balanced_df['project_year'] == y].set_index('repo_name')
                if 'total_code_smells' in vals.columns:
                    groups.append(vals['total_code_smells'].reindex(balanced_repos))

            # Remover repos com NaN
            valid_mask = pd.concat(groups, axis=1).dropna().index
            if len(valid_mask) >= 10:
                clean_groups = [g.loc[valid_mask].values for g in groups]
                try:
                    stat, p = scipy_stats.friedmanchisquare(*clean_groups)
                    print(f"    Friedman (code smells, {len(years)} years, n={len(valid_mask)}): "
                          f"χ²={stat:.3f}, p={p:.4f}")
                except Exception as e:
                    print(f"    Friedman: erro - {e}")

        # Wilcoxon signed-rank entre Year 1 e último year
        if len(years) >= 2:
            for metric in ['total_code_smells', 'lone_wolf', 'radio_silence']:
                if metric not in balanced_df.columns:
                    continue
                y1_data = balanced_df[balanced_df['project_year'] == years[0]].set_index('repo_name')
                yn_data = balanced_df[balanced_df['project_year'] == years[-1]].set_index('repo_name')
                common = y1_data.index.intersection(yn_data.index)

                v1 = y1_data.loc[common, metric].dropna()
                vn = yn_data.loc[common, metric].dropna()
                common_clean = v1.index.intersection(vn.index)

                if len(common_clean) >= 10:
                    try:
                        stat, p = scipy_stats.wilcoxon(
                            v1.loc[common_clean], vn.loc[common_clean],
                            alternative='two-sided'
                        )
                        print(f"    Wilcoxon {metric} (Year {years[0]} vs {years[-1]}, "
                              f"n={len(common_clean)}): W={stat:.1f}, p={p:.4f}")
                    except Exception as e:
                        print(f"    Wilcoxon {metric}: {e}")

    # ---- 3d. Figuras ----
    if HAS_MPL and fig_dir:
        _plot_evolution(balanced_df, years, balanced_repos, fig_dir)


def _plot_evolution(df: 'pd.DataFrame', years: list, repos: list, fig_dir: str):
    """Gera figuras de evolução temporal."""
    os.makedirs(fig_dir, exist_ok=True)

    # --- Figura 1: Evolução de Code Smells (boxplot por year) ---
    if 'total_code_smells' in df.columns:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Boxplot
        ax = axes[0]
        data_by_year = []
        labels = []
        for y in years:
            vals = df[df['project_year'] == y]['total_code_smells'].dropna()
            data_by_year.append(vals)
            labels.append(f'Year {y}\n(n={len(vals)})')

        bp = ax.boxplot(data_by_year, labels=labels, patch_artist=True,
                        showfliers=False, widths=0.6)
        colors = plt.cm.Blues(np.linspace(0.3, 0.8, len(years)))
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_edgecolor('black')
            patch.set_linewidth(0.5)

        ax.set_xlabel('Project Year', fontsize=11)
        ax.set_ylabel('Total Code Smells', fontsize=11)
        ax.set_title('Code Smells por Project Year', fontsize=12)

        # Medians com labels
        for i, y in enumerate(years):
            median = data_by_year[i].median()
            ax.text(i + 1, median, f'{median:.0f}', ha='center', va='bottom',
                    fontsize=8, fontweight='bold', color='darkblue')

        # Line plot de medianas
        ax2 = axes[1]
        medians = [d.median() for d in data_by_year]
        q25 = [d.quantile(0.25) for d in data_by_year]
        q75 = [d.quantile(0.75) for d in data_by_year]

        ax2.fill_between(years, q25, q75, alpha=0.2, color='steelblue', label='IQR')
        ax2.plot(years, medians, 'o-', color='steelblue', linewidth=2,
                 markersize=8, label='Mediana')
        ax2.set_xlabel('Project Year', fontsize=11)
        ax2.set_ylabel('Total Code Smells (mediana)', fontsize=11)
        ax2.set_title('Tendência Temporal - Code Smells', fontsize=12)
        ax2.set_xticks(years)
        ax2.legend(fontsize=9)
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        path = os.path.join(fig_dir, 'fig_temporal_code_smells.pdf')
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ {path}")

    # --- Figura 2: Evolução de Community Smells (prevalência) ---
    cs_indicators = ['lone_wolf', 'radio_silence']
    available_cs = [c for c in cs_indicators if c in df.columns]

    if available_cs:
        fig, ax = plt.subplots(figsize=(8, 5))

        colors_cs = {'lone_wolf': '#e74c3c', 'radio_silence': '#3498db',
                     'org_silo': '#2ecc71', 'org_silo_proxy': '#f39c12'}
        labels_cs = {'lone_wolf': 'Lone Wolf', 'radio_silence': 'Radio Silence',
                     'org_silo': 'Org Silo', 'org_silo_proxy': 'Org Silo (proxy)'}

        for indicator in available_cs:
            prevalences = []
            for y in years:
                year_df = df[df['project_year'] == y]
                vals = year_df[indicator].dropna()
                if len(vals) > 0:
                    prevalences.append(vals.sum() / len(vals) * 100)
                else:
                    prevalences.append(0)

            ax.plot(years, prevalences, 'o-', color=colors_cs.get(indicator, 'gray'),
                    linewidth=2, markersize=8, label=labels_cs.get(indicator, indicator))

            # Anotar valores
            for x, y_val in zip(years, prevalences):
                ax.annotate(f'{y_val:.1f}%', (x, y_val),
                           textcoords="offset points", xytext=(0, 10),
                           ha='center', fontsize=8)

        ax.set_xlabel('Project Year', fontsize=11)
        ax.set_ylabel('Prevalência (%)', fontsize=11)
        ax.set_title('Evolução de Community Smells por Project Year', fontsize=12)
        ax.set_xticks(years)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)

        plt.tight_layout()
        path = os.path.join(fig_dir, 'fig_temporal_community_smells.pdf')
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ {path}")

    # --- Figura 3: Evolução do Bus Factor ---
    if 'bus_factor_number' in df.columns:
        fig, ax = plt.subplots(figsize=(8, 5))

        bf_medians = []
        bf_q25 = []
        bf_q75 = []
        for y in years:
            vals = df[df['project_year'] == y]['bus_factor_number'].dropna()
            bf_medians.append(vals.median() if len(vals) > 0 else np.nan)
            bf_q25.append(vals.quantile(0.25) if len(vals) > 0 else np.nan)
            bf_q75.append(vals.quantile(0.75) if len(vals) > 0 else np.nan)

        ax.fill_between(years, bf_q25, bf_q75, alpha=0.2, color='coral')
        ax.plot(years, bf_medians, 'o-', color='coral', linewidth=2, markersize=8)

        for x, y_val in zip(years, bf_medians):
            if not np.isnan(y_val):
                ax.annotate(f'{y_val:.2f}', (x, y_val),
                           textcoords="offset points", xytext=(0, 10),
                           ha='center', fontsize=9, fontweight='bold')

        ax.set_xlabel('Project Year', fontsize=11)
        ax.set_ylabel('Bus Factor (mediana)', fontsize=11)
        ax.set_title('Evolução do Bus Factor por Project Year', fontsize=12)
        ax.set_xticks(years)
        ax.axhline(y=0.9, color='red', linestyle='--', alpha=0.5,
                   label='Limiar Lone Wolf (0.9)')
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 1.05)

        plt.tight_layout()
        path = os.path.join(fig_dir, 'fig_temporal_bus_factor.pdf')
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ {path}")

    # --- Figura 4: Coocorrência por Project Year ---
    if 'total_code_smells' in df.columns and available_cs:
        fig, axes = plt.subplots(1, len(available_cs), figsize=(6 * len(available_cs), 5))
        if len(available_cs) == 1:
            axes = [axes]

        for idx, indicator in enumerate(available_cs):
            ax = axes[idx]
            label = labels_cs.get(indicator, indicator)

            medians_with = []
            medians_without = []

            for y in years:
                year_df = df[df['project_year'] == y]
                with_smell = year_df[year_df[indicator] == 1]['total_code_smells'].dropna()
                without_smell = year_df[year_df[indicator] == 0]['total_code_smells'].dropna()
                medians_with.append(with_smell.median() if len(with_smell) > 0 else 0)
                medians_without.append(without_smell.median() if len(without_smell) > 0 else 0)

            x = np.arange(len(years))
            width = 0.35
            ax.bar(x - width/2, medians_with, width, label=f'Com {label}',
                   color=colors_cs.get(indicator, 'gray'), alpha=0.8, edgecolor='black', linewidth=0.5)
            ax.bar(x + width/2, medians_without, width, label=f'Sem {label}',
                   color='#ecf0f1', edgecolor='black', linewidth=0.5)

            ax.set_xlabel('Project Year', fontsize=10)
            ax.set_ylabel('Code Smells (mediana)', fontsize=10)
            ax.set_title(f'Code Smells × {label}', fontsize=11)
            ax.set_xticks(x)
            ax.set_xticklabels([f'Y{y}' for y in years])
            ax.legend(fontsize=9)

        plt.tight_layout()
        path = os.path.join(fig_dir, 'fig_temporal_cooccurrence.pdf')
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ {path}")


# ============================================================
# 4. COOCORRÊNCIA POR PROJECT YEAR
# ============================================================
def cooccurrence_by_year(df: 'pd.DataFrame', output_dir: str):
    """Analisa coocorrência de smells por project year."""
    print("\n" + "=" * 60)
    print("4. COOCORRÊNCIA POR PROJECT YEAR")
    print("=" * 60)

    years = sorted(df['project_year'].unique())
    cs_indicators = ['lone_wolf', 'radio_silence']
    cs_indicators = [c for c in cs_indicators if c in df.columns]

    if not cs_indicators or 'total_code_smells' not in df.columns:
        print("  [SKIP] Dados insuficientes")
        return

    rows = []
    for y in years:
        year_df = df[df['project_year'] == y]
        n = len(year_df)

        for indicator in cs_indicators:
            with_smell = year_df[year_df[indicator] == 1]
            without_smell = year_df[year_df[indicator] == 0]

            row = {
                'project_year': y,
                'community_smell': indicator,
                'n_total': n,
                'n_with': len(with_smell),
                'n_without': len(without_smell),
                'prevalence_pct': round(len(with_smell) / n * 100, 1) if n > 0 else 0,
                'cs_median_with': round(with_smell['total_code_smells'].median(), 1) if len(with_smell) > 0 else None,
                'cs_median_without': round(without_smell['total_code_smells'].median(), 1) if len(without_smell) > 0 else None,
            }

            # Mann-Whitney U
            if HAS_SCIPY and len(with_smell) >= 5 and len(without_smell) >= 5:
                try:
                    u, p = scipy_stats.mannwhitneyu(
                        with_smell['total_code_smells'].dropna(),
                        without_smell['total_code_smells'].dropna(),
                        alternative='two-sided'
                    )
                    n1, n2 = len(with_smell), len(without_smell)
                    r_rb = 1 - (2 * u) / (n1 * n2)  # rank-biserial
                    row['mann_whitney_U'] = round(u, 1)
                    row['mann_whitney_p'] = round(p, 4)
                    row['rank_biserial'] = round(r_rb, 3)
                except:
                    pass

            # Spearman com Bus Factor
            if 'bus_factor_number' in year_df.columns:
                valid = year_df[['total_code_smells', 'bus_factor_number']].dropna()
                if len(valid) >= 10:
                    try:
                        rho, p = scipy_stats.spearmanr(
                            valid['total_code_smells'], valid['bus_factor_number']
                        )
                        row['spearman_bf_rho'] = round(rho, 3)
                        row['spearman_bf_p'] = round(p, 4)
                    except:
                        pass

            rows.append(row)
            print(f"  Year {y} × {indicator}: "
                  f"prevalence={row['prevalence_pct']}%, "
                  f"CS median with={row.get('cs_median_with', 'N/A')}, "
                  f"without={row.get('cs_median_without', 'N/A')}")

    cooc_df = pd.DataFrame(rows)
    path = os.path.join(output_dir, "temporal_cooccurrence.csv")
    cooc_df.to_csv(path, index=False)
    print(f"\n  Salvo: {path}")


# ============================================================
# 5. SPEARMAN POR PROJECT YEAR (Evolução das correlações)
# ============================================================
def correlations_by_year(df: 'pd.DataFrame', output_dir: str, fig_dir: str):
    """Computa correlações de Spearman por project year."""
    print("\n" + "=" * 60)
    print("5. CORRELAÇÕES POR PROJECT YEAR")
    print("=" * 60)

    if not HAS_SCIPY:
        print("  [SKIP] scipy não disponível")
        return

    years = sorted(df['project_year'].unique())
    social_vars = ['commit_count', 'author_count', 'bus_factor_number',
                   'pr_count', 'issue_count', 'timezone_count']
    tech_vars = ['total_code_smells', 'total_design_smells', 'total_impl_smells']

    social_vars = [v for v in social_vars if v in df.columns]
    tech_vars = [v for v in tech_vars if v in df.columns]

    rows = []
    for y in years:
        year_df = df[df['project_year'] == y]
        for sv in social_vars:
            for tv in tech_vars:
                valid = year_df[[sv, tv]].dropna()
                if len(valid) >= 10:
                    try:
                        rho, p = scipy_stats.spearmanr(valid[sv], valid[tv])
                        rows.append({
                            'project_year': y,
                            'social_var': sv,
                            'tech_var': tv,
                            'n': len(valid),
                            'spearman_rho': round(rho, 4),
                            'p_value': round(p, 6),
                            'significant': p < 0.05,
                        })
                        if p < 0.05:
                            print(f"  Year {y}: {sv} × {tv}: ρ={rho:.3f}, p={p:.4f} *")
                    except:
                        pass

    if rows:
        corr_df = pd.DataFrame(rows)
        path = os.path.join(output_dir, "temporal_correlations.csv")
        corr_df.to_csv(path, index=False)
        print(f"\n  Salvo: {path}")

        # Figura: evolução do ρ(Bus Factor × Code Smells) ao longo dos years
        if HAS_MPL and fig_dir:
            bf_corr = corr_df[
                (corr_df['social_var'] == 'bus_factor_number') &
                (corr_df['tech_var'] == 'total_code_smells')
            ]
            if len(bf_corr) >= 2:
                fig, ax = plt.subplots(figsize=(8, 5))
                ax.plot(bf_corr['project_year'], bf_corr['spearman_rho'],
                        'o-', color='coral', linewidth=2, markersize=8)
                ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)

                for _, row in bf_corr.iterrows():
                    marker = '**' if row['p_value'] < 0.01 else ('*' if row['significant'] else '')
                    ax.annotate(f"ρ={row['spearman_rho']:.3f}{marker}",
                               (row['project_year'], row['spearman_rho']),
                               textcoords="offset points", xytext=(0, 12),
                               ha='center', fontsize=9)

                ax.set_xlabel('Project Year', fontsize=11)
                ax.set_ylabel('Spearman ρ', fontsize=11)
                ax.set_title('Evolução: Bus Factor × Code Smells', fontsize=12)
                ax.set_xticks(years)
                ax.grid(True, alpha=0.3)

                plt.tight_layout()
                path = os.path.join(fig_dir, 'fig_temporal_correlation_evolution.pdf')
                plt.savefig(path, dpi=300, bbox_inches='tight')
                plt.close()
                print(f"  ✓ {path}")


# ============================================================
# 6. SUMÁRIO PARA A DISSERTAÇÃO
# ============================================================
def generate_summary(df: 'pd.DataFrame', output_dir: str):
    """Gera um sumário textual para inclusão na dissertação."""
    print("\n" + "=" * 60)
    print("6. SUMÁRIO PARA A DISSERTAÇÃO")
    print("=" * 60)

    years = sorted(df['project_year'].unique())
    n_repos = df['repo_name'].nunique()

    summary = []
    summary.append(f"Dataset temporal: {n_repos} repositórios × {len(years)} project years")
    summary.append(f"Total de snapshots: {len(df)}")
    summary.append("")

    for y in years:
        yd = df[df['project_year'] == y]
        summary.append(f"Year {y} (n={len(yd)}):")
        if 'total_code_smells' in yd.columns:
            summary.append(f"  Code Smells: median={yd['total_code_smells'].median():.0f}, "
                          f"mean={yd['total_code_smells'].mean():.1f}")
        if 'lone_wolf' in yd.columns:
            lw = yd['lone_wolf'].sum()
            summary.append(f"  Lone Wolf: {lw}/{len(yd)} ({lw/len(yd)*100:.1f}%)")
        if 'radio_silence' in yd.columns:
            rs = yd['radio_silence'].sum()
            summary.append(f"  Radio Silence: {rs}/{len(yd)} ({rs/len(yd)*100:.1f}%)")
        if 'bus_factor_number' in yd.columns:
            summary.append(f"  Bus Factor: median={yd['bus_factor_number'].median():.3f}")
        summary.append("")

    summary_text = "\n".join(summary)
    print(summary_text)

    path = os.path.join(output_dir, "temporal_summary.txt")
    with open(path, 'w') as f:
        f.write(summary_text)
    print(f"\n  Salvo: {path}")


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Análise dos dados temporais por project year"
    )
    parser.add_argument("--input", required=True,
                        help="CSV com dados temporais (de 08_temporal_extraction.py)")
    parser.add_argument("--output-dir", default="analysis/temporal",
                        help="Diretório para CSVs de análise")
    parser.add_argument("--fig-dir", default=None,
                        help="Diretório para figuras (cap6)")

    args = parser.parse_args()

    if not HAS_PANDAS:
        print("[ERRO] pandas é necessário. Instale com: pip install pandas")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    if args.fig_dir:
        os.makedirs(args.fig_dir, exist_ok=True)

    # Carregar dados
    df = load_temporal_data(args.input)

    # Executar análises
    descriptive_stats_by_year(df, args.output_dir)
    evolution_analysis(df, args.output_dir, args.fig_dir)
    cooccurrence_by_year(df, args.output_dir)
    correlations_by_year(df, args.output_dir, args.fig_dir)
    generate_summary(df, args.output_dir)

    print("\n" + "=" * 60)
    print("  Análise temporal concluída!")
    print(f"  Resultados em: {args.output_dir}")
    if args.fig_dir:
        print(f"  Figuras em: {args.fig_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
