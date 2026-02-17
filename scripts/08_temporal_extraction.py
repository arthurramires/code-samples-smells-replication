#!/usr/bin/env python3
"""
08_temporal_extraction.py — Extração Temporal por Project Year
=============================================================
Dissertação: Coocorrência Evolutiva de Code Smells e Community Smells
             em Code Samples Java

Este script implementa a decomposição temporal completa por project year,
conforme descrito na Seção 5.4 (Estratégia de Análise Temporal) da dissertação.

Abordagem:
  - Para cada repositório R com primeiro commit em t0:
    - Year n = estado do repositório no instante t0 + n × 365 dias
    - Snapshot = último commit antes da data-alvo (git log --before)
  - Dimensão técnica: Designite Java no código do snapshot (git checkout)
  - Dimensão social: métricas do GitHub API filtradas por período

Referências:
  - De Stefano et al. (2021): análise longitudinal com snapshots anuais
  - Rebuttal SBSI (R3): normalização por project year
  - Palomba et al. (2018): co-evolução de smells ao longo do tempo

Uso:
  python 08_temporal_extraction.py --repos-csv repositories.csv \
      --urls-file repo_urls.txt --owner-map owner_map.json \
      --github-token ghp_XXX --designite-jar DesigniteJava.jar \
      --output-dir results/temporal [--max-years 5] [--dry-run] [--skip-designite]

Autor: Arthur Bueno (dissertação de mestrado)
"""

