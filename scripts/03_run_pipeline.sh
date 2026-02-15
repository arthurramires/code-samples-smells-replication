#!/bin/bash
# ==============================================================
# 03_run_pipeline.sh — Execução do pipeline Designite + csDetector
# Uso: bash 03_run_pipeline.sh repos_final.csv [--dry-run]
# ==============================================================
set -euo pipefail

REPOS_CSV="${1:-}"
DRY_RUN="${2:-}"
WORK_DIR="$HOME/mestrado-pipeline"
DESIGNITE_JAR=$(find "$WORK_DIR/tools" -name "DesigniteJava*.jar" 2>/dev/null | head -1)
CSDETECTOR_DIR="$WORK_DIR/tools/csDetector"
SENTISTRENGTH_DIR="$WORK_DIR/tools/SentiStrength"
OUTPUT_BASE="$WORK_DIR/results"
CLONE_BASE="$WORK_DIR/repos"
LOG_DIR="$WORK_DIR/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/pipeline_${TIMESTAMP}.log"
PROGRESS_FILE="$LOG_DIR/progress_${TIMESTAMP}.csv"

# ---- Validações ----
if [ -z "$REPOS_CSV" ]; then
    echo "Uso: bash 03_run_pipeline.sh <repos_final.csv> [--dry-run]"
    echo ""
    echo "  O CSV deve ter colunas: repo_name,repo_url"
    echo "  Use --dry-run para testar com os 3 primeiros repos"
    exit 1
fi

if [ ! -f "$REPOS_CSV" ]; then
    echo "[ERRO] Arquivo não encontrado: $REPOS_CSV"
    exit 1
fi

if [ -z "$DESIGNITE_JAR" ]; then
    echo "[ERRO] DesigniteJava.jar não encontrado em $WORK_DIR/tools/"
    echo "Baixe de: https://www.designite-tools.com/designitejava"
    exit 1
fi

if [ ! -d "$CSDETECTOR_DIR" ]; then
    echo "[ERRO] csDetector não encontrado em $CSDETECTOR_DIR"
    echo "Clone: git clone https://github.com/Nuri22/csDetector.git $CSDETECTOR_DIR"
    exit 1
fi

if [ ! -f "$SENTISTRENGTH_DIR/SentiStrength.jar" ]; then
    echo "[ERRO] SentiStrength.jar não encontrado em $SENTISTRENGTH_DIR/"
    echo "Baixe de: https://github.com/MikeThelwall/SentiStrength"
    echo "Coloque SentiStrength.jar e SentiStrength_Data/ em: $SENTISTRENGTH_DIR/"
    exit 1
fi

if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "[ERRO] GITHUB_TOKEN não definido. csDetector requer o token."
    echo "Defina: export GITHUB_TOKEN='ghp_SEU_TOKEN'"
    exit 1
fi

mkdir -p "$OUTPUT_BASE"/{code_smells,community_smells} "$LOG_DIR" "$CLONE_BASE"

# ---- Contar repos ----
TOTAL_REPOS=$(tail -n +2 "$REPOS_CSV" | wc -l | tr -d ' ')
PROCESSED=0
FAILED=0

if [ "$DRY_RUN" == "--dry-run" ]; then
    MAX_REPOS=3
    echo "[DRY-RUN] Executando apenas nos primeiros $MAX_REPOS repos"
else
    MAX_REPOS=$TOTAL_REPOS
fi

echo "============================================" | tee -a "$LOG_FILE"
echo "  Pipeline de Execução — $TIMESTAMP" | tee -a "$LOG_FILE"
echo "  Total de repos: $TOTAL_REPOS (executando: $MAX_REPOS)" | tee -a "$LOG_FILE"
echo "  Designite: $DESIGNITE_JAR" | tee -a "$LOG_FILE"
echo "  csDetector: $CSDETECTOR_DIR/devNetwork.py" | tee -a "$LOG_FILE"
echo "  SentiStrength: $SENTISTRENGTH_DIR" | tee -a "$LOG_FILE"
echo "  Log: $LOG_FILE" | tee -a "$LOG_FILE"
echo "============================================" | tee -a "$LOG_FILE"

# ---- Header do progresso ----
echo "repo_name,designite_status,csdetector_status,duration_seconds" > "$PROGRESS_FILE"

