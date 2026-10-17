# A engenharia reversa do acaso: os arquivos

Limiar Research, Gabriel Santos, 16 de outubro de 2026.

## Summary (English)

This repository holds an ongoing research project, "The reverse engineering of chance": a formula that searches for a candidate from a specification written as clauses (D), the measured numbers of its environment (Π) and a fixed verifier (V), the machines that run it, and the evidence of what they found. The table below lists each result with the machine that produced it, its exact scope, its limit and the files that hold its evidence. It includes the negative results. The rest of the repository is written in Portuguese.

| result | machine and date | scope | limit | evidence | how to reproduce |
|---|---|---|---|---|---|
| An 8-element sorting routine with 4.3% fewer cycles per vector than the reference (22.273 against 23.359), correct on all 16,777,216 vectors with values from 0 to 7 | the closed engine of formula 4.0, without a learner, 29/09/2026; 384 candidates evaluated in 581.7 s | the same optimal 19-comparator network as the reference, with a different order of the comparators within each level and the swap done in memory instead of registers; measured on a first-generation AMD EPYC (Zen 1) with gcc 13, meter noise 0.46% | it is not a new network; the gain comes from how that processor and that compiler execute the code, and on another processor it may differ or vanish; declared as best found and verified, not proven best, because part of the space was sampled | `06_evidencias/ordenacao_29-09/` | compile and run the measured program (below) |
| On a battery of 192 finite-state-machine construction cases, 1,152 formulations, against 17,588 for CEGIS with pruning and 16,120 for CEGIS | the first machine of the formula, 28/09/2026 | a formulation is a complete candidate that the method builds and sends to be judged; the formula and CEGIS with pruning found 82 solutions each, with the same cost on all 82, and CEGIS without pruning found 50; z3 5.1.0, run separately, confirmed the 192 verdicts with 0 disagreements in 2,870 queries | the battery is the author's own, and so is the CEGIS implementation; in total time the formula and CEGIS with pruning were close (153.3 s against 159.0 s); the code of the battery and of the CEGIS is not in this repository | `06_evidencias/cegis_e_z3/` | not reproducible from this repository; the per-case results and the z3 audit can be read |
| No candidate met D | C★3, 04 and 05/10/2026 | the Dever-Ser Machine 4.3.1 applied to a continual-learning D | this folder is the code to reproduce the search, not a result; the records of that run are not in this repository | `08_c_estrela_3/` | `08_c_estrela_3/README.md` (Linux, long runs, `--autorizacao`) |
| The premises of a small test being, computed from its D by hand, each with its prediction recorded before its life ran; premise 1b, for example, predicted 12 wrong activations out of 4,110 and measured 24, 9 and 12 at 2, 4 and 6 hours of life | the conta 15, by hand, before the machines, 26/09/2026 | each premise in its own test, with the prediction and the life in machine logs | the whole body assembled from the full D did not learn; the scripts read configuration and voices from the research server, which are not in the package; the commits cited are from the working repository, not this one | `07_conta_15/registros/`, `07_conta_15/A_CONTA_15.md` | not reproducible from this repository alone |

## Sobre

Este repositório traz uma pesquisa em andamento, "A engenharia reversa do acaso": uma fórmula que procura um candidato a partir de uma especificação escrita em cláusulas (D), dos números medidos do meio (Π) e de um verificador fixo (V); as máquinas que a executam; e as evidências do que elas acharam. A tabela abaixo dá cada resultado com a máquina que o produziu, o alcance exato, o limite e os arquivos da evidência. Os resultados negativos estão nela.

## Os resultados

