# MSR Data and Tool Showcase — Compliance Checklist

This document maps our replication package against the MSR 2025/2026 Data and Tool Showcase requirements and the FAIR principles.

## Sources

- [MSR 2026 Data and Tool Showcase Track](https://2026.msrconf.org/track/msr-2026-data-and-tool-showcase-track)
- [MSR 2025 Data and Tool Showcase Track](https://2025.msrconf.org/track/msr-2025-data-and-tool-showcase-track)
- [FAIR Guiding Principles (GO FAIR)](https://www.go-fair.org/fair-principles/)
- [Wilkinson et al. 2016 — FAIR Principles (Nature Scientific Data)](https://www.nature.com/articles/sdata201618)
- [FAIR for Research Software (FAIR4RS)](https://www.nature.com/articles/s41597-022-01710-x)
- [Directory of MSR Datasets (MDPI 2025)](https://www.mdpi.com/2306-5729/10/3/28)

---

## 1. MSR Data Showcase Requirements

### Required Content for Dataset Papers

| Requirement | Status | Notes |
|---|---|---|
| Details about the dataset | ✅ | README.md + CODEBOOK.md |
| Limitations and challenges | ✅ | README.md (csDetector 268 failures) + INSTALL.md |
| Source code of custom tools | ✅ | scripts/ folder (5 scripts) |
| Clear documentation on how to recreate | ✅ | INSTALL.md (step-by-step) |
| Open-source license | ✅ | MIT License |
| Citable release with DOI | ⬜ PENDING | Zenodo integration needed |
| DOI citation in camera-ready | ⬜ PENDING | Will add to LaTeX text |
| CITATION file | ⬜ PENDING | Need CITATION.cff |

### Review Criteria

| Criterion | How We Address It |
|---|---|
| Value, usefulness, reusability | First dataset combining Code Smells + Community Smells in code samples |
| Quality of presentation | Structured README, CODEBOOK, INSTALL docs |
| Relation with related work | README cites Designite, csDetector, Palomba, Tamburri |
| Availability and accessibility | Public GitHub repo + Zenodo DOI |

---

## 2. FAIR Principles Compliance

### F — Findable

| Principle | Compliance | Implementation |
|---|---|---|
| F1: Globally unique persistent identifier | ⬜ PENDING | Zenodo DOI |
| F2: Rich metadata | ✅ | CODEBOOK.md (62 variables documented) |
| F3: Metadata includes data identifier | ⬜ PENDING | Will link DOI in CODEBOOK |
| F4: Indexed in searchable resource | ⬜ PENDING | Zenodo + GitHub |

### A — Accessible

| Principle | Compliance | Implementation |
|---|---|---|
| A1: Retrievable by identifier via standard protocol | ⬜ PENDING | HTTPS via Zenodo/GitHub |
| A1.1: Open, free protocol | ✅ | HTTPS |
| A1.2: Authentication if needed | ✅ | Public (no auth) |
| A2: Metadata accessible even if data gone | ⬜ PENDING | Zenodo preserves metadata |

### I — Interoperable

| Principle | Compliance | Implementation |
|---|---|---|
| I1: Formal, shared language | ✅ | CSV (RFC 4180), Markdown |
| I2: FAIR vocabularies | ✅ | Standard MSR variable names (LOC, CC, WMC) |
| I3: Qualified references | ✅ | BibTeX citation, tool references |

### R — Reusable

| Principle | Compliance | Implementation |
|---|---|---|
| R1: Rich descriptions | ✅ | CODEBOOK.md, README.md |
| R1.1: Clear license | ✅ | MIT License |
| R1.2: Detailed provenance | ✅ | INSTALL.md documents full pipeline |
| R1.3: Domain community standards | ✅ | Follows MSR Data Showcase norms |

---

## 3. Pending Actions

1. **Create CITATION.cff** — GitHub-native citation file
2. **Publish to GitHub** — Public repository
3. **Create Zenodo release** — Archive with DOI
4. **Add DOI badge** to README.md
5. **Reference DOI** in LaTeX dissertation text
6. **Add datapackage.json** (optional, for machine-readable metadata)

---

## 4. Repository Structure (MSR-aligned)

Based on analysis of accepted MSR Data Showcase papers, the recommended structure is:

```
replication-package/
├── README.md              # Overview, motivation, structure, citation
├── CITATION.cff           # Machine-readable citation metadata
├── LICENSE                 # Open-source license (MIT)
├── INSTALL.md             # Setup and reproduction instructions
├── data/
│   ├── raw/               # (optional) Raw tool outputs
│   ├── processed/         # Consolidated CSVs
│   └── README.md          # Data-specific documentation
├── scripts/
│   ├── collect/           # Data collection scripts
│   ├── analyze/           # Analysis scripts
│   └── README.md          # Script documentation
├── docs/
│   ├── CODEBOOK.md        # Variable definitions
│   ├── MSR-FAIR-COMPLIANCE.md  # This file
│   └── figures/           # Generated figures (if any)
└── results/               # (optional) Statistical outputs
```

Note: Our current flat structure (`scripts/`, `data/`) is acceptable for a dissertation replication package. The nested structure above is recommended if targeting a standalone MSR Data Showcase submission.
