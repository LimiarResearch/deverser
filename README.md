# A engenharia reversa do acaso: os arquivos

Limiar Research, Gabriel Santos, 16 de outubro de 2026. Revisado em 18/10/2026 com as provas independentes (`09_provas_independentes/`).

## Summary (English)

This repository holds an ongoing research project, "The reverse engineering of chance": a formula that searches for a candidate from a specification written as clauses (D), the measured numbers of its environment (Π) and a fixed verifier (V), the machines that run it, and the evidence of what they found. In 17 and 18/10/2026 a separate session checked the claims against the records and ran the code on other machines (`09_provas_independentes/`). The numbers match the records, but several sentences said more than the records show, and the new tests do not show a search advantage of the machine over simple alternatives. The table below lists each result with the machine that produced it, its exact scope, its limit and the files that hold its evidence, failures included. The rest of the repository is written in Portuguese.

What is different is the method, not the search engine: S★ = C★(D, Π) turns a problem into a verified calculation (intent written as clauses, measured environment, a fixed verifier calibrated by controls, five declared outcomes including "impossible in this form", and a record of what failed). Shown in three domains; the search is a pluggable part and is not, so far, the advantage.

| result | machine and date | scope | limit | evidence |
|---|---|---|---|---|
| An 8-element sorting routine with 4.3% fewer cycles per vector than the reference | the closed engine of formula 4.0, 29/09/2026 | the same optimal 19-comparator network, with a different order within each level and the swap done in memory; 0.957 is the median over 21 repetitions of the per-block ratios (the ratio of the medians, 22.273/23.359, is 0.9535); correct on all 16,777,216 vectors from 0 to 7 | one measurement of the winner, the smallest of 384, never re-measured; three candidates fall within the 1% resolution of D; the 3% threshold of D was set by the AI on behalf of the author; the processor model and the gcc version were not recorded | `06_evidencias/ordenacao_29-09/` |
| The same published program on two Intel processors | independent session, 17 and 18/10/2026 | ratio from 0.960 to 0.961 on a 2.1 GHz Xeon and from 0.990 to 0.993 on a 2.8 GHz Xeon (Cascade Lake), 5 runs each, 0 sorting errors | the gain depends on the processor, also between two Intel | `09_provas_independentes/provas/b1/` |
| The engine of 29/09 on the two Intel: vector code 35% to 43% faster than the hand-written scalar network, correct on 16.7 million vectors | independent session, 17 and 18/10/2026 | 14 to 16 times faster than std::sort | a textbook bitonic network was 11% to 12% faster (AVX-512) and 3% to 5% faster (AVX2) than the engine's code | `09_provas_independentes/provas/b3/`, `b4/` |
| The engine against blind random sampling with the same budget (726 candidates) | independent session, 17/10/2026 | the engine won: best re-measured 0.842 against 1.452 | it tied with a sampler that keeps the 19 comparators (0.8418 against 0.8417); the same binary varied about 6% between processes | `09_provas_independentes/provas/motor_aqui/` |
| On a battery of 192 finite-state-machine cases, 1,152 formulations against 17,588 for CEGIS with pruning | the first machine of the formula, 28/09/2026 | fewer formulations in all 192 cases, median 19 times per case; the same 82 machines as CEGIS with pruning; z3 confirmed the 192 verdicts of the formula with 0 disagreements | "15 times" holds only against CEGIS with pruning (14.0 times against CEGIS without pruning, which stopped 72 times at the node limit); the unit differs between the methods: in verifier calls the advantage is 1.25 times, in time 1.04 times; 48 of the 82 solutions are trivial; the battery and the CEGIS implementation are the author's own and their code is not here | `06_evidencias/cegis_e_z3/` |
| Lossless compression of a metrics table: the best single codec was 59 times smaller than the CSV and 15.5% smaller than the best generic alternative, on 23 held-out days | the Dever-Ser Machine 4.3.1 without changes, plus exhaustive search, 18/10/2026 | the best single codec was found by exhaustive search inside the method | the machine did not meet D and ended behind the best single codec; in version 3, also behind blind random sampling | `09_provas_independentes/provas/codec/` |
| No candidate met D | C★3, 04 and 05/10/2026 | the Dever-Ser Machine 4.3.1 applied to a continual-learning D | the folder is the code to reproduce the search, not a result; the records of that run are not in this repository | `08_c_estrela_3/` |
| The premises of a small simulated test being, computed by hand from its D, each with a printed prediction before its life | the conta 15, 26/09/2026 | premise 1b predicted 12 wrong activations out of 4,110 and measured 24, 9 and 12 at 2, 4 and 6 hours | several failed predictions were omitted from the text; in premises 3 and 4 the prediction is fixed text in the script; the whole body did not learn; the logs carry no timestamps | `07_conta_15/` |

