# Raw Data Directory

This directory is populated during pipeline reproduction (Step 3 of INSTALL.md).

## Expected Contents After Reproduction

```
raw/
├── designite/           # Designite Java outputs (one folder per repo)
│   ├── repo1/
│   │   ├── DesignSmells.csv
│   │   ├── ImplementationSmells.csv
│   │   └── TypeMetrics.csv
│   └── ...
└── csdetector/          # csDetector-fixed outputs (one folder per repo)
    ├── repo1/
    │   ├── results.json
    │   ├── commitNetwork.graphml
    │   └── devNetwork.graphml
    └── ...
```

## Why Raw Data Is Not Included

Raw outputs exceed GitHub's file size limits (>2 GB total for 318 repositories).
The pipeline scripts regenerate all raw data from source repositories.

To obtain the raw data without re-running the pipeline, contact:
- arthur.ramires@ufms.br
