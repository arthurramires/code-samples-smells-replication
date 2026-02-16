#!/usr/bin/env python3
"""
build_repo_urls.py — Constroi arquivo de URLs do GitHub a partir dos nomes dos repos.

Usa a GitHub Search API para encontrar o owner de cada repo.

Uso:
    python build_repo_urls.py \
        --repos-csv /path/to/consolidated_code_smells.csv \
        --pat YOUR_GITHUB_PAT \
        --output /path/to/repo_urls.txt

Gera:
  - repo_urls.txt: uma URL por linha (https://github.com/owner/repo)
  - owner_map.json: mapeamento repo_name -> owner
  - not_found.txt: repos que não foram encontrados no GitHub
"""

import os
import csv
import json
import time
import argparse
import requests


def parse_args():
    parser = argparse.ArgumentParser(description="Build GitHub URLs from repo names")
    parser.add_argument("--repos-csv", required=True)
    parser.add_argument("--pat", required=True)
    parser.add_argument("--output", required=True, help="Output directory")
    return parser.parse_args()


def search_repo(name, pat):
    """Search for a repo on GitHub by name."""
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Try exact match first
    url = f"https://api.github.com/search/repositories?q={name}+in:name+language:java&per_page=5"
    resp = requests.get(url, headers=headers)

    if resp.status_code == 403:
        # Rate limited
        reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
        wait = max(reset - int(time.time()), 5)
        print(f"  Rate limited, waiting {wait}s...")
        time.sleep(wait)
        resp = requests.get(url, headers=headers)

    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code}"

    data = resp.json()
    items = data.get("items", [])

    if not items:
        return None, "not found"

    # Find exact name match
    for item in items:
        if item["name"].lower() == name.lower():
            return item["html_url"], None

    # If no exact match, try the first result if the name is close
    first = items[0]
    if first["name"].lower().replace("-", "").replace("_", "") == name.lower().replace("-", "").replace("_", ""):
        return first["html_url"], None

    return None, f"no exact match (closest: {first['full_name']})"


def main():
    args = parse_args()
    os.makedirs(args.output, exist_ok=True)

    # Load repos
    repos = []
    with open(args.repos_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            repos.append(row["repo_name"])

    print(f"Processing {len(repos)} repos...")

    urls = []
    owner_map = {}
    not_found = []

    for idx, repo in enumerate(repos):
        print(f"[{idx+1}/{len(repos)}] {repo}...", end=" ")

        url, error = search_repo(repo, args.pat)
        if url:
            urls.append(url)
            # Extract owner from URL
            parts = url.rstrip("/").split("/")
            owner_map[repo] = parts[-2]
            print(f"-> {url}")
        else:
            not_found.append(f"{repo}: {error}")
            print(f"NOT FOUND ({error})")

        # GitHub search has 30 req/min limit
        time.sleep(2.5)

    # Save outputs
    urls_path = os.path.join(args.output, "repo_urls.txt")
    with open(urls_path, "w") as f:
        for url in urls:
            f.write(url + "\n")

    map_path = os.path.join(args.output, "owner_map.json")
    with open(map_path, "w") as f:
        json.dump(owner_map, f, indent=2)

    nf_path = os.path.join(args.output, "not_found.txt")
    with open(nf_path, "w") as f:
        for entry in not_found:
            f.write(entry + "\n")

    print(f"\nDone!")
    print(f"  Found: {len(urls)}")
    print(f"  Not found: {len(not_found)}")
    print(f"  URLs: {urls_path}")
    print(f"  Owner map: {map_path}")
    print(f"  Not found: {nf_path}")


if __name__ == "__main__":
    main()
