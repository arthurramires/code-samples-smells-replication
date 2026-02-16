#!/usr/bin/env python3
"""
run_batch.py — Wrapper para executar o csDetector corrigido em múltiplos repositórios.

Uso:
    python run_batch.py \
        --repos-list /path/to/repo_urls.txt \
        --pat YOUR_GITHUB_PAT \
        --senti-path /path/to/SentiStrength \
        --output-path /path/to/output \
        [--google-key YOUR_GOOGLE_KEY] \
        [--batch-months 9999] \
        [--start-from REPO_NAME] \
        [--timeout SECONDS]

O script:
  1. Lê a lista de repos do CSV ou arquivo de URLs
  2. Pula repos que já possuem results_0.csv no output (auto-resume)
  3. Executa o csDetector para cada repo, capturando erros individuais
  4. Gera relatório final com sucesso/falha por repo
"""

import os
import sys
import csv
import json
import time
import signal
import shutil
import argparse
import traceback
import subprocess
from datetime import datetime


def parse_args():
    parser = argparse.ArgumentParser(description="Batch runner for csDetector-fixed")
    parser.add_argument("--repos-csv", required=False, default=None,
                        help="CSV with repo_name column (e.g., consolidated_code_smells.csv)")
    parser.add_argument("--repos-list", required=False, default=None,
                        help="Alternative: text file with one GitHub URL per line")
    parser.add_argument("--pat", required=True,
                        help="GitHub Personal Access Token")
    parser.add_argument("--senti-path", required=True,
                        help="Path to SentiStrength directory")
    parser.add_argument("--output-path", required=True,
                        help="Base output directory")
    parser.add_argument("--google-key", default=None,
                        help="Google Cloud API key for Perspective API (optional)")
    parser.add_argument("--batch-months", type=int, default=9999,
                        help="Batch months (default: 9999 = single batch)")
    parser.add_argument("--start-from", default=None,
                        help="Skip repos until this repo_name (for resuming)")
    parser.add_argument("--owner-map", default=None,
                        help="JSON file mapping repo_name -> owner (if not inferable)")
    parser.add_argument("--default-owner", default=None,
                        help="Default GitHub owner if repos don't have consistent owners")
    parser.add_argument("--max-retries", type=int, default=1,
                        help="Max retries per repo on failure (default: 1 = no retry)")
    parser.add_argument("--timeout", type=int, default=900,
                        help="Timeout per repo in seconds (default: 900 = 15min)")
    return parser.parse_args()


def load_repos_from_csv(csv_path):
    """Load repo names from CSV file with repo_name column."""
    repos = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            repos.append(row["repo_name"])
    return repos


