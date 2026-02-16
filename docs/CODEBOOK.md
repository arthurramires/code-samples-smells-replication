# Codebook — Variable Definitions

This document describes all variables in the consolidated CSV files.
## repositories.csv (318 rows) — PRIMARY DATASET

| Variable | Type | Description |
|----------|------|-------------|
| `id` | int | Sequential identifier (1–318) |
| `repo_name` | string | GitHub repository name |
| `github_url` | string | GitHub search URL for repository resolution |
| `CommitCount` | int | Total number of commits |
| `AuthorCount` | int | Number of unique commit authors |
| `DaysActive` | int | Days between first and last commit |
| `BusFactorNumber` | float | Bus Factor score (0–1, NULL if < 2 authors) |
| `lone_wolf` | binary | 1 = Lone Wolf detected (BusFactor > 0.9) |
| `radio_silence` | binary | 1 = Radio Silence detected (0 PRs AND 0 Issues) |
| `org_silo` | binary | 1 = Org Silo detected (communities ≥ 3, density < 0.3) |
| `total_code_smells` | int | Sum of design + implementation smells |
| `total_design_smells` | int | Design smells count (Designite Java) |
| `total_impl_smells` | int | Implementation smells count (Designite Java) |
| `in_social_analysis` | binary | 1 = included in social analysis subset (N=300) |
| `in_clustering` | binary | 1 = included in k-means clustering (N=113) |
| `clustering_outlier` | binary | 1 = excluded from clustering as ±2 SD outlier (N=22) |
| `has_bus_factor` | binary | 1 = Bus Factor data available (N=135) |
| `url_note` | string | Note on URL resolution method |

## clustering_outliers.csv (22 rows)

| Variable | Type | Description |
|----------|------|-------------|
| `repo_name` | string | Repository name |
| `total_code_smells` | int | Total code smells |
| `CommitCount` | int | Total commits |
| `AuthorCount` | int | Number of authors |
| `commitCentrality_Density` | float | Network density |
| `BusFactorNumber` | float | Bus Factor score |
| `DaysActive` | int | Days active |
| `outlier_variables` | string | Variable(s) exceeding ±2 SD threshold |



## consolidated_code_smells.csv (318 rows)

| Variable | Type | Description |
|----------|------|-------------|
| `repo_name` | string | Repository name (GitHub) |
| `total_design_smells` | int | Total design smells detected by Designite |
| `total_impl_smells` | int | Total implementation smells detected by Designite |
| `total_code_smells` | int | Sum of design + implementation smells |
| `God_Class` | int | Classes with excessive responsibility |
| `Feature_Envy` | int | Methods more interested in other classes |
| `Unutilized_Abstraction` | int | Unused abstract classes/interfaces |
| `Deficient_Encapsulation` | int | Insufficient access control |
| `Unexploited_Encapsulation` | int | Encapsulation not leveraged |
| `Multifaceted_Abstraction` | int | Classes with multiple unrelated responsibilities |
| `Insufficient_Modularization` | int | Large, poorly decomposed classes |
| `Hub_Like_Modularization` | int | Central classes with excessive dependencies |
| `Cyclically_Dependent_Modularization` | int | Circular dependency chains |
| `Broken_Hierarchy` | int | Subclass does not properly extend parent |
| `Rebellious_Hierarchy` | int | Subclass rejects parent behavior |
| `Missing_Hierarchy` | int | Missing abstraction in hierarchy |
| `Wide_Hierarchy` | int | Too many direct subclasses |
| `Deep_Hierarchy` | int | Excessively deep inheritance |
| `Long_Method` | int | Methods exceeding length threshold |
| `Complex_Method` | int | Methods with high cyclomatic complexity |
| `Long_Parameter_List` | int | Methods with too many parameters |
| `Magic_Number` | int | Literal numeric values without named constants |
| `Duplicate_Code` | int | Repeated code fragments |
| `Empty_Catch_Clause` | int | Exception handlers with no logic |
| `Long_Statement` | int | Statements exceeding line length |
| `Long_Identifier` | int | Excessively long variable/method names |
| `Missing_Default` | int | Switch without default case |
| `Complex_Conditional` | int | Overly complex conditional expressions |

## consolidated_metrics.csv (318 rows)

| Variable | Type | Description |
|----------|------|-------------|
| `repo_name` | string | Repository name |
| `num_classes` | int | Number of Java classes |
| `num_methods` | int | Number of methods |
| `total_LOC` | float | Total lines of code |
| `mean_LOC` | float | Mean LOC per class |
| `median_LOC` | float | Median LOC per class |
| `mean_WMC` | float | Mean Weighted Method Complexity per class |
| `mean_NOF` | float | Mean Number of Fields per class |
| `mean_NOM` | float | Mean Number of Methods per class |
| `mean_FANIN` | float | Mean afferent coupling |
| `mean_FANOUT` | float | Mean efferent coupling |
| `mean_LCOM` | float | Mean Lack of Cohesion of Methods |
| `mean_DIT` | float | Mean Depth of Inheritance Tree |
| `mean_method_LOC` | float | Mean LOC per method |
| `mean_CC` | float | Mean Cyclomatic Complexity |
| `max_CC` | float | Maximum Cyclomatic Complexity |
| `smell_density` | float | total_code_smells / num_classes × 100 |

## consolidated_community.csv (50 rows)

| Variable | Type | Description |
|----------|------|-------------|
| `repo_name` | string | Repository name |
| `commit_count` | int | Total number of commits |
| `days_active` | int | Days between first and last commit |
| `author_count` | int | Number of unique commit authors |
| `timezone_count` | int | Number of distinct timezones |
| `num_communities` | int | Communities detected in collaboration network |
| `num_tags` | int | Number of Git tags |
| `num_prs` | int | Number of pull requests |
| `num_issues` | int | Number of issues |
| `mean_author_days` | float | Mean active days per author |
| `mean_commits_per_author` | float | Mean commits per author |
| `max_commits_per_author` | int | Maximum commits by a single author |
| `mean_centrality` | float | Mean degree centrality in collaboration network |
| `mean_pr_participants` | float | Mean participants per PR |
| `mean_issue_participants` | float | Mean participants per issue |
| `mean_issue_comments` | float | Mean comments per issue |
| `lone_wolf_indicator` | binary | 1 = Lone Wolf detected (isolated contributor) |
| `radio_silence_indicator` | binary | 1 = Radio Silence detected (inactive communication) |
| `org_silo_indicator` | binary | 1 = Organizational Silo detected (disconnected subgroups) |

## consolidated_full.csv (50 rows)

Contains all columns from the three files above, merged by `repo_name` (inner join).
Total: 62 columns.

## Community Smell Indicators

The binary indicators are derived by csDetector based on heuristic thresholds:

- **Lone Wolf**: A contributor performs > 80% of total commits AND has no PR/issue interactions with other contributors.
- **Organizational Silo**: The collaboration network (based on co-commits and PR reviews) contains ≥ 2 disconnected components with ≥ 2 members each.
- **Radio Silence**: No issue comments AND no PR review comments exist in the repository.
