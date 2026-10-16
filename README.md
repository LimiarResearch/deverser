# A engenharia reversa do acaso: os arquivos

Limiar Research, Gabriel Santos, 16 de outubro de 2026.

Este pacote acompanha o artigo "A engenharia reversa do acaso". Ele traz a fórmula, as máquinas só com a seleção, sem os aprendizes, e as evidências dos resultados do artigo.

| pasta | o que tem |
|---|---|
| `01_artigo/` | o artigo |
| `02_formula/` | a fórmula do dever ser, versão 4.3 com as emendas 6 a 13, na edição formal para publicação |
| `03_motor_de_29-09/` | o motor fechado da fórmula 4.0, exatamente como rodou quando achou a rotina de ordenação 4,3% mais rápida (29/09/2026) |
| `04_maquina_do_dever_ser_selecao/` | a Máquina do Dever-Ser 4.3.1 só com a seleção: as peças da 4.3.1 sem a rede que aprende |
| `05_tear_selecao/` | o Tear só com a seleção: a ilha em C e o leito em C, sem as ferramentas e sem a mente |
| `06_evidencias/` | a corrida da ordenação de 29/09, com o plano, os registros da máquina sem edição e o programa medido, pronto para compilar; e a bateria de 192 casos contra o CEGIS |
| `07_conta_15/` | a conta 15 (26/09/2026), a origem do Sismo e do aprendiz de sinapses: como foi feita, as premissas, as previsões registradas antes de cada vida, os resultados, o código sem comentários e os registros de máquina |
| `MANIFESTO.sha256` | o sha256 de cada arquivo |

Cada pasta de máquina tem o seu LEIA-ME, com o que é, de onde veio e como rodar e conferir.

## O que se conferiu na montagem (16/10/2026, Windows 11, Python 3.13, numpy 2)

- **O motor de 29/09:** as 18 provas do compilador e as 8 do núcleo passaram. O código é o do commit `7edc5af` do repositório de trabalho, o último antes da corrida de 8 elementos começar.
- **A 4.3.1 só com a seleção:** as 11 provas passaram. As peças tiradas da 4.3.1 foram conferidas como idênticas às originais.
- **O Tear só com a seleção:** a mesma semente, rodada pelo pacote e pela árvore original do Tear, deu os mesmos recordes, byte a byte.
- **Os comentários de código que transcreviam conversas** foram reescritos como decisões formais. Nenhuma linha executável mudou: a árvore sintática de cada arquivo Python e o código C sem comentários foram comparados com os originais, e as provas rodaram de novo depois da mudança.
- **Nenhum endereço de servidor, chave ou senha** está no pacote.

## O que não está aqui

Nenhum aprendiz. Ficaram de fora a rede da 4.3.1, a mente e as ferramentas do Tear, o aprendiz da variação do motor e o desafio do Ser. Não estão aqui as cópias do servidor de pesquisa nem a bancada de laboratório. O artigo publica o sha256 delas, e o conteúdo fica guardado.
