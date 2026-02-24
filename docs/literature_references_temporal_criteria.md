# Referências para Embasamento do Critério de Idade Mínima (Project Years)

## Referência Principal

**Rio, A., & Brito e Abreu, F. (2023).** PHP code smells in web apps: Evolution, survival and anomalies.
*Journal of Systems and Software*, 200, 111644.
- DOI: https://doi.org/10.1016/j.jss.2023.111644
- Critério: projetos com histórico longo (5+ anos)
- Achado-chave: sobrevivência média de code smells ≈ 4 anos; 61% dos CS introduzidos são removidos
- Replication: https://github.com/studydatacs/servercs / https://doi.org/10.5281/zenodo.7626150

## Referências Complementares

**Olbrich, S., Cruzes, D. S., & Sjøberg, D. I. K. (2009).** The evolution and impact of code smells: A case study of two open source systems.
*3rd International Symposium on Empirical Software Engineering and Measurement (ESEM 2009)*, pp. 390–400.
- DOI: https://doi.org/10.1109/ESEM.2009.5314231
- Projetos analisados: Lucene e Xerces (7–10 anos de histórico)
- Achado: fases distintas na evolução de God Class e Shotgun Surgery

**Tufano, M., Palomba, F., Bavota, G., Oliveto, R., Di Penta, M., De Lucia, A., & Poshyvanyk, D. (2017).** When and why your code starts to smell bad (and whether the smells go away).
*IEEE Transactions on Software Engineering*, 43(11), 1063–1088.
- DOI: https://doi.org/10.1109/TSE.2017.2653105
- 200 projetos (Android, Apache, Eclipse), históricos variados
- Achado: maioria dos smells introduzidos no primeiro commit; 80% sobrevivem no sistema

**Palomba, F., Tamburri, D. A., Arcelli Fontana, F., Oliveto, R., Zaidman, A., & Serebrenik, A. (2021).** Beyond technical aspects: How do community smells influence the intensity of code smells?
*IEEE Transactions on Software Engineering*, 47(1), 108–129.
- DOI: https://doi.org/10.1109/TSE.2018.2883603
- 117 releases de 9 sistemas open-source
- Janelas de 3 meses para grafos de comunicação

## Argumentação para Mínimo de 2 Project Years

Estudos longitudinais de evolução de code smells utilizam projetos com histórico suficiente para
capturar ciclos de introdução e remoção. Rio & Brito e Abreu (2023) demonstraram que a
sobrevivência média de code smells é de ~4 anos, selecionando projetos com ≥5 anos. Olbrich et al.
(2009) analisaram projetos com 7–10 anos. Tufano et al. (2017) usaram 200 projetos com históricos
variados em 3 ecossistemas.

Contudo, code samples são artefatos de ciclo de vida intrinsecamente mais curto (99,5% write-once,
mediana de 6 dias de atividade). Para equilibrar representatividade temporal com a natureza desses
artefatos, adota-se o critério de mínimo 2 project years (≈ 730 dias de idade), garantindo pelo menos
dois pontos de observação longitudinal. Esse limiar é conservador para o domínio estudado e permite
maximizar o N temporal sem incluir repositórios onde a análise seria trivial (snapshot único).
