#!/usr/bin/env python3
"""
consolidate_results.py — Consolida os resultados do csDetector em CSVs para análise.

Lê os diretórios de resultado gerados pelo csDetector e produz:
  - consolidated_community_new.csv: todas as métricas comunitárias
  - detected_smells_summary.csv: Community Smells detectados por repo

Uso:
    python consolidate_results.py \
        --results-dir /path/to/output \
        --output /path/to/dados/
"""

import os
import csv
import argparse
import glob


def parse_args():
    parser = argparse.ArgumentParser(description="Consolidate csDetector results")
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def parse_results_csv(filepath):
    """Parse csDetector's key-value CSV format into a dictionary."""
    results = {}
    try:
        with open(filepath, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    key = row[0].strip()
                    value = row[1].strip()
                    results[key] = value
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
    return results


def parse_detected_smells(filepath):
    """Parse detected_smells CSV."""
    smells = {
        "OSE": 0, "BCE": 0, "PDE": 0, "SV": 0, "OS": 0,
        "SD": 0, "RS": 0, "TF": 0, "UI": 0, "TC": 0,
    }
    try:
        with open(filepath, "r") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header is None:
                return smells
            # The detected smells file has: LastCommitDate, then smell names
            row = next(reader, None)
            if row and len(row) > 1:
                for smell_name in row[1:]:
                    smell_name = smell_name.strip()
                    if smell_name in smells:
                        smells[smell_name] = 1
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
    return smells


# Key metrics to extract from csDetector results
METRICS_TO_EXTRACT = [
    "CommitCount", "DaysActive", "AuthorCount", "TimezoneCount",
    "SponsoredAuthorCount", "PercentageSponsoredAuthors",
    "NumberPRs", "NumberIssues",
    "NumberPRComments", "NumberIssueComments",
    "PRCommentsPositive", "PRCommentsNegative",
    "IssueCommentsPositive", "IssueCommentsNegative",
    "PRCommentsNegativeRatio", "IssueCommentsNegativeRatio",
    "PRCommentsToxicityPercentage", "IssueCommentsToxicityPercentage",
    "BusFactorNumber",
    "commitCentrality_Density",
    "commitCentrality_Community Count",
    "commitCentrality_TFN", "commitCentrality_TFC",
    "commitCentrality_NumberHighCentralityAuthors",
    "commitCentrality_PercentageHighCentralityAuthors",
    "AuthorActiveDays_mean", "AuthorActiveDays_stdev",
    "AuthorCommitCount_mean", "AuthorCommitCount_stdev",
    "commitCentrality_Centrality_mean", "commitCentrality_Centrality_stdev",
    "commitCentrality_Centrality_count",
    "commitCentrality_Betweenness_mean", "commitCentrality_Betweenness_count",
    "commitCentrality_Closeness_mean", "commitCentrality_Closeness_count",
    "PRParticipantsCount_mean", "PRParticipantsCount_stdev",
    "IssueParticipantCount_mean", "IssueParticipantCount_stdev",
    "PRCommentsCount_mean", "IssueCommentsCount_mean",
    "PRDuration_mean", "IssueDuration_mean",
    "NumberReleases",
    "ACCL", "RPCPR", "RPCIssue",
    "FirstCommitDate", "LastCommitDate",
    # Community smell indicators
    "NumberActiveExperiencedDevs",
    "SponsoredTFC", "ExperiencedTFC",
]

# Mapping for the consolidated community CSV (simplified names)
COLUMN_MAPPING = {
    "CommitCount": "commit_count",
    "DaysActive": "days_active",
    "AuthorCount": "author_count",
    "TimezoneCount": "timezone_count",
    "commitCentrality_Community Count": "num_communities",
    "NumberPRs": "num_prs",
    "NumberIssues": "num_issues",
    "AuthorActiveDays_mean": "mean_author_days",
    "AuthorCommitCount_mean": "mean_commits_per_author",
    "commitCentrality_Centrality_mean": "mean_centrality",
    "PRParticipantsCount_mean": "mean_pr_participants",
    "IssueParticipantCount_mean": "mean_issue_participants",
    "IssueCommentsCount_mean": "mean_issue_comments",
    "BusFactorNumber": "bus_factor",
    "commitCentrality_Density": "network_density",
}


def main():
    args = parse_args()
    os.makedirs(args.output, exist_ok=True)

    # Find all result directories
    # csDetector outputs to: output_path/owner/repo/results/results_0.csv
    results_files = glob.glob(
        os.path.join(args.results_dir, "*", "*", "results", "results_0.csv")
    )

    print(f"Found {len(results_files)} result files")

    # Consolidated data
    all_rows = []
    smell_rows = []

    for results_file in sorted(results_files):
        parts = results_file.split(os.sep)
        # Extract repo name from path: .../owner/repo/results/results_0.csv
        repo_dir = os.path.dirname(os.path.dirname(results_file))
        repo_name = os.path.basename(repo_dir)

        print(f"Processing: {repo_name}")
        results = parse_results_csv(results_file)

        if not results:
            print(f"  EMPTY results, skipping")
            continue

        # Build row
        row = {"repo_name": repo_name}
        for metric in METRICS_TO_EXTRACT:
            row[metric] = results.get(metric, "")

        all_rows.append(row)

        # Check for detected smells
        smells_file = os.path.join(
            os.path.dirname(results_file),
            "detected_smells_0.csv"
        )
        smell_data = {"repo_name": repo_name}
        if os.path.exists(smells_file):
            detected = parse_detected_smells(smells_file)
            smell_data.update(detected)
        smell_rows.append(smell_data)

    # Write consolidated metrics
    if all_rows:
        output_file = os.path.join(args.output, "consolidated_community_new.csv")
        fieldnames = ["repo_name"] + METRICS_TO_EXTRACT
        with open(output_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)
        print(f"\nWrote {len(all_rows)} repos to {output_file}")

    # Write simplified community CSV (matching original format)
    if all_rows:
        output_file2 = os.path.join(args.output, "consolidated_community_compatible.csv")
        simplified_fields = ["repo_name"] + list(COLUMN_MAPPING.values()) + [
            "lone_wolf_indicator", "radio_silence_indicator", "org_silo_indicator"
        ]
        with open(output_file2, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=simplified_fields)
            writer.writeheader()
            for row in all_rows:
                simplified = {"repo_name": row["repo_name"]}
                for orig, new in COLUMN_MAPPING.items():
                    simplified[new] = row.get(orig, "")
                # Smell indicators will come from detected_smells
                repo_smells = next(
                    (s for s in smell_rows if s["repo_name"] == row["repo_name"]),
                    {}
                )
                # Map detected smells to original indicator columns
                # OS = Organizational Silo, RS = Radio Silence, UI = Uninvolved (Lone Wolf proxy)
                simplified["org_silo_indicator"] = repo_smells.get("OS", 0)
                simplified["radio_silence_indicator"] = repo_smells.get("RS", 0)
                simplified["lone_wolf_indicator"] = repo_smells.get("UI", 0)
                writer.writerow(simplified)
        print(f"Wrote {len(all_rows)} repos to {output_file2}")

    # Write detected smells
    if smell_rows:
        output_smells = os.path.join(args.output, "detected_smells_summary.csv")
        smell_fields = ["repo_name", "OSE", "BCE", "PDE", "SV", "OS", "SD", "RS", "TF", "UI", "TC"]
        with open(output_smells, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=smell_fields)
            writer.writeheader()
            writer.writerows(smell_rows)
        print(f"Wrote {len(smell_rows)} repos to {output_smells}")

    print(f"\nConsolidation complete!")


if __name__ == "__main__":
    main()
