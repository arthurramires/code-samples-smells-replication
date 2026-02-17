#!/usr/bin/env python3
"""
08b_run_designite_temporal.py — Rodar Designite nos snapshots já extraídos
=========================================================================
Script complementar ao 08_temporal_extraction.py.

Lê o CSV de dados temporais (que já contém métricas sociais) e, para cada
snapshot (repo × project_year), faz git checkout no commit correspondente
e roda o Designite Java. Depois, mescla os Code Smells no CSV original.

Isso permite separar a extração social (demorada, consome API) da técnica
(local, só precisa do JAR + repos clonados).

Uso:
  python3 08b_run_designite_temporal.py \
      --input results/temporal/temporal_data_FINAL.csv \
      --repos-dir results/temporal/repos \
      --designite-jar /Users/arthurbueno/mestrado-pipeline/tools/DesigniteJava.jar \
      --output results/temporal/temporal_data_complete.csv
"""

import argparse
import csv
import os
import subprocess
import sys
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def checkout_commit(repo_dir: str, commit_hash: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "checkout", commit_hash, "--force"],
            cwd=repo_dir, capture_output=True, text=True, timeout=60
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Checkout falhou: {e}")
        return False


def checkout_default(repo_dir: str) -> bool:
    for branch in ["main", "master", "HEAD"]:
        try:
            result = subprocess.run(
                ["git", "checkout", branch, "--force"],
                cwd=repo_dir, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return True
        except:
            pass
    return False


def run_designite(jar_path: str, source_dir: str, output_dir: str) -> dict:
    """Roda Designite Java e retorna contagem de smells."""
    os.makedirs(output_dir, exist_ok=True)
    smells = {}

    try:
        result = subprocess.run(
            ["java", "-jar", jar_path, "-i", source_dir, "-o", output_dir],
            capture_output=True, text=True, timeout=300
        )

        if result.returncode != 0:
            logger.debug(f"Designite retornou {result.returncode}: {result.stderr[:200]}")

    except subprocess.TimeoutExpired:
        logger.warning(f"Designite timeout para {source_dir}")
        return smells
    except Exception as e:
        logger.error(f"Erro Designite: {e}")
        return smells

    # Parse design smells
    design_file = os.path.join(output_dir, "designCodeSmells.csv")
    design_total = 0
    if os.path.exists(design_file):
        try:
            with open(design_file, 'r', errors='ignore') as f:
                reader = csv.DictReader(f)
                counts = {}
                for row in reader:
                    st = row.get("Design Smell", "Unknown").replace(" ", "_")
                    counts[st] = counts.get(st, 0) + 1
                design_total = sum(counts.values())
                for k, v in counts.items():
                    smells[f"design_{k}"] = v
        except Exception as e:
            logger.debug(f"Erro lendo designCodeSmells.csv: {e}")

    # Parse implementation smells
    impl_file = os.path.join(output_dir, "implementationCodeSmells.csv")
    impl_total = 0
    if os.path.exists(impl_file):
        try:
            with open(impl_file, 'r', errors='ignore') as f:
                reader = csv.DictReader(f)
                counts = {}
                for row in reader:
                    st = row.get("Implementation Smell", "Unknown").replace(" ", "_")
                    counts[st] = counts.get(st, 0) + 1
                impl_total = sum(counts.values())
                for k, v in counts.items():
                    smells[f"impl_{k}"] = v
        except Exception as e:
            logger.debug(f"Erro lendo implementationCodeSmells.csv: {e}")

    smells["total_design_smells"] = design_total
    smells["total_impl_smells"] = impl_total
    smells["total_code_smells"] = design_total + impl_total

    return smells


def main():
    parser = argparse.ArgumentParser(
        description="Rodar Designite nos snapshots temporais já extraídos"
    )
    parser.add_argument("--input", required=True,
                        help="CSV com dados temporais (do 08_temporal_extraction.py)")
    parser.add_argument("--repos-dir", required=True,
                        help="Diretório com repos clonados (results/temporal/repos)")
    parser.add_argument("--designite-jar", required=True,
                        help="Caminho para DesigniteJava.jar")
    parser.add_argument("--output", required=True,
                        help="CSV de saída com Code Smells adicionados")
    parser.add_argument("--designite-output-dir", default="results/temporal/designite_results",
                        help="Diretório para outputs do Designite")
    parser.add_argument("--start-from", type=int, default=0,
                        help="Índice da linha para retomar execução")

    args = parser.parse_args()

    # Validações
    if not os.path.exists(args.input):
        logger.error(f"Input não encontrado: {args.input}")
        sys.exit(1)

    if not os.path.exists(args.designite_jar):
        logger.error(f"Designite JAR não encontrado: {args.designite_jar}")
        sys.exit(1)

    if not os.path.isdir(args.repos_dir):
        logger.error(f"Diretório de repos não encontrado: {args.repos_dir}")
        sys.exit(1)

    # Verificar Java
    try:
        subprocess.run(["java", "-version"], capture_output=True, timeout=10)
    except:
        logger.error("Java não encontrado. Instale OpenJDK 17+.")
        sys.exit(1)

    os.makedirs(args.designite_output_dir, exist_ok=True)

    # Ler CSV input
    with open(args.input, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    logger.info(f"Carregados {len(rows)} snapshots de {args.input}")
    logger.info(f"Repos dir: {args.repos_dir}")
    logger.info(f"Designite JAR: {args.designite_jar}")
    logger.info(f"Start from: {args.start_from}")

    # Coletar todas as novas colunas que podem surgir
    all_smell_keys = set()
    processed = 0
    failed = 0

    for i, row in enumerate(rows):
        if i < args.start_from:
            continue

        repo_name = row["repo_name"]
        year = row["project_year"]
        commit = row["snapshot_commit"]

        repo_dir = os.path.join(args.repos_dir, repo_name)
        if not os.path.isdir(repo_dir):
            logger.warning(f"[{i+1}/{len(rows)}] Repo não clonado: {repo_name}")
            failed += 1
            continue

        logger.info(f"[{i+1}/{len(rows)}] {repo_name} Year {year} ({commit})")

        # Checkout
        if not checkout_commit(repo_dir, commit):
            logger.warning(f"  Checkout falhou para {commit}")
            failed += 1
            checkout_default(repo_dir)
            continue

        # Rodar Designite
        designite_out = os.path.join(
            args.designite_output_dir, repo_name, f"year_{year}"
        )
        smells = run_designite(args.designite_jar, repo_dir, designite_out)

        # Adicionar ao row
        row.update(smells)
        all_smell_keys.update(smells.keys())

        total = smells.get("total_code_smells", 0)
        logger.info(f"  → {total} code smells ({smells.get('total_design_smells', 0)} design + {smells.get('total_impl_smells', 0)} impl)")

        # Voltar à branch padrão
        checkout_default(repo_dir)

        processed += 1

        # Salvar progresso a cada 20 snapshots
        if processed % 20 == 0:
            _save(rows, fieldnames, all_smell_keys, args.output + ".partial")
            logger.info(f"  Progresso salvo ({processed} processados)")

    # Salvar resultado final
    _save(rows, fieldnames, all_smell_keys, args.output)

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Finalizado! Processados: {processed}, Falhas: {failed}")
    logger.info(f"Output: {args.output}")
    logger.info("=" * 60)


def _save(rows, original_fieldnames, smell_keys, output_path):
    """Salva CSV com colunas originais + novas de smells."""
    # Manter ordem original + novas colunas ordenadas
    all_fields = list(original_fieldnames)
    for key in sorted(smell_keys):
        if key not in all_fields:
            all_fields.append(key)

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=all_fields, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


if __name__ == "__main__":
    main()
