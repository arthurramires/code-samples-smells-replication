#!/bin/bash
# ==============================================================
# 02_expand_dataset.sh — Expansão do dataset de repos Java
# Busca repositórios de code samples Java no GitHub
# ==============================================================
set -euo pipefail

WORK_DIR="$HOME/mestrado-pipeline"
OUTPUT_DIR="$WORK_DIR/dataset"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "============================================"
echo "  Expansão do Dataset — Code Samples Java"
echo "  Output: $OUTPUT_DIR"
echo "============================================"

# Verificar gh CLI
if ! command -v gh &> /dev/null; then
    echo "[ERRO] GitHub CLI não encontrado. Execute 01_setup_macos.sh"
    exit 1
fi

# ---- 1. Buscar por organizações oficiais ----
echo ""
echo "--- Buscando em organizações oficiais ---"

ORGS=("aws-samples" "Azure-Samples" "GoogleCloudPlatform" "spring-guides" "googlesamples" "microsoftarchive" "oracle-samples")

for org in "${ORGS[@]}"; do
    echo "  Buscando: $org (Java repos)..."
    gh repo list "$org" --language=Java --limit=500 \
        --json fullName,url,stargazersCount,createdAt,pushedAt,description \
        > "$OUTPUT_DIR/raw_${org}.json" 2>/dev/null || echo "  [WARN] Falhou para $org"
done

# ---- 2. Buscar por keywords ----
echo ""
echo "--- Buscando por keywords ---"

KEYWORDS=("java code samples" "java examples" "java sample code" "java demo application" "java tutorial project")

for i in "${!KEYWORDS[@]}"; do
    keyword="${KEYWORDS[$i]}"
    echo "  Buscando: '$keyword'..."
    gh search repos "$keyword" --language=Java --limit=100 \
        --json fullName,url,stargazersCount,createdAt,description \
        > "$OUTPUT_DIR/raw_search_$i.json" 2>/dev/null || echo "  [WARN] Falhou para '$keyword'"
done

# ---- 3. Consolidar e deduplicar ----
echo ""
echo "--- Consolidando resultados ---"

python3 << 'PYEOF'
import json
import glob
import csv
import os

output_dir = os.path.expanduser("~/mestrado-pipeline/dataset")
all_repos = {}

# Ler todos os JSONs
for f in glob.glob(os.path.join(output_dir, "raw_*.json")):
    try:
        with open(f) as fh:
            data = json.load(fh)
            for repo in data:
                name = repo.get("fullName", "")
                if name and name not in all_repos:
                    all_repos[name] = {
                        "fullName": name,
                        "url": repo.get("url", f"https://github.com/{name}"),
                        "stars": repo.get("stargazersCount", 0),
                        "createdAt": repo.get("createdAt", ""),
                        "pushedAt": repo.get("pushedAt", ""),
                        "description": (repo.get("description", "") or "")[:200]
                    }
    except Exception as e:
        print(f"  [WARN] Erro ao ler {f}: {e}")

# Salvar CSV consolidado
csv_path = os.path.join(output_dir, "candidates_all.csv")
with open(csv_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["fullName", "url", "stars", "createdAt", "pushedAt", "description"])
    writer.writeheader()
    for repo in sorted(all_repos.values(), key=lambda x: x["stars"], reverse=True):
        writer.writerow(repo)

print(f"\n  Total de repos candidatos (deduplicated): {len(all_repos)}")
print(f"  Salvo em: {csv_path}")
PYEOF

echo ""
echo "============================================"
echo "  PRÓXIMO PASSO:"
echo "  1. Revisar candidates_all.csv"
echo "  2. Filtrar por critérios IC/EC (LOC 500-100k, ≥2 anos, Java)"
echo "  3. Criar repos_final.csv com apenas os aprovados"
echo "  4. Executar: bash 03_run_pipeline.sh repos_final.csv"
echo "============================================"
