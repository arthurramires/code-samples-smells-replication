#!/usr/bin/env python3
"""
11_consolidate_unified.py — Consolidação Unificada V1 + V2
==========================================================
Consolida resultados do Designite + csDetector de AMBAS as versões do dataset:
  - V1: resultados já existentes (progress CSV)
  - V2: resultados novos (manifesto JSON do pipeline incremental)

Gera:
  1. consolidated_code_smells.csv  — contagem de code smells por repo
  2. consolidated_metrics.csv      — métricas técnicas agregadas por repo
  3. consolidated_community.csv    — métricas comunitárias por repo
  4. consolidated_full_unified.csv — merge de tudo (repos com ambos OK)

Uso:
  # Consolidar tudo (V1 + V2):
  python 11_consolidate_unified.py \
    --base-dir ~/mestrado-pipeline \
    --v1-progress ~/mestrado-pipeline/logs/progress_XXXXXXXX.csv \
    --v2-manifest ~/mestrado-pipeline/manifest.json \
    --output-dir ~/mestrado-pipeline/consolidated

  # Só V1 (como o 04_consolidate.py original):
  python 11_consolidate_unified.py \
    --base-dir ~/mestrado-pipeline \
    --v1-progress ~/mestrado-pipeline/logs/progress_XXXXXXXX.csv \
    --output-dir ~/mestrado-pipeline/consolidated

  # Só V2 (resultados novos):
  python 11_consolidate_unified.py \
    --base-dir ~/mestrado-pipeline \
    --v2-manifest ~/mestrado-pipeline/manifest.json \
    --output-dir ~/mestrado-pipeline/consolidated

Autor: Arthur Bueno (dissertação de mestrado)
"""

import argparse
import csv
import json
import os
import sys
import statistics
from collections import Counter
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Consolidação Unificada V1 + V2")
    p.add_argument("--base-dir", required=True, help="Diretório base (~mestrado-pipeline)")
    p.add_argument("--v1-progress", default=None, help="CSV de progresso V1 (04_consolidate format)")
    p.add_argument("--v2-manifest", default=None, help="JSON manifesto V2 (10_pipeline_incremental)")
    p.add_argument("--output-dir", required=True, help="Diretório de saída")
    p.add_argument("--v1-consolidated", default=None,
                   help="CSV consolidado V1 existente (pula re-processamento, só faz merge)")
    return p.parse_args()


# ============================================================
# Helpers
# ============================================================

def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def safe_mean(lst):
    return statistics.mean(lst) if lst else 0.0

def safe_median(lst):
    return statistics.median(lst) if lst else 0.0


# ============================================================
# Repo Status Collection
# ============================================================

