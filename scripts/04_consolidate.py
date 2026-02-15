#!/usr/bin/env python3
"""
04_consolidate.py — Consolidação dos resultados do pipeline Designite + csDetector.

Gera 4 CSVs principais:
  1. consolidated_code_smells.csv  — contagem de code smells por repo
  2. consolidated_metrics.csv      — métricas técnicas agregadas por repo
  3. consolidated_community.csv    — métricas comunitárias agregadas por repo
  4. consolidated_full.csv         — merge de todos (apenas repos com ambos OK)

Uso:
  python 04_consolidate.py \
    --base-dir ~/mestrado-pipeline \
    --progress ~/mestrado-pipeline/logs/progress_20260214_211441.csv \
    --output-dir ~/mestrado-pipeline/consolidated
"""

import argparse
import csv
import os
import sys
import statistics
from collections import Counter


def parse_args():
    p = argparse.ArgumentParser(description="Consolida resultados do pipeline")
    p.add_argument("--base-dir", required=True, help="Diretório base do pipeline (ex: ~/mestrado-pipeline)")
    p.add_argument("--progress", required=True, help="CSV de progresso do pipeline")
    p.add_argument("--output-dir", required=True, help="Diretório de saída para CSVs consolidados")
    return p.parse_args()


def read_progress(path):
    """Lê o CSV de progresso e retorna dict {repo_name: (designite_status, csdetector_status)}"""
    repos = {}
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            repos[row["repo_name"]] = (row["designite_status"], row["csdetector_status"])
    return repos


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
# DESIGNITE CONSOLIDATION
# ============================================================