## Sobre

Este repositório traz uma pesquisa em andamento, "A engenharia reversa do acaso": uma fórmula que procura um candidato a partir de uma especificação escrita em cláusulas (D), dos números medidos do meio (Π) e de um verificador fixo (V); as máquinas que a executam; e as evidências do que elas acharam. Em 17 e 18/10/2026, uma sessão separada conferiu as alegações pelos registros e rodou o código em outras máquinas (`09_provas_independentes/`). Os números conferem com os registros, mas várias frases diziam mais do que eles mostram, e os testes novos não mostram vantagem de busca da máquina sobre alternativas simples. A tabela abaixo dá cada resultado com a máquina que o produziu, o alcance exato, o limite e os arquivos da evidência, inclusive os fracassos.

## O que é diferente

O generalista é o método, não o motor de busca. A fórmula S★ = C★(D, Π) transforma um problema num cálculo verificado, com cinco peças:
- a intenção escrita em cláusulas (D);
- os números do meio medidos (Π);
- um verificador fixo, calibrado por controles (V);
- cinco desfechos declarados, inclusive "impossível nesta forma";
- o registro do que falhou.

| problema | o que o método entregou | com qual busca | evidência |
|---|---|---|---|
| ordenação de 8 números | código que muda com o processador: escalar no servidor de 29/09 (declarado como AMD EPYC), com 4,3% menos ciclos que a referência; vetorial nos dois Intel, de 35% a 43% mais rápido que a rede escalar escrita à mão; correção conferida em 16,7 milhões de vetores | a seleção do motor de 29/09 | `06_evidencias/ordenacao_29-09/`, `09_provas_independentes/provas/b3/`, `b4/`, `motor_aqui/` |
| máquinas de estados, 192 casos | as mesmas 82 máquinas do CEGIS com poda, com menos formulações em todos os casos, e os 192 vereditos da fórmula confirmados pelo z3 | a primeira máquina | `06_evidencias/cegis_e_z3/` |
| compressão sem perda de métricas | 59 vezes menor que o CSV e 15,5% menor que a melhor alternativa genérica, em 23 dias retidos | busca exaustiva dentro do mesmo método | `09_provas_independentes/provas/codec/` |

**O teste de generalidade de 18/10.** Para o codec, foram escritos só a codificação, o D e o V do problema (`codec/d_codec2.py`, `codec/d_codec3.py` e `codec/codec.py`). A Máquina do Dever-Ser 4.3.1 da pasta 04 rodou sem mudança, segundo o relatório (`codec/RESULTADO_codec.md`). A declaração da corrida registra a máquina e a versão, `4.3.1-selecao` (`codec/v3_maquina/declaracao.json`). A conferência da máquina pelo MANIFESTO antes de rodar não ficou registrada na pasta.

**O que não está demonstrado, com o mesmo peso.** A busca por seleção não mostrou vantagem sobre alternativas simples:
- na ordenação, ela empatou com um sorteio que mantém a estrutura;
- no codec, ela perdeu da busca exaustiva.

No método, a busca é uma peça trocável. A catraca, a parte que deixaria a máquina melhorar o próprio motor, não tem registros neste repositório.

## Os resultados