def load_v1_repos(progress_path):
    """Lê CSV de progresso V1 → dict {repo_name: (d_status, cs_status)}"""
    repos = {}
    if not progress_path or not os.path.isfile(progress_path):
        return repos
    with open(progress_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("repo_name", "").strip()
            if name:
                repos[name] = (
                    row.get("designite_status", "UNKNOWN"),
                    row.get("csdetector_status", "UNKNOWN")
                )
    return repos

def load_v2_repos(manifest_path):
    """Lê manifesto JSON V2 → dict {repo_name: (d_status, cs_status)}"""
    repos = {}
    if not manifest_path or not os.path.isfile(manifest_path):
        return repos
    with open(manifest_path, "r") as f:
        data = json.load(f)
    for repo_name, stages in data.get("repos", {}).items():
        d_status = stages.get("designite_cross", {}).get("status", "PENDING")
        cs_status = stages.get("csdetector", {}).get("status", "PENDING")
        repos[repo_name] = (d_status, cs_status)
    return repos


# ============================================================
# Designite Consolidation (mesma lógica do 04_consolidate.py)
# ============================================================

DESIGN_SMELLS = [
    "God_Class", "Feature_Envy", "Unutilized_Abstraction", "Deficient_Encapsulation",
    "Unexploited_Encapsulation", "Multifaceted_Abstraction", "Insufficient_Modularization",
    "Hub_Like_Modularization", "Cyclically_Dependent_Modularization",
    "Broken_Hierarchy", "Rebellious_Hierarchy", "Missing_Hierarchy",
    "Wide_Hierarchy", "Deep_Hierarchy"
]

IMPL_SMELLS = [
    "Long_Method", "Complex_Method", "Long_Parameter_List", "Magic_Number",
    "Duplicate_Code", "Empty_Catch_Clause", "Long_Statement", "Long_Identifier",
    "Missing_Default", "Complex_Conditional"
]

DESIGN_SMELL_MAP = {s.replace("_", " "): s for s in DESIGN_SMELLS}
DESIGN_SMELL_MAP["Hub-like Modularization"] = "Hub_Like_Modularization"
DESIGN_SMELL_MAP["Cyclically-dependent Modularization"] = "Cyclically_Dependent_Modularization"

IMPL_SMELL_MAP = {s.replace("_", " "): s for s in IMPL_SMELLS}
IMPL_SMELL_MAP["Empty catch clause"] = "Empty_Catch_Clause"


def consolidate_designite(base_dir, repos):
    cs_dir = os.path.join(base_dir, "results", "code_smells")
    smell_rows = []
    metric_rows = []

    for repo_name, (d_status, _) in repos.items():
        if d_status not in ("OK", "SKIP"):
            continue

        repo_path = os.path.join(cs_dir, repo_name)
        if not os.path.isdir(repo_path):
            continue

        design_smells = Counter()
        impl_smells = Counter()

        design_file = os.path.join(repo_path, "designCodeSmells.csv")
        if os.path.isfile(design_file):
            with open(design_file, "r", errors="replace") as f:
                for row in csv.DictReader(f):
                    smell = row.get("Code Smell", "Unknown")
                    design_smells[smell] += 1

        impl_file = os.path.join(repo_path, "implementationCodeSmells.csv")
        if os.path.isfile(impl_file):
            with open(impl_file, "r", errors="replace") as f:
                for row in csv.DictReader(f):
                    smell = row.get("Code Smell", "Unknown")
                    impl_smells[smell] += 1

        total_design = sum(design_smells.values())
        total_impl = sum(impl_smells.values())

        smell_row = {
            "repo_name": repo_name,
            "total_design_smells": total_design,
            "total_impl_smells": total_impl,
            "total_code_smells": total_design + total_impl,
        }
        for display, field in DESIGN_SMELL_MAP.items():
            smell_row[field] = design_smells.get(display, 0)
        for display, field in IMPL_SMELL_MAP.items():
            smell_row[field] = impl_smells.get(display, 0)

        smell_rows.append(smell_row)

        # Type metrics
        type_file = os.path.join(repo_path, "typeMetrics.csv")
        locs, wmcs, nofs, noms = [], [], [], []
        fanins, fanouts, lcoms, dits = [], [], [], []
        num_classes = 0

        if os.path.isfile(type_file):
            with open(type_file, "r", errors="replace") as f:
                for row in csv.DictReader(f):
                    num_classes += 1
                    locs.append(safe_float(row.get("LOC", 0)))
                    wmcs.append(safe_float(row.get("WMC", 0)))
                    nofs.append(safe_float(row.get("NOF", 0)))
                    noms.append(safe_float(row.get("NOM", 0)))
                    fanins.append(safe_float(row.get("FANIN", 0)))
                    fanouts.append(safe_float(row.get("FANOUT", 0)))
                    lcoms.append(safe_float(row.get("LCOM", 0)))
                    dits.append(safe_float(row.get("DIT", 0)))

        method_file = os.path.join(repo_path, "methodMetrics.csv")
        method_locs, method_ccs = [], []
        num_methods = 0

        if os.path.isfile(method_file):
            with open(method_file, "r", errors="replace") as f:
                for row in csv.DictReader(f):
                    num_methods += 1
                    method_locs.append(safe_float(row.get("LOC", 0)))
                    method_ccs.append(safe_float(row.get("CC", 0)))

        total_loc = sum(locs)
        total_smells = smell_row["total_code_smells"]

        metric_rows.append({
            "repo_name": repo_name,
            "num_classes": num_classes,
            "num_methods": num_methods,
            "total_LOC": total_loc,
            "mean_LOC": round(safe_mean(locs), 2),
            "median_LOC": round(safe_median(locs), 2),
            "mean_WMC": round(safe_mean(wmcs), 2),
            "mean_NOM": round(safe_mean(noms), 2),
            "mean_FANIN": round(safe_mean(fanins), 2),
            "mean_FANOUT": round(safe_mean(fanouts), 2),
            "mean_LCOM": round(safe_mean(lcoms), 4),
            "mean_DIT": round(safe_mean(dits), 2),
            "mean_method_LOC": round(safe_mean(method_locs), 2),
            "mean_CC": round(safe_mean(method_ccs), 2),
            "max_CC": max(method_ccs) if method_ccs else 0,
            "smell_density": round((total_smells / total_loc * 1000) if total_loc > 0 else 0, 4),
        })

    return smell_rows, metric_rows


# ============================================================
# csDetector Consolidation
# ============================================================

def find_results_dir(repo_cs_path):
    for root, dirs, files in os.walk(repo_cs_path):
        if os.path.basename(root) == "results" and "metrics" in dirs:
            return root
    for root, dirs, files in os.walk(repo_cs_path):
        if "results_0.csv" in files:
            return root
    return None


def consolidate_csdetector(base_dir, repos):
    cs_dir = os.path.join(base_dir, "results", "community_smells")
    community_rows = []

    for repo_name, (_, cs_status) in repos.items():
        if cs_status not in ("OK", "SKIP"):
            continue

        repo_path = os.path.join(cs_dir, repo_name)
        if not os.path.isdir(repo_path):
            continue

        results_dir = find_results_dir(repo_path)
        if not results_dir:
            continue

        summary = {}
        results_file = os.path.join(results_dir, "results_0.csv")
        if os.path.isfile(results_file):
            with open(results_file, "r", errors="replace") as f:
                for row in csv.reader(f):
                    if len(row) >= 2:
                        summary[row[0].strip()] = row[1].strip()

        metrics_dir = os.path.join(results_dir, "metrics")

        # Timezones
        tz_count = 0
        tz_file = os.path.join(metrics_dir, "timezones_0.csv")
        if os.path.isfile(tz_file):
            with open(tz_file, "r", errors="replace") as f:
                tz_count = sum(1 for _ in csv.DictReader(f))

        # Author days
        author_days = []
        ad_file = os.path.join(metrics_dir, "authorDaysOnProject_0.csv")
        if os.path.isfile(ad_file):
            with open(ad_file, "r", errors="replace") as f:
                for row in csv.DictReader(f):
                    author_days.append(safe_int(row.get("# of Days", 0)))

        # Commits per author
        commits_per_author = []
        cpa_file = os.path.join(metrics_dir, "commitsPerAuthor_0.csv")
        if os.path.isfile(cpa_file):
            with open(cpa_file, "r", errors="replace") as f:
                for row in csv.DictReader(f):
                    commits_per_author.append(safe_int(row.get("Commit Count", 0)))

        # Centralities
        centralities = []
        cc_file = os.path.join(metrics_dir, "commitCentrality_centrality_0.csv")
        if os.path.isfile(cc_file):
            with open(cc_file, "r", errors="replace") as f:
                for row in csv.DictReader(f):
                    centralities.append(safe_float(row.get("Centrality", 0)))

        # Communities
        num_communities = 0
        comm_file = os.path.join(metrics_dir, "commitCentrality_community_0.csv")
        if os.path.isfile(comm_file):
            with open(comm_file, "r", errors="replace") as f:
                num_communities = sum(1 for _ in csv.DictReader(f))

        # PRs
        pr_participants = []
        prp_file = os.path.join(metrics_dir, "PRParticipants_0.csv")
        if os.path.isfile(prp_file):
            with open(prp_file, "r", errors="replace") as f:
                for row in csv.DictReader(f):
                    pr_participants.append(safe_int(row.get("Developer Count", 0)))

        # Issues
        issue_participants = []
        ip_file = os.path.join(metrics_dir, "issueParticipantCount_0.csv")
        if os.path.isfile(ip_file):
            with open(ip_file, "r", errors="replace") as f:
                for row in csv.DictReader(f):
                    issue_participants.append(safe_int(row.get("Developer Count", 0)))

        issue_comments = []
        ic_file = os.path.join(metrics_dir, "issueCommentsCount_0.csv")
        if os.path.isfile(ic_file):
            with open(ic_file, "r", errors="replace") as f:
                for row in csv.DictReader(f):
                    issue_comments.append(safe_int(row.get("Comment Count", 0)))

        author_count = len(commits_per_author)
        commit_count = safe_int(summary.get("CommitCount", 0))
        days_active = safe_int(summary.get("DaysActive", 0))

        community_rows.append({
            "repo_name": repo_name,
            "CommitCount": commit_count,
            "DaysActive": days_active,
            "AuthorCount": author_count,
            "TimezoneCount": tz_count,
            "NumberPRs": len(pr_participants) if pr_participants else None,
            "NumberIssues": len(issue_participants) if issue_participants else None,
            "BusFactorNumber": safe_float(summary.get("BusFactorNumber")) if summary.get("BusFactorNumber") else None,
            "commitCentrality_Density": safe_float(summary.get("commitCentrality_Density"))
                if summary.get("commitCentrality_Density") else None,
            "commitCentrality_Community Count": num_communities,
            "commitCentrality_NumberHighCentralityAuthors":
                safe_int(summary.get("commitCentrality_NumberHighCentralityAuthors"))
                if summary.get("commitCentrality_NumberHighCentralityAuthors") else None,
            "PRParticipantsCount_mean": round(safe_mean(pr_participants), 2) if pr_participants else None,
            "IssueParticipantCount_mean": round(safe_mean(issue_participants), 2) if issue_participants else None,
            "IssueCommentsCount_mean": round(safe_mean(issue_comments), 2) if issue_comments else None,
            "AuthorCommitCount_mean": round(safe_mean(commits_per_author), 2) if commits_per_author else None,
            "AuthorActiveDays_mean": round(safe_mean(author_days), 2) if author_days else None,
            "commitCentrality_Centrality_mean": round(safe_mean(centralities), 4) if centralities else None,
            # Indicadores heurísticos de Community Smells (mesmos do csDetector)
            "lone_wolf": 1 if safe_float(summary.get("BusFactorNumber", -1)) > 0.5 else 0,
            "radio_silence": 1 if (len(issue_comments) == 0 and len(pr_participants) == 0) else 0,
            "org_silo": 1 if num_communities >= 3 else 0,
        })

    return community_rows


def write_csv(rows, path, fieldnames=None):
    if not rows:
        print(f"  [WARN] Sem dados para {path}")
        return
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  [OK] {path} ({len(rows)} repos)")


# ============================================================
# Main
# ============================================================

def main():
    args = parse_args()
    base_dir = os.path.expanduser(args.base_dir)
    output_dir = os.path.expanduser(args.output_dir)

    print("=" * 60)
    print("  CONSOLIDAÇÃO UNIFICADA V1 + V2")
    print("=" * 60)

    # 1. Coletar repos de ambas as fontes
    v1_repos = load_v1_repos(args.v1_progress)
    v2_repos = load_v2_repos(args.v2_manifest)

    # Unificar (V2 tem precedência se houver overlap)
    all_repos = {}
    all_repos.update(v1_repos)
    all_repos.update(v2_repos)

    v1_ok = sum(1 for n,(d,c) in v1_repos.items() if d=="OK" and c=="OK")
    v2_ok = sum(1 for n,(d,c) in v2_repos.items() if d=="OK" and c=="OK")
    overlap = len(set(v1_repos.keys()) & set(v2_repos.keys()))

    print(f"\n  V1 repos: {len(v1_repos)} (ambos OK: {v1_ok})")
    print(f"  V2 repos: {len(v2_repos)} (ambos OK: {v2_ok})")
    print(f"  Overlap: {overlap}")
    print(f"  Total unificado: {len(all_repos)}")

    # 2. Se tiver V1 consolidado pré-existente, fazer merge rápido
    if args.v1_consolidated and os.path.isfile(args.v1_consolidated):
        print(f"\n  [FAST] Usando V1 pré-consolidado: {args.v1_consolidated}")
        import pandas as pd
        v1_df = pd.read_csv(args.v1_consolidated)
        v1_names = set(v1_df.repo_name)

        # Processar só V2 novos
        v2_only = {k: v for k, v in v2_repos.items() if k not in v1_names}
        print(f"  V2 novos para processar: {len(v2_only)}")

        if v2_only:
            v2_smells, v2_metrics = consolidate_designite(base_dir, v2_only)
            v2_community = consolidate_csdetector(base_dir, v2_only)

            # Merge com V1
            # (implementação simplificada — gerar os novos CSVs e concatenar)
            smell_rows_v2 = v2_smells
            community_rows_v2 = v2_community

            # Gerar merge completo
            community_dict_v2 = {r["repo_name"]: r for r in community_rows_v2}
            smell_dict_v2 = {r["repo_name"]: r for r in smell_rows_v2}
            metric_dict_v2 = {r["repo_name"]: r for r in v2_metrics}

            v2_full = []
            for rn in community_dict_v2:
                if rn in smell_dict_v2 and rn in metric_dict_v2:
                    merged = {}
                    merged.update(smell_dict_v2[rn])
                    for k, v in metric_dict_v2[rn].items():
                        if k != "repo_name": merged[k] = v
                    for k, v in community_dict_v2[rn].items():
                        if k != "repo_name": merged[k] = v
                    v2_full.append(merged)

            if v2_full:
                v2_new_df = pd.DataFrame(v2_full)
                unified = pd.concat([v1_df, v2_new_df], ignore_index=True)
            else:
                unified = v1_df

            unified.to_csv(os.path.join(output_dir, "consolidated_full_unified.csv"), index=False)
            print(f"\n  [OK] consolidated_full_unified.csv ({len(unified)} repos)")
        else:
            # Sem V2 novos, copiar V1
            import shutil
            dest = os.path.join(output_dir, "consolidated_full_unified.csv")
            shutil.copy2(args.v1_consolidated, dest)
            print(f"\n  [OK] Sem V2 novos; V1 copiado como unified ({len(v1_df)} repos)")

        return

    # 3. Consolidação completa (processar tudo)
    print("\n[1/4] Consolidando Designite...")
    smell_rows, metric_rows = consolidate_designite(base_dir, all_repos)
    write_csv(smell_rows, os.path.join(output_dir, "consolidated_code_smells.csv"))
    write_csv(metric_rows, os.path.join(output_dir, "consolidated_metrics.csv"))

    print("\n[2/4] Consolidando csDetector...")
    community_rows = consolidate_csdetector(base_dir, all_repos)
    write_csv(community_rows, os.path.join(output_dir, "consolidated_community.csv"))

    print("\n[3/4] Gerando dataset unificado...")
    smell_dict = {r["repo_name"]: r for r in smell_rows}
    metric_dict = {r["repo_name"]: r for r in metric_rows}
    community_dict = {r["repo_name"]: r for r in community_rows}

    full_rows = []
    for repo_name in community_dict:
        if repo_name in smell_dict and repo_name in metric_dict:
            merged = {}
            merged.update(smell_dict[repo_name])
            for k, v in metric_dict[repo_name].items():
                if k != "repo_name": merged[k] = v
            for k, v in community_dict[repo_name].items():
                if k != "repo_name": merged[k] = v
            full_rows.append(merged)

    write_csv(full_rows, os.path.join(output_dir, "consolidated_full_unified.csv"))

    print("\n" + "=" * 60)
    print("  RESUMO")
    print("=" * 60)
    print(f"  Code smells:  {len(smell_rows)} repos")
    print(f"  Metrics:      {len(metric_rows)} repos")
    print(f"  Community:    {len(community_rows)} repos")
    print(f"  Full unified: {len(full_rows)} repos")
    print("=" * 60)


if __name__ == "__main__":
    main()