| resultado | máquina e data | alcance | limite | evidência | como reproduzir |
|---|---|---|---|---|---|
| Uma rotina de ordenação de 8 elementos com 4,3% menos ciclos por vetor que a referência (22,273 contra 23,359), correta nos 16.777.216 vetores com valores de 0 a 7 | o motor fechado da fórmula 4.0, sem aprendiz, 29/09/2026; 384 candidatos avaliados em 581,7 s | a mesma rede ótima de 19 comparadores da referência, com outra ordem dos comparadores dentro de cada nível e a troca feita na memória e não nos registradores; medida num AMD EPYC de primeira geração (Zen 1) com gcc 13, ruído do medidor de 0,46% | não é uma rede nova; o ganho vem de como esse processador e esse compilador executam o código, e em outro processador pode ser outro ou não existir; declarada como melhor encontrada e verificada, sem demonstração de que é a melhor possível, porque parte do espaço foi amostrada | `06_evidencias/ordenacao_29-09/` | compilar e rodar o programa medido (abaixo) |
| Na bateria de 192 casos de construção de máquinas de estados finitos, 1.152 formulações, contra 17.588 do CEGIS com poda e 16.120 do CEGIS | a primeira máquina da fórmula, 28/09/2026 | uma formulação é um candidato completo que o método monta e manda julgar; a fórmula e o CEGIS com poda acharam 82 soluções cada, com o mesmo custo nas 82, e o CEGIS sem poda achou 50; o z3 5.1.0, rodado à parte, confirmou os 192 vereditos, com 0 discordâncias em 2.870 perguntas | a bateria é própria, e o CEGIS é uma implementação do próprio autor; no tempo total, a fórmula e o CEGIS com poda ficaram próximos (153,3 s contra 159,0 s); o código da bateria e do CEGIS não está neste repositório | `06_evidencias/cegis_e_z3/` | não reproduzível a partir deste repositório; os resultados por caso e a auditoria do z3 podem ser lidos |
| Nenhum candidato cumpriu D | a C★3, 04 e 05/10/2026 | a Máquina do Dever-Ser 4.3.1 aplicada a um D de aprendizado contínuo | a pasta é o código para reproduzir a busca, não um resultado; os registros dessa corrida não estão neste repositório | `08_c_estrela_3/` | `08_c_estrela_3/README.md` (Linux, corridas longas, `--autorizacao`) |
| As premissas de um pequeno ser de teste, calculadas à mão a partir do D, cada uma com a previsão registrada antes de a vida rodar; na premissa 1b, por exemplo, a previsão foi de 12 acendimentos errados em 4.110, e a vida mediu 24, 9 e 12 com 2, 4 e 6 horas | a conta 15, à mão, antes das máquinas, 26/09/2026 | cada premissa no seu teste, com a previsão e a vida em registros de máquina | o corpo inteiro montado a partir do D completo não aprendeu; os roteiros leem configuração e vozes do servidor de pesquisa, que não estão no pacote; os commits citados são do repositório de trabalho, não deste | `07_conta_15/registros/`, `07_conta_15/A_CONTA_15.md` | não reproduzível só com este repositório |

Onde está cada número:
- **Ordenação:**
  - os ciclos, a razão de 0,95682, o ruído de 0,00457 e a correção estão em `06_evidencias/ordenacao_29-09/01_resultado_8_elementos/rede_vencedora.json`;
  - as 7 gerações, os 384 avaliados e os 581,7 s estão em `.../corrida_motor8/estado.json`, no campo da parada.
- **CEGIS:**
  - as formulações, as soluções e os segundos estão em `06_evidencias/cegis_e_z3/bateria_dse_v4/resumo.json`;
  - o z3 está em `06_evidencias/cegis_e_z3/auditoria_z3.json`.
- **Conta 15:** os números da premissa 1b estão em `07_conta_15/registros/p1b_conta.log` e `p1b_vida.log`.

## Reproduza a ordenação

Num Linux x86-64, de dentro de `06_evidencias/ordenacao_29-09/01_resultado_8_elementos/`:

```
g++ -O2 -march=native -std=c++17 -falign-functions=64 -falign-loops=64 rotina_8_vencedora_e_referencia.cpp -o rotina
./rotina 21
```

A saída é uma linha JSON com:
- o erro de ordenação;
- os ciclos por vetor da vencedora e da referência;
- a razão entre elas e a razão da referência contra a própria cópia;
- o ruído.

Num Zen 1 com gcc 13, a razão fica perto de 0,957. Fora de um Zen 1 ela muda, e a própria saída mostra quanto.

## Glossário

Os termos próprios, com a definição que o repositório dá e o termo mais próximo na área. A definição completa de cada um está na fórmula (`02_formula`, seções 2, 4 e 9) e nos LEIA-ME citados.

