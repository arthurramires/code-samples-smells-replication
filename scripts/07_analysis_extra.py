#!/usr/bin/env python3
"""
Análises adicionais para N=300: scatter plots, Mann-Whitney, clusters, RQ2 temporal.
Gera figuras e imprime estatísticas para atualizar cap6/resultados.tex.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats as scipy_stats
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import KMeans
import warnings
import os

warnings.filterwarnings('ignore')

BASE = "/sessions/practical-bold-turing/mnt/Mestrado/Dissertação"
DADOS = os.path.join(BASE, "dados")
FIGS = os.path.join(BASE, "texto-quali", "cap6")

# Load merged dataset
df = pd.read_csv(os.path.join(DADOS, "consolidated_full_v2.csv"))
print(f"Loaded {len(df)} repos")

# Ensure numeric
for col in df.columns:
    if col != 'repo_name':
        df[col] = pd.to_numeric(df[col], errors='coerce')

N = len(df)

# ============================================================
# 1. SCATTER: Bus Factor vs Total Code Smells
# ============================================================
print("\n" + "="*60)
print("1. SCATTER: Bus Factor vs Total Code Smells")
print("="*60)

valid = df[['BusFactorNumber', 'total_code_smells']].dropna()
rho, p = scipy_stats.spearmanr(valid['BusFactorNumber'], valid['total_code_smells'])
print(f"  N={len(valid)}, ρ={rho:.3f}, p={p:.4f}")

fig, ax = plt.subplots(figsize=(8, 6))
ax.scatter(valid['BusFactorNumber'], valid['total_code_smells'], alpha=0.5, s=30, color='#3498db', edgecolors='black', linewidth=0.3)
# Trend line
z = np.polyfit(valid['BusFactorNumber'], valid['total_code_smells'], 1)
px = np.linspace(valid['BusFactorNumber'].min(), valid['BusFactorNumber'].max(), 100)
ax.plot(px, np.polyval(z, px), 'r--', linewidth=1.5, label=f'ρ = {rho:.3f} (p < 0.001)')
ax.set_xlabel('Bus Factor', fontsize=11)
ax.set_ylabel('Total Code Smells', fontsize=11)
ax.set_title(f'Bus Factor vs. Total Code Smells (N = {len(valid)})', fontsize=12)
ax.legend(fontsize=10)
plt.tight_layout()
plt.savefig(os.path.join(FIGS, 'fig_scatter_busfactor_smells.pdf'), dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ fig_scatter_busfactor_smells.pdf")

# ============================================================
# 2. SCATTER: Network Density vs Smell Density (if available)
# ============================================================
print("\n" + "="*60)
print("2. SCATTER: Density vs Impl Smells")
print("="*60)

# Use commitCentrality_Density vs total_impl_smells
valid2 = df[['commitCentrality_Density', 'total_impl_smells']].dropna()
valid2 = valid2[valid2['commitCentrality_Density'] > 0]  # exclude 0-density (solo devs)
rho2, p2 = scipy_stats.spearmanr(valid2['commitCentrality_Density'], valid2['total_impl_smells'])
print(f"  N={len(valid2)}, ρ={rho2:.3f}, p={p2:.4f}")

fig, ax = plt.subplots(figsize=(8, 6))
ax.scatter(valid2['commitCentrality_Density'], valid2['total_impl_smells'], alpha=0.5, s=30, color='#e74c3c', edgecolors='black', linewidth=0.3)
z2 = np.polyfit(valid2['commitCentrality_Density'], valid2['total_impl_smells'], 1)
px2 = np.linspace(valid2['commitCentrality_Density'].min(), valid2['commitCentrality_Density'].max(), 100)
ax.plot(px2, np.polyval(z2, px2), 'b--', linewidth=1.5, label=f'ρ = {rho2:.3f} (p = {p2:.4f})')
ax.set_xlabel('Network Density', fontsize=11)
ax.set_ylabel('Total Implementation Smells', fontsize=11)
ax.set_title(f'Network Density vs. Implementation Smells (N = {len(valid2)})', fontsize=12)
ax.legend(fontsize=10)
plt.tight_layout()
plt.savefig(os.path.join(FIGS, 'fig_scatter_density_smells.pdf'), dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ fig_scatter_density_smells.pdf")

# ============================================================
# 3. MANN-WHITNEY U TESTS
# ============================================================
print("\n" + "="*60)
print("3. MANN-WHITNEY U TESTS")
print("="*60)

for smell_name, col in [('Lone Wolf', 'lone_wolf'), ('Radio Silence', 'radio_silence'), ('Org Silo', 'org_silo')]:
    present = df[df[col] == 1]['total_code_smells'].dropna()
    absent = df[df[col] == 0]['total_code_smells'].dropna()
    if len(present) > 0 and len(absent) > 0:
        u, p = scipy_stats.mannwhitneyu(present, absent, alternative='two-sided')
        print(f"  {smell_name}:")
        print(f"    Present: n={len(present)}, median={present.median():.1f}, mean={present.mean():.1f}")
        print(f"    Absent:  n={len(absent)}, median={absent.median():.1f}, mean={absent.mean():.1f}")
        print(f"    U={u:.0f}, p={p:.4f} {'***' if p<0.001 else '**' if p<0.01 else '*' if p<0.05 else 'ns'}")
    print()

# Also for total_impl_smells
print("  --- Impl smells ---")
for smell_name, col in [('Lone Wolf', 'lone_wolf'), ('Radio Silence', 'radio_silence'), ('Org Silo', 'org_silo')]:
    present = df[df[col] == 1]['total_impl_smells'].dropna()
    absent = df[df[col] == 0]['total_impl_smells'].dropna()
    if len(present) > 0 and len(absent) > 0:
        u, p = scipy_stats.mannwhitneyu(present, absent, alternative='two-sided')
        print(f"  {smell_name} (impl):")
        print(f"    Present: n={len(present)}, median={present.median():.1f}")
        print(f"    Absent:  n={len(absent)}, median={absent.median():.1f}")
        print(f"    U={u:.0f}, p={p:.4f} {'***' if p<0.001 else '**' if p<0.01 else '*' if p<0.05 else 'ns'}")

# Generate boxplot figure
fig, axes = plt.subplots(1, 3, figsize=(14, 5))
for idx, (smell_name, col) in enumerate([('Lone Wolf', 'lone_wolf'), ('Radio Silence', 'radio_silence'), ('Org Silo', 'org_silo')]):
    present = df[df[col] == 1]['total_code_smells'].dropna()
    absent = df[df[col] == 0]['total_code_smells'].dropna()
    u, p = scipy_stats.mannwhitneyu(present, absent, alternative='two-sided')

    bp = axes[idx].boxplot([absent.values, present.values], labels=['Absent', 'Present'],
                           patch_artist=True, showfliers=True,
                           flierprops=dict(marker='o', markersize=3, alpha=0.5))
    bp['boxes'][0].set_facecolor('#2ecc71')
    bp['boxes'][1].set_facecolor('#e74c3c')

    sig_text = f'p = {p:.4f}' if p >= 0.001 else 'p < 0.001'
    if p < 0.05:
        sig_text += ' *'
    if p < 0.01:
        sig_text += '*'
    if p < 0.001:
        sig_text += '*'

    axes[idx].set_title(f'{smell_name}\n(U = {u:.0f}, {sig_text})', fontsize=10)
    axes[idx].set_ylabel('Total Code Smells' if idx == 0 else '')

    # Add median annotations
    axes[idx].annotate(f'Med={absent.median():.0f}', xy=(1, absent.median()),
                       xytext=(1.3, absent.median()), fontsize=8, color='green')
    axes[idx].annotate(f'Med={present.median():.0f}', xy=(2, present.median()),
                       xytext=(2.1, present.median()), fontsize=8, color='red')

fig.suptitle(f'Code Smells Distribution by Community Smell Indicators (N = {N})', fontsize=12, y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(FIGS, 'fig_boxplot_mann_whitney.pdf'), dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ fig_boxplot_mann_whitney.pdf")

# ============================================================
# 4. RQ2: TEMPORAL INDICATORS
# ============================================================
print("\n" + "="*60)
print("4. RQ2: TEMPORAL INDICATORS")
print("="*60)

valid_t = df[['DaysActive', 'total_code_smells']].dropna()
rho_t, p_t = scipy_stats.spearmanr(valid_t['DaysActive'], valid_t['total_code_smells'])
print(f"  DaysActive vs total_code_smells: ρ={rho_t:.3f}, p={p_t:.4f}")

# DaysActive stats
print(f"  DaysActive median: {df['DaysActive'].median():.0f} days ({df['DaysActive'].median()/365:.1f} years)")
print(f"  DaysActive range: {df['DaysActive'].min():.0f} - {df['DaysActive'].max():.0f}")

# Split by longevity
long_lived = df[df['DaysActive'] > 3000]
short_lived = df[df['DaysActive'] <= 1000]
print(f"\n  Long-lived (>3000 days): n={len(long_lived)}")
print(f"    Mean code smells: {long_lived['total_code_smells'].mean():.1f}")
print(f"    Mean impl smells: {long_lived['total_impl_smells'].mean():.1f}")
print(f"  Short-lived (<=1000 days): n={len(short_lived)}")
print(f"    Mean code smells: {short_lived['total_code_smells'].mean():.1f}")
print(f"    Mean impl smells: {short_lived['total_impl_smells'].mean():.1f}")

# CommitCount vs total_code_smells
valid_c = df[['CommitCount', 'total_code_smells']].dropna()
rho_c, p_c = scipy_stats.spearmanr(valid_c['CommitCount'], valid_c['total_code_smells'])
print(f"\n  CommitCount vs total_code_smells: ρ={rho_c:.3f}, p={p_c:.4f}")

# DaysActive vs CommitCount
valid_dc = df[['DaysActive', 'CommitCount']].dropna()
rho_dc, p_dc = scipy_stats.spearmanr(valid_dc['DaysActive'], valid_dc['CommitCount'])
print(f"  DaysActive vs CommitCount: ρ={rho_dc:.3f}, p={p_dc:.4f}")

# ============================================================
# 5. RQ3: K-MEANS CLUSTERING
# ============================================================
print("\n" + "="*60)
print("5. RQ3: K-MEANS CLUSTERING")
print("="*60)

# Select clustering variables
cluster_vars = ['total_code_smells', 'CommitCount', 'AuthorCount',
                'commitCentrality_Density', 'BusFactorNumber', 'DaysActive']
cluster_df = df[['repo_name'] + cluster_vars + ['lone_wolf', 'radio_silence', 'org_silo',
                 'total_impl_smells', 'total_design_smells']].dropna(subset=cluster_vars)

print(f"  Repos with complete clustering data: {len(cluster_df)}")

# Remove outliers (beyond ±2 std)
z_scores = (cluster_df[cluster_vars] - cluster_df[cluster_vars].mean()) / cluster_df[cluster_vars].std()
mask = (z_scores.abs() < 2).all(axis=1)
cluster_clean = cluster_df[mask].copy()
print(f"  After outlier removal (±2 std): {len(cluster_clean)}")

# Normalize
scaler = MinMaxScaler()
X = scaler.fit_transform(cluster_clean[cluster_vars])

# Elbow method
inertias = []
K_range = range(2, 8)
for k in K_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(X)
    inertias.append(km.inertia_)
    print(f"  k={k}: inertia={km.inertia_:.2f}")

# Use k=3
k_opt = 3
km = KMeans(n_clusters=k_opt, random_state=42, n_init=10)
cluster_clean['cluster'] = km.fit_predict(X)

print(f"\n  Optimal k={k_opt}")
for c in range(k_opt):
    sub = cluster_clean[cluster_clean['cluster'] == c]
    print(f"\n  Cluster {c} (n={len(sub)}):")
    print(f"    total_code_smells: mean={sub['total_code_smells'].mean():.1f}, median={sub['total_code_smells'].median():.1f}")
    print(f"    CommitCount: mean={sub['CommitCount'].mean():.1f}")
    print(f"    AuthorCount: mean={sub['AuthorCount'].mean():.1f}")
    print(f"    Density: mean={sub['commitCentrality_Density'].mean():.3f}")
    print(f"    BusFactor: mean={sub['BusFactorNumber'].mean():.3f}")
    print(f"    DaysActive: mean={sub['DaysActive'].mean():.0f}")
    print(f"    Lone Wolf: {sub['lone_wolf'].sum()}/{len(sub)} ({sub['lone_wolf'].mean()*100:.0f}%)")
    print(f"    Radio Silence: {sub['radio_silence'].sum()}/{len(sub)} ({sub['radio_silence'].mean()*100:.0f}%)")
    print(f"    Org Silo: {sub['org_silo'].sum()}/{len(sub)} ({sub['org_silo'].mean()*100:.0f}%)")
    print(f"    total_impl_smells: mean={sub['total_impl_smells'].mean():.1f}")
    print(f"    total_design_smells: mean={sub['total_design_smells'].mean():.1f}")

# Generate cluster figure
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
colors = ['#3498db', '#e74c3c', '#2ecc71']
markers = ['o', 's', '^']

for c in range(k_opt):
    sub = cluster_clean[cluster_clean['cluster'] == c]
    ax1.scatter(sub['CommitCount'], sub['total_code_smells'],
                c=colors[c], marker=markers[c], s=40, alpha=0.7,
                label=f'Cluster {c} (n={len(sub)})', edgecolors='black', linewidth=0.3)
    ax2.scatter(sub['BusFactorNumber'], sub['commitCentrality_Density'],
                c=colors[c], marker=markers[c], s=40, alpha=0.7,
                label=f'Cluster {c} (n={len(sub)})', edgecolors='black', linewidth=0.3)

ax1.set_xlabel('Commit Count', fontsize=11)
ax1.set_ylabel('Total Code Smells', fontsize=11)
ax1.set_title('(a) Code Smells vs. Commits', fontsize=11)
ax1.legend(fontsize=9)

ax2.set_xlabel('Bus Factor', fontsize=11)
ax2.set_ylabel('Network Density', fontsize=11)
ax2.set_title('(b) Bus Factor vs. Network Density', fontsize=11)
ax2.legend(fontsize=9)

fig.suptitle(f'K-Means Clusters (k={k_opt}, N={len(cluster_clean)})', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(FIGS, 'fig_clusters.pdf'), dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ fig_clusters.pdf")

# ============================================================
# 6. ADDITIONAL CORRELATIONS FOR TEXT
# ============================================================
print("\n" + "="*60)
print("6. ADDITIONAL CORRELATIONS")
print("="*60)

pairs = [
    ('CommitCount', 'total_code_smells'),
    ('CommitCount', 'total_impl_smells'),
    ('AuthorCount', 'total_code_smells'),
    ('DaysActive', 'total_code_smells'),
    ('NumberPRs', 'total_code_smells'),
    ('NumberIssues', 'total_code_smells'),
    ('commitCentrality_Density', 'total_code_smells'),
    ('BusFactorNumber', 'Long_Parameter_List'),
    ('BusFactorNumber', 'Deficient_Encapsulation'),
    ('BusFactorNumber', 'Complex_Method'),
    ('BusFactorNumber', 'Unutilized_Abstraction'),
    ('CommitCount', 'Long_Method'),
]

for a, b in pairs:
    if a in df.columns and b in df.columns:
        v = df[[a, b]].dropna()
        if len(v) > 3:
            rho, p = scipy_stats.spearmanr(v[a], v[b])
            print(f"  {a} x {b}: ρ={rho:.3f}, p={p:.4f} (N={len(v)})")

print("\nDone!")