import argparse
import csv
import json
import os
import subprocess
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ============================================================
# Configuração
# ============================================================
MAX_PROJECT_YEARS = 5
DAYS_PER_YEAR = 365
GITHUB_API_BASE = "https://api.github.com"
REQUEST_DELAY = 0.8  # segundos entre requests (conservador para 5000/h)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================
# GitHub API Helper
# ============================================================
class GitHubAPI:
    """Wrapper para chamadas à API do GitHub com rate-limit handling."""

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.remaining = 5000
        self.reset_time = 0
        self.request_count = 0

    def _check_rate_limit(self):
        """Verifica e aguarda se necessário."""
        if self.remaining < 50:
            wait = max(0, self.reset_time - time.time()) + 5
            logger.warning(f"Rate limit baixo ({self.remaining}). Aguardando {wait:.0f}s...")
            time.sleep(wait)

    def get(self, url: str, params: dict = None) -> Optional[dict]:
        """GET request com retry e rate-limit handling."""
        import urllib.request
        import urllib.parse
        import urllib.error

        self._check_rate_limit()

        if params:
            query = urllib.parse.urlencode(params)
            full_url = f"{url}?{query}"
        else:
            full_url = url

        for attempt in range(3):
            try:
                req = urllib.request.Request(full_url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    self.remaining = int(resp.headers.get("X-RateLimit-Remaining", 5000))
                    self.reset_time = int(resp.headers.get("X-RateLimit-Reset", 0))
                    self.request_count += 1
                    data = json.loads(resp.read().decode())
                    time.sleep(REQUEST_DELAY)
                    return data
            except urllib.error.HTTPError as e:
                if e.code == 403:
                    # Rate limited
                    reset = int(e.headers.get("X-RateLimit-Reset", 0))
                    wait = max(0, reset - time.time()) + 5
                    logger.warning(f"Rate limited (403). Aguardando {wait:.0f}s...")
                    time.sleep(wait)
                elif e.code == 404:
                    logger.debug(f"404: {full_url}")
                    return None
                elif e.code == 422:
                    logger.debug(f"422 (Unprocessable): {full_url}")
                    return None
                else:
                    logger.error(f"HTTP {e.code}: {full_url}")
                    if attempt < 2:
                        time.sleep(5 * (attempt + 1))
                    else:
                        return None
            except Exception as e:
                logger.error(f"Erro: {e} - {full_url}")
                if attempt < 2:
                    time.sleep(5 * (attempt + 1))
                else:
                    return None
        return None

    def get_paginated(self, url: str, params: dict = None, max_pages: int = 10) -> list:
        """GET com paginação automática."""
        import urllib.parse

        all_items = []
        if params is None:
            params = {}
        params["per_page"] = 100
        page = 1

        while page <= max_pages:
            params["page"] = page
            data = self.get(url, params)
            if data is None or len(data) == 0:
                break
            all_items.extend(data)
            if len(data) < 100:
                break
            page += 1

        return all_items


# ============================================================
# Git Helper
# ============================================================
class GitHelper:
    """Operações Git sobre repositórios clonados."""

    @staticmethod
    def get_first_commit_date(repo_dir: str) -> Optional[datetime]:
        """Obtém a data do primeiro commit do repositório."""
        try:
            result = subprocess.run(
                ["git", "log", "--reverse", "--format=%aI", "--max-count=1"],
                cwd=repo_dir, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                date_str = result.stdout.strip()
                # Parse ISO format, remove timezone info for simplicity
                return datetime.fromisoformat(date_str.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception as e:
            logger.error(f"Erro ao obter primeiro commit: {e}")
        return None

    @staticmethod
    def get_last_commit_before(repo_dir: str, before_date: datetime) -> Optional[str]:
        """Obtém o hash do último commit antes de uma data."""
        date_str = before_date.strftime("%Y-%m-%dT23:59:59")
        try:
            result = subprocess.run(
                ["git", "log", f"--before={date_str}", "--format=%H", "--max-count=1"],
                cwd=repo_dir, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception as e:
            logger.error(f"Erro ao buscar commit antes de {date_str}: {e}")
        return None

    @staticmethod
    def checkout(repo_dir: str, commit_hash: str) -> bool:
        """Faz checkout de um commit específico."""
        try:
            result = subprocess.run(
                ["git", "checkout", commit_hash, "--force"],
                cwd=repo_dir, capture_output=True, text=True, timeout=60
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Erro no checkout {commit_hash}: {e}")
            return False

    @staticmethod
    def checkout_default_branch(repo_dir: str) -> bool:
        """Retorna à branch padrão."""
        for branch in ["main", "master"]:
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

    @staticmethod
    def get_commit_authors_until(repo_dir: str, until_date: datetime) -> list:
        """Extrai lista de autores e seus commits até uma data."""
        date_str = until_date.strftime("%Y-%m-%dT23:59:59")
        try:
            result = subprocess.run(
                ["git", "log", f"--before={date_str}",
                 "--format=%aE|%aI", "--no-merges"],
                cwd=repo_dir, capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
                return lines
        except Exception as e:
            logger.error(f"Erro ao extrair autores: {e}")
        return []

    @staticmethod
    def get_commit_count_until(repo_dir: str, until_date: datetime) -> int:
        """Conta commits até uma data."""
        date_str = until_date.strftime("%Y-%m-%dT23:59:59")
        try:
            result = subprocess.run(
                ["git", "rev-list", "--count", f"--before={date_str}", "HEAD"],
                cwd=repo_dir, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
        except:
            pass
        return 0


# ============================================================
# Social Metrics Extractor
# ============================================================
class SocialMetricsExtractor:
    """Extrai métricas sociais filtradas por período via GitHub API + git log."""

    def __init__(self, api: GitHubAPI):
        self.api = api

    def extract_for_period(self, owner: str, repo: str, repo_dir: str,
                           until_date: datetime) -> dict:
        """
        Extrai métricas sociais de um repositório até uma data específica.

        Retorna dict com:
          - commit_count: total de commits até a data
          - author_count: número de autores distintos
          - bus_factor: proporção de commits do top contributor
          - pr_count: número de PRs criadas até a data
          - issue_count: número de issues criadas até a data
          - pr_participants_mean: média de participantes por PR
          - issue_participants_mean: média de participantes por issue
          - timezone_count: estimativa de fusos horários distintos
        """
        metrics = {
            "commit_count": 0,
            "author_count": 0,
            "bus_factor_number": None,
            "pr_count": 0,
            "issue_count": 0,
            "pr_participants_mean": 0.0,
            "issue_participants_mean": 0.0,
            "timezone_count": 0,
            "days_active": 0,
        }

        # --- Métricas de commits (via git log - sem custo de API) ---
        commit_lines = GitHelper.get_commit_authors_until(repo_dir, until_date)
        if commit_lines:
            metrics["commit_count"] = len(commit_lines)

            # Autores distintos
            authors = {}
            timezones = set()
            first_date = None
            last_date = None

            for line in commit_lines:
                parts = line.split("|")
                if len(parts) >= 2:
                    email = parts[0].lower().strip()
                    date_str = parts[1].strip()
                    authors[email] = authors.get(email, 0) + 1

                    # Extrair timezone offset
                    if "+" in date_str[-6:] or "-" in date_str[-6:]:
                        tz = date_str[-6:]
                        timezones.add(tz)

                    try:
                        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00")).replace(tzinfo=None)
                        if first_date is None or dt < first_date:
                            first_date = dt
                        if last_date is None or dt > last_date:
                            last_date = dt
                    except:
                        pass

            metrics["author_count"] = len(authors)
            metrics["timezone_count"] = len(timezones)

            if first_date and last_date:
                metrics["days_active"] = (last_date - first_date).days

            # Bus Factor: proporção do top contributor
            if authors:
                sorted_authors = sorted(authors.values(), reverse=True)
                total_commits = sum(sorted_authors)
                if total_commits > 0:
                    top_ratio = sorted_authors[0] / total_commits
                    metrics["bus_factor_number"] = round(top_ratio, 4)

        # --- PRs e Issues (via GitHub API com filtro de data) ---
        until_str = until_date.strftime("%Y-%m-%d")

        # PRs criadas até a data
        pr_data = self._count_issues_or_prs(owner, repo, "pr", until_str)
        metrics["pr_count"] = pr_data.get("count", 0)
        metrics["pr_participants_mean"] = pr_data.get("participants_mean", 0.0)

        # Issues criadas até a data
        issue_data = self._count_issues_or_prs(owner, repo, "issue", until_str)
        metrics["issue_count"] = issue_data.get("count", 0)
        metrics["issue_participants_mean"] = issue_data.get("participants_mean", 0.0)

        return metrics

    def _count_issues_or_prs(self, owner: str, repo: str,
                              item_type: str, until_date: str) -> dict:
        """Conta issues ou PRs criadas até uma data via REST API."""
        result = {"count": 0, "participants_mean": 0.0}

        # Usar REST API para listar issues/PRs com filtro de data
        # Issues API: GET /repos/{owner}/{repo}/issues
        # state=all inclui abertas e fechadas
        # since não funciona como "until", então precisamos iterar

        endpoint = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues"
        params = {
            "state": "all",
            "sort": "created",
            "direction": "asc",
            "per_page": 100,
        }

        if item_type == "pr":
            # PRs são retornadas pela issues API mas têm pull_request field
            pass

        all_items = []
        page = 1
        max_pages = 20  # Limitar para não gastar muitas requests

        while page <= max_pages:
            params["page"] = page
            data = self.api.get(endpoint, params)
            if data is None or len(data) == 0:
                break

            for item in data:
                created = item.get("created_at", "")[:10]
                if created > until_date:
                    # Passamos da data-alvo
                    page = max_pages + 1  # Sair do while
                    break

                is_pr = "pull_request" in item
                if (item_type == "pr" and is_pr) or (item_type == "issue" and not is_pr):
                    all_items.append(item)

            if len(data) < 100:
                break
            page += 1

        result["count"] = len(all_items)

        # Calcular média de participantes (aproximação: comentários)
        if all_items:
            total_comments = sum(item.get("comments", 0) for item in all_items)
            result["participants_mean"] = round(total_comments / len(all_items), 2) if all_items else 0

        return result


# ============================================================
# Designite Runner
# ============================================================
class DesigniteRunner:
    """Executa Designite Java em um snapshot específico."""

    def __init__(self, jar_path: str):
        self.jar_path = jar_path

    def run(self, source_dir: str, output_dir: str) -> dict:
        """
        Executa Designite Java e retorna sumário de smells.

        Retorna dict com contagem de cada tipo de smell.
        """
        os.makedirs(output_dir, exist_ok=True)

        try:
            result = subprocess.run(
                ["java", "-jar", self.jar_path, "-i", source_dir, "-o", output_dir],
                capture_output=True, text=True, timeout=300
            )

            if result.returncode != 0:
                logger.warning(f"Designite retornou código {result.returncode}")
                logger.debug(f"stderr: {result.stderr[:500]}")

            return self._parse_results(output_dir)

        except subprocess.TimeoutExpired:
            logger.error(f"Designite timeout para {source_dir}")
            return {}
        except Exception as e:
            logger.error(f"Erro ao executar Designite: {e}")
            return {}

    def _parse_results(self, output_dir: str) -> dict:
        """Parse dos CSVs de resultado do Designite."""
        smells = {
            "total_design_smells": 0,
            "total_impl_smells": 0,
            "total_code_smells": 0,
        }

        # Design smells
        design_file = os.path.join(output_dir, "designCodeSmells.csv")
        if os.path.exists(design_file):
            try:
                with open(design_file, 'r', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    smell_counts = {}
                    for row in reader:
                        smell_type = row.get("Design Smell", "Unknown")
                        smell_counts[smell_type] = smell_counts.get(smell_type, 0) + 1
                    smells["total_design_smells"] = sum(smell_counts.values())
                    for k, v in smell_counts.items():
                        safe_key = k.replace(" ", "_")
                        smells[f"design_{safe_key}"] = v
            except Exception as e:
                logger.debug(f"Erro ao ler designCodeSmells.csv: {e}")

        # Implementation smells
        impl_file = os.path.join(output_dir, "implementationCodeSmells.csv")
        if os.path.exists(impl_file):
            try:
                with open(impl_file, 'r', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    smell_counts = {}
                    for row in reader:
                        smell_type = row.get("Implementation Smell", "Unknown")
                        smell_counts[smell_type] = smell_counts.get(smell_type, 0) + 1
                    smells["total_impl_smells"] = sum(smell_counts.values())
                    for k, v in smell_counts.items():
                        safe_key = k.replace(" ", "_")
                        smells[f"impl_{safe_key}"] = v
            except Exception as e:
                logger.debug(f"Erro ao ler implementationCodeSmells.csv: {e}")

        smells["total_code_smells"] = smells["total_design_smells"] + smells["total_impl_smells"]
        return smells


# ============================================================
# Community Smell Indicators (mesmos limiares da dissertação)
# ============================================================
def compute_community_smell_indicators(metrics: dict) -> dict:
    """
    Computa indicadores de Community Smells por limiares heurísticos.
    Tabela 6 da dissertação (Seção 5.3.2.1).
    """
    indicators = {
        "lone_wolf": 0,
        "radio_silence": 0,
        "org_silo": 0,
    }

    # Lone Wolf: BusFactor > 0.9
    bf = metrics.get("bus_factor_number")
    if bf is not None and bf > 0.9:
        indicators["lone_wolf"] = 1

    # Radio Silence: 0 PRs AND 0 Issues
    if metrics.get("pr_count", 0) == 0 and metrics.get("issue_count", 0) == 0:
        indicators["radio_silence"] = 1

    # Org Silo: requer dados de centralidade (não disponível via git log)
    # Será computado apenas se dados de rede estiverem disponíveis
    # Por ora, usa proxy: author_count >= 5 AND bus_factor > 0.7
    # Nota: o indicador completo requer communities >= 3 AND density < 0.3
    # que depende da análise de rede do csDetector
    indicators["org_silo_proxy"] = 0
    if metrics.get("author_count", 0) >= 5 and bf is not None and bf > 0.7:
        indicators["org_silo_proxy"] = 1

    return indicators


# ============================================================
# Pipeline Principal
# ============================================================
class TemporalExtractionPipeline:
    """Pipeline completo de extração temporal por project year."""

    def __init__(self, args):
        self.args = args
        self.api = GitHubAPI(args.github_token) if args.github_token else None
        self.designite = DesigniteRunner(args.designite_jar) if args.designite_jar and not args.skip_designite else None
        self.output_dir = args.output_dir
        self.clone_dir = os.path.join(args.output_dir, "repos")
        self.results_dir = os.path.join(args.output_dir, "results")
        self.max_years = args.max_years

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.clone_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)

    def load_repos(self) -> list:
        """Carrega lista de repositórios com URLs resolvidas."""
        repos = []

        # Ler CSV principal
        with open(self.args.repos_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                repos.append(row)

        # Ler URLs resolvidas
        url_map = {}
        if self.args.urls_file and os.path.exists(self.args.urls_file):
            with open(self.args.urls_file, 'r') as f:
                for line in f:
                    url = line.strip()
                    if url and "github.com/" in url:
                        # Extrair repo_name da URL
                        parts = url.rstrip("/").split("/")
                        if len(parts) >= 2:
                            repo_name = parts[-1]
                            url_map[repo_name.lower()] = url

        # Ler owner map
        owner_map = {}
        if self.args.owner_map and os.path.exists(self.args.owner_map):
            with open(self.args.owner_map, 'r') as f:
                owner_map = json.load(f)

        # Resolver URLs
        for repo in repos:
            name = repo.get("repo_name", "")
            url = repo.get("github_url", "")

            # Tentar URL resolvida
            if name.lower() in url_map:
                repo["resolved_url"] = url_map[name.lower()]
            elif "search?q=" in url and name in owner_map:
                owner = owner_map[name]
                repo["resolved_url"] = f"https://github.com/{owner}/{name}"
            else:
                repo["resolved_url"] = url

            # Extrair owner/repo da URL resolvida
            resolved = repo.get("resolved_url", "")
            if "github.com/" in resolved and "search?q=" not in resolved:
                parts = resolved.rstrip("/").split("github.com/")[-1].split("/")
                if len(parts) >= 2:
                    repo["owner"] = parts[0]
                    repo["repo_slug"] = parts[1]

        # Filtrar repos sem URL resolvida
        valid = [r for r in repos if "owner" in r and "repo_slug" in r]
        logger.info(f"Repositórios com URL válida: {len(valid)}/{len(repos)}")

        return valid

    def clone_repo(self, repo: dict) -> Optional[str]:
        """Clona um repositório se não existir."""
        name = repo.get("repo_name", "")
        url = repo.get("resolved_url", "")
        clone_path = os.path.join(self.clone_dir, name)

        if os.path.exists(clone_path):
            logger.debug(f"  [SKIP] Já clonado: {name}")
            return clone_path

        logger.info(f"  Clonando {name}...")
        try:
            result = subprocess.run(
                ["git", "clone", "--quiet", url, clone_path],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                return clone_path
            else:
                logger.warning(f"  [FALHA] Clone: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            logger.warning(f"  [TIMEOUT] Clone de {name}")
        except Exception as e:
            logger.error(f"  [ERRO] Clone: {e}")
        return None

    def process_repo(self, repo: dict) -> list:
        """
        Processa um repositório: extrai dados para cada project year.
        Retorna lista de dicts (um por project year).
        """
        name = repo.get("repo_name", "")
        owner = repo.get("owner", "")
        slug = repo.get("repo_slug", "")

        results = []

        # 1. Clone
        repo_dir = self.clone_repo(repo)
        if repo_dir is None:
            return results

        # 2. Obter data do primeiro commit
        first_commit_date = GitHelper.get_first_commit_date(repo_dir)
        if first_commit_date is None:
            logger.warning(f"  [SKIP] Sem commits: {name}")
            return results

        logger.info(f"  Primeiro commit: {first_commit_date.strftime('%Y-%m-%d')}")

        # 3. Para cada project year
        social_extractor = SocialMetricsExtractor(self.api) if self.api else None

        for year_n in range(1, self.max_years + 1):
            snapshot_date = first_commit_date + timedelta(days=year_n * DAYS_PER_YEAR)

            # Verificar se a data está no futuro
            if snapshot_date > datetime.now():
                logger.info(f"  Year {year_n}: data futura ({snapshot_date.strftime('%Y-%m-%d')}), parando.")
                break

            logger.info(f"  Year {year_n}: snapshot em {snapshot_date.strftime('%Y-%m-%d')}")

            # 3a. Encontrar último commit antes da data
            commit_hash = GitHelper.get_last_commit_before(repo_dir, snapshot_date)
            if commit_hash is None:
                logger.info(f"    Sem commit antes de {snapshot_date.strftime('%Y-%m-%d')}")
                continue

            year_result = {
                "repo_name": name,
                "owner": owner,
                "repo_slug": slug,
                "project_year": year_n,
                "snapshot_date": snapshot_date.strftime("%Y-%m-%d"),
                "first_commit_date": first_commit_date.strftime("%Y-%m-%d"),
                "snapshot_commit": commit_hash[:12],
            }

            # 3b. Designite (checkout + análise)
            if self.designite and not self.args.dry_run:
                logger.info(f"    Rodando Designite...")
                if GitHelper.checkout(repo_dir, commit_hash):
                    designite_out = os.path.join(
                        self.results_dir, name, f"year_{year_n}", "designite"
                    )
                    smells = self.designite.run(repo_dir, designite_out)
                    year_result.update(smells)

                    # Voltar à branch padrão após Designite
                    GitHelper.checkout_default_branch(repo_dir)
                else:
                    logger.warning(f"    [FALHA] Checkout {commit_hash[:8]}")

            # 3c. Métricas sociais (git log + GitHub API)
            if social_extractor and not self.args.dry_run:
                logger.info(f"    Extraindo métricas sociais...")
                social = social_extractor.extract_for_period(
                    owner, slug, repo_dir, snapshot_date
                )
                year_result.update(social)

                # Community smell indicators
                indicators = compute_community_smell_indicators(social)
                year_result.update(indicators)

            elif self.args.dry_run:
                # Dry-run: apenas simula
                social_from_git = {
                    "commit_count": GitHelper.get_commit_count_until(repo_dir, snapshot_date),
                }
                year_result.update(social_from_git)

            results.append(year_result)

        # Garantir que o repo volta à branch padrão
        if repo_dir:
            GitHelper.checkout_default_branch(repo_dir)

        return results

    def run(self):
        """Executa o pipeline completo."""
        logger.info("=" * 60)
        logger.info("  Pipeline de Extração Temporal por Project Year")
        logger.info("=" * 60)

        # Carregar repos
        repos = self.load_repos()

        if self.args.dry_run:
            repos = repos[:3]
            logger.info(f"[DRY-RUN] Processando apenas {len(repos)} repos")

        all_results = []
        total = len(repos)
        failed = 0
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Log file
        log_dir = os.path.join(self.output_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"temporal_{timestamp}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        logger.addHandler(file_handler)

        for i, repo in enumerate(repos):
            name = repo.get("repo_name", "")
            logger.info(f"\n[{i+1}/{total}] Processando: {name}")

            try:
                results = self.process_repo(repo)
                all_results.extend(results)
                logger.info(f"  → {len(results)} project years extraídos")
            except Exception as e:
                logger.error(f"  [ERRO] {name}: {e}")
                failed += 1

            # Salvar progresso a cada 10 repos
            if (i + 1) % 10 == 0:
                self._save_results(all_results, timestamp, partial=True)

        # Salvar resultado final
        self._save_results(all_results, timestamp, partial=False)

        # Sumário
        logger.info("\n" + "=" * 60)
        logger.info("  Pipeline finalizado!")
        logger.info(f"  Repos processados: {total - failed}/{total}")
        logger.info(f"  Falhas: {failed}")
        logger.info(f"  Total de snapshots: {len(all_results)}")
        logger.info(f"  API requests: {self.api.request_count if self.api else 0}")
        logger.info(f"  Log: {log_file}")
        logger.info("=" * 60)

    def _save_results(self, results: list, timestamp: str, partial: bool = False):
        """Salva resultados em CSV."""
        if not results:
            return

        suffix = "_partial" if partial else ""
        csv_path = os.path.join(self.output_dir, f"temporal_data{suffix}_{timestamp}.csv")

        # Coletar todas as colunas
        all_keys = set()
        for r in results:
            all_keys.update(r.keys())

        # Ordenar colunas: meta primeiro, depois social, depois code smells
        meta_cols = ["repo_name", "owner", "repo_slug", "project_year",
                     "snapshot_date", "first_commit_date", "snapshot_commit"]
        social_cols = ["commit_count", "author_count", "days_active",
                       "bus_factor_number", "pr_count", "issue_count",
                       "pr_participants_mean", "issue_participants_mean",
                       "timezone_count"]
        indicator_cols = ["lone_wolf", "radio_silence", "org_silo", "org_silo_proxy"]
        smell_cols = sorted([k for k in all_keys
                            if k.startswith("total_") or k.startswith("design_") or k.startswith("impl_")])

        fieldnames = []
        for col in meta_cols + social_cols + indicator_cols + smell_cols:
            if col in all_keys:
                fieldnames.append(col)
        # Adicionar qualquer coluna restante
        for col in sorted(all_keys):
            if col not in fieldnames:
                fieldnames.append(col)

        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for r in results:
                writer.writerow(r)

        logger.info(f"  Resultados salvos: {csv_path} ({len(results)} linhas)")


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Extração temporal por project year para dissertação MSR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Dry-run com 3 repos (sem Designite, sem API)
  python 08_temporal_extraction.py \\
      --repos-csv data/repositories.csv \\
      --urls-file urls/repo_urls.txt \\
      --owner-map urls/owner_map.json \\
      --output-dir results/temporal \\
      --dry-run

  # Execução completa
  python 08_temporal_extraction.py \\
      --repos-csv data/repositories.csv \\
      --urls-file urls/repo_urls.txt \\
      --owner-map urls/owner_map.json \\
      --github-token ghp_XXX \\
      --designite-jar tools/DesigniteJava.jar \\
      --output-dir results/temporal \\
      --max-years 5
        """
    )

    parser.add_argument("--repos-csv", required=True,
                        help="CSV com lista de repositórios (repositories.csv)")
    parser.add_argument("--urls-file",
                        help="Arquivo com URLs resolvidas (repo_urls.txt)")
    parser.add_argument("--owner-map",
                        help="JSON com mapa repo_name → owner (owner_map.json)")
    parser.add_argument("--github-token",
                        help="Token pessoal do GitHub (ou env GITHUB_TOKEN)")
    parser.add_argument("--designite-jar",
                        help="Caminho para DesigniteJava.jar")
    parser.add_argument("--output-dir", default="results/temporal",
                        help="Diretório de saída (default: results/temporal)")
    parser.add_argument("--max-years", type=int, default=MAX_PROJECT_YEARS,
                        help=f"Máximo de project years (default: {MAX_PROJECT_YEARS})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Processa apenas 3 repos, sem Designite/API")
    parser.add_argument("--skip-designite", action="store_true",
                        help="Pula a execução do Designite (apenas métricas sociais)")
    parser.add_argument("--start-from", type=int, default=0,
                        help="Índice do repo inicial (para retomar execução)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Log detalhado (DEBUG)")

    args = parser.parse_args()

    # Token do env se não fornecido
    if not args.github_token:
        args.github_token = os.environ.get("GITHUB_TOKEN")

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validações
    if not os.path.exists(args.repos_csv):
        logger.error(f"Arquivo não encontrado: {args.repos_csv}")
        sys.exit(1)

    if args.designite_jar and not os.path.exists(args.designite_jar):
        logger.warning(f"Designite JAR não encontrado: {args.designite_jar}")
        logger.warning("Continuando sem análise de Code Smells.")
        args.skip_designite = True

    # Executar pipeline
    pipeline = TemporalExtractionPipeline(args)
    pipeline.run()


if __name__ == "__main__":
    main()
