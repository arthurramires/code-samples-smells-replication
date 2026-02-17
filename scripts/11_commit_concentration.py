#!/usr/bin/env python3
"""
11_commit_concentration.py — Análise de concentração temporal de commits
========================================================================
Investiga por que 99.5% dos repos têm o MESMO commit hash em todos os
project years: os code samples são artefatos "write once".

Analisa:
1. Distribuição temporal dos commits (% no primeiro ano)
2. Período de atividade real vs. idade do repo
3. Classificação: write-once vs evolving repos
"""

import csv
import subprocess
import os
import sys
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

import glob as _glob

def _find(pattern, fallback):
    m = _glob.glob(pattern)
    return m[0] if m else fallback

REPOS_DIR = sys.argv[1] if len(sys.argv) > 1 else _find("/sessions/sleepy-loving-ride/mnt/Disserta*/results/temporal/repos", "repos")
DATA_CSV = sys.argv[2] if len(sys.argv) > 2 else _find("/sessions/sleepy-loving-ride/mnt/Disserta*/results/temporal/temporal_data_complete_fixed.csv", "data.csv")
OUTPUT_DIR = "/sessions/sleepy-loving-ride/analysis"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_commit_dates(repo_dir):
    """Get all commit dates from a repo."""
    try:
        result = subprocess.run(
            ["git", "log", "--format=%aI", "--all"],
            cwd=repo_dir, capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return []
        dates = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                try:
                    dt = datetime.fromisoformat(line.strip().replace('Z', '+00:00'))
                    dates.append(dt)
                except:
                    pass
        return sorted(dates)
    except:
        return []

def analyze_repo_commits(repo_name, repo_dir):
    """Analyze commit concentration for a single repo."""
    dates = get_commit_dates(repo_dir)
    if not dates:
        return None

    first = dates[0]
    last = dates[-1]
    total = len(dates)
    total_days = (last - first).days

    # Commits in first 30, 90, 365 days
    c30 = sum(1 for d in dates if (d - first).days <= 30)
    c90 = sum(1 for d in dates if (d - first).days <= 90)
    c365 = sum(1 for d in dates if (d - first).days <= 365)

    # Active days (unique days with commits)
    unique_days = len(set(d.date() for d in dates))

    # "Burst" detection: days between first and last commit
    active_span = total_days if total_days > 0 else 1

    return {
        'repo_name': repo_name,
        'total_commits': total,
        'first_commit': first.strftime('%Y-%m-%d'),
        'last_commit': last.strftime('%Y-%m-%d'),
        'total_days_span': total_days,
        'unique_active_days': unique_days,
        'commits_first_30d': c30,
        'commits_first_90d': c90,
        'commits_first_365d': c365,
        'pct_first_30d': round(100 * c30 / total, 1),
        'pct_first_90d': round(100 * c90 / total, 1),
        'pct_first_365d': round(100 * c365 / total, 1),
        'write_once': 1 if (c30 / total >= 0.8) else 0,
        'burst_then_idle': 1 if (c90 / total >= 0.9 and total_days > 365) else 0,
    }

def main():
    # Get unique repos from temporal data
    repos = set()
    with open(DATA_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            repos.add(row['repo_name'])

    logger.info(f"Analyzing commit concentration for {len(repos)} repos...")

    results = []
    processed = 0
    for repo_name in sorted(repos):
        repo_dir = os.path.join(REPOS_DIR, repo_name)
        if not os.path.isdir(repo_dir):
            continue

        info = analyze_repo_commits(repo_name, repo_dir)
        if info:
            results.append(info)

        processed += 1
        if processed % 50 == 0:
            logger.info(f"  Processed {processed}/{len(repos)}")

    logger.info(f"Successfully analyzed {len(results)} repos")

    # Save detailed CSV
    out_path = os.path.join(OUTPUT_DIR, "commit_concentration.csv")
    if results:
        with open(out_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

    # Summary statistics
    import statistics

    pct30 = [r['pct_first_30d'] for r in results]
    pct90 = [r['pct_first_90d'] for r in results]
    pct365 = [r['pct_first_365d'] for r in results]
    write_once = sum(r['write_once'] for r in results)
    burst_idle = sum(r['burst_then_idle'] for r in results)

    print("\n" + "="*60)
    print("COMMIT CONCENTRATION ANALYSIS")
    print("="*60)
    print(f"Total repos analyzed: {len(results)}")
    print(f"\n% of commits in first 30 days:")
    print(f"  Median: {statistics.median(pct30):.1f}%")
    print(f"  Mean:   {statistics.mean(pct30):.1f}%")
    print(f"  ≥80%:   {sum(1 for p in pct30 if p >= 80)}/{len(results)} ({100*sum(1 for p in pct30 if p >= 80)/len(results):.1f}%)")
    print(f"  ≥90%:   {sum(1 for p in pct30 if p >= 90)}/{len(results)} ({100*sum(1 for p in pct30 if p >= 90)/len(results):.1f}%)")

    print(f"\n% of commits in first 90 days:")
    print(f"  Median: {statistics.median(pct90):.1f}%")
    print(f"  Mean:   {statistics.mean(pct90):.1f}%")
    print(f"  ≥90%:   {sum(1 for p in pct90 if p >= 90)}/{len(results)} ({100*sum(1 for p in pct90 if p >= 90)/len(results):.1f}%)")

    print(f"\n% of commits in first 365 days:")
    print(f"  Median: {statistics.median(pct365):.1f}%")
    print(f"  Mean:   {statistics.mean(pct365):.1f}%")
    print(f"  ≥95%:   {sum(1 for p in pct365 if p >= 95)}/{len(results)} ({100*sum(1 for p in pct365 if p >= 95)/len(results):.1f}%)")

    print(f"\nWrite-once repos (≥80% commits in 30d): {write_once}/{len(results)} ({100*write_once/len(results):.1f}%)")
    print(f"Burst-then-idle (≥90% in 90d, span>1yr): {burst_idle}/{len(results)} ({100*burst_idle/len(results):.1f}%)")

    # Active days distribution
    active_days = [r['unique_active_days'] for r in results]
    print(f"\nUnique active days:")
    print(f"  Median: {statistics.median(active_days):.0f}")
    print(f"  Mean:   {statistics.mean(active_days):.1f}")
    print(f"  1 day:  {sum(1 for a in active_days if a == 1)}/{len(results)}")
    print(f"  ≤7 days: {sum(1 for a in active_days if a <= 7)}/{len(results)}")
    print(f"  ≤30 days: {sum(1 for a in active_days if a <= 30)}/{len(results)}")

    print("="*60)

if __name__ == "__main__":
    main()
