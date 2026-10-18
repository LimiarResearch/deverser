# O codec sem perda pela Máquina do Dever-Ser 4.3.1 (18/10/2026)

Dados: a tabela de métricas da empresa simulada do Estalo (itens.csv, 36.000 minutos, 496 colunas, 75,6 MB; cópia só de leitura).
Um dia é um bloco que se lê sozinho. Desenvolvimento: dias 5 e 6. Retidos: os outros 23 dias. Toda medida confere a volta exata.
A máquina: a 4.3.1 só com a seleção, do repositório deverser, sem mudança; o D e a codificação estão em d_codec2.py.

## Nos dias de desenvolvimento (bytes; 6,0 MB de CSV)

| codec | bytes | vezes o melhor codec único |
|---|---|---|
| melhor codec único da L (busca exaustiva, 1.024 medidas) | 61.224 | 1,00 |
| melhor da máquina (5.995 medidas) | cerca de 74.600 | cerca de 1,22 |
| colunar int32 + xz -9e | 76.084 | 1,24 |
| sorteio estruturado (6.004 medidas) | cerca de 81.900 | 1,34 |
| seletor exaustivo por classe | 92.024 | 1,50 |
| sorteio cego (6.004 medidas) | cerca de 113.700 | 1,86 |
| xz -9e no CSV | 153.036 | 2,50 |

O D (no máximo 0,95 do melhor codec único) não foi cumprido por ninguém. A máquina melhorou sobre o pai 541 vezes em 5.931
filhos e terminou à frente dos dois sorteios, mas usou os 8 grupos (de 53 a 76 colunas cada) e não achou o agrupamento do melhor
codec conhecido, que é uma coluna só, com tudo junto.

## Nos 23 dias retidos (69,5 MB de CSV)

| codec | bytes | vezes o melhor codec único | vezes menor que o CSV |
|---|---|---|---|
| melhor codec único da L | 1.180.998 | 1,000 | 59 |
| colunar int32 + xz -9e | 1.398.416 | 1,184 | 50 |
| melhor da máquina | 1.517.508 | 1,285 | 46 |
| xz -9e no CSV | 2.585.304 | 2,189 | 27 |

Todos exatos nos 23 dias.

## Registros

A corrida 1 da máquina (escala 0,15 em c1) saturou a distância e ficou cega; foi parada pelo PID e guardada em
corrida_maquina_cega_escala015/. A corrida 2 (corrida_maquina/) usa o log2 dos bytes, com o mesmo D. Os sha256 estão em hashes.txt.


## A versão 3 (grupo padrão e até 64 exceções; o mesmo D e o mesmo V), 4.004 medidas por braço

Declarada depois da corrida 2, porque na v2 o melhor codec conhecido (um grupo só) era quase inalcançável. Nos dias 5 e 6, em vezes o melhor codec único (61.224 bytes):

| quem | melhor |
|---|---|
| subida simples, a partir do melhor codec único | 1.000 |
| sorteio estruturado (o melhor codec único + exceções sorteadas) | 1.028 |
| sorteio cego | 1.060 |
| a máquina (parte do sorteio) | 1.084 |

Ninguém cumpriu o D (no máximo 0,95). A subida simples, que começou no melhor codec único, não achou nenhuma mudança que melhorasse; o sorteio cego chegou mais perto que a máquina. Nesta L, o melhor codec único parece ser o ótimo, ou muito perto dele: separar colunas do grupo padrão não ajudou em nenhum dos quatro braços.
