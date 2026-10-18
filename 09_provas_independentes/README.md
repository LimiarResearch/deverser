# Provas independentes (17 e 18/10/2026)

Esta pasta traz o trabalho de uma sessão separada, feita em 17 e 18/10/2026 com autorização de Gabriel Santos. Ela fez duas coisas:
- conferiu as alegações do repositório pelos próprios registros (`verif/`);
- rodou o código em outras máquinas, com testes novos (`provas/`).

Os arquivos estão como a sessão os entregou, com os scripts, as sementes, as saídas e os hashes. Os caminhos citados dentro dos relatórios são os da máquina daquela sessão.

**O resumo:**
- Os números do repositório conferem com os registros e são coerentes entre si.
- Várias frases diziam mais do que os registros mostram. As correções estão no README da raiz, no artigo e nos LEIA-ME.
- Os testes novos não sustentam vantagem de busca da máquina sobre alternativas simples.

## O que cada subpasta mostra

### `provas/test_compilador.txt` e `provas/test_nucleo.txt`

As provas do motor de 29/09 (`03_motor_de_29-09/testes`) passaram em Linux, com Python 3.13 e numpy 2.5.3: 18 de 18 no compilador e 8 de 8 no núcleo.

### `provas/b1/`: a ordenação de 29/09 em dois processadores Intel

O programa publicado da ordenação, compilado como no LEIA-ME e rodado 5 vezes com `./rotina 21`:

| máquina | razão contra a referência, nas 5 rodadas | arquivo |
|---|---|---|
| Intel Xeon de 2,1 GHz (servidor A, 17/10) | de 0,960 a 0,961 | `b1/saida_host_A_17-10.txt` |
| Intel Xeon de 2,8 GHz, Cascade Lake (servidor B, 18/10) | de 0,990 a 0,993 | `b1/saida_5_rodadas.txt` |

A rotina errou 0 dos 16.777.216 vetores em todas as rodadas. O ganho da vencedora de 29/09 depende do processador, também entre dois Intel, como o LEIA-ME da ordenação já previa.

### `provas/b2/`, `provas/b3/` e `provas/b4/`: a ordenação contra alternativas

Mesmo medidor do programa publicado. Cinco rodadas por servidor, cada uma num processo novo. Todas as rotinas foram conferidas nos 16.777.216 vetores de 0 a 7 e em 10 milhões de vetores int32 sorteados, com 0 erros. As medianas estão em `RESUMO_alternativas.md`; a razão é contra a rede escalar de referência.

| rotina | servidor A (`b3/`) | servidor B (`b4/`) |
|---|---|---|
| rede bitônica em AVX-512, versão de livro | 0,505 | 0,570 |
| rede bitônica em AVX2, versão de livro | 0,550 | 0,619 |
| código vetorial achado pelo motor de 29/09 nesse meio (Batcher e rede ótima, AVX2) | 0,568 e 0,570 | 0,639 e 0,650 |
| referência vetorial da ferramenta do motor | 0,679 | 0,783 |
| vencedora de 29/09 | 0,959 | 0,995 |
| x86-simd-sort da Intel | 3,610 | 3,654 |
| std::sort (libstdc++ 13) | 9,068 | 8,939 |

Nesses dois meios, o motor escolheu código vetorial. As contas abaixo saem das medianas da tabela:
- o código do motor foi de 35% a 43% mais rápido que a rede escalar escrita à mão;
- foi de 14 a 16 vezes mais rápido que o std::sort, que ficou cerca de 9 vezes mais lento que a rede escalar;
- a rede bitônica de livro em AVX-512, que usa instruções mais largas que as do motor, foi de 11% a 12% mais rápida que o código do motor;
- a bitônica de livro em AVX2, a mesma família de instruções do motor, foi de 3% a 5% mais rápida.

### `provas/motor_aqui/`: o motor contra o sorteio cego, no mesmo orçamento

O relatório completo é `motor_aqui/RELATORIO.md`. O motor de 29/09 rodou com o mesmo D e o mesmo medidor no Xeon de 2,1 GHz, contra dois sorteios com o mesmo orçamento de 726 candidatos:

| comparação | melhor remedida, mediana de 5 processos | leitura |
|---|---|---|
| motor contra sorteio cego na mesma L | motor 0,844 (a escolhida) e 0,842 (a melhor); sorteio 1,452 | a seleção ganhou; o sorteio achou 1 rede que ordena e nenhuma que cumpre o D |
| motor contra sorteio que mantém os 19 comparadores | 0,8418 contra 0,8417 | empate; os melhores dos dois são os mesmos dois binários |

O que a seleção acrescentou foram duas escolhas discretas: manter os 19 comparadores e usar a troca `simd_imediato`. O sorteio cego acerta as duas com cerca de 0,07% de chance por sorteio. O relatório estima, por cálculo e não por medida, cerca de 30% de chance de um sorteio cego empatar com o motor no mesmo orçamento.

O mesmo binário variou cerca de 6% entre processos. É mais que o ruído que o medidor calcula dentro do processo, que fica perto de 0,1%. Nesse meio, a vencedora de 29/09 mediu 0,964 contra a referência escalar e 1,41 contra a referência vetorial, e não cumpriu o D.

### `provas/codec/`: a Máquina 4.3.1 num D de compressão sem perda

O relatório é `codec/RESULTADO_codec.md`. A Máquina do Dever-Ser 4.3.1 só com a seleção, sem mudança, recebeu um D de compressão sem perda para uma tabela de métricas, em duas versões da codificação (v2 e v3).

| quem | dias de desenvolvimento, em vezes o melhor codec único (v2) | v3 |
|---|---|---|
| melhor codec único da L, por busca exaustiva | 1,00 | 1,000 (a subida simples partindo dele) |
| a máquina | cerca de 1,22 | 1,084 |
| colunar int32 com xz -9e | 1,24 | |
| sorteio estruturado | cerca de 1,34 | 1,028 |
| sorteio cego | cerca de 1,86 | 1,060 |

O D, que pedia no máximo 0,95 do melhor codec único, não foi cumprido por ninguém. A máquina terminou atrás do melhor codec único; na v3, também atrás do sorteio cego.

Nos 23 dias retidos, o melhor codec único ficou 59 vezes menor que o CSV e 15,5% menor que a melhor alternativa genérica, o colunar int32 com xz -9e (1.180.998 contra 1.398.416 bytes). Esse resultado é do método, com D, Π e V fixos e busca exaustiva, e não da seleção.

A tabela de dados (`itens.csv`, sha256 `ebbd0256ee7584c1948121c67bdbfe927eaf0e0aaae00e923c5d71525ba3fce2`) não está aqui. Ela sai da empresa simulada de outro projeto.

### `verif/`: as três verificações pelos registros

- **`VERIF_ordenacao.md`:** a corrida de 29/09. A rede foi conferida de forma independente nos 16.777.216 vetores, e os números conferem com o ledger. O relatório lista as frases que diziam mais do que os registros mostram.
- **`VERIF_cegis.md`:** a bateria de 192 casos e a auditoria do z3. Os números conferem caso a caso. A razão de "15 vezes" depende da unidade e da variante comparada.
- **`VERIF_outros.md`:** a conta 15, a C★3, o artigo, o README e as datas.

Os scripts de cada verificação estão nas subpastas `verif/ordenacao/`, `verif/cegis/` e `verif/outros/`, com as saídas. O chaveiro temporário do GPG usado para conferir a assinatura do commit `f571ac7` foi deixado de fora. A chave pública do GitHub usada está em `verif/outros/webflow_ks.asc`.
