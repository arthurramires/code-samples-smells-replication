#!/usr/bin/env python3
"""
05_filter_dataset.py — Filtragem e mesclagem do dataset
Mescla repos existentes (CodeSamples-Consolidado.csv) com novos candidatos
(candidates_all.csv) e filtra por critérios IC/EC.

Critérios de Inclusão:
  IC1: Linguagem principal = Java
  IC2: LOC entre 500 e 100.000
  IC3: Pelo menos 2 anos de histórico (para análise longitudinal)
  IC4: Repositório público no GitHub
  IC5: Classificado como code sample / example / demo / tutorial

Critérios de Exclusão:
  EC1: Repositório arquivado
  EC2: Repositório fork (não-original)
  EC3: LOC < 500 (trivial) ou > 100.000 (monolítico)
  EC4: Menos de 2 anos entre primeiro e último commit

Uso: python3 05_filter_dataset.py
"""

import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

# ---- Caminhos ----
PIPELINE_DIR = os.path.expanduser("~/mestrado-pipeline")
DATASET_DIR = os.path.join(PIPELINE_DIR, "dataset")

# O CSV original pode estar em vários locais — tentar encontrar
POSSIBLE_EXISTING = [
    os.path.join(DATASET_DIR, "CodeSamples-Consolidado.csv"),
    os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/Mestrado/Dissertação/CodeSamples-Consolidado.csv"),
]

CANDIDATES_CSV = os.path.join(DATASET_DIR, "candidates_all.csv")
OUTPUT_CSV = os.path.join(DATASET_DIR, "repos_final.csv")
REPORT_PATH = os.path.join(DATASET_DIR, "filter_report.txt")

# ---- Critérios ----
MIN_LOC = 500
MAX_LOC = 100_000
MIN_YEARS = 2


def load_existing_repos():
    """Carrega repos Java do CodeSamples-Consolidado.csv"""
    existing = {}

    csv_path = None
    for path in POSSIBLE_EXISTING:
        if os.path.exists(path):
            csv_path = path
            break

    if not csv_path:
        print("[INFO] CodeSamples-Consolidado.csv não encontrado localmente.")
        print("       Copiando do iCloud se disponível...")
        return existing

    print(f"[OK] Carregando dataset existente: {csv_path}")

    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        # Pular primeira linha (headers de grupo)
        first_line = f.readline()
        reader = csv.DictReader(f)

        for row in reader:
            name = row.get("name", "").strip()
            language = row.get("Language", "").strip()
            html_url = row.get("html_url", "").strip()
            ecosystem = row.get("Ecosystem", "").strip()

            # Tentar extrair LOC
            loc_str = row.get("LOC", "0").replace(".", "").replace(",", "").strip()
            try:
                loc = int(float(loc_str))
            except ValueError:
                loc = 0

            # Tentar extrair período
            first_commit = row.get("First Commit", "").strip()
            last_commit = row.get("Last Commit", "").strip()
            archived = row.get("archived", "FALSE").strip().upper()

            # Calcular anos
            years = 0
            if first_commit and last_commit:
                try:
                    fc = datetime.strptime(first_commit, "%d/%m/%Y")
                    lc = datetime.strptime(last_commit, "%d/%m/%Y")
                    years = (lc - fc).days / 365.25
                except ValueError:
                    years = 0

            existing[name] = {
                "name": name,
                "url": html_url,
                "ecosystem": ecosystem,
                "language": language,
                "loc": loc,
                "years": round(years, 1),
                "archived": archived == "TRUE",
                "source": "existing",
            }

    print(f"  Total no CSV existente: {len(existing)}")
    java_count = sum(1 for r in existing.values() if r["language"] == "Java")
    print(f"  Repos Java: {java_count}")
    return existing