| resultado | máquina e data | alcance | limite | evidência |
|---|---|---|---|---|
| Uma rotina de ordenação de 8 elementos com 4,3% menos ciclos por vetor que a referência | o motor fechado da fórmula 4.0, sem aprendiz, 29/09/2026; 384 candidatos avaliados em 581,7 s | a mesma rede ótima de 19 comparadores da referência, com outra ordem dentro de cada nível e a troca feita na memória; 0,957 é a mediana, em 21 repetições, das medianas das razões por bloco (a razão das medianas, 22,273/23,359, dá 0,9535); correta nos 16.777.216 vetores de 0 a 7 | não é uma rede nova; uma só medida da vencedora, a menor entre 384, sem remedição; três candidatos cabem na resolução de 1% do D; o limite de 3% do D foi posto pela IA no lugar do criador; o modelo do processador e a versão do gcc não ficaram gravados | `06_evidencias/ordenacao_29-09/` |
| O mesmo programa publicado em dois Intel | sessão independente, 17 e 18/10/2026 | razão de 0,960 a 0,961 num Xeon de 2,1 GHz e de 0,990 a 0,993 num Xeon de 2,8 GHz (Cascade Lake), 5 rodadas em cada um, 0 erros de ordenação | o ganho depende do processador, também entre dois Intel | `09_provas_independentes/provas/b1/` |
| O motor de 29/09 nos dois Intel: código vetorial de 35% a 43% mais rápido que a rede escalar escrita à mão, com a correção conferida em 16,7 milhões de vetores | sessão independente, 17 e 18/10/2026 | de 14 a 16 vezes mais rápido que o std::sort | uma rede bitônica de livro foi de 11% a 12% mais rápida (AVX-512) e de 3% a 5% mais rápida (AVX2) que o código do motor | `09_provas_independentes/provas/b3/`, `b4/` |
| O motor contra o sorteio cego, no mesmo orçamento de 726 candidatos | sessão independente, 17/10/2026 | o motor ganhou: melhor remedida de 0,842 contra 1,452 | empatou com um sorteio que mantém os 19 comparadores (0,8418 contra 0,8417); o mesmo binário variou cerca de 6% entre processos | `09_provas_independentes/provas/motor_aqui/` |
| Na bateria de 192 casos de máquinas de estados finitos, 1.152 formulações contra 17.588 do CEGIS com poda | a primeira máquina da fórmula, 28/09/2026 | menos formulações em todos os 192 casos, mediana de 19 vezes por caso; as mesmas 82 máquinas do CEGIS com poda; os 192 vereditos da fórmula confirmados pelo z3, com 0 discordâncias | "15 vezes" vale só contra o CEGIS com poda (14,0 contra o sem poda, que parou 72 vezes no limite de nós); a unidade difere entre os métodos: em chamadas ao verificador a vantagem é de 1,25 vez, e em tempo, de 1,04 vez; 48 das 82 soluções são triviais (1 estado lendo `s_autorizado`); a bateria e o CEGIS são implementações próprias, e o código deles não está aqui | `06_evidencias/cegis_e_z3/` |
| Compressão sem perda de uma tabela de métricas: o melhor codec único ficou 59 vezes menor que o CSV e 15,5% menor que a melhor alternativa genérica, em 23 dias retidos | a Máquina do Dever-Ser 4.3.1 sem mudança, mais busca exaustiva, 18/10/2026 | o melhor codec único foi achado por busca exaustiva dentro do método | a máquina não cumpriu o D e terminou atrás do melhor codec único; na versão 3, também atrás do sorteio cego | `09_provas_independentes/provas/codec/` |
| Nenhum candidato cumpriu D | a C★3, 04 e 05/10/2026 | a Máquina do Dever-Ser 4.3.1 aplicada a um D de aprendizado contínuo | a pasta é o código para reproduzir a busca, não um resultado; os registros dessa corrida não estão neste repositório | `08_c_estrela_3/` |
| As premissas de um pequeno ser de teste simulado, calculadas à mão a partir do D, cada uma com a previsão impressa antes da vida | a conta 15, 26/09/2026 | na premissa 1b, a previsão foi de 12 acendimentos errados em 4.110, e a vida mediu 24, 9 e 12 com 2, 4 e 6 horas | várias previsões que caíram ficaram fora do texto (lista em `07_conta_15/A_CONTA_15.md`); nas premissas 3 e 4 a previsão é texto fixo do roteiro; o corpo inteiro não aprendeu; os registros não têm carimbo de tempo | `07_conta_15/` |

