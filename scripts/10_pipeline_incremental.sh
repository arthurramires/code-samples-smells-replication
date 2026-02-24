#!/bin/bash
# ==============================================================
# 10_pipeline_incremental.sh — Pipeline Incremental com Liberação de Disco
# ==============================================================
# Processa cada repositório de forma completa e independente:
#   1. Clone
#   2. Designite (cross-sectional)
#   3. Designite temporal (snapshots por project year)
#   4. csDetector
#   5. Consolidar métricas do repo
#   6. Limpar clone do disco
#
# Diferenças do 03_run_pipeline.sh:
#   - Processa UM repo por vez e libera disco após consolidar
#   - Inclui temporal extraction integrado (antes era script separado)
#   - Usa manifesto JSON para tracking de progresso e resumabilidade
#   - Filtra por idade mínima (MIN_AGE_DAYS) para temporal
#
# Uso: bash 10_pipeline_incremental.sh repos.csv [--dry-run] [--skip-temporal]
# ==============================================================
set -euo pipefail

# ---- Parâmetros ----
REPOS_CSV="${1:-}"
DRY_RUN=false
SKIP_TEMPORAL=false
for arg in "${@:2}"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --skip-temporal) SKIP_TEMPORAL=true ;;
    esac
done

# ---- Configuração ----
WORK_DIR="$HOME/mestrado-pipeline"
DESIGNITE_JAR=$(find "$WORK_DIR/tools" -name "DesigniteJava*.jar" 2>/dev/null | head -1)
CSDETECTOR_DIR="$WORK_DIR/tools/csDetector-fixed"
SENTISTRENGTH_DIR="$WORK_DIR/tools/SentiStrength"
OUTPUT_BASE="$WORK_DIR/results"
CLONE_BASE="$WORK_DIR/repos"
LOG_DIR="$WORK_DIR/logs"
MANIFEST="$WORK_DIR/manifest.json"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/pipeline_incr_${TIMESTAMP}.log"

# ---- Critérios de filtragem temporal ----
MIN_AGE_DAYS=730          # Mínimo 2 project years (Rio & Brito e Abreu, 2023)
MAX_PROJECT_YEARS=5
DAYS_PER_YEAR=365

# ---- Validações ----
if [ -z "$REPOS_CSV" ]; then
    echo "Uso: bash 10_pipeline_incremental.sh <repos.csv> [--dry-run] [--skip-temporal]"
    echo ""
    echo "  CSV: repo_name,org,url,loc_val,age_years,commits_val"
    echo "  --dry-run       Testa com 3 repos sem executar ferramentas"
    echo "  --skip-temporal  Pula a análise temporal (só cross-sectional)"
    exit 1
fi

[ ! -f "$REPOS_CSV" ] && echo "[ERRO] CSV não encontrado: $REPOS_CSV" && exit 1
[ -z "$DESIGNITE_JAR" ] && echo "[ERRO] DesigniteJava.jar não encontrado" && exit 1
[ ! -d "$CSDETECTOR_DIR" ] && echo "[ERRO] csDetector não encontrado" && exit 1
[ -z "${GITHUB_TOKEN:-}" ] && echo "[ERRO] GITHUB_TOKEN não definido" && exit 1

mkdir -p "$OUTPUT_BASE"/{code_smells,community_smells,temporal} "$LOG_DIR" "$CLONE_BASE"

# ---- Manifesto (JSON para tracking) ----
init_manifest() {
    if [ ! -f "$MANIFEST" ]; then
        echo '{"version":"2.0","created":"'"$TIMESTAMP"'","repos":{}}' > "$MANIFEST"
    fi
}

get_repo_status() {
    local repo="$1"
    local stage="$2"
    python3 -c "
import json, sys
try:
    m = json.load(open('$MANIFEST'))
    print(m.get('repos',{}).get('$repo',{}).get('$stage',{}).get('status','PENDING'))
except: print('PENDING')
" 2>/dev/null
}

