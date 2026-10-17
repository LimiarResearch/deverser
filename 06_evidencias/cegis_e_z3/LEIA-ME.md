# A comparação com o CEGIS e o z3

A bateria de 192 casos da primeira máquina (28/09/2026), que constrói máquinas de estados finitos.

**O que se compara.** Uma formulação é um candidato completo que o método monta e manda julgar. Os três métodos rodaram nos mesmos 192 casos, com o protocolo congelado antes. O CEGIS daqui, a síntese guiada por contraexemplo, é uma implementação do próprio autor, nas duas variantes (com e sem poda), e não uma ferramenta publicada. No tempo total, a fórmula e o CEGIS com poda ficaram próximos: 153,3 s contra 159,0 s (`resumo.json`). O código da bateria e do CEGIS não está neste repositório; estão o protocolo, o resultado de cada caso e a auditoria do z3.

- `bateria_dse_v4/protocolo.json`: o protocolo, congelado antes de rodar.
- `bateria_dse_v4/resultados.jsonl`: o resultado de cada caso, para cada método:
  - `f`, a fórmula;
  - `cegis_poda`, o CEGIS com poda;
  - `cegis`, o CEGIS.
- `bateria_dse_v4/resumo.json`: os totais. Os números que o artigo cita estão lá:
  - a fórmula precisou de 1.152 formulações;
  - o CEGIS com poda, de 17.588;
  - o CEGIS, de 16.120.
  - A fórmula e o CEGIS com poda acharam 82 soluções cada; o CEGIS sem poda achou 50. Nenhum dos três falhou na conferência.
- `auditoria_z3.json`: a conferência pelo z3, um resolvedor isolado que recebeu os 192 casos por outro caminho, sem ver a busca. Os 192 vereditos foram confirmados (54 de memória insuficiente, 82 soluções, 37 acima do orçamento e 19 não observáveis), com 0 discordâncias, em 2.870 perguntas ao z3. O hash dos casos é o mesmo do protocolo da bateria.
- `PROCEDENCIA.md`: a versão do z3 e o hash da roda instalada.
