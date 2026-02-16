#!/usr/bin/env python3
"""
Análise completa do dataset expandido (300 repos community + 318 code smells).
Gera:
  - consolidated_full_v2.csv (merge community + code_smells + metrics)
  - Figuras para a dissertação
  - Estatísticas descritivas e correlações
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy import stats as scipy_stats
import warnings
import os
import sys

warnings.filterwarnings('ignore')

# Paths
BASE = "/sessions/practical-bold-turing/mnt/Mestrado/Dissertação"
DADOS = os.path.join(BASE, "dados")
FIGS = os.path.join(BASE, "texto-quali", "cap6")

# ============================================================
# 1. LOAD DATA
# ============================================================
print("=" * 60)
print("1. LOADING DATA")
print("=" * 60)

community = pd.read_csv(os.path.join(DADOS, "consolidated_community_new.csv"))
code_smells = pd.read_csv(os.path.join(DADOS, "consolidated_code_smells.csv"))
metrics = pd.read_csv(os.path.join(DADOS, "consolidated_metrics.csv"))

print(f"  Community repos: {len(community)}")
print(f"  Code smells repos: {len(code_smells)}")
print(f"  Metrics repos: {len(metrics)}")

# ============================================================
# 2. MATCH REPOS
# ============================================================
print("\n" + "=" * 60)
print("2. MATCHING REPOS")
print("=" * 60)

# Normalize names for matching
community['repo_name_lower'] = community['repo_name'].str.lower().str.strip()
code_smells['repo_name_lower'] = code_smells['repo_name'].str.lower().str.strip()
metrics['repo_name_lower'] = metrics['repo_name'].str.lower().str.strip()

# Inner join on repo names
merged = community.merge(code_smells, on='repo_name_lower', how='inner', suffixes=('_comm', '_cs'))
merged = merged.merge(metrics, on='repo_name_lower', how='left', suffixes=('', '_met'))

print(f"  Matched repos (community ∩ code_smells): {len(merged)}")
print(f"  Community only (no code smells): {len(community) - len(merged)}")

# Use code_smells repo_name as canonical
if 'repo_name_cs' in merged.columns:
    merged['repo_name'] = merged['repo_name_cs']

# ============================================================
# 3. COMPUTE COMMUNITY SMELL INDICATORS
# ============================================================
print("\n" + "=" * 60)
print("3. COMPUTING COMMUNITY SMELL INDICATORS")
print("=" * 60)

# Convert numeric columns
for col in ['CommitCount', 'AuthorCount', 'DaysActive', 'NumberPRs', 'NumberIssues',
            'TimezoneCount', 'BusFactorNumber', 'commitCentrality_Density',
            'commitCentrality_Community Count', 'commitCentrality_NumberHighCentralityAuthors',
            'commitCentrality_PercentageHighCentralityAuthors',
            'PRParticipantsCount_mean', 'IssueParticipantCount_mean',
            'IssueCommentsCount_mean', 'AuthorCommitCount_mean', 'AuthorCommitCount_stdev',
            'AuthorActiveDays_mean', 'commitCentrality_Centrality_mean']:
    if col in merged.columns:
        merged[col] = pd.to_numeric(merged[col], errors='coerce')

# Community Smell Indicators based on csDetector's ML model features:
# Lone Wolf: high bus factor (few devs do most work) + low centrality
# Radio Silence: low PR/issue participation + few comments
# Org Silo: high community count + low density

# Lone Wolf: BusFactorNumber > 0.9 (one dev does >90% of work)
merged['lone_wolf'] = (merged['BusFactorNumber'].fillna(0) > 0.9).astype(int)

# Radio Silence: 0 PRs AND 0 Issues (no community interaction)
merged['radio_silence'] = (
    (merged['NumberPRs'].fillna(0) == 0) &
    (merged['NumberIssues'].fillna(0) == 0)
).astype(int)

# Org Silo: community count >= 3 AND density < 0.3 (fragmented network)
merged['org_silo'] = (
    (merged['commitCentrality_Community Count'].fillna(0) >= 3) &
    (merged['commitCentrality_Density'].fillna(1) < 0.3)
).astype(int)

lw = merged['lone_wolf'].sum()
rs = merged['radio_silence'].sum()
os_count = merged['org_silo'].sum()
total = len(merged)

print(f"  Total matched repos: {total}")
print(f"  Lone Wolf: {lw} ({lw/total*100:.1f}%)")
print(f"  Radio Silence: {rs} ({rs/total*100:.1f}%)")
print(f"  Org Silo: {os_count} ({os_count/total*100:.1f}%)")
print(f"  No community smell: {total - merged[['lone_wolf','radio_silence','org_silo']].max(axis=1).sum()}")

# ============================================================
# 4. CODE SMELLS SUMMARY
# ============================================================
print("\n" + "=" * 60)
print("4. CODE SMELLS SUMMARY")
print("=" * 60)

cs_cols = [c for c in merged.columns if c in code_smells.columns and c not in
           ['repo_name', 'repo_name_lower', 'total_design_smells', 'total_impl_smells', 'total_code_smells']]

# Get total code smell columns
for total_col in ['total_code_smells', 'total_design_smells', 'total_impl_smells']:
    if total_col in merged.columns:
        merged[total_col] = pd.to_numeric(merged[total_col], errors='coerce')

if 'total_code_smells' in merged.columns:
    print(f"  Mean total code smells: {merged['total_code_smells'].mean():.1f}")
    print(f"  Median total code smells: {merged['total_code_smells'].median():.1f}")
    print(f"  Repos with 0 code smells: {(merged['total_code_smells'] == 0).sum()}")

# Specific code smell types
cs_type_cols = ['God_Class', 'Feature_Envy', 'Long_Method', 'Complex_Method',
                'Long_Parameter_List', 'Magic_Number', 'Duplicate_Code',
                'Unutilized_Abstraction', 'Deficient_Encapsulation']
for col in cs_type_cols:
    if col in merged.columns:
        merged[col] = pd.to_numeric(merged[col], errors='coerce')
        prevalence = (merged[col] > 0).sum()
        print(f"  {col}: present in {prevalence}/{total} repos ({prevalence/total*100:.1f}%)")

# ============================================================
# 5. SPEARMAN CORRELATIONS
# ============================================================
print("\n" + "=" * 60)
print("5. SPEARMAN CORRELATIONS")
print("=" * 60)

# Community metrics
comm_metrics = ['CommitCount', 'AuthorCount', 'DaysActive', 'TimezoneCount',
                'NumberPRs', 'NumberIssues', 'BusFactorNumber',
                'commitCentrality_Density', 'commitCentrality_Community Count',
                'lone_wolf', 'radio_silence', 'org_silo']

# Code smell metrics
cs_metrics = ['total_code_smells', 'total_design_smells', 'total_impl_smells',
              'God_Class', 'Long_Method', 'Complex_Method', 'Long_Parameter_List',
              'Unutilized_Abstraction', 'Deficient_Encapsulation']

# Filter to existing columns
comm_metrics = [c for c in comm_metrics if c in merged.columns]
cs_metrics = [c for c in cs_metrics if c in merged.columns]

# Compute correlation matrix
corr_data = merged[comm_metrics + cs_metrics].apply(pd.to_numeric, errors='coerce')
corr_matrix = corr_data[comm_metrics].corrwith(corr_data[cs_metrics], method='spearman')

# Full pairwise matrix for heatmap
full_corr = pd.DataFrame(index=comm_metrics, columns=cs_metrics, dtype=float)
full_pval = pd.DataFrame(index=comm_metrics, columns=cs_metrics, dtype=float)

for cm in comm_metrics:
    for cs in cs_metrics:
        valid = corr_data[[cm, cs]].dropna()
        if len(valid) > 3:
            rho, p = scipy_stats.spearmanr(valid[cm], valid[cs])
            full_corr.loc[cm, cs] = rho
            full_pval.loc[cm, cs] = p
        else:
            full_corr.loc[cm, cs] = np.nan
            full_pval.loc[cm, cs] = np.nan

# Print significant correlations
print("\n  Significant correlations (p < 0.05):")
for cm in comm_metrics:
    for cs in cs_metrics:
        rho = full_corr.loc[cm, cs]
        p = full_pval.loc[cm, cs]
        if pd.notna(p) and p < 0.05 and abs(rho) > 0.1:
            print(f"    {cm} x {cs}: ρ={rho:.3f}, p={p:.4f}")

# ============================================================
# 6. GENERATE FIGURES
# ============================================================
print("\n" + "=" * 60)
print("6. GENERATING FIGURES")
print("=" * 60)

os.makedirs(FIGS, exist_ok=True)

# --- Figure: Heatmap Spearman ---
fig, ax = plt.subplots(figsize=(14, 8))

# Clean labels
label_map_comm = {
    'CommitCount': 'Commits', 'AuthorCount': 'Authors', 'DaysActive': 'Days Active',
    'TimezoneCount': 'Timezones', 'NumberPRs': 'PRs', 'NumberIssues': 'Issues',
    'BusFactorNumber': 'Bus Factor', 'commitCentrality_Density': 'Network Density',
    'commitCentrality_Community Count': 'Communities',
    'lone_wolf': 'Lone Wolf', 'radio_silence': 'Radio Silence', 'org_silo': 'Org Silo'
}
label_map_cs = {
    'total_code_smells': 'Total Smells', 'total_design_smells': 'Design Smells',
    'total_impl_smells': 'Impl. Smells', 'God_Class': 'God Class',
    'Long_Method': 'Long Method', 'Complex_Method': 'Complex Method',
    'Long_Parameter_List': 'Long Param List', 'Unutilized_Abstraction': 'Unutilized Abstr.',
    'Deficient_Encapsulation': 'Deficient Encaps.'
}

plot_corr = full_corr.copy()
plot_corr.index = [label_map_comm.get(c, c) for c in plot_corr.index]
plot_corr.columns = [label_map_cs.get(c, c) for c in plot_corr.columns]

im = ax.imshow(plot_corr.values.astype(float), cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')

# Add text annotations
for i in range(len(plot_corr.index)):
    for j in range(len(plot_corr.columns)):
        val = plot_corr.values[i, j]
        p = full_pval.values[i, j]
        if pd.notna(val):
            color = 'white' if abs(float(val)) > 0.5 else 'black'
            text = f'{float(val):.2f}'
            if pd.notna(p) and float(p) < 0.05:
                text += '*'
            if pd.notna(p) and float(p) < 0.01:
                text += '*'
            ax.text(j, i, text, ha='center', va='center', fontsize=7, color=color)

ax.set_xticks(range(len(plot_corr.columns)))
ax.set_xticklabels(plot_corr.columns, rotation=45, ha='right', fontsize=9)
ax.set_yticks(range(len(plot_corr.index)))
ax.set_yticklabels(plot_corr.index, fontsize=9)
plt.colorbar(im, ax=ax, label='Spearman ρ', shrink=0.8)
ax.set_title(f'Spearman Correlation: Community Metrics × Code Smells (n={total})', fontsize=11)
plt.tight_layout()
plt.savefig(os.path.join(FIGS, 'fig_heatmap_spearman.pdf'), dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ fig_heatmap_spearman.pdf")

# --- Figure: Community Smells Bar Chart ---
fig, ax = plt.subplots(figsize=(8, 5))
smells = ['Lone Wolf', 'Radio Silence', 'Org Silo']
present = [lw, rs, os_count]
absent = [total - lw, total - rs, total - os_count]

x = np.arange(len(smells))
width = 0.35
bars1 = ax.bar(x - width/2, present, width, label='Present', color='#e74c3c', edgecolor='black', linewidth=0.5)
bars2 = ax.bar(x + width/2, absent, width, label='Absent', color='#2ecc71', edgecolor='black', linewidth=0.5)

for bar, val in zip(bars1, present):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
            f'{val}\n({val/total*100:.1f}%)', ha='center', va='bottom', fontsize=9)
for bar, val in zip(bars2, absent):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
            f'{val}\n({val/total*100:.1f}%)', ha='center', va='bottom', fontsize=9)

ax.set_xlabel('Community Smell', fontsize=11)
ax.set_ylabel('Number of Repositories', fontsize=11)
ax.set_title(f'Community Smells Distribution (n={total})', fontsize=12)
ax.set_xticks(x)
ax.set_xticklabels(smells, fontsize=10)
ax.legend(fontsize=10)
ax.set_ylim(0, max(absent) * 1.25)
plt.tight_layout()
plt.savefig(os.path.join(FIGS, 'fig_community_smells.pdf'), dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ fig_community_smells.pdf")

# --- Figure: Dataset Coverage ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Pie chart
matched = total
unmatched_comm = len(community) - total
unmatched_cs = len(code_smells) - total
ax1.pie([matched, unmatched_cs], labels=[f'Matched\n(n={matched})', f'Code Smells only\n(n={unmatched_cs})'],
        colors=['#3498db', '#ecf0f1'], autopct='%1.1f%%', startangle=90,
        wedgeprops={'edgecolor': 'black', 'linewidth': 0.5}, textprops={'fontsize': 10})
ax1.set_title(f'csDetector Coverage\n({matched}/{len(code_smells)} repos)', fontsize=11)

# Literature comparison
studies = ['This study', 'Almarimi et al.\n(2022)', 'Caballero et al.\n(2023)', 'De Stefano et al.\n(2021)']
sizes = [matched, 74, 48, 10]
colors_bar = ['#3498db', '#95a5a6', '#95a5a6', '#95a5a6']
bars = ax2.barh(studies, sizes, color=colors_bar, edgecolor='black', linewidth=0.5)
for bar, val in zip(bars, sizes):
    ax2.text(bar.get_width() + 3, bar.get_y() + bar.get_height()/2,
             str(val), ha='left', va='center', fontsize=10, fontweight='bold')
ax2.set_xlabel('Number of Repositories', fontsize=11)
ax2.set_title('Sample Size Comparison\nwith Related Studies', fontsize=11)
ax2.set_xlim(0, max(sizes) * 1.2)

plt.tight_layout()
plt.savefig(os.path.join(FIGS, 'fig_dataset_coverage.pdf'), dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ fig_dataset_coverage.pdf")

# --- Figure: Co-occurrence heatmap (community smells x top code smells) ---
fig, ax = plt.subplots(figsize=(10, 4))

cooccur = pd.DataFrame(index=['Lone Wolf', 'Radio Silence', 'Org Silo'],
                        columns=cs_type_cols[:7], dtype=float)

for cs_col in cs_type_cols[:7]:
    if cs_col not in merged.columns:
        continue
    has_cs = (merged[cs_col].fillna(0) > 0)
    cooccur.loc['Lone Wolf', cs_col] = (merged['lone_wolf'] & has_cs).sum()
    cooccur.loc['Radio Silence', cs_col] = (merged['radio_silence'] & has_cs).sum()
    cooccur.loc['Org Silo', cs_col] = (merged['org_silo'] & has_cs).sum()

# Normalize by total repos with that community smell
cooccur_pct = cooccur.copy()
totals = {'Lone Wolf': lw, 'Radio Silence': rs, 'Org Silo': os_count}
for smell, t in totals.items():
    if t > 0:
        cooccur_pct.loc[smell] = cooccur.loc[smell] / t * 100

cooccur_pct.columns = [c.replace('_', ' ') for c in cooccur_pct.columns]

im = ax.imshow(cooccur_pct.values.astype(float), cmap='YlOrRd', aspect='auto', vmin=0, vmax=100)
for i in range(len(cooccur_pct.index)):
    for j in range(len(cooccur_pct.columns)):
        val = cooccur_pct.values[i, j]
        raw = cooccur.values[i, j]
        if pd.notna(val):
            color = 'white' if float(val) > 60 else 'black'
            ax.text(j, i, f'{int(raw)}\n({float(val):.0f}%)', ha='center', va='center',
                    fontsize=8, color=color)

ax.set_xticks(range(len(cooccur_pct.columns)))
ax.set_xticklabels(cooccur_pct.columns, rotation=45, ha='right', fontsize=9)
ax.set_yticks(range(len(cooccur_pct.index)))
ax.set_yticklabels(cooccur_pct.index, fontsize=10)
plt.colorbar(im, ax=ax, label='% repos with co-occurrence', shrink=0.8)
ax.set_title(f'Co-occurrence: Community Smells × Code Smells (n={total})', fontsize=11)
plt.tight_layout()
plt.savefig(os.path.join(FIGS, 'fig_cooccurrence.pdf'), dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ fig_cooccurrence.pdf")

# ============================================================
# 7. SAVE MERGED DATASET
# ============================================================
print("\n" + "=" * 60)
print("7. SAVING MERGED DATASET")
print("=" * 60)

# Select key columns for output
output_cols = ['repo_name']
# Community metrics
for c in ['CommitCount', 'AuthorCount', 'DaysActive', 'TimezoneCount',
          'NumberPRs', 'NumberIssues', 'BusFactorNumber',
          'commitCentrality_Density', 'commitCentrality_Community Count',
          'commitCentrality_NumberHighCentralityAuthors',
          'PRParticipantsCount_mean', 'IssueParticipantCount_mean',
          'IssueCommentsCount_mean', 'AuthorCommitCount_mean',
          'AuthorActiveDays_mean', 'commitCentrality_Centrality_mean']:
    if c in merged.columns:
        output_cols.append(c)

# Community smell indicators
output_cols.extend(['lone_wolf', 'radio_silence', 'org_silo'])

# Code smells
for c in ['total_code_smells', 'total_design_smells', 'total_impl_smells'] + cs_type_cols:
    if c in merged.columns:
        output_cols.append(c)

# Deduplicate
output_cols = list(dict.fromkeys(output_cols))
output = merged[output_cols].copy()

output_path = os.path.join(DADOS, "consolidated_full_v2.csv")
output.to_csv(output_path, index=False)
print(f"  Saved {len(output)} repos to {output_path}")

# ============================================================
# 8. SUMMARY STATISTICS
# ============================================================
print("\n" + "=" * 60)
print("8. SUMMARY FOR DISSERTATION")
print("=" * 60)
print(f"  Dataset: {len(code_smells)} repos with code smells (Designite)")
print(f"  Community analysis: {len(community)} repos processed (csDetector-fixed)")
print(f"  Matched (code + community): {total} repos ({total/len(code_smells)*100:.1f}%)")
print(f"")
print(f"  Community Smells:")
print(f"    Lone Wolf: {lw}/{total} ({lw/total*100:.1f}%)")
print(f"    Radio Silence: {rs}/{total} ({rs/total*100:.1f}%)")
print(f"    Org Silo: {os_count}/{total} ({os_count/total*100:.1f}%)")
print(f"")
print(f"  Community metrics (median):")
print(f"    Commits: {merged['CommitCount'].median():.0f}")
print(f"    Authors: {merged['AuthorCount'].median():.0f}")
print(f"    Days active: {merged['DaysActive'].median():.0f}")
print(f"    PRs: {merged['NumberPRs'].median():.0f}")
print(f"    Issues: {merged['NumberIssues'].median():.0f}")

print(f"\n  Figures generated in: {FIGS}")
print(f"  Done!")