| termo | o que é, segundo o repositório | termo próximo na área |
|---|---|---|
| D | o dever ser: a intenção escrita em cláusulas rígidas, objetivos e preferência; só muda com a confirmação do criador | especificação |
| V | o critério do que é cumprir, calibrado por controles antes de julgar; o juiz fixo, que a busca não altera | verificador |
| Π | os números do meio, cada um com a sua incerteza e a sua procedência; só mudam por medida | parâmetros medidos do ambiente |
| L | a linguagem das formas: as primitivas que se compõem para formar um candidato | linguagem dos candidatos, espaço de busca |
| M | o modelo, ou a medida no alvo, com o seu domínio de validade | modelo |
| f | a forma do motor, o jeito de procurar: uma regra declarada (σ) e, quando ligado, um aprendiz | estratégia de busca |
| S★ | o corpus escolhido: o que melhor atende D dentro do que o meio admite | solução |
| corpus | o concorrente que está sendo selecionado para atender D | candidato |
| foto atômica | o candidato decomposto até a menor unidade do meio; no digital, a sequência de bits do candidato numa codificação fixa | codificação do candidato em bits |
| seleção selecionada | a busca que corre sobre formulações, com cada fracasso registrado (decisão de 22/09/2026, `02_formula`, seção 23) | |
| catraca | o mecanismo pelo qual o motor propõe uma mudança em si mesmo, adotada só se ganhar com folga nos moldes de desenvolvimento e nos de confirmação (laço 11) | |
| braço | cada fonte de filhos de um mesmo pai: a escrita às cegas, o operador, o sorteio e, na C★3, a escrita aprendida (`04_maquina_do_dever_ser_selecao/LEIA-ME.md`, `08_c_estrela_3/README.md`) | operador de variação |
| testemunha | um método conhecido, escrito na mesma linguagem do candidato e medido à parte, só para comparação; na C★3, SGD, EWC, CBP e SP | linha de base (baseline) |
| oráculo | uma conferência por outro método, independente de V; na ordenação, a conferência pelo princípio 0-1; na fórmula, o laço 12 | verificador independente |

## As pastas

| pasta | o que tem |
|---|---|
| `01_artigo/` | o artigo |
| `02_formula/` | a fórmula do dever ser, versão 4.3 com as emendas 6 a 13, na edição formal para publicação |
| `03_motor_de_29-09/` | o motor fechado da fórmula 4.0, exatamente como rodou quando achou a rotina de ordenação de 29/09/2026 |
| `04_maquina_do_dever_ser_selecao/` | a Máquina do Dever-Ser 4.3.1 só com a seleção: as peças da 4.3.1 sem a rede que aprende |
| `05_tear_selecao/` | o Tear só com a seleção: a ilha em C e o leito em C, sem as ferramentas e sem a mente |
| `06_evidencias/` | a corrida da ordenação de 29/09, com o plano, os registros da máquina sem edição e o programa medido, pronto para compilar; e a bateria de 192 casos contra o CEGIS |
| `07_conta_15/` | a conta 15 (26/09/2026), a origem do Sismo e do aprendiz de sinapses: como foi feita, as premissas, as previsões registradas antes de cada vida, os resultados, o código sem comentários e os registros de máquina |
| `08_c_estrela_3/` | a C★3: o código e as instruções para rodar |
| `MANIFESTO.sha256` | o sha256 de cada arquivo |

Cada pasta de máquina tem o seu LEIA-ME, com o que é, de onde veio e como rodar e conferir.

## O que se conferiu na montagem (16/10/2026, Windows 11, Python 3.13, numpy 2)

- **O motor de 29/09:** as 18 provas do compilador e as 8 do núcleo passaram. O código é o do commit `7edc5af` do repositório de trabalho, o último antes da corrida de 8 elementos começar.
- **A 4.3.1 só com a seleção:** as 11 provas passaram. As peças tiradas da 4.3.1 foram conferidas como idênticas às originais.
- **O Tear só com a seleção:** a mesma semente, rodada pelo pacote e pela árvore original do Tear, deu os mesmos recordes, byte a byte.
- **A C★3:** o código executável é idêntico ao original sem os comentários, conferido pela árvore sintática de cada arquivo Python e pelo C++ sem comentários; os textos de saída que citavam pessoas foram reescritos em forma neutra. As provas da C★3 passaram no Windows, inclusive a V da busca e a calibração de V, que usam a V real: perturbação, sonda, V repartida, condutor v2, coletor, V da busca e calibração. A prova da V compartilhada só roda em Linux.
- **Os comentários de código que transcreviam conversas** foram reescritos como decisões formais. Nenhuma linha executável mudou: a árvore sintática de cada arquivo Python e o código C sem comentários foram comparados com os originais, e as provas rodaram de novo depois da mudança.
- **Nenhum endereço de servidor, chave ou senha** está no pacote.

## O que não está aqui

As pastas 03, 04 e 05 vão sem aprendiz: ficaram de fora a rede da 4.3.1, a mente e as ferramentas do Tear e o aprendiz da variação do motor. A C★3 vai com o aprendiz, como rodou. Não estão aqui os manuais, os planos de construção, os registros de trabalho nem as cópias do servidor de pesquisa.

## Licença

O código e os documentos deste repositório estão sob a licença MIT (`LICENSE`).
