#!/bin/bash
# ==============================================================
# 01_setup_macos.sh — Configuração do ambiente no macOS
# Dissertação: Coocorrência de Code Smells e Community Smells
# Autor: Arthur Bueno
# ==============================================================
set -euo pipefail

echo "============================================"
echo "  Setup do Ambiente — Dissertação Mestrado"
echo "============================================"

# ---- 1. Verificar Homebrew ----
if ! command -v brew &> /dev/null; then
    echo "[ERRO] Homebrew não encontrado. Instale em https://brew.sh"
    exit 1
fi
echo "[OK] Homebrew encontrado"

# ---- 2. Java 17 (para Designite) ----
echo ""
echo "--- Configurando Java 17 ---"
if ! java -version 2>&1 | grep -q "17"; then
    echo "Instalando OpenJDK 17..."
    brew install openjdk@17
    echo 'export JAVA_HOME=$(/usr/libexec/java_home -v 17)' >> ~/.zshrc
    echo 'export PATH="$JAVA_HOME/bin:$PATH"' >> ~/.zshrc
    source ~/.zshrc 2>/dev/null || true
else
    echo "[OK] Java 17 já instalado"
fi
echo "Java version: $(java -version 2>&1 | head -1)"

# ---- 3. Python 3.10+ (para csDetector) ----
echo ""
echo "--- Configurando Python ---"
if ! command -v python3 &> /dev/null; then
    echo "Instalando Python 3.10..."
    brew install python@3.10
else
    echo "[OK] Python encontrado: $(python3 --version)"
fi

# ---- 4. GitHub CLI (para expansão do dataset) ----
echo ""
echo "--- Configurando GitHub CLI ---"
if ! command -v gh &> /dev/null; then
    echo "Instalando GitHub CLI..."
    brew install gh
    echo "[AÇÃO] Execute: gh auth login"
else
    echo "[OK] GitHub CLI encontrado"
fi

# ---- 5. Criar estrutura de diretórios ----
echo ""
echo "--- Criando estrutura de diretórios ---"
WORK_DIR="$HOME/mestrado-pipeline"
mkdir -p "$WORK_DIR"/{tools,logs,results/{code_smells,community_smells},repos,dataset}

echo "[OK] Estrutura criada em $WORK_DIR"
echo ""
echo "============================================"
echo "  Próximos passos:"
echo "  1. Baixar Designite Java de https://www.designite-tools.com/designitejava"
echo "     (versão acadêmica gratuita — solicitar com email @ufms.br)"
echo "     Colocar o .jar em: $WORK_DIR/tools/"
echo ""
echo "  2. Clonar csDetector:"
echo "     git clone https://github.com/Nuri22/csDetector.git $WORK_DIR/tools/csDetector"
echo "     cd $WORK_DIR/tools/csDetector && python3 -m venv venv"
echo "     source venv/bin/activate && pip install -r requirements.txt"
echo ""
echo "  3. Criar token GitHub (para csDetector API):"
echo "     https://github.com/settings/tokens"
echo "     export GITHUB_TOKEN='ghp_SEU_TOKEN'"
echo ""
echo "  4. Executar dry-run:"
echo "     bash 02_expand_dataset.sh (para buscar repos)"
echo "     bash 03_run_pipeline.sh --dry-run (para testar com 3 repos)"
echo "============================================"
