#!/bin/bash
# vigia_codec3.sh: os controles da v3 a cada 1.000 medidas e no fim; a máquina v3 nas candidatas, no fim e nos erros; as mortes. Só lê.
C=/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/provas/codec; F=$C/vigia3.feito; touch $F
ja() { grep -qxF "$1" $F; }; marca() { echo "$1" >> $F; }
read P0 P1 P2 P3 < $C/v3_pids.txt
while true; do
  for n in v3_cego v3_estruturado v3_escalada; do
    l=$(grep -E ": (1000|2000|3000|4000)/" $C/$n.log 2>/dev/null | tail -1)
    [ -n "$l" ] && ! ja "$l" && { marca "$l"; echo "$l"; }
    grep -q "^fim" $C/$n.log 2>/dev/null && ! ja "fim $n" && { marca "fim $n"; echo "$n terminou"; }
    grep -qE "Traceback|Error" $C/$n.log 2>/dev/null && ! ja "erro $n" && { marca "erro $n"; echo "$n ERRO: $(tail -1 $C/$n.log | cut -c1-200)"; }
  done
  ls $C/v3_maquina/candidata_*.json >/dev/null 2>&1 && ! ja "candidata" && { marca "candidata"; echo "máquina v3: candidata que cumpre D gravada"; }
  grep -q "^fim" $C/v3_maquina.log 2>/dev/null && ! ja "fim maquina" && { marca "fim maquina"; echo "máquina v3: $(grep '^fim' $C/v3_maquina.log | cut -c1-250)"; }
  grep -qE "Traceback|Error" $C/v3_maquina.log 2>/dev/null && ! ja "erro maquina" && { marca "erro maquina"; echo "máquina v3 ERRO: $(tail -2 $C/v3_maquina.log | cut -c1-200)"; }
  for p in $P0 $P1 $P2 $P3; do kill -0 $p 2>/dev/null || { ja "morto $p" || { marca "morto $p"; echo "processo $p terminou"; }; }; done
  sleep 30
done