def consolidate_designite(base_dir, repos):
    """
    Para cada repo com Designite OK:
    - Conta code smells (design + implementation)
    - Agrega métricas de typeMetrics e methodMetrics
    """
    cs_dir = os.path.join(base_dir, "results", "code_smells")

    smell_rows = []
    metric_rows = []

    for repo_name, (d_status, _) in repos.items():
        if d_status != "OK":
            continue

        repo_path = os.path.join(cs_dir, repo_name)
        if not os.path.isdir(repo_path):
            print(f"  [WARN] Diretório não encontrado: {repo_path}")
            continue

        # --- Code Smells ---
        design_smells = Counter()
        impl_smells = Counter()
        total_design = 0
        total_impl = 0

        design_file = os.path.join(repo_path, "designCodeSmells.csv")
        if os.path.isfile(design_file):
            with open(design_file, "r", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    smell = row.get("Code Smell", "Unknown")
                    design_smells[smell] += 1
                    total_design += 1

        impl_file = os.path.join(repo_path, "implementationCodeSmells.csv")
        if os.path.isfile(impl_file):
            with open(impl_file, "r", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    smell = row.get("Code Smell", "Unknown")
                    impl_smells[smell] += 1
                    total_impl += 1

        smell_rows.append({
            "repo_name": repo_name,
            "total_design_smells": total_design,
            "total_impl_smells": total_impl,
            "total_code_smells": total_design + total_impl,
            # Design smells
            "God_Class": design_smells.get("God Class", 0),
            "Feature_Envy": design_smells.get("Feature Envy", 0),
            "Unutilized_Abstraction": design_smells.get("Unutilized Abstraction", 0),
            "Deficient_Encapsulation": design_smells.get("Deficient Encapsulation", 0),
            "Unexploited_Encapsulation": design_smells.get("Unexploited Encapsulation", 0),
            "Multifaceted_Abstraction": design_smells.get("Multifaceted Abstraction", 0),
            "Insufficient_Modularization": design_smells.get("Insufficient Modularization", 0),
            "Hub_Like_Modularization": design_smells.get("Hub-like Modularization", 0),
            "Cyclically_Dependent_Modularization": design_smells.get("Cyclically-dependent Modularization", 0),
            "Broken_Hierarchy": design_smells.get("Broken Hierarchy", 0),
            "Rebellious_Hierarchy": design_smells.get("Rebellious Hierarchy", 0),
            "Missing_Hierarchy": design_smells.get("Missing Hierarchy", 0),
            "Wide_Hierarchy": design_smells.get("Wide Hierarchy", 0),
            "Deep_Hierarchy": design_smells.get("Deep Hierarchy", 0),
            # Implementation smells
            "Long_Method": impl_smells.get("Long Method", 0),
            "Complex_Method": impl_smells.get("Complex Method", 0),
            "Long_Parameter_List": impl_smells.get("Long Parameter List", 0),
            "Magic_Number": impl_smells.get("Magic Number", 0),
            "Duplicate_Code": impl_smells.get("Duplicate Code", 0),
            "Empty_Catch_Clause": impl_smells.get("Empty catch clause", 0),
            "Long_Statement": impl_smells.get("Long Statement", 0),
            "Long_Identifier": impl_smells.get("Long Identifier", 0),
            "Missing_Default": impl_smells.get("Missing default", 0),
            "Complex_Conditional": impl_smells.get("Complex Conditional", 0),
        })

        # --- Type Metrics ---
        type_file = os.path.join(repo_path, "typeMetrics.csv")
        locs, wmcs, nofs, noms = [], [], [], []
        fanins, fanouts, lcoms, dits = [], [], [], []
        num_classes = 0

        if os.path.isfile(type_file):
            with open(type_file, "r", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    num_classes += 1
                    locs.append(safe_float(row.get("LOC", 0)))
                    wmcs.append(safe_float(row.get("WMC", 0)))
                    nofs.append(safe_float(row.get("NOF", 0)))
                    noms.append(safe_float(row.get("NOM", 0)))
                    fanins.append(safe_float(row.get("FANIN", 0)))
                    fanouts.append(safe_float(row.get("FANOUT", 0)))
                    lcoms.append(safe_float(row.get("LCOM", 0)))
                    dits.append(safe_float(row.get("DIT", 0)))

        # Method metrics
        method_file = os.path.join(repo_path, "methodMetrics.csv")
        method_locs, method_ccs = [], []
        num_methods = 0

        if os.path.isfile(method_file):
            with open(method_file, "r", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    num_methods += 1
                    method_locs.append(safe_float(row.get("LOC", 0)))
                    method_ccs.append(safe_float(row.get("CC", 0)))

        total_loc = sum(locs)
        total_smells = smell_rows[-1]["total_code_smells"]

        metric_rows.append({
            "repo_name": repo_name,
            "num_classes": num_classes,
            "num_methods": num_methods,
            "total_LOC": total_loc,
            "mean_LOC": round(safe_mean(locs), 2),
            "median_LOC": round(safe_median(locs), 2),
            "mean_WMC": round(safe_mean(wmcs), 2),
            "mean_NOF": round(safe_mean(nofs), 2),
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
# CSDETECTOR CONSOLIDATION
# ============================================================

def find_results_dir(repo_cs_path):
    """Encontra o diretório 'results' dentro da estrutura aninhada do csDetector."""
    for root, dirs, files in os.walk(repo_cs_path):
        if os.path.basename(root) == "results" and "metrics" in dirs:
            return root
    for root, dirs, files in os.walk(repo_cs_path):
        if "results_0.csv" in files:
            return root
    return None


def consolidate_csdetector(base_dir, repos):
    """
    Para cada repo com csDetector OK:
    - Lê results_0.csv (métricas agregadas)
    - Lê métricas detalhadas de metrics/
    """
    cs_dir = os.path.join(base_dir, "results", "community_smells")
    community_rows = []

    for repo_name, (_, cs_status) in repos.items():
        if cs_status != "OK":
            continue

        repo_path = os.path.join(cs_dir, repo_name)
        if not os.path.isdir(repo_path):
            print(f"  [WARN] Diretório CS não encontrado: {repo_path}")
            continue

        results_dir = find_results_dir(repo_path)
        if not results_dir:
            print(f"  [WARN] results/ não encontrado em: {repo_path}")
            continue

        print(f"  [OK] {repo_name}")

        # --- results_0.csv (key-value format) ---
        summary = {}
        results_file = os.path.join(results_dir, "results_0.csv")
        if os.path.isfile(results_file):
            with open(results_file, "r", errors="replace") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        summary[row[0].strip()] = row[1].strip()

        metrics_dir = os.path.join(results_dir, "metrics")

        # --- Timezones ---
        tz_count = 0
        tz_file = os.path.join(metrics_dir, "timezones_0.csv")
        if os.path.isfile(tz_file):
            with open(tz_file, "r", errors="replace") as f:
                reader = csv.DictReader(f)
                tz_count = sum(1 for _ in reader)

        # --- Author days on project ---
        author_days = []
        ad_file = os.path.join(metrics_dir, "authorDaysOnProject_0.csv")
        if os.path.isfile(ad_file):
            with open(ad_file, "r", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    author_days.append(safe_int(row.get("# of Days", 0)))

        # --- Commits per author ---
        commits_per_author = []
        cpa_file = os.path.join(metrics_dir, "commitsPerAuthor_0.csv")
        if os.path.isfile(cpa_file):
            with open(cpa_file, "r", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    commits_per_author.append(safe_int(row.get("Commit Count", 0)))

        # --- Commit centrality ---
        centralities = []
        cc_file = os.path.join(metrics_dir, "commitCentrality_centrality_0.csv")
        if os.path.isfile(cc_file):
            with open(cc_file, "r", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    centralities.append(safe_float(row.get("Centrality", 0)))

        # --- Community detection ---
        num_communities = 0
        comm_file = os.path.join(metrics_dir, "commitCentrality_community_0.csv")
        if os.path.isfile(comm_file):
            with open(comm_file, "r", errors="replace") as f:
                reader = csv.DictReader(f)
                num_communities = sum(1 for _ in reader)

        # --- PRs ---
        pr_participants = []
        prp_file = os.path.join(metrics_dir, "PRParticipants_0.csv")
        if os.path.isfile(prp_file):
            with open(prp_file, "r", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pr_participants.append(safe_int(row.get("Developer Count", 0)))

        # --- Issues ---
        issue_participants = []
        ip_file = os.path.join(metrics_dir, "issueParticipantCount_0.csv")
        if os.path.isfile(ip_file):
            with open(ip_file, "r", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    issue_participants.append(safe_int(row.get("Developer Count", 0)))

        # --- Issue comments ---
        issue_comments = []
        ic_file = os.path.join(metrics_dir, "issueCommentsCount_0.csv")
        if os.path.isfile(ic_file):
            with open(ic_file, "r", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    issue_comments.append(safe_int(row.get("Comment Count", 0)))

        # --- Tags ---
        num_tags = 0
        tags_file = os.path.join(metrics_dir, "tags_0.csv")
        if os.path.isfile(tags_file):
            with open(tags_file, "r", errors="replace") as f:
                reader = csv.DictReader(f)
                num_tags = sum(1 for _ in reader)

        author_count = len(commits_per_author)
        commit_count = safe_int(summary.get("CommitCount", 0))
        days_active = safe_int(summary.get("DaysActive", 0))

        community_rows.append({
            "repo_name": repo_name,
            "commit_count": commit_count,
            "days_active": days_active,
            "author_count": author_count,
            "timezone_count": tz_count,
            "num_communities": num_communities,
            "num_tags": num_tags,
            "num_prs": len(pr_participants),
            "num_issues": len(issue_participants),
            "mean_author_days": round(safe_mean(author_days), 2),
            "mean_commits_per_author": round(safe_mean(commits_per_author), 2),
            "max_commits_per_author": max(commits_per_author) if commits_per_author else 0,
            "mean_centrality": round(safe_mean(centralities), 4),
            "mean_pr_participants": round(safe_mean(pr_participants), 2),
            "mean_issue_participants": round(safe_mean(issue_participants), 2),
            "mean_issue_comments": round(safe_mean(issue_comments), 2),
            # Indicadores heurísticos de Community Smells
            "lone_wolf_indicator": 1 if author_count <= 2 else 0,
            "radio_silence_indicator": 1 if len(issue_comments) == 0 and len(pr_participants) == 0 else 0,
            "org_silo_indicator": 1 if num_communities >= 3 else 0,
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
    print(f"  [OK] Escrito: {path} ({len(rows)} linhas)")


def main():
    args = parse_args()
    base_dir = os.path.expanduser(args.base_dir)
    progress_path = os.path.expanduser(args.progress)
    output_dir = os.path.expanduser(args.output_dir)

    print("=" * 60)
    print("  CONSOLIDAÇÃO DE RESULTADOS")
    print("=" * 60)

    # 1. Ler progresso
    print("\n[1/4] Lendo progresso do pipeline...")
    repos = read_progress(progress_path)
    d_ok = sum(1 for _, (d, _) in repos.items() if d == "OK")
    cs_ok = sum(1 for _, (_, cs) in repos.items() if cs == "OK")
    both_ok = sum(1 for _, (d, cs) in repos.items() if d == "OK" and cs == "OK")
    print(f"  Total repos: {len(repos)}")
    print(f"  Designite OK: {d_ok}")
    print(f"  csDetector OK: {cs_ok}")
    print(f"  Ambos OK: {both_ok}")

    # 2. Consolidar Designite
    print("\n[2/4] Consolidando Designite (code smells + métricas)...")
    smell_rows, metric_rows = consolidate_designite(base_dir, repos)
    write_csv(smell_rows, os.path.join(output_dir, "consolidated_code_smells.csv"))
    write_csv(metric_rows, os.path.join(output_dir, "consolidated_metrics.csv"))

    # 3. Consolidar csDetector
    print("\n[3/4] Consolidando csDetector (community metrics)...")
    community_rows = consolidate_csdetector(base_dir, repos)
    write_csv(community_rows, os.path.join(output_dir, "consolidated_community.csv"))

    # 4. Merge: repos com ambos OK
    print("\n[4/4] Gerando dataset unificado (repos com ambos OK)...")
    smell_dict = {r["repo_name"]: r for r in smell_rows}
    metric_dict = {r["repo_name"]: r for r in metric_rows}
    community_dict = {r["repo_name"]: r for r in community_rows}

    full_rows = []
    for repo_name in community_dict:
        if repo_name in smell_dict and repo_name in metric_dict:
            merged = {}
            merged.update(smell_dict[repo_name])
            for k, v in metric_dict[repo_name].items():
                if k != "repo_name":
                    merged[k] = v
            for k, v in community_dict[repo_name].items():
                if k != "repo_name":
                    merged[k] = v
            full_rows.append(merged)

    write_csv(full_rows, os.path.join(output_dir, "consolidated_full.csv"))

    # Summary
    print("\n" + "=" * 60)
    print("  RESUMO DA CONSOLIDAÇÃO")
    print("=" * 60)
    print(f"  consolidated_code_smells.csv: {len(smell_rows)} repos")
    print(f"  consolidated_metrics.csv:     {len(metric_rows)} repos")
    print(f"  consolidated_community.csv:   {len(community_rows)} repos")
    print(f"  consolidated_full.csv:        {len(full_rows)} repos (ambos OK)")
    print("=" * 60)


if __name__ == "__main__":
    main()