**Onde está cada número:**
- **Ordenação de 29/09:**
  - os ciclos, a razão, o ruído e a correção estão em `06_evidencias/ordenacao_29-09/01_resultado_8_elementos/rede_vencedora.json`;
  - as 7 gerações, os 384 avaliados, os 581,7 s e as decisões da IA no lugar do criador estão em `.../corrida_motor8/estado.json`;
  - os dois critérios da razão, os três candidatos dentro da resolução e os 48 vereditos do ledger estão em `09_provas_independentes/verif/VERIF_ordenacao.md`, seções 2 e 3.
- **Ordenação nos Intel e o motor contra o sorteio:** `09_provas_independentes/provas/b1/`, `RESUMO_alternativas.md` e `motor_aqui/RELATORIO.md`.
- **CEGIS:**
  - os totais estão em `06_evidencias/cegis_e_z3/bateria_dse_v4/resumo.json`;
  - o z3 está em `auditoria_z3.json`;
  - as razões por caso, as unidades, os 72 cortes e as 48 soluções triviais estão em `09_provas_independentes/verif/VERIF_cegis.md`.
- **Codec:** `09_provas_independentes/provas/codec/RESULTADO_codec.md`.
- **Conta 15:** os registros estão em `07_conta_15/registros/`; a conferência deles está em `09_provas_independentes/verif/VERIF_outros.md`, seção 1.

## As datas

A única data com garantia de terceiro neste repositório é a do commit `f571ac7`, assinado pelo GitHub em 16/10/2026 às 21:00:02 (-03). Como cada commit carrega o hash do anterior, ela garante que todo o conteúdo dos commits anteriores já existia nesse momento. As datas anteriores vêm de registros da própria máquina e de textos do autor (`09_provas_independentes/verif/VERIF_outros.md`, seção 4).

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

O programa tem a vencedora e a referência idênticas às medidas em 29/09. O programa que rodou naquele dia media também a versão AVX2, que não está neste arquivo.

A razão muda com o processador, e a própria saída mostra quanto. Na verificação independente, ela foi:
- de 0,960 a 0,961 num Xeon de 2,1 GHz;
- de 0,990 a 0,993 num Xeon de 2,8 GHz.

## Glossário

Os termos próprios, com a definição que o repositório dá e o termo mais próximo na área. A definição completa de cada um está na fórmula (`02_formula`, seções 2, 4 e 9) e nos LEIA-ME citados. Para "seleção selecionada" e "catraca" não há termo exato na área, e a tabela diz o que fica mais perto.

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
| seleção selecionada | a busca que corre sobre formulações, com cada fracasso registrado (decisão de 22/09/2026, `02_formula`, seção 23) | não há termo exato; é uma busca sobre formulações do problema, com registro dos fracassos |
| catraca | o mecanismo pelo qual o motor propõe uma mudança em si mesmo, adotada só se ganhar com folga nos moldes de desenvolvimento e nos de confirmação (laço 11) | não há termo exato; é uma auto-modificação aceita só se ganhar em problemas retidos, próxima de um portão de validação (em inglês, ratchet) |
| braço | cada fonte de filhos de um mesmo pai: a escrita às cegas, o operador, o sorteio e, na C★3, a escrita aprendida (`04_maquina_do_dever_ser_selecao/LEIA-ME.md`, `08_c_estrela_3/README.md`) | operador de variação |
| testemunha | um método conhecido, escrito na mesma linguagem do candidato e medido à parte, só para comparação; na C★3, SGD, EWC, CBP e SP | linha de base (baseline) |
| oráculo | uma conferência por outro método, independente de V; na ordenação, a conferência pelo princípio 0-1; na fórmula, o laço 12 | verificador independente |

