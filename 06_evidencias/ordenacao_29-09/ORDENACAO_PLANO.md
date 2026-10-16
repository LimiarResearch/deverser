# Rotinas curtas de ordenação para CPU real: o plano

Pesquisa privada da Limiar Research. A escolha do problema é do autor (29/09/2026): um corpo digital com meio real, de repercussão global, que ative todos os laços da fórmula e do motor e tenha seleção quase tão rápida quanto a matemática. O texto foi escrito pelo Claude, como ferramenta, em 29/09, antes de qualquer medida deste problema.

## Por que este problema

A AlphaDev (Nature, 2023) achou rotinas mais rápidas para ordenar 3, 4 e 5 elementos, e elas entraram no libc++ do LLVM. Os trabalhos de 2025 ficaram de 3 a 5 elementos. De 6 a 8 elementos, rotinas sem desvio medidas em máquina real ainda são fronteira. V é exato e exaustivo, e medir o tempo leva milissegundos: são milhares de candidatos por minuto.

## A conta

- **D (a intenção, confirmada pelo autor antes da corrida):** ordenar n inteiros de 32 bits (n = 6, depois 7 e 8), correto para toda entrada; mais rápido que a rotina de referência no alvo; o tamanho do código como objetivo. "Em assembly x86" é cláusula de forma, e só fica se Gabriel disser que é intenção.
- **Π (medidos no alvo, nunca postos à mão):** a latência e a vazão de min, max, cmov, cmp e mov; o custo de um desvio errado; o ruído da medida de tempo (a resolução que decide a distinguibilidade); o modelo do processador; a versão do gcc; o tempo das referências.
- **V (preso):** todas as ordens com empate (as ordens fracas: 4.683 para n = 6, 47.293 para n = 7, 545.835 para n = 8), conferidas em C. Depois, o tempo: a mediana de R repetições sobre um conjunto fixo de vetores, com as referências medidas no mesmo processo e na mesma rodada.
- **As referências:** o std::sort do libstdc++ (o gcc da VPS não traz o libc++), as redes ótimas conhecidas por tamanho e por profundidade, escritas à mão, e as rotinas da AlphaDev para 3 a 5 elementos, para calibrar a bancada.
- **L0:** redes de ordenação em C, com a ordem dos comparadores (o paralelismo que o processador aproveita) e os comparadores parciais (só o mínimo ou só o máximo, o truque da AlphaDev) como genes. O corpo é uma lista de peças: L que compõe.
- **L1 (a abertura preparada para quando L0 empacar):** sequências de instruções x86 (mov, cmp, cmovl, cmovg) montadas com o gcc, com V exaustivo interpretando a sequência antes de ela rodar.
- **A ferramenta declarada:** o candidato passa uma descrição estruturada (a lista de peças), e a ferramenta gera o C ou o assembly a partir dela, compila com o gcc numa pasta temporária, confere V e mede o tempo. O candidato nunca manda código livre para o compilador. O binário do medidor é declarado por caminho e sha256, como na emenda 2.

## As voltas que este problema ativa

1. **Distinguibilidade:** uma diferença de tempo menor que o ruído da VPS não decide nada. A conferência antes da busca mede o ruído e diz quantas repetições separam duas rotinas.
2. **Ponto fixo:** o tamanho do código pesa no cache de instruções de quem chama. O efeito no meio é medido chamando a rotina de dentro de um laço maior.
3. **Horizonte:** processadores mudam de geração. U cobre as máquinas medidas; com uma VPS só, U é pequeno, e isso vai nas premissas.
4. **Mapa(D, L):** as instruções de L1 pedem as latências delas.
5. **Dom(M):** o modelo de tempo vale na microarquitetura medida.
6. **O mundo:** enviar a rotina ao LLVM e ao libstdc++, e contar se ela passa nos testes e nos benchmarks de outras pessoas.
7. **σ:** a população sai do custo medido de um lote.

## A prova da fórmula

Com o mesmo V, o mesmo orçamento e o mesmo alvo:
- a fórmula inteira;
- um evolutivo simples, sem as voltas.

As rotinas finais das duas se comparam entre si, com o std::sort e com as redes ótimas. A fórmula está provada neste problema se a versão inteira ganhar das duas coisas: do evolutivo simples e das referências.

## A ordem do trabalho

1. O medidor em C: V exaustivo e a medida de tempo com as referências. Medir o ruído da VPS antes de tudo.
2. A ferramenta declarada, com a sua prova.
3. O questionário do motor, com as respostas pelo criador marcadas, e L1 preparada como abertura.
4. O teste do fluxo inteiro no PC (sem compilador, com o medidor rodando pela VPS) ou direto na VPS.
5. A corrida, depois o evolutivo simples, depois a comparação.

## O que ficou parado em 29/09, às 02h05

- Na VPS, em /home/iro/bancada-criacao/calculadora-matmul/parados_0200: o 3×3 e o 4×4 pelo motor fechado, com o passeio em C (ainda na primeira concorrência, sem resultado).
- Antes disso, os scripts em C: o 3×3 com 42 concorrentes, todos no recorde de 23; o 4×4 partindo de 64, com o melhor em 49.
- No PC, em saida/calculadora/matmul/motor: o 3×3 pelo motor fechado em Python, na primeira concorrência.
- O desafio final, em /home/iro/bancada-criacao/calculadora-desafio/motor_desafio_parado.