# ---- Loop principal ----
CURRENT=0
while IFS=, read -r repo_name repo_url source ecosystem loc years _rest; do
    # Pular header
    if [ "$repo_name" == "repo_name" ] || [ "$repo_name" == "fullName" ]; then
        continue
    fi

    CURRENT=$((CURRENT + 1))
    if [ $CURRENT -gt $MAX_REPOS ]; then
        break
    fi

    START_TIME=$(date +%s)
    echo "" | tee -a "$LOG_FILE"
    echo "[$CURRENT/$MAX_REPOS] Processando: $repo_name" | tee -a "$LOG_FILE"
    echo "  URL: $repo_url" | tee -a "$LOG_FILE"

    DESIGNITE_STATUS="OK"
    CSDETECTOR_STATUS="OK"

    # ---- Clone ----
    CLONE_DIR="$CLONE_BASE/$repo_name"
    if [ ! -d "$CLONE_DIR" ]; then
        echo "  Clonando..." | tee -a "$LOG_FILE"
        git clone "$repo_url" "$CLONE_DIR" 2>>"$LOG_FILE" || {
            echo "  [FALHA] Clone falhou" | tee -a "$LOG_FILE"
            DESIGNITE_STATUS="CLONE_FAIL"
            CSDETECTOR_STATUS="CLONE_FAIL"
            echo "$repo_name,$DESIGNITE_STATUS,$CSDETECTOR_STATUS,0" >> "$PROGRESS_FILE"
            FAILED=$((FAILED + 1))
            continue
        }
    else
        echo "  [SKIP] Repo já clonado" | tee -a "$LOG_FILE"
    fi

    # ---- Designite ----
    DESIGNITE_OUT="$OUTPUT_BASE/code_smells/$repo_name"
    if [ ! -d "$DESIGNITE_OUT" ] || [ -z "$(ls -A "$DESIGNITE_OUT" 2>/dev/null)" ]; then
        echo "  Rodando Designite..." | tee -a "$LOG_FILE"
        mkdir -p "$DESIGNITE_OUT"
        java -jar "$DESIGNITE_JAR" \
            -i "$CLONE_DIR" \
            -o "$DESIGNITE_OUT" \
            2>>"$LOG_FILE" || {
            echo "  [FALHA] Designite falhou" | tee -a "$LOG_FILE"
            DESIGNITE_STATUS="FAIL"
        }
    else
        echo "  [SKIP] Designite já executado" | tee -a "$LOG_FILE"
        DESIGNITE_STATUS="SKIP"
    fi

    # ---- csDetector ----
    CSDETECTOR_OUT="$OUTPUT_BASE/community_smells/$repo_name"
    if [ ! -d "$CSDETECTOR_OUT" ] || [ -z "$(ls -A "$CSDETECTOR_OUT" 2>/dev/null)" ]; then
        echo "  Rodando csDetector..." | tee -a "$LOG_FILE"
        mkdir -p "$CSDETECTOR_OUT"
        (
            cd "$CSDETECTOR_DIR"
            source venv/bin/activate 2>/dev/null || true
            python devNetwork.py \
                -p "$GITHUB_TOKEN" \
                -r "$repo_url" \
                -s "$SENTISTRENGTH_DIR" \
                -o "$CSDETECTOR_OUT" \
                2>>"$LOG_FILE"
        ) || {
            echo "  [FALHA] csDetector falhou" | tee -a "$LOG_FILE"
            CSDETECTOR_STATUS="FAIL"
        }
    else
        echo "  [SKIP] csDetector já executado" | tee -a "$LOG_FILE"
        CSDETECTOR_STATUS="SKIP"
    fi

    # ---- Registrar progresso ----
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    echo "$repo_name,$DESIGNITE_STATUS,$CSDETECTOR_STATUS,$DURATION" >> "$PROGRESS_FILE"

    PROCESSED=$((PROCESSED + 1))
    echo "  Concluído em ${DURATION}s (Status: D=$DESIGNITE_STATUS, CS=$CSDETECTOR_STATUS)" | tee -a "$LOG_FILE"

done < "$REPOS_CSV"

echo "" | tee -a "$LOG_FILE"
echo "============================================" | tee -a "$LOG_FILE"
echo "  Pipeline finalizado!" | tee -a "$LOG_FILE"
echo "  Processados: $PROCESSED / $MAX_REPOS" | tee -a "$LOG_FILE"
echo "  Falhas: $FAILED" | tee -a "$LOG_FILE"
echo "  Progresso salvo em: $PROGRESS_FILE" | tee -a "$LOG_FILE"
echo "  Log completo em: $LOG_FILE" | tee -a "$LOG_FILE"
echo "============================================" | tee -a "$LOG_FILE"
