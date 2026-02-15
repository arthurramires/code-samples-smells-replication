# Replication Package: Co-occurrence of Code Smells and Community Smells in Java Code Samples

[![DOI](https://img.shields.io/badge/DOI-pending-blue)]()
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

The study investigates the co-occurrence between Code Smells (detected by Designite Java) and Community Smells (detected by csDetector) in 318 Java open-source code sample repositories.

## Repository Structure

```
replication-package/
├── README.md                  # This file
├── CITATION.cff               # Machine-readable citation (GitHub-native)
├── LICENSE                    # MIT License
├── INSTALL.md                 # Setup and reproduction instructions
├── scripts/
│   ├── 01_setup_macos.sh      # Environment setup (macOS/Apple Silicon)
│   ├── 02_expand_dataset.sh   # Dataset expansion via GitHub API
│   ├── 03_run_pipeline.sh     # Main pipeline: Designite + csDetector
│   ├── 04_consolidate.py      # Consolidation of raw outputs into unified CSV
│   └── 05_filter_dataset.py   # Dataset filtering by IC/EC criteria
├── data/
│   ├── README.md              # Data provenance and format documentation
│   ├── consolidated_code_smells.csv   # 318 repos × 24 code smell types
│   ├── consolidated_metrics.csv       # 318 repos × 16 software metrics
│   ├── consolidated_community.csv     # 50 repos × 19 community metrics
│   └── consolidated_full.csv          # 50 repos × merged technical + social
└── docs/
    ├── CODEBOOK.md            # Variable definitions and data dictionary
    └── MSR-FAIR-COMPLIANCE.md # FAIR principles compliance checklist
```

## Dataset Summary

| Subset | Repositories | Variables | Description |
|--------|-------------|-----------|-------------|
| Code Smells | 318 | 28 | Design and implementation smells per repo |
| Metrics | 318 | 17 | LOC, WMC, CC, FANIN/OUT, LCOM, DIT, smell density |
| Community | 50 | 20 | Commits, authors, PRs, issues, centrality, CS indicators |
| Full | 50 | 62 | Merged technical + social (inner join) |

## Key Findings

- **100,643 Code Smell instances** across 318 repositories
- Top 3 smells: Magic Number (57.4%), Unutilized Abstraction (20.8%), Long Statement (13.3%)
- **24 significant Spearman correlations** (|ρ| ≥ 0.3, p < 0.05) between technical and social metrics
- Strongest: total_code_smells ↔ commit_count (ρ = 0.666, p < 0.001)
- Key negative: smell_density ↔ mean_centrality (ρ = −0.328, p = 0.020)
- Community Smell indicators: Org Silo in 46% of repos, Lone Wolf in 22%
- **3 sociotechnical profiles** identified via k-means clustering

## Tools and Versions

| Tool | Version | Purpose |
|------|---------|---------|
| Designite Java | 2.x (free academic) | Code Smell detection |
| csDetector | master (commit hash in INSTALL.md) | Community Smell detection |
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

2. **Expand dataset** (collect repository list from GitHub organizations):
   ```bash
   bash scripts/02_expand_dataset.sh
   ```

3. **Run pipeline** (Designite + csDetector on all repos):
   ```bash
   bash scripts/03_run_pipeline.sh
   ```

4. **Consolidate results:**
   ```bash
   python scripts/04_consolidate.py \
     --base-dir ~/mestrado-pipeline \
     --progress ~/mestrado-pipeline/logs/progress_*.csv \
     --output-dir data/
   ```

5. **Statistical analysis** can be performed using standard Python libraries (scipy, sklearn, pandas).

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
  type    = {Dissertação de Mestrado}
}
```

## License

This replication package is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Contact

- **Arthur Bueno** — guitarumoto@gmail.com
- **Prof. Awdren Fontão** — awdren.fontao@ufms.br
