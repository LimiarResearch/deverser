# A comparação com o CEGIS e o z3

A bateria de 192 casos da primeira máquina (28/09/2026), que constrói máquinas de estados finitos.

**O que se compara.** Os três métodos rodaram nos mesmos 192 casos, com o protocolo congelado antes. O CEGIS daqui, a síntese guiada por contraexemplo, é uma implementação do próprio autor, nas duas variantes (com e sem poda), e não uma ferramenta publicada. O código da bateria e do CEGIS não está neste repositório; estão o protocolo, o resultado de cada caso e a auditoria do z3.

**A unidade.** A palavra "formulação" não mede a mesma coisa nos dois métodos. Na fórmula, uma formulação pode encerrar um caso sem busca, como nos 54 de memória insuficiente. No CEGIS com poda, 94% das formulações terminam sem verificação, e a contagem acompanha o número de classes estruturais que ele percorre (`09_provas_independentes/verif/VERIF_cegis.md`, seção 4). Por isso a comparação vai em três unidades:

| unidade | fórmula | CEGIS com poda | CEGIS sem poda |
|---|---|---|---|
| formulações | 1.152 | 17.588 (15,3 vezes) | 16.120 (14,0 vezes) |
| chamadas ao verificador | 817 | 1.018 (1,25 vez) | 2.912 (3,56 vezes) |
| segundos no total | 153,3 | 159,0 (1,04 vez) | 362,7 (2,37 vezes) |

A fórmula usou menos formulações em todos os 192 casos, com mediana de 19 vezes por caso contra o CEGIS com poda. Nos 82 casos que os dois resolveram, o tempo foi praticamente igual. O CEGIS sem poda parou 72 vezes no limite de 300.000 nós, e por isso as 50 soluções dele medem também esse limite.

- `bateria_dse_v4/protocolo.json`: o protocolo, congelado antes de rodar.
- `bateria_dse_v4/resultados.jsonl`: o resultado de cada caso, para cada método:
  - `f`, a fórmula;
  - `cegis_poda`, o CEGIS com poda;
  - `cegis`, o CEGIS.
- `bateria_dse_v4/resumo.json`: os totais. Os números que o artigo cita estão lá:
  - a fórmula precisou de 1.152 formulações;
  - o CEGIS com poda, de 17.588;
  - o CEGIS, de 16.120.
  - A fórmula e o CEGIS com poda acharam as mesmas 82 máquinas; o CEGIS sem poda achou 50. Nenhum dos três falhou na conferência, que nos vereditos negativos do CEGIS não foi feita.
  - 48 das 82 soluções são triviais: máquinas de 1 estado que leem o sensor `s_autorizado`.
- `auditoria_z3.json`: a conferência pelo z3, um resolvedor rodado num processo à parte. A auditoria guarda o veredito da fórmula em cada caso e confirma os vereditos da fórmula, não os do CEGIS; o código do auditor e as perguntas feitas ao z3 não estão no repositório. Os 192 vereditos foram confirmados (54 de memória insuficiente, 82 soluções, 37 acima do orçamento e 19 não observáveis), com 0 discordâncias, em 2.870 perguntas ao z3. O hash dos casos é o mesmo do protocolo da bateria.
- `PROCEDENCIA.md`: a versão do z3 e o hash da roda instalada.
