# o meio desta verificação: o compilador declarado (caminho e sha256) e a pasta temporária dentro de provas/motor_aqui
export P=/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/provas/motor_aqui
export R=/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/run/03_motor_de_29-09
export FERRAMENTA_GXX=/usr/bin/g++
export FERRAMENTA_GXX_SHA256=1353e9bdd29a7295c7226bf6c63abccce056d8cac31f112e5cdbecc3f28c2769
export TMPDIR=/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/provas/motor_aqui/tmp
log() { echo "$(date +%H:%M:%S) $*" >> $P/corrida_roteiro.log; }
