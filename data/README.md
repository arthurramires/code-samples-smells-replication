# Data Directory

## Structure

```
data/
├── README.md                          # This file
├── repositories.csv                   # PRIMARY DATASET: 318 repos with metadata
├── clustering_outliers.csv            # 22 repos excluded from clustering (±2 SD)
├── processed/                         # Consolidated analysis-ready CSVs
│   ├── consolidated_code_smells.csv   # 318 repos × 28 code smell types
│   ├── consolidated_metrics.csv       # 318 repos × 17 software metrics
│   ├── consolidated_community.csv     # 50 repos × 20 community metrics (v1)
│   ├── consolidated_community_300.csv # 300 repos × 53 community metrics (v2)
│   ├── consolidated_full.csv          # 50 repos × 62 merged (v1)
│   └── consolidated_full_300.csv      # 300 repos × 35 merged (v2)
└── raw/                               # Raw tool outputs (populated during reproduction)
    └── README.md                      # Instructions for raw data access
```

## Primary Dataset: `repositories.csv`

The central dataset listing all 318 Java code sample repositories with:

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Sequential identifier (1–318) |
| `repo_name` | string | GitHub repository name |
| `github_url` | string | GitHub search URL for resolution |
| `CommitCount` | int | Total commits (NULL if not in social analysis) |
| `AuthorCount` | int | Unique authors |
| `DaysActive` | int | Days between first and last commit |
| `BusFactorNumber` | float | Bus Factor (NULL if < 2 active authors) |
| `lone_wolf` | binary | Lone Wolf indicator |
| `radio_silence` | binary | Radio Silence indicator |
| `org_silo` | binary | Organizational Silo indicator |
| `total_code_smells` | int | Total code smells (design + implementation) |
| `total_design_smells` | int | Design smells count |
| `total_impl_smells` | int | Implementation smells count |
| `in_social_analysis` | binary | 1 = included in social analysis (N=300) |
| `in_clustering` | binary | 1 = included in k-means clustering (N=113) |
| `clustering_outlier` | binary | 1 = excluded from clustering as outlier (N=22) |
| `has_bus_factor` | binary | 1 = Bus Factor data available (N=135) |

### Subset Summary

| Subset | N | Selection Criteria |
|--------|---|-------------------|
| All repositories | 318 | IC1–IC5, EC1–EC4 |
| Social analysis | 300 | csDetector-fixed successful (94.3%) |
| Bus Factor available | 135 | ≥2 active authors in collaboration graph |
| Clustering (k-means) | 113 | Complete data + within ±2 SD |
| Clustering outliers | 22 | Complete data but >±2 SD in any variable |
| Excluded from social | 18 | Repository deleted/renamed on GitHub |

## Provenance

- **Collection date**: February 14, 2026
- **GitHub API data**: Reflects repository state as of collection date
- **Tools**: Designite Java 2.x (code smells), csDetector-fixed (community)
- **Pipeline**: Fully automated via `scripts/01–07`

## Data Flow

```
GitHub API (343 candidate repos)
    │
    ├── scripts/05_filter_dataset.py ──→ 318 repos (IC/EC criteria)
    │
    ├── Designite Java ──────→ raw/designite/   → processed/consolidated_code_smells.csv
    │                                            → processed/consolidated_metrics.csv
    │
    ├── csDetector-fixed ────→ raw/csdetector/  → processed/consolidated_community_300.csv
    │
    └── scripts/04_consolidate.py ────→ processed/consolidated_full_300.csv
                                       → repositories.csv (merged metadata)
```

## Format

- **Encoding**: UTF-8
- **Delimiter**: Comma (`,`)
- **Header**: First row contains column names
- **Missing values**: Empty cells (no sentinel values)
- **Numeric format**: Decimal point (`.`), no thousands separator
- **Boolean/binary**: 0 or 1 (integer)

## Variable Definitions

See [`../docs/CODEBOOK.md`](../docs/CODEBOOK.md) for complete variable definitions.

## License

Released under MIT License. See [`../LICENSE`](../LICENSE).
