# csDetector-fixed: Correções e Melhorias

Fork do [csDetector](https://github.com/Nuri22/csDetector) (Almarimi et al., 2022) com correções de bugs que impediam a execução em ambientes não-Windows e em repositórios com baixa atividade social.

## Bugs Críticos Corrigidos

### 1. Crash em Mac/Linux (devNetwork.py:24)
**Original:** `FILEBROWSER_PATH = os.path.join(os.getenv("WINDIR"), "explorer.exe")`
**Problema:** `WINDIR` não existe em Mac/Linux → `TypeError: expected str, bytes or os.PathLike object, not NoneType`
**Fix:** Condicional por `os.name == 'nt'`

### 2. Hardcoded branch "master" (repoLoader.py:22)
**Original:** `branch="master"` no `git.Repo.clone_from()`
**Problema:** Repos que usam "main" como branch default falham no clone
**Fix:** Fallback sequencial: "master" → "main" → branch default do repo

### 3. Python 3.8 obrigatório (devNetwork.py:36)
**Original:** `if sys.version_info.minor != 8: raise Exception(...)`
**Problema:** Impede execução em Python 3.9+
**Fix:** Aceita Python 3.8+ com warning

### 4. Sem retry na API do GitHub (graphqlAnalysisHelper.py)
**Original:** Uma única tentativa por request, sem tratamento de rate limit
**Problema:** Rate limit (HTTP 403/429) ou erros transitórios (502/503) abortam toda a análise
**Fix:** Retry com exponential backoff (até 5 tentativas), respeita header `X-RateLimit-Reset`

### 5. Divisão por zero em repos sem PRs (prAnalysis.py:121)
**Original:** `generallyNegativeRatio = len(generallyNegative) / prCount`
**Problema:** `ZeroDivisionError` quando batch tem 0 PRs
**Fix:** Guard `if prCount > 0 else 0`

### 6. Divisão por zero em repos sem Issues (issueAnalysis.py:122)
**Original:** `generallyNegativeRatio = len(generallyNegative) / issueCount`
**Fix:** Guard `if issueCount > 0 else 0`

### 7. Divisão por zero em centralityAnalysis.py
**Linhas 148 e 156:** `percentageHighCentralityAuthors` e `tfc`
**Fix:** Guards para `len(allRelatedAuthors) > 0` e `total_items > 0`

### 8. Divisão por zero em devAnalysis.py
**Linhas 22, 43, 44:** `busFactor`, `sponsoredTFC`, `experiencedTFC`
**Fix:** Guards para `len(devs) > 0` e `commitCount > 0`

### 9. Divisão por zero em commitAnalysis.py
**Linhas 176, 192:** `diff` e `percentageSponsoredAuthors`
**Fix:** Guards para `commitCount > 0` e `authorCount > 0`

### 10. statsAnalysis.py não trata lista vazia
**Original:** `calculateStats([])` → `StatisticsError: mean requires at least one data point`
**Fix:** Return `{count: 0, mean: 0, stdev: 0}` para lista vazia; `stdev` retorna 0 (não None) para lista com 1 elemento

### 11. Bug de precedência na ACCL (politenessAnalysis.py:31)
**Original:** `accl = prCommentLengthsMean + issueCommentLengthsMean / 2`
**Problema:** Calcula `pr + (issue/2)` em vez de `(pr + issue) / 2` (média)
**Fix:** `accl = (prCommentLengthsMean + issueCommentLengthsMean) / 2`

### 12. Bug: RPCIssue usa dados de PR (politenessAnalysis.py:19)
**Original:** `calculateRPC(config, "Issue", prCommentBatches)` — usa `prCommentBatches` duas vezes
**Fix:** `calculateRPC(config, "Issue", issueCommentBatches)`

### 13. politenessAnalysis crash com 0 comentários
**Original:** `getResults([])` → crash no ConvoKit ao criar corpus vazio
**Fix:** Early return 0 se `len(comments) == 0`

## Scripts Auxiliares

- `build_repo_urls.py`: Resolve nomes de repos → URLs do GitHub via Search API
- `run_batch.py`: Wrapper para execução em lote com tratamento de erro individual
- `consolidate_results.py`: Consolida resultados em CSVs compatíveis com o dataset original