def load_new_candidates():
    """Carrega novos candidatos do candidates_all.csv"""
    candidates = {}

    if not os.path.exists(CANDIDATES_CSV):
        print(f"[WARN] {CANDIDATES_CSV} não encontrado. Rode 02_expand_dataset.sh primeiro.")
        return candidates

    print(f"\n[OK] Carregando candidatos novos: {CANDIDATES_CSV}")

    with open(CANDIDATES_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            full_name = row.get("fullName", "").strip()
            url = row.get("url", "").strip()

            # Extrair nome curto (sem org/)
            short_name = full_name.split("/")[-1] if "/" in full_name else full_name

            candidates[short_name] = {
                "name": short_name,
                "full_name": full_name,
                "url": url or f"https://github.com/{full_name}",
                "stars": int(row.get("stars", 0) or 0),
                "description": row.get("description", ""),
                "source": "new_candidate",
                # Estes campos serão preenchidos pela verificação via gh
                "language": "Java",  # veio da busca por Java
                "loc": 0,
                "years": 0,
                "archived": False,
            }

    print(f"  Total de candidatos novos: {len(candidates)}")
    return candidates


def check_repo_via_gh(full_name):
    """Verifica informações do repo via GitHub CLI (se disponível)."""
    try:
        result = subprocess.run(
            ["gh", "repo", "view", full_name, "--json",
             "name,primaryLanguage,isArchived,isFork,createdAt,pushedAt,diskUsage"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        # Calcular anos
        created = data.get("createdAt", "")
        pushed = data.get("pushedAt", "")
        years = 0
        if created and pushed:
            try:
                c = datetime.fromisoformat(created.replace("Z", "+00:00"))
                p = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
                years = (p - c).days / 365.25
            except Exception:
                pass

        lang = ""
        if data.get("primaryLanguage"):
            lang = data["primaryLanguage"].get("name", "")

        return {
            "language": lang,
            "archived": data.get("isArchived", False),
            "is_fork": data.get("isFork", False),
            "years": round(years, 1),
            "disk_kb": data.get("diskUsage", 0),
        }
    except Exception:
        return None


def filter_repos(all_repos, verify_via_gh=False):
    """Aplica critérios IC/EC e retorna repos aprovados."""
    approved = []
    rejected = {"not_java": [], "loc_low": [], "loc_high": [],
                "too_young": [], "archived": [], "fork": [], "unknown": []}

    total = len(all_repos)
    print(f"\n--- Filtrando {total} repos ---")

    for i, (name, repo) in enumerate(all_repos.items()):
        # Verificação via GitHub API (opcional, lento)
        if verify_via_gh and repo.get("source") == "new_candidate":
            full_name = repo.get("full_name", name)
            if (i + 1) % 20 == 0:
                print(f"  Verificando {i+1}/{total}...")

            gh_info = check_repo_via_gh(full_name)
            if gh_info:
                repo["language"] = gh_info["language"]
                repo["archived"] = gh_info["archived"]
                repo["years"] = gh_info["years"]
                if gh_info.get("is_fork"):
                    rejected["fork"].append(name)
                    continue

        # IC1: Java
        if repo.get("language", "") != "Java":
            rejected["not_java"].append(name)
            continue

        # EC1: Não arquivado
        if repo.get("archived"):
            rejected["archived"].append(name)
            continue

        # IC2/EC3: LOC entre 500 e 100k (apenas para repos existentes que têm LOC)
        loc = repo.get("loc", 0)
        if loc > 0:  # só filtrar se temos o dado
            if loc < MIN_LOC:
                rejected["loc_low"].append(name)
                continue
            if loc > MAX_LOC:
                rejected["loc_high"].append(name)
                continue

        # IC3/EC4: Pelo menos 2 anos
        years = repo.get("years", 0)
        if years > 0 and years < MIN_YEARS:
            rejected["too_young"].append(name)
            continue

        approved.append(repo)

    return approved, rejected


def main():
    print("=" * 55)
    print("  Filtragem e Mesclagem do Dataset")
    print("  Critérios: Java, 500-100k LOC, ≥2 anos, não-arquivado")
    print("=" * 55)

    # Carregar dados
    existing = load_existing_repos()
    candidates = load_new_candidates()

    # Mesclar (existentes têm prioridade)
    all_repos = {}
    all_repos.update(candidates)  # novos primeiro
    all_repos.update(existing)    # existentes sobrescrevem (têm mais dados)

    print(f"\n  Total mesclado (deduplicated): {len(all_repos)}")

    # Perguntar se quer verificar via gh (lento)
    verify = False
    if "--verify" in sys.argv:
        verify = True
        print("\n[INFO] Modo --verify ativo: consultando GitHub API para cada candidato novo.")
        print("       Isso pode demorar vários minutos.")

    # Filtrar
    approved, rejected = filter_repos(all_repos, verify_via_gh=verify)

    # Separar por fonte
    from_existing = [r for r in approved if r.get("source") == "existing"]
    from_new = [r for r in approved if r.get("source") == "new_candidate"]

    # Salvar repos_final.csv
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["repo_name", "repo_url", "source", "ecosystem", "loc", "years"])
        for repo in sorted(approved, key=lambda x: x["name"]):
            writer.writerow([
                repo["name"],
                repo["url"],
                repo.get("source", ""),
                repo.get("ecosystem", ""),
                repo.get("loc", 0),
                repo.get("years", 0),
            ])

    # Gerar relatório
    report_lines = [
        "=" * 55,
        "  RELATÓRIO DE FILTRAGEM DO DATASET",
        f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 55,
        "",
        f"Total de repos analisados: {len(all_repos)}",
        f"  - Do dataset existente: {len(existing)}",
        f"  - Candidatos novos: {len(candidates)}",
        "",
        f"APROVADOS: {len(approved)}",
        f"  - Vindos do dataset existente: {len(from_existing)}",
        f"  - Candidatos novos: {len(from_new)}",
        "",
        "REJEITADOS:",
        f"  - Não é Java: {len(rejected['not_java'])}",
        f"  - LOC < {MIN_LOC}: {len(rejected['loc_low'])}",
        f"  - LOC > {MAX_LOC}: {len(rejected['loc_high'])}",
        f"  - < {MIN_YEARS} anos de histórico: {len(rejected['too_young'])}",
        f"  - Arquivado: {len(rejected['archived'])}",
        f"  - Fork: {len(rejected['fork'])}",
        "",
        f"Dataset final salvo em: {OUTPUT_CSV}",
        "",
        "NOTA: Candidatos novos ainda precisam de verificação de LOC.",
        "Execute com --verify para consultar a API do GitHub (mais lento).",
        "Ou verifique LOC após clonar os repos no pipeline.",
    ]

    report = "\n".join(report_lines)
    with open(REPORT_PATH, "w") as f:
        f.write(report)

    print(f"\n{report}")
    print(f"\nRelatório salvo em: {REPORT_PATH}")


if __name__ == "__main__":
    main()
