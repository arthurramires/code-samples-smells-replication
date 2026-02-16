# Installation and Setup Guide

## Prerequisites

- **OS**: macOS (Apple Silicon) or Linux (x86_64)
- **Java**: OpenJDK 17+
- **Python**: 3.10+
- **Git**: 2.30+
- **GitHub Token**: Personal Access Token with `repo` and `read:org` scopes

## Step 1: Environment Setup

```bash
# Clone this replication package
git clone https://github.com/<user>/code-community-smells-replication.git
cd code-community-smells-replication

# Run setup script (installs dependencies, creates directory structure)
bash scripts/01_setup_macos.sh
```

The setup script will:
- Verify Java and Python installations
- Install Python dependencies (`pandas`, `scipy`, `scikit-learn`)
- Download Designite Java JAR (free academic version)
- Clone and build csDetector from source
- Create the pipeline directory structure at `~/mestrado-pipeline/`

## Step 2: GitHub Token Configuration

```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

**Important**: The csDetector requires a valid GitHub token to access the GitHub API for collecting commit, PR, and issue data. Ensure your token has sufficient rate limits.

## Step 3: Dataset Collection

```bash
# Collect repository list from GitHub organizations
bash scripts/02_expand_dataset.sh
```

This script queries the GitHub API for repositories from:
- `aws-samples`, `Azure-Samples`, `GoogleCloudPlatform`
- `spring-guides`, `googlesamples`, `oracle-samples`
- Keyword searches: "java sample", "java example", "java tutorial", "java demo"

Output: `~/mestrado-pipeline/repos_list.csv`

## Step 4: Run Analysis Pipeline

```bash
# Run Designite Java and csDetector on all repositories
bash scripts/03_run_pipeline.sh
```

**Expected runtime**: 8-12 hours for ~340 repositories (depends on network speed and GitHub API rate limits).

Output structure:
```
~/mestrado-pipeline/
├── results/
│   ├── code_smells/<repo_name>/    # Designite CSV outputs
│   └── community_smells/<repo_name>/  # csDetector outputs
└── logs/
    └── progress_<timestamp>.csv    # Pipeline progress log
```

## Step 5: Consolidate Results

```bash
python scripts/04_consolidate.py \
  --base-dir ~/mestrado-pipeline \
  --progress ~/mestrado-pipeline/logs/progress_*.csv \
  --output-dir data/
```

This generates the four consolidated CSV files in `data/`.

## Step 6: Statistical Analysis

The statistical analysis can be reproduced using standard Python:

```python
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import MinMaxScaler

# Load data
full = pd.read_csv("data/consolidated_full.csv")

# Spearman correlations
rho, p = stats.spearmanr(full['total_code_smells'], full['commit_count'])

# K-means clustering (k=3, after outlier removal)
features = ['total_code_smells', 'smell_density', 'author_count',
            'mean_centrality', 'commit_count', 'mean_commits_per_author']
X = MinMaxScaler().fit_transform(full[features])
km = KMeans(n_clusters=3, random_state=42, n_init=10)
full['cluster'] = km.fit_predict(X)
```

## Tool Versions (Frozen)

| Tool | Version | Source |
|------|---------|--------|
| Designite Java | 2.x | https://www.designite-tools.com/ |
| csDetector | master branch | https://github.com/Nuri22/csDetector |
| SentiStrength | Oct 2019 data | http://sentistrength.wlv.ac.uk/ |
| Python | 3.10 | https://python.org |
| Java | OpenJDK 17 | https://openjdk.org |

## Troubleshooting

### csDetector failures (268/318 repos)
This is expected. csDetector requires sufficient GitHub activity (contributors, PRs, issues) to produce results. Repositories with minimal social activity will fail gracefully.

### Fish shell compatibility
If using Fish shell, replace `$()` with `()` and `&&` with `; and` in bash commands.

### Rate limiting
If encountering GitHub API rate limits, set `GITHUB_TOKEN` and consider adding delays between API calls in the pipeline script.

## Data Directory Structure

The `data/` directory follows MSR Data Showcase conventions:

- **`repositories.csv`** — Primary dataset: complete list of 318 repositories with metadata, analysis subset flags, and code smell totals. This is the entry point for any analysis.
- **`clustering_outliers.csv`** — 22 repositories excluded from k-means clustering (±2 SD criterion).
- **`processed/`** — Consolidated CSVs ready for analysis. These are the files used by `scripts/06_analysis_v2.py` and `scripts/07_analysis_extra.py`.
- **`raw/`** — Empty by default. Populated during reproduction with per-repository outputs from Designite Java and csDetector-fixed.

**Note:** The analysis scripts reference a configurable `DADOS` directory. When using the pre-computed data, point `DADOS` to `data/processed/`.