update_manifest() {
    local repo="$1" stage="$2" status="$3" details="${4:-}"
    python3 -c "
import json, datetime
m = json.load(open('$MANIFEST'))
if '$repo' not in m['repos']: m['repos']['$repo'] = {}
m['repos']['$repo']['$stage'] = {
    'status': '$status',
    'timestamp': datetime.datetime.now().isoformat(),
    'details': '$details'
}
json.dump(m, open('$MANIFEST','w'), indent=2)
" 2>/dev/null
}

# ---- Funções do pipeline ----

clone_repo() {
    local repo_name="$1" repo_url="$2"
    local clone_dir="$CLONE_BASE/$repo_name"

    if [ -d "$clone_dir/.git" ]; then
        echo "  [SKIP] Já clonado" | tee -a "$LOG_FILE"
        return 0
    fi

    echo "  Clonando $repo_url..." | tee -a "$LOG_FILE"
    git clone --quiet "$repo_url" "$clone_dir" 2>>"$LOG_FILE"
}

run_designite_cross() {
    local repo_name="$1"
    local clone_dir="$CLONE_BASE/$repo_name"
    local out_dir="$OUTPUT_BASE/code_smells/$repo_name"

    local status=$(get_repo_status "$repo_name" "designite_cross")
    if [ "$status" == "OK" ] && [ -d "$out_dir" ] && [ -n "$(ls -A "$out_dir" 2>/dev/null)" ]; then
        echo "  [SKIP] Designite cross-sectional já OK" | tee -a "$LOG_FILE"
        return 0
    fi

    echo "  Rodando Designite (cross-sectional)..." | tee -a "$LOG_FILE"
    mkdir -p "$out_dir"

    if java -jar "$DESIGNITE_JAR" -i "$clone_dir" -o "$out_dir" 2>>"$LOG_FILE"; then
        update_manifest "$repo_name" "designite_cross" "OK"
        echo "  Designite cross OK" | tee -a "$LOG_FILE"
    else
        update_manifest "$repo_name" "designite_cross" "FAIL"
        echo "  [FALHA] Designite cross" | tee -a "$LOG_FILE"
        return 1
    fi
}