## As pastas

| pasta | o que tem |
|---|---|
| `01_artigo/` | o artigo |
| `02_formula/` | a fórmula do dever ser, versão 4.3 com as emendas 6 a 13, na edição formal para publicação |
| `03_motor_de_29-09/` | o motor fechado da fórmula 4.0, como estava quando achou a rotina de ordenação de 29/09/2026 |
| `04_maquina_do_dever_ser_selecao/` | a Máquina do Dever-Ser 4.3.1 só com a seleção: as peças da 4.3.1 sem a rede que aprende |
| `05_tear_selecao/` | o Tear só com a seleção: a ilha em C e o leito em C, sem as ferramentas e sem a mente |
| `06_evidencias/` | a corrida da ordenação de 29/09, com o plano, os registros da máquina sem edição e o programa da vencedora e da referência; e a bateria de 192 casos contra o CEGIS |
| `07_conta_15/` | a conta 15 (26/09/2026), a origem do Sismo e do aprendiz de sinapses: como foi feita, as premissas, as previsões impressas antes de cada vida, os resultados, o código sem comentários e os registros de máquina |
| `08_c_estrela_3/` | a C★3: o código e as instruções para rodar |
| `09_provas_independentes/` | a verificação e os testes de 17 e 18/10/2026, com scripts, saídas e hashes |
| `MANIFESTO.sha256` | o sha256 de cada arquivo |

Cada pasta de máquina tem o seu LEIA-ME, com o que é, de onde veio e como rodar e conferir.

## O que se conferiu na montagem (16/10/2026, Windows 11, Python 3.13, numpy 2)

- **O motor de 29/09:** as 18 provas do compilador e as 8 do núcleo passaram; em 17/10 passaram também em Linux, na verificação independente (`09_provas_independentes/provas/test_*.txt`). O código é o do commit `7edc5af` do repositório de trabalho, o último antes da corrida de 8 elementos começar; esse repositório não é público.
- **A 4.3.1 só com a seleção:** as 11 provas passaram. As peças tiradas da 4.3.1 foram conferidas como idênticas às originais.
- **O Tear só com a seleção:** a mesma semente, rodada pelo pacote e pela árvore original do Tear, deu os mesmos recordes, byte a byte. Os registros dessa conferência não estão no repositório.
- **A C★3:** o código executável é idêntico ao original exceto pelas cadeias de texto de saída reescritas: a conferência comparou a árvore sintática de cada arquivo Python com essas cadeias apagadas, e o C++ sem comentários. Os textos de saída que citavam pessoas foram reescritos em forma neutra. As provas da C★3 passaram no Windows, inclusive a V da busca e a calibração de V, que usam a V real: perturbação, sonda, V repartida, condutor v2, coletor, V da busca e calibração. A prova da V compartilhada só roda em Linux.
- **Os comentários de código que transcreviam conversas** foram reescritos como decisões formais na C★3 e em parte das outras pastas. Nas pastas 03, 04 e 05 ainda há comentários e docstrings, e alguns, na 05, ainda citam conversas (`09_provas_independentes/verif/VERIF_outros.md`, seção 5).
- **Nenhum endereço de servidor, chave ou senha** está no pacote. Há caminhos de disco do servidor (`/home/iro/...`).

## O que não está aqui

As pastas 03, 04 e 05 vão sem aprendiz: ficaram de fora a rede da 4.3.1, a mente e as ferramentas do Tear e o aprendiz da variação do motor. A C★3 vai com o aprendiz, como rodou. Não estão aqui os manuais, os planos de construção, os registros de trabalho, as cópias do servidor de pesquisa, o código da bateria do CEGIS nem os registros da corrida da C★3 e da catraca.

## Licença

O código e os documentos deste repositório estão sob a licença MIT (`LICENSE`).
