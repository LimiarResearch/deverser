#!/bin/bash
# vigia_codec.sh: avisa a cada 2.000 medidas dos controles, cada candidata e o fim da máquina, os erros e as mortes. Só lê. Lembra o que avisou.
C=/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/provas/codec; F=$C/vigia.feito; touch $F
ja() { grep -qxF "$1" $F; }; marca() { echo "$1" >> $F; }
while true; do
  for n in nulo_cego nulo_estruturado; do
    l=$(grep -E "^(cego|estruturado): (2000|4000|6000)/" $C/$n.log 2>/dev/null | tail -1)
    [ -n "$l" ] && ! ja "$l" && { marca "$l"; echo "$l"; }
    grep -q "^fim" $C/$n.log 2>/dev/null && ! ja "fim $n" && { marca "fim $n"; echo "$n terminou"; }
    grep -qE "Traceback|Error" $C/$n.log 2>/dev/null && ! ja "erro $n" && { marca "erro $n"; echo "$n ERRO: $(tail -1 $C/$n.log | cut -c1-200)"; }
  done
  ls $C/corrida_maquina/candidata_*.json >/dev/null 2>&1 && ! ja "candidata" && { marca "candidata"; echo "máquina: candidata que cumpre D gravada"; }
  grep -q "^fim" $C/corrida_maquina.log 2>/dev/null && ! ja "fim maquina" && { marca "fim maquina"; echo "máquina: $(grep '^fim' $C/corrida_maquina.log | cut -c1-250)"; }
  grep -qE "Traceback|Error" $C/corrida_maquina.log 2>/dev/null && ! ja "erro maquina" && { marca "erro maquina"; echo "máquina ERRO: $(tail -2 $C/corrida_maquina.log | cut -c1-200)"; }
  for p in 26231 24746 24799; do kill -0 $p 2>/dev/null || { ja "morto $p" || { marca "morto $p"; echo "processo $p terminou"; }; }; done
  sleep 30
done