run_designite_temporal() {
    local repo_name="$1"
    local clone_dir="$CLONE_BASE/$repo_name"
    local temporal_dir="$OUTPUT_BASE/temporal/$repo_name"

    local status=$(get_repo_status "$repo_name" "designite_temporal")
    if [ "$status" == "OK" ]; then
        echo "  [SKIP] Designite temporal já OK" | tee -a "$LOG_FILE"
        return 0
    fi

    if [ "$SKIP_TEMPORAL" == "true" ]; then
        echo "  [SKIP] Temporal desabilitado" | tee -a "$LOG_FILE"
        return 0
    fi

    echo "  Rodando Designite temporal (snapshots)..." | tee -a "$LOG_FILE"
    mkdir -p "$temporal_dir"

    # Obter data do primeiro commit
    local first_commit_date=$(git -C "$clone_dir" log --reverse --format="%aI" | head -1)
    if [ -z "$first_commit_date" ]; then
        update_manifest "$repo_name" "designite_temporal" "FAIL" "no_commits"
        return 1
    fi

    local first_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${first_commit_date%%+*}" "+%s" 2>/dev/null || \
                        date -d "${first_commit_date}" "+%s" 2>/dev/null)

    # Calcular idade em dias
    local now_epoch=$(date "+%s")
    local age_days=$(( (now_epoch - first_epoch) / 86400 ))

    if [ "$age_days" -lt "$MIN_AGE_DAYS" ]; then
        echo "  [SKIP] Idade ($age_days dias) < mínimo ($MIN_AGE_DAYS)" | tee -a "$LOG_FILE"
        update_manifest "$repo_name" "designite_temporal" "SKIP_AGE" "age_days=$age_days"
        return 0
    fi

    # Salvar HEAD original
    local original_ref=$(git -C "$clone_dir" rev-parse HEAD)
    local snapshots_ok=0

    for year_n in $(seq 1 $MAX_PROJECT_YEARS); do
        local target_epoch=$((first_epoch + year_n * DAYS_PER_YEAR * 86400))

        # Se a data-alvo é no futuro, parar
        if [ "$target_epoch" -gt "$now_epoch" ]; then
            break
        fi

        local target_date=$(date -r "$target_epoch" "+%Y-%m-%d" 2>/dev/null || \
                           date -d "@$target_epoch" "+%Y-%m-%d" 2>/dev/null)

        # Encontrar último commit antes da data-alvo
        local snapshot_hash=$(git -C "$clone_dir" log --before="$target_date" --format="%H" -1 2>/dev/null)

        if [ -z "$snapshot_hash" ]; then
            echo "    Year $year_n ($target_date): nenhum commit encontrado" | tee -a "$LOG_FILE"
            continue
        fi

        local year_dir="$temporal_dir/year_${year_n}"
        mkdir -p "$year_dir"

        echo "    Year $year_n ($target_date): checkout $snapshot_hash" | tee -a "$LOG_FILE"

        # Checkout no snapshot
        git -C "$clone_dir" checkout --quiet "$snapshot_hash" 2>>"$LOG_FILE"

        # Rodar Designite no snapshot
        if java -jar "$DESIGNITE_JAR" -i "$clone_dir" -o "$year_dir" 2>>"$LOG_FILE"; then
            snapshots_ok=$((snapshots_ok + 1))
        else
            echo "    [WARN] Designite falhou em year $year_n" | tee -a "$LOG_FILE"
        fi
    done

    # Restaurar HEAD
    git -C "$clone_dir" checkout --quiet "$original_ref" 2>>"$LOG_FILE" || \
    git -C "$clone_dir" checkout --quiet main 2>>"$LOG_FILE" || \
    git -C "$clone_dir" checkout --quiet master 2>>"$LOG_FILE" || true

    if [ "$snapshots_ok" -gt 0 ]; then
        update_manifest "$repo_name" "designite_temporal" "OK" "snapshots=$snapshots_ok"
        echo "  Designite temporal OK ($snapshots_ok snapshots)" | tee -a "$LOG_FILE"
    else
        update_manifest "$repo_name" "designite_temporal" "FAIL" "no_snapshots"
        echo "  [FALHA] Nenhum snapshot temporal processado" | tee -a "$LOG_FILE"
    fi
}

run_csdetector() {
    local repo_name="$1" repo_url="$2"
    local out_dir="$OUTPUT_BASE/community_smells/$repo_name"

    local status=$(get_repo_status "$repo_name" "csdetector")
    if [ "$status" == "OK" ] && [ -d "$out_dir" ] && [ -n "$(ls -A "$out_dir" 2>/dev/null)" ]; then
        echo "  [SKIP] csDetector já OK" | tee -a "$LOG_FILE"
        return 0
    fi

    echo "  Rodando csDetector..." | tee -a "$LOG_FILE"
    mkdir -p "$out_dir"

    if (
        cd "$CSDETECTOR_DIR"
        source venv/bin/activate 2>/dev/null || true
        python devNetwork.py \
            -p "$GITHUB_TOKEN" \
            -r "$repo_url" \
            -s "$SENTISTRENGTH_DIR" \
            -o "$out_dir" \
            2>>"$LOG_FILE"
    ); then
        update_manifest "$repo_name" "csdetector" "OK"
        echo "  csDetector OK" | tee -a "$LOG_FILE"
    else
        update_manifest "$repo_name" "csdetector" "FAIL"
        echo "  [FALHA] csDetector" | tee -a "$LOG_FILE"
        return 1
    fi
}

cleanup_clone() {
    local repo_name="$1"
    local clone_dir="$CLONE_BASE/$repo_name"

    if [ -d "$clone_dir" ]; then
        local size=$(du -sh "$clone_dir" 2>/dev/null | cut -f1)
        rm -rf "$clone_dir"
        echo "  [CLEAN] Clone removido ($size liberados)" | tee -a "$LOG_FILE"
    fi
}

# ---- MAIN ----
init_manifest

