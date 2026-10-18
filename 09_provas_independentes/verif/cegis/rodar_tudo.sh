#!/bin/sh
# Roda todas as conferencias sobre os arquivos de dados (nenhum codigo do repositorio e executado).
# Uso: sh rodar_tudo.sh <pasta main_ro>
set -e
R="$1"; E="$R/06_evidencias/cegis_e_z3"; B="$E/bateria_dse_v4"; D="$(dirname "$0")"
python3 -I "$D/recontagem.py" "$B/resultados.jsonl" "$B/resumo.json" "$B/protocolo.json" "$E/auditoria_z3.json" > "$D/saida_recontagem.txt"
python3 -I "$D/razoes.py" "$B/resultados.jsonl" > "$D/saida_razoes.txt"
python3 -I "$D/pares.py" "$B/resultados.jsonl" > "$D/saida_pares.txt"
python3 -I "$D/ordem_das_linhas.py" "$B/resultados.jsonl" > "$D/saida_ordem.txt"
python3 -I "$D/auditoria_tempo.py" "$E/auditoria_z3.json" > "$D/saida_auditoria_tempo.txt"
python3 -I "$D/hash_tentativas.py" "$B/resultados.jsonl" "$B/protocolo.json" > "$D/saida_hash.txt"
python3 -I "$D/poda.py" "$B/resultados.jsonl" > "$D/saida_poda.txt"
python3 -I "$D/nao_triviais.py" "$B/resultados.jsonl" > "$D/saida_nao_triviais.txt"
python3 -I "$D/classes.py" "$B/resultados.jsonl" "$E/auditoria_z3.json" > "$D/saida_classes.txt"
python3 -I "$D/classes_por_familia.py" "$E/auditoria_z3.json" > "$D/saida_classes2.txt"
( cd "$R" && sha256sum 06_evidencias/cegis_e_z3/LEIA-ME.md 06_evidencias/cegis_e_z3/PROCEDENCIA.md 06_evidencias/cegis_e_z3/auditoria_z3.json \
  06_evidencias/cegis_e_z3/bateria_dse_v4/protocolo.json 06_evidencias/cegis_e_z3/bateria_dse_v4/resultados.jsonl \
  06_evidencias/cegis_e_z3/bateria_dse_v4/resumo.json 01_artigo/A_ENGENHARIA_REVERSA_DO_ACASO.md 02_formula/A_FORMULA_DO_DEVER_SER_v4.3.md ) > "$D/sha_calc.txt"
n=$(grep -c -F -x -f "$D/sha_calc.txt" "$R/MANIFESTO.sha256" || true)
echo "arquivos conferidos contra o MANIFESTO: $n de 8" > "$D/saida_manifesto.txt"
echo ok