def load_repos_from_list(list_path):
    """Load GitHub URLs from a text file (one per line)."""
    repos = []
    with open(list_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                repos.append(line)
    return repos


def infer_github_url(repo_name, owner_map=None, default_owner=None):
    if repo_name.startswith("http"):
        return repo_name
    if owner_map and repo_name in owner_map:
        return f"https://github.com/{owner_map[repo_name]}/{repo_name}"
    if default_owner:
        return f"https://github.com/{default_owner}/{repo_name}"
    return None


def repo_already_processed(repo_url, output_path):
    """Check if a repo already has results_0.csv in the output directory."""
    split = repo_url.rstrip("/").split("/")
    if len(split) < 2:
        return False
    owner, name = split[-2], split[-1]
    results_file = os.path.join(output_path, owner, name, "results", "results_0.csv")
    return os.path.exists(results_file)


def run_csdetector_for_repo(repo_url, args, csdetector_dir):
    """Run csDetector for a single repository using subprocess."""

    cmd = [
        sys.executable, os.path.join(csdetector_dir, "devNetwork.py"),
        "-r", repo_url,
        "-p", args.pat,
        "-s", args.senti_path,
        "-o", args.output_path,
        "-m", str(args.batch_months),
    ]

    if args.google_key:
        cmd.extend(["-g", args.google_key])

    env = os.environ.copy()
    env["PYTHONPATH"] = csdetector_dir

    # Use Popen instead of run so we can kill properly on timeout
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=csdetector_dir,
        env=env,
        preexec_fn=os.setsid,  # new process group so we can kill all children
    )

    try:
        stdout, stderr = process.communicate(timeout=args.timeout)
        return subprocess.CompletedProcess(cmd, process.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        # Kill entire process group (includes git clone, java, etc.)
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        raise


def main():
    args = parse_args()
    csdetector_dir = os.path.dirname(os.path.abspath(__file__))

    # Load repos
    if args.repos_list:
        repos = load_repos_from_list(args.repos_list)
        print(f"Loaded {len(repos)} repos from list file")
    elif args.repos_csv:
        repos = load_repos_from_csv(args.repos_csv)
        print(f"Loaded {len(repos)} repos from CSV")
    else:
        print("ERROR: Provide either --repos-list or --repos-csv")
        sys.exit(1)

    # Load owner map if provided
    owner_map = None
    if args.owner_map:
        with open(args.owner_map, "r") as f:
            owner_map = json.load(f)

    # Skip to start_from if specified
    start_idx = 0
    if args.start_from:
        for i, repo in enumerate(repos):
            if repo == args.start_from or repo.endswith(f"/{args.start_from}"):
                start_idx = i
                break
        print(f"Starting from repo #{start_idx}: {repos[start_idx]}")

    # Results tracking
    results = {
        "success": [],
        "failed": [],
        "skipped": [],
        "start_time": datetime.now().isoformat(),
    }

    report_path = os.path.join(args.output_path, "batch_report.json")
    os.makedirs(args.output_path, exist_ok=True)

    total = len(repos)
    already_done = 0

    for idx in range(start_idx, total):
        repo = repos[idx]

        # Infer URL
        if repo.startswith("http"):
            repo_url = repo
        else:
            repo_url = infer_github_url(repo, owner_map, args.default_owner)
            if repo_url is None:
                print(f"[{idx+1}/{total}] SKIP: Cannot infer URL for '{repo}'")
                results["skipped"].append({"repo": repo, "reason": "cannot_infer_url"})
                continue

        # AUTO-RESUME: skip repos that already have results
        if repo_already_processed(repo_url, args.output_path):
            already_done += 1
            if already_done <= 3 or already_done % 50 == 0:
                print(f"[{idx+1}/{total}] ALREADY DONE: {repo_url.split('/')[-1]} (skipping)")
            elif already_done == 4:
                print(f"  ... skipping already-processed repos ...")
            results["success"].append({"repo": repo, "url": repo_url, "attempt": 0})
            continue

        print(f"\n{'='*60}")
        print(f"[{idx+1}/{total}] Processing: {repo_url}")
        print(f"{'='*60}")

        success = False
        last_error = ""

        for attempt in range(1, args.max_retries + 1):
            try:
                result = run_csdetector_for_repo(repo_url, args, csdetector_dir)

                if result.returncode == 0:
                    print(f"  SUCCESS (attempt {attempt})")
                    results["success"].append({
                        "repo": repo,
                        "url": repo_url,
                        "attempt": attempt,
                    })
                    success = True
                    break
                else:
                    last_error = result.stderr[-500:] if result.stderr else "No stderr"
                    print(f"  FAILED attempt {attempt}/{args.max_retries}: exit code {result.returncode}")
                    print(f"  Error: {last_error[:200]}")

                    # Clean up failed repo clone to retry fresh
                    split = repo_url.rstrip("/").split("/")
                    owner, name = split[-2], split[-1]
                    repo_clone_path = os.path.join(args.output_path, owner, name, f"{owner}.{name}")
                    if os.path.exists(repo_clone_path) and attempt < args.max_retries:
                        shutil.rmtree(repo_clone_path, ignore_errors=True)

            except subprocess.TimeoutExpired:
                last_error = f"Timeout after {args.timeout}s"
                print(f"  TIMEOUT attempt {attempt}/{args.max_retries} ({args.timeout}s)")
                # Clean up timed-out repo clone
                split = repo_url.rstrip("/").split("/")
                owner, name = split[-2], split[-1]
                repo_clone_path = os.path.join(args.output_path, owner, name, f"{owner}.{name}")
                if os.path.exists(repo_clone_path):
                    shutil.rmtree(repo_clone_path, ignore_errors=True)
            except Exception as e:
                last_error = str(e)
                print(f"  ERROR attempt {attempt}/{args.max_retries}: {e}")

            if attempt < args.max_retries:
                wait = 5 * attempt
                print(f"  Waiting {wait}s before retry...")
                time.sleep(wait)

        if not success:
            results["failed"].append({
                "repo": repo,
                "url": repo_url,
                "error": last_error[:500],
            })

        # Save intermediate report every 5 repos
        if (idx + 1) % 5 == 0 or idx == total - 1:
            results["end_time"] = datetime.now().isoformat()
            results["summary"] = {
                "total": total,
                "processed": idx + 1 - start_idx,
                "success": len(results["success"]),
                "failed": len(results["failed"]),
                "skipped": len(results["skipped"]),
                "already_done": already_done,
            }
            with open(report_path, "w") as f:
                json.dump(results, f, indent=2)

    # Final report
    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE")
    print(f"{'='*60}")
    print(f"  Total: {total}")
    print(f"  Success: {len(results['success'])} ({already_done} from previous run)")
    print(f"  Failed: {len(results['failed'])}")
    print(f"  Skipped: {len(results['skipped'])}")
    print(f"\n  Report saved to: {report_path}")

    # Print failed repos for quick reference
    if results["failed"]:
        print(f"\n  Failed repos:")
        for entry in results["failed"]:
            print(f"    - {entry['repo']}: {entry['error'][:100]}")


if __name__ == "__main__":
    main()