TOTAL=$(tail -n +2 "$REPOS_CSV" | wc -l | tr -d ' ')
CURRENT=0
OK_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

MAX_REPOS=$TOTAL
$DRY_RUN && MAX_REPOS=3

echo "============================================" | tee -a "$LOG_FILE"
echo "  Pipeline Incremental — $TIMESTAMP" | tee -a "$LOG_FILE"
echo "  Repos: $TOTAL (executando: $MAX_REPOS)" | tee -a "$LOG_FILE"
echo "  Temporal: $($SKIP_TEMPORAL && echo 'desabilitado' || echo "habilitado (min ${MIN_AGE_DAYS}d)")" | tee -a "$LOG_FILE"
echo "  Dry-run: $DRY_RUN" | tee -a "$LOG_FILE"
echo "  Manifesto: $MANIFEST" | tee -a "$LOG_FILE"
echo "============================================" | tee -a "$LOG_FILE"

while IFS=, read -r repo_name org url loc_val age_years commits_val; do
    # Pular header
    [ "$repo_name" == "repo_name" ] && continue

    CURRENT=$((CURRENT + 1))
    [ $CURRENT -gt $MAX_REPOS ] && break

    # Construir URL se necessário
    repo_url="$url"
    [ -z "$repo_url" ] && repo_url="https://github.com/${org}/${repo_name}"

    echo "" | tee -a "$LOG_FILE"
    echo "[$CURRENT/$MAX_REPOS] ===== $org/$repo_name =====" | tee -a "$LOG_FILE"
    echo "  LOC=$loc_val, age=${age_years}y, commits=$commits_val" | tee -a "$LOG_FILE"

    START_TIME=$(date +%s)
    REPO_OK=true

    if $DRY_RUN; then
        echo "  [DRY-RUN] Simulando processamento..." | tee -a "$LOG_FILE"
        update_manifest "$repo_name" "dry_run" "SIMULATED"
    else
        # 1. Clone
        clone_repo "$repo_name" "$repo_url" || { REPO_OK=false; }

        if $REPO_OK; then
            # 2. Designite cross-sectional
            run_designite_cross "$repo_name" || true

            # 3. Designite temporal (snapshots)
            run_designite_temporal "$repo_name" || true

            # 4. csDetector
            run_csdetector "$repo_name" "$repo_url" || true

            # 5. Limpar clone (LIBERA DISCO!)
            cleanup_clone "$repo_name"
        fi
    fi

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    # Verificar status final
    d_status=$(get_repo_status "$repo_name" "designite_cross")
    t_status=$(get_repo_status "$repo_name" "designite_temporal")
    c_status=$(get_repo_status "$repo_name" "csdetector")

    if [ "$d_status" == "OK" ] && [ "$c_status" == "OK" ]; then
        OK_COUNT=$((OK_COUNT + 1))
    elif [ "$d_status" == "SKIP" ] || [ "$c_status" == "SKIP" ]; then
        SKIP_COUNT=$((SKIP_COUNT + 1))
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    echo "  Concluído em ${DURATION}s (D=$d_status, T=$t_status, CS=$c_status)" | tee -a "$LOG_FILE"

done < "$REPOS_CSV"

# ---- Resumo final ----
echo "" | tee -a "$LOG_FILE"
echo "============================================" | tee -a "$LOG_FILE"
echo "  Pipeline Incremental Finalizado!" | tee -a "$LOG_FILE"
echo "  OK: $OK_COUNT | SKIP: $SKIP_COUNT | FAIL: $FAIL_COUNT" | tee -a "$LOG_FILE"
echo "  Manifesto: $MANIFEST" | tee -a "$LOG_FILE"
echo "  Log: $LOG_FILE" | tee -a "$LOG_FILE"
echo "============================================" | tee -a "$LOG_FILE"
echo ""
echo "Próximos passos:"
echo "  1. python 04_consolidate.py  (para gerar consolidated.csv)"
echo "  2. python 05_filter_dataset.py  (para aplicar filtros IC/EC)"
echo "  3. python 12_dissertation_analysis.py  (para gerar figuras e tabelas)"
