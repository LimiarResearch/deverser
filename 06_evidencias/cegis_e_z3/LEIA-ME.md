# A comparação com o CEGIS e o z3

A bateria de 192 casos da primeira máquina (28/09/2026), que constrói máquinas de estados finitos.

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
- `PROCEDENCIA.md`: a versão do z3 e o hash da roda instalada. O z3 recebeu os 192 casos por outro caminho, sem ver a busca, e confirmou os 192 vereditos.
