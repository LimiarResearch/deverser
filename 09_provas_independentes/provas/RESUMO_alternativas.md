# A ordenação de 8 elementos neste Intel Xeon, contra as alternativas (17/10/2026)

Máquina: Intel Xeon 2,1 GHz (máquina virtual), AVX-512, 4 núcleos, Linux, g++ 13.3.0, `-O2 -march=native`. Mesmo medidor do programa
publicado em 06_evidencias/ordenacao_29-09 (blocos alternados de 256 vetores, tiques do rdtsc, mediana das razões por bloco, 21
repetições). Cada rotina conferida nos 8^8 = 16.777.216 vetores de 0 a 7 e em 10 milhões de vetores int32 sorteados (com extremos)
contra o std::sort: 0 erros em todas, nas 5 rodadas. Cinco rodadas, cada uma num processo novo (b3/rodada_1..5.jsonl).

| rotina | razão contra a rede escalar de referência: mediana [mín; máx] |
|---|---|
| rede bitônica em AVX-512 (versão de livro, 3 instruções por nível) | 0,505 [0,505; 0,516] |
| rede bitônica em AVX2 (versão de livro) | 0,550 [0,550; 0,553] |
| achada pelo motor de 29/09 neste Xeon: rede de Batcher, simd_imediato | 0,568 [0,568; 0,599] |
| achada pelo motor de 29/09 neste Xeon: rede ótima, simd_imediato | 0,570 [0,569; 0,595] |
| referência vetorial da própria ferramenta do motor | 0,679 [0,679; 0,680] |
| vencedora de 29/09 (Zen 1) | 0,959 [0,958; 0,960] |
| cópia da referência escalar (controle) | 1,000 [1,000; 1,001] |
| x86-simd-sort da Intel (6e059b1, 09/10/2026), qsort de 8 elementos | 3,610 [3,602; 3,624] |
| std::sort (libstdc++ 13) | 9,068 [7,977; 9,163] |

Arquivos: b3/alternativas3.cpp (sha256[:24] 027d98fce59813037d01f4b4), b3/motor_simd.inc (2b24f3804d0bdb2b52e2d5d7, gerado pela
própria ferramenta do motor, compilador/ferramenta_ordenacao.py, _simd), b3/redes_29-09.inc (b80be267bfacabaedf884104, copiado do
programa publicado). A corrida do motor e o nulo estão em motor_aqui/RELATORIO.md.

## O mesmo, no servidor B (18/10/2026): Intel Xeon @ 2.80GHz, família 6, modelo 85, passo 7 (Cascade Lake), AVX-512

O contêiner mudou de servidor entre os dias. Mesmo programa (b4/, recompilado aqui), 5 rodadas em processos novos, 0 erros em todas.

| rotina | razão contra a rede escalar: mediana [mín; máx] |
|---|---|
| rede bitônica em AVX-512 (versão de livro) | 0,570 [0,569; 0,575] |
| rede bitônica em AVX2 (versão de livro) | 0,619 [0,619; 0,619] |
| achada pelo motor no servidor A: rede de Batcher, simd_imediato | 0,639 [0,639; 0,652] |
| achada pelo motor no servidor A: rede ótima, simd_imediato | 0,650 [0,645; 0,656] |
| referência vetorial da ferramenta do motor | 0,783 [0,781; 0,783] |
| vencedora de 29/09 | 0,995 [0,994; 1,000] |
| cópia da referência escalar (controle) | 0,999 [0,999; 1,000] |
| x86-simd-sort da Intel | 3,654 [2,654; 3,691] |
| std::sort | 8,939 [8,902; 9,058] |

O programa publicado da ordenação, neste servidor (b1/saida_5_rodadas.txt): razão de 0,990 a 0,993. No servidor A tinha dado de 0,960
a 0,961 (b1/saida_host_A_17-10.txt). O ganho da vencedora de 29/09 depende do processador também entre dois Intel.
