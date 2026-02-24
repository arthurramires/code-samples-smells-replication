# Changelog

## [v2.1] — 2026-02-24

### Corrigido (csDetector-fixed)
- `devNetwork.py`: IndexError em repos com poucos PRs/issues — `prAnalysis()` e `issueAnalysis()` retornavam listas menores que `batchDates` quando o repo tinha poucos PRs/issues. Adicionado padding com listas vazias para garantir alinhamento com `batchDates`. Corrige 33/52 falhas no dataset V2.
- `repoLoader.py`: branch fallback (None → master → main) para repos que não usam "master" como branch padrão
- `devAnalysis.py`: guard contra divisão por zero em `busFactor` quando `len(devs) == 0`
- `commitAnalysis.py`: guard contra divisão por zero em `percentageSponsoredAuthors` quando `authorInfoDict` está vazio

### Adicionado
- Diagrama BPMN do pipeline metodológico (`docs/pipeline_overview.pdf`) com swim lanes (pesquisador/scripts/ferramentas/dados) e 5 fases
- Script gerador do diagrama (`docs/gen_pipeline_diagram.py`)

## [v2.0] — 2026-02-24

### Adicionado
- Dataset V2: 444 repositórios candidatos (Azure-Samples, aws-samples, spring-guides, googlesamples)
- Pipeline incremental (`10_pipeline_incremental.sh`) com liberação de disco
- Manifesto JSON para tracking de progresso e resumabilidade
- Critério de idade mínima (2 project years) com embasamento na literatura
- Documentação de decisões metodológicas (`docs/METHODOLOGY.md`)
- Referências bibliográficas para critério temporal (`docs/literature_references_temporal_criteria.md`)

### Adicionado (scripts)
- Script de consolidação unificada V1+V2 (`13_consolidate_unified.py`)
- csDetector-fixed copiado para `tools/` do pipeline de execução

### Alterado
- README.md reestruturado seguindo padrões MSR
- Separação explícita entre pool cross-sectional e pool temporal
- IC4 atualizado: "≥ 2 project years (730 dias)" com referências (Rio 2023, Olbrich 2009, Tufano 2017)
- Autocitações (sbsibueno) substituídas por referências externas (Munaiah 2017, Kalliamvakou 2016, Carruthers 2024)
- Pipeline `10_pipeline_incremental.sh` aponta para `csDetector-fixed` (fix branch master→main)

### Estrutura de dados
- `data/raw/v2_new_repos_to_process.csv` — 18 novos repos (LOC + age ≥ 2y)
- `data/raw/v2_new_repos_all_loc_filtered.csv` — 52 novos repos (LOC only)

## [v1.0] — 2026-02-15

### Dataset original
- 343 candidatos → 318 filtrados → 300 com dados sociais
- 208 repositórios na análise temporal (800 snapshots)
- 135 com Bus Factor → 113 no clustering
- Resultados publicados nos capítulos 6-8 da dissertação
