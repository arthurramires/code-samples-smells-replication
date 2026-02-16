# Replication Package: Co-occurrence of Code Smells and Community Smells in Java Code Samples

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18649168.svg)](https://doi.org/10.5281/zenodo.18649168)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![FAIR](https://img.shields.io/badge/FAIR-compliant-green)]()

> **FAIR Compliance:** This package follows the [FAIR Guiding Principles](https://www.go-fair.org/fair-principles/) for scientific data management. See [`docs/MSR-FAIR-COMPLIANCE.md`](docs/MSR-FAIR-COMPLIANCE.md) for the full compliance checklist.

## Overview

This replication package accompanies the Master's thesis:

> **Análise Evolutiva da Coocorrência entre Code Smells e Community Smells em Code Samples**
>
> Arthur Ramires Rodrigues Neto Bueno
> Universidade Federal de Mato Grosso do Sul (UFMS), 2026
>
> Advisor: Prof. Dr. Awdren de Lima Fontão
> Co-advisor: Profa. Dra. Maria Istela Cagnin Machado

The study investigates the co-occurrence between Code Smells (detected by Designite Java) and Community Smells (detected by csDetector-fixed) in 318 Java open-source code sample repositories, achieving 94.3% community data coverage (300/318 repos).

## Repository Structure

```
replication-package/
├── README.md                  # This file
├── CITATION.cff               # Machine-readable citation (GitHub-native)
├── LICENSE                    # MIT License
├── INSTALL.md                 # Setup and reproduction instructions
├── requirements.txt           # Python dependencies
├── scripts/
│   ├── 01_setup_macos.sh      # Environment setup (macOS/Apple Silicon)
│   ├── 02_expand_dataset.sh   # Dataset expansion via GitHub API
│   ├── 03_run_pipeline.sh     # Main pipeline: Designite + csDetector
│   ├── 04_consolidate.py      # Consolidation of raw outputs into unified CSV
│   ├── 05_filter_dataset.py   # Dataset filtering by IC/EC criteria
│   ├── 06_analysis_v2.py      # Main analysis: correlations, figures, merge
│   └── 07_analysis_extra.py   # Additional: scatter, Mann-Whitney, clusters
├── tools/
│   └── csDetector-fixed/      # Patched version of csDetector (13 bug fixes)
│       ├── CHANGES.md         # Detailed changelog of all fixes
│       ├── devNetwork.py      # Main orchestrator (patched)
│       ├── repoLoader.py      # Git clone with branch fallback
│       ├── graphqlAnalysis/   # GitHub API modules (patched)
│       ├── build_repo_urls.py # Resolve repo names to GitHub URLs
│       ├── run_batch.py       # Batch runner with auto-resume
│       └── consolidate_results.py  # Consolidate csDetector outputs
├── data/
│   ├── README.md                      # Data provenance, format, and flow
│   ├── repositories.csv               # PRIMARY DATASET: 318 repos + metadata
│   ├── clustering_outliers.csv        # 22 repos excluded from clustering
│   ├── processed/                     # Consolidated analysis-ready CSVs
│   │   ├── consolidated_code_smells.csv   # 318 repos × 28 smell types
│   │   ├── consolidated_metrics.csv       # 318 repos × 17 quality metrics
│   │   ├── consolidated_community.csv     # 50 repos × 20 community (v1)
│   │   ├── consolidated_community_300.csv # 300 repos × 53 community (v2)
│   │   ├── consolidated_full.csv          # 50 repos × merged (v1)
│   │   └── consolidated_full_300.csv      # 300 repos × merged (v2)
│   └── raw/                           # Raw tool outputs (see raw/README.md)
│       └── README.md
└── docs/
    ├── CODEBOOK.md            # Variable definitions and data dictionary
    └── MSR-FAIR-COMPLIANCE.md # FAIR principles compliance checklist
```

## Dataset Summary

| Subset | Repositories | Variables | Description |
|--------|-------------|-----------|-------------|
| Code Smells | 318 | 28 | Design and implementation smells per repo |
| Metrics | 318 | 17 | LOC, WMC, CC, FANIN/OUT, LCOM, DIT, smell density |
| Community (original) | 50 | 20 | Original csDetector output |
| Community (expanded) | 300 | 53 | csDetector-fixed output (94.3% coverage) |
| Full (original) | 50 | 62 | Merged technical + social |
| Full (expanded) | 300 | 35 | Merged technical + social + CS indicators |

## Key Findings (Expanded Dataset, N=300)

- **100,643 Code Smell instances** across 318 repositories
- Top 3 smells: Magic Number (57.4%), Unutilized Abstraction (20.8%), Long Statement (13.3%)
- **Bus Factor** is the strongest social correlate of Code Smells (ρ = −0.366, p < 0.001)
- Mann-Whitney U tests confirm significant differences for **Org Silo** (p < 0.001) and **Lone Wolf** (p = 0.012)
- Community Smell indicators: Radio Silence 39.7%, Lone Wolf 30.0%, Org Silo 28.7%
- **3 sociotechnical profiles** identified via k-means clustering (N=113)
- Network density is the key contextual factor differentiating cluster profiles

### csDetector-fixed

The original csDetector tool processed only 50/318 repositories (15.7%) due to multiple bugs. We created **csDetector-fixed**, a patched version with 13 bug fixes that achieved **300/318 (94.3%)** coverage. Key fixes include:

- Cross-platform compatibility (macOS/Linux support)
- Python 3.10+ compatibility
- Division-by-zero guards in 7 analysis modules
- GitHub API retry with exponential backoff
- Git branch fallback (master → main → default)
- Robust error handling for politeness/sentiment analysis

See [`tools/csDetector-fixed/CHANGES.md`](tools/csDetector-fixed/CHANGES.md) for the full changelog.

## Tools and Versions

| Tool | Version | Purpose |
|------|---------|---------|
| Designite Java | 2.x (free academic) | Code Smell detection |
| csDetector-fixed | Based on csDetector master + 13 patches | Community Smell detection |
| SentiStrength | Oct 2019 data | Sentiment analysis (used by csDetector) |
| Java | OpenJDK 17 | Runtime |
| Python | 3.10+ | Pipeline scripts, consolidation, analysis |

## How to Reproduce

### Prerequisites

- macOS (Apple Silicon) or Linux
- Java 17+, Python 3.10+, Git
- GitHub Personal Access Token (for API access)

### Steps

1. **Setup environment:**
   ```bash
   bash scripts/01_setup_macos.sh
   ```

2. **Resolve repo URLs** (map repo names to GitHub URLs):
   ```bash
   python tools/csDetector-fixed/build_repo_urls.py \
     --repos-csv data/consolidated_code_smells.csv \
     --pat YOUR_GITHUB_PAT \
     --output urls/
   ```

3. **Run csDetector-fixed batch** (community smell detection on all repos):
   ```bash
   python tools/csDetector-fixed/run_batch.py \
     --repos-list urls/repo_urls.txt \
     --output-dir Dataset/community_smells_v2 \
     --senti-path /path/to/SentiStrength \
     --pat YOUR_GITHUB_PAT \
     --timeout 900
   ```

4. **Consolidate results:**
   ```bash
   python tools/csDetector-fixed/consolidate_results.py \
     --results-dir Dataset/community_smells_v2 \
     --output-dir data/
   ```

5. **Run analysis:**
   ```bash
   python scripts/06_analysis_v2.py
   python scripts/07_analysis_extra.py
   ```

## Inclusion/Exclusion Criteria

| ID | Criterion | Justification |
|----|-----------|---------------|
| IC1 | Java as primary language | Research focus |
| IC2 | Public GitHub repository | API access and reproducibility |
| IC3 | 500 ≤ LOC ≤ 100,000 | Representative code sample size |
| IC4 | ≥ 1 year of commit history | Temporal analysis feasibility |
| IC5 | Characterized as code sample | Research scope |
| EC1 | Fork repository | Avoid data duplication |
| EC2 | Archived repository | No recent activity |
| EC3 | LOC outside 500–100k range | Out of scope |
| EC4 | No identifiable contributors | Infeasible community analysis |

## Citation

If you use this dataset or pipeline, please cite:

```bibtex
@mastersthesis{Bueno2026,
  author  = {Arthur Ramires Rodrigues Neto Bueno},
  title   = {Análise Evolutiva da Coocorrência entre Code Smells
             e Community Smells em Code Samples},
  school  = {Universidade Federal de Mato Grosso do Sul},
  year    = {2026},
  type    = {Dissertação de Mestrado},
  doi     = {10.5281/zenodo.18649168},
  url     = {https://doi.org/10.5281/zenodo.18649168}
}
```

## License

This replication package is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Contact

- **Arthur Bueno** — arthur.ramires@ufms.br
- **Prof. Awdren Fontão** — awdren.fontao@ufms.br
