# C★3

A C★3 é a Máquina do Dever-Ser 4.3.1 aplicada a um D de aprendizado contínuo, o Ser: um programa que aprende coisas novas sem rodadas de treinamento e sem guardar todo o histórico. Esta pasta traz o código da C★3 e as instruções para rodá-la.

## O problema

- **D:** 28 cláusulas e 116 predicados, julgados em 15 vidas de quatro famílias (sequências, linguagem, trilhas e agentes). O prazo por candidato é de 440 s.
- **O candidato:** uma foto atômica de 3.316 bits, que descreve um programa de 16 seções de 8 nós e 32 operações.
- **As testemunhas:** SGD, EWC, CBP e SP, os métodos conhecidos de aprendizado contínuo, escritos na mesma linguagem do candidato. Elas são medidas à parte, para comparação, e servem também de doadoras de material para a busca.

## A busca

A C★3 é a busca da Máquina do Dever-Ser 4.3.1, com a rede que lê, julga e escreve as fotos, e com estes acréscimos:

- **Um meio que perturba:** cada peso das vidas é multiplicado por 1 + eps·u depois de cada passo, com eps = 2^-17 e u tirado de um contador, idêntico em numpy e em C++.
- **A piscina de vidas:** 24 conjuntos de vidas de sementes declaradas, com os oráculos calculados antes da corrida, mais 3 sementes de desenvolvimento.
- **A sonda:** uma assinatura do comportamento do candidato que decide em qual conjunto da piscina ele vive.
- **A V da busca v2:** a pior de 3 medidas para tudo o que decide (pai, molde, doador, recorde), o recorde só com margem e um sal que gira por época.
- **As doadoras:** as testemunhas entram na colheita das sementes como doadoras, nunca como pais.
- **O braço gêmeo:** uma cópia do braço cego, que mede o piso de ruído do crédito por fonte.
- **O coletor em sombra:** gasta até 20% de V em experimentos pareados de composição, sem alterar a busca.
- **A operação longa:** a parada pelo arquivo `PARAR`, a retomada pela mesma pasta e a migração declarada do hash de V.

## Requisitos

- Linux x86-64 (a V compartilhada entre os processos usa `fork`; no Windows a máquina usa a V repartida, mais lenta);
- Python 3.11 ou mais novo e numpy 2;
- g++ com C++17 (o núcleo do interpretador é compilado na primeira execução).

```bash
pip install -r requirements.txt
```

Variáveis de ambiente: `OPENBLAS_NUM_THREADS=1` e `SER_BACKEND=cpp`. A pasta do núcleo compilado pode ser escolhida com `SER_CPP_CACHE`.

## Como rodar

Os comandos rodam de dentro desta pasta. Nada é lançado sem `--autorizacao`, com a frase e a data de quem autorizou a corrida, que fica gravada na declaração.

**A corrida:**

```bash
python -B -m experimentos.condutor_do_ser --modo corrida --backend cpp --v2 --processos 6 --saida <pasta> --config config_c3.json --autorizacao "<quem autorizou e quando>"
```

**A fumaça,** uma corrida curta de teste, com fusível padrão de 600 s:

```bash
python -B -m experimentos.condutor_do_ser --modo fumaca --backend cpp --v2 --processos 2 --saida <pasta> --config config_c3.json --autorizacao "<quem autorizou e quando>"
```

**Antes da busca,** a máquina calibra V nos 28 conjuntos de vidas, o que leva cerca de 10 minutos num servidor de 6 núcleos.

**A retomada:** o mesmo comando, com a mesma `--saida`.

**Parar:** criar o arquivo `<pasta>/PARAR`. A corrida para no fim da geração em curso.

**O selo do banco da prova cega:** o banco retido é selado por hash antes da busca. Se o selo não conferir no seu ambiente, refaça-o antes de rodar:

```bash
python -B -m experimentos.banco_da_prova_cega conferir
python -B -m experimentos.banco_da_prova_cega selar
```

## A configuração

`config_c3.json` é a configuração da corrida de 04/10/2026. A chave `doadoras_de_corridas` aponta para corridas anteriores no servidor de pesquisa; em outra máquina esses caminhos não existem, e nenhuma doadora dessas corridas entra, sem erro. Uma chave desconhecida faz a configuração recusar a corrida.

## Os arquivos de uma corrida

| arquivo | o que guarda |
|---|---|
| `estado.json` | o estado a cada geração: contadores, crédito por braço, curvas, hash de V, parada, calibração, testemunhas, catraca e gasto de V por finalidade |
| `resumo.json` | o resumo no fechamento |
| `declaracao.json` | por laço da fórmula, o que foi exercitado e o que não foi, com o motivo |
| `log_rodadas.jsonl` e `log_eventos.jsonl` | uma linha por rodada e por evento |
| `fotos/` e `edicoes/` | o arquivo de fotos e de edições, só de acréscimo |
| `testemunhas.json` | as 4 testemunhas medidas à parte |
| `candidata_<k>.json` | só quando uma foto cumpre D; a corrida para e espera o Ok humano |

## As provas

Cada prova roda com `python -B testes/<nome>.py`, de dentro desta pasta.

| prova | o que garante |
|---|---|
| `test_c3_perturbacao.py` | o fator de perturbação é o mesmo nos dois motores |
| `test_c3_sonda.py` | formas idênticas dão a mesma assinatura, e as testemunhas dão assinaturas distintas |
| `test_c3_v_da_busca.py` | a escolha dos conjuntos é determinista e muda com o sal; a piscina não usa as sementes proibidas |
| `test_c3_condutor_v2.py` | com mundos de teste, a corrida confirma, vira o sal, grava e retoma |
| `test_c3_calibrar_v2.py` | a calibração de V numa semente; precisa do g++ |
| `test_c3_v_compartilhada.py` | a V compartilhada dá a mesma medida que a V de um dono por conjunto (só em Linux) |
| `test_c3_v_repartida.py` | o roteamento entre processos não muda nenhuma medida |
| `test_coletor_de_intervencoes.py` | o coletor em sombra não muda a busca e gasta entre 10% e 30% de V |
| `test_estresse_ser_cpp.py` | o estresse dos dois motores com a perturbação (com a variável `ESTRESSE_EPS`) |

## Sobre esta versão

O código é o da C★3 na sua última versão, de 05/10/2026, sem os comentários. O código executável é idêntico ao original, conferido pela árvore sintática de cada arquivo Python e pelo código C++ sem comentários. Alguns textos que o programa grava nas declarações foram reescritos em forma neutra. Como o hash de V é calculado sobre os arquivos-fonte, o hash desta versão difere do da corrida de 04/10/2026.

Ficaram de fora o manual, os planos de construção, o visor e os registros da corrida. A corrida de 04 e 05/10/2026 parou com estado retomável depois de 15 rodadas, 3 gerações, 1.488 fotos e 2.033 medidas de V, e nenhuma foto cumpriu D.
