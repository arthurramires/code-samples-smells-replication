# Decisões Metodológicas

## 1. Critério de Idade Mínima para Análise Temporal

**Decisão:** Mínimo de 2 project years (≈ 730 dias de idade).

**Embasamento:**
- Rio & Brito e Abreu (2023) demonstraram que a sobrevivência média de code smells é ~4 anos, utilizando projetos com 5+ anos de histórico para análise longitudinal em PHP.
- Olbrich et al. (2009) analisaram projetos com 7–10 anos de histórico para rastrear a evolução de God Class e Shotgun Surgery.
- Tufano et al. (2017) mostraram que a maioria dos smells é introduzida no primeiro commit, sugerindo que a observação de pelo menos 2 pontos temporais já captura o padrão fundamental.

**Justificativa para 2 anos (não 3 ou 5):**
Code samples são artefatos de ciclo de vida intrinsecamente curto — 99,5% são write-once com mediana de 6 dias de atividade. Um limiar de 5 anos (como em estudos de produção) eliminaria a grande maioria do dataset. O mínimo de 2 project years garante pelo menos dois pontos de observação longitudinal (Year 1 e Year 2), sendo pragmático para o domínio estudado.

## 2. Separação Cross-sectional vs. Temporal

**Decisão:** Dois pools de análise distintos.

- **Pool cross-sectional (RQ1, RQ3):** Todos os repositórios com dados sociais completos, independente de idade. Maximiza o N para correlações e clustering.
- **Pool temporal (RQ2):** Apenas repositórios com idade ≥ 2 years. Garante que a análise de evolução temporal tenha sentido.

## 3. Unificação V1 + V2

**Decisão:** Combinar os dois datasets, não substituir.

- V1 (300 repos) já possui resultados consolidados e publicados.
- V2 (444 candidatos) traz 412 repos novos, predominantemente de Azure-Samples e aws-samples.
- Após filtros, V2 adiciona 52 repos (cross-sectional) e 18 repos (temporal).

## 4. Pipeline Incremental

**Decisão:** Processar cada repo individualmente (clone → ferramentas → consolidar → limpar).

**Motivação:** Limitação de disco (~100-200GB de clones acumulados se todos forem mantidos simultaneamente). O pipeline incremental processa um repo por vez e libera o clone após consolidar métricas.
