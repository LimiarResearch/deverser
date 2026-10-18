# Verificação da ordenação de 8 elementos (deverser, corrida de 29/09/2026)

Repositório: LimiarResearch/deverser, ramo main, commit a28eec9, cópia somente leitura em `main_ro`. Os 81 arquivos de `03_motor_de_29-09/` e `06_evidencias/ordenacao_29-09/` conferem com o `MANIFESTO.sha256`. A cópia não tem histórico git.

Método: só leitura. Nenhum arquivo do repositório foi executado, compilado ou importado. As conferências foram feitas por scripts meus (lista no fim), rodados com `python3 -I`, recebendo os arquivos do repositório como dados. O fonte da ferramenta de medida foi lido só com `ast.parse`, para extrair as constantes de texto `MOLDE` e `VARIANTES`, sem executar nada.

## 1. Resumo

O núcleo da alegação se sustenta. A rotina vencedora é a mesma rede de 19 comparadores e profundidade 6 da referência, só com outra ordem dentro de cada camada e com a troca feita na memória. Ela ordena corretamente: conferi de forma independente as 256 entradas 0-1, as 40.320 permutações e os 16.777.216 vetores de 0 a 7. Os números da tabela são os que o ledger registrou. A cadeia de hashes interna dos registros fecha: diário, respostas, D, Π e modelo.

Achei inconsistências e lacunas, nenhuma delas sobre a correção da rede:

1. **O `.cpp` publicado não é "o programa exato que foi compilado e medido".** O `fonte_sha256_24` de `rede_vencedora.json` (`40cc63c9f9df2ba7bf0cecd7`) é o hash do próprio `.cpp` publicado. Mas o programa medido tinha a referência AVX2 dentro do laço de tempo e imprimia `razao_vs_simd`, `razao_vs_melhor` e `ciclos_simd`. O ledger tem esses campos e as métricas da corrida os exigem. O `.cpp` publicado não tem essas partes: são 24 linhas de diferença. Os corpos da vencedora e da referência são idênticos byte a byte. O que muda é o arnês.
2. **A razão 0,957 e a conta 22,273/23,359 = 0,9535 vêm de dois estimadores diferentes.** Os dois são coerentes entre si. A tabela, porém, mistura os dois: a linha da vencedora usa a mediana das razões por bloco, e a linha do AVX2 usa a razão das medianas.
3. **O ruído de 0,46% e o "1,000" da referência contra a cópia são valores medidos durante a busca, no processo da vencedora.** O LEIA-ME os apresenta como a conferência feita antes. A conferência registrada antes da busca deu `ruido_medido` 0,0113 e `desvio_ref_contra_ref` 0,0053. A comparação com o AVX2 (44,8 contra 23,4) também vem do processo da vencedora, durante a busca, e não de antes.
4. **O ledger tem 48 avaliações, não 384.** São só as da população final. As outras 336 estão apenas contadas.
5. **O D foi formulado e confirmado pela IA em nome do criador.** O limite de 3% foi posto pela IA, e houve 0 pedidos ao criador. O plano diz que o D foi "confirmada pelo autor", e o LEIA-ME não menciona quem confirmou.
6. **Pela resolução declarada no próprio D (1%), três candidatos empatam em 0,96:** 0,95682, 0,95727 e 0,96393. O motor não os separou. O escolhido foi o primeiro da lista. A margem sobre o segundo é de 0,00045.
7. **Não há prova nos registros para "Zen 1", "gcc 13", "std::sort cerca de 6 vezes", "D de 15% não cumprido" e "6 elementos com violação 0,062".** Para o caso de 6 elementos, o `02_formula` dá outro relato.

## 2. Tabela de alegações e vereditos

Abreviações: E = `01_resultado_8_elementos/corrida_motor8/estado.json`; L = `ledger.jsonl` (a vencedora é o veredito `seq` 3); RV = `rede_vencedora.json`; FO = `03_motor_de_29-09/compilador/ferramenta_ordenacao.py`.

| # | Alegação (LEIA-ME) | O que os registros mostram (arquivo, campo, valor literal) | Veredito |
|---|---|---|---|
| 1 | 9,7 minutos e 384 candidatos | E `criacoes[0].calculo_antes.concorrencia.parada`: `"avaliados": 384, "segundos": 581.7` (581,7/60 = 9,695 min); `codigos_que_concorreram`: 384; `diario.jsonl`: 8 eventos `geracao` com `"avaliados": 48` (soma 384) | Confirmado |
| 2 | População 48 | E `sigma_da_concorrencia.populacao`: 48. Pela regra declarada: int(max(2, min(16, 604800/4,403/20))) = 16 lotes, vezes `paralelo_no_alvo` 3 = 48 | Confirmado |
| 3 | 7 gerações | `parada.geracoes`: 7; `concorrencia.geracoes`: 8 (conta o lote inicial). 48 + 7 × 48 = 384 = 8 lotes no diário | Confirmado (7 gerações de filhos mais a população inicial) |
| 4 | 581,7 s | `parada.segundos`: 581.7. A criação levou 586,14 s (`criacoes[0].segundos`) e o motor 590,0 s (`contadores.segundos_motor`). O roteiro mostra 02:31:44 `passo` e 02:41:30 `desfecho`, ou seja, 586 s | Confirmado |
| 5 | Parada pela fronteira igual por 3 gerações | `parada.motivo`: "a primeira fronteira ficou igual por 3 gerações seguidas", `sem_melhora`: 3. Pelo código (`gerar.nsga2` e `motor._concorrencia`), a fronteira é comparada com a razão arredondada a 0,01. "Igual" quer dizer que nenhum candidato válido chegou a 0,955 ou menos | Confirmado, com a nuance da resolução |
| 6 | Desfecho "solução: melhor encontrado e verificado" | E `desfecho.tipo`: "solucao"; `otimalidade`: "melhor encontrado e verificado; não demonstrado como o melhor, porque parte de L foi amostrada" | Confirmado |
| 7 | AMD EPYC de 1ª geração (Zen 1), 6 núcleos, 3 por problema, 12 GB | `problema.json` `alvos[0].descricao`: "a VPS: AMD EPYC, 3 dos 6 núcleos para este problema" (texto declarado, não medido). `numeros.cpus`: 6 "núcleos lógicos" (os.cpu_count). `ram_total_mb`: 11960 MiB. `paralelo_no_alvo`: 3. O modelo do processador não foi medido em nenhum registro, e "Zen" não aparece em nenhum registro | 6 núcleos lógicos, cerca de 12 GB e 3 em paralelo: confirmados. "EPYC": só declarado. "Zen 1": não verificável |
| 8 | gcc 13, declarado por caminho e sha256, `-O2 -march=native` | Em FO, `_gxx()` exige `FERRAMENTA_GXX` e `FERRAMENTA_GXX_SHA256` e confere o sha256 antes de compilar. As flags no código são `-O2 -march=native -std=c++17 -falign-functions=64 -falign-loops=64`. Caminho, sha256 e versão não estão gravados em nenhum registro da corrida. "gcc 13" aparece só em RV `compilacao`, texto escrito depois | Mecanismo e flags: confirmados no código. Versão 13: não verificável |
| 9 | Referência: rede ótima de 19 comparadores, troca em registradores | RV `rede_de_referencia` (19 pares), `troca_da_referencia`: "ternario", `referencia_em_registradores`: true; `refe_` no `.cpp` usa x0..x7 | Confirmado (conferido também pelo meu script) |
| 10 | std::sort cerca de 6 vezes mais lento, medido antes da corrida | L seq 3: `ns_std_sort` 104.517 ns, contra `ciclos_referencia` 23.359 em tiques do TSC. Nas 48 medidas, `ns_std_sort` vai de 80,718 a 130,29 ns (mediana 87,02). Converter tiques em ns exige a frequência do TSC, que não foi gravada. Um fator 6 implicaria um TSC de 1,34 GHz (números da vencedora) ou 1,74 GHz (medianas). A 2,0 GHz, o fator seria 6,9 (medianas). Não há registro de medida antes da busca | Não verificável (ordem de grandeza plausível, provavelmente subestimada) |
| 11 | AVX2 cerca de 2× mais lento (44,8 contra 23,4 ciclos), medido antes da corrida | L seq 3: `ciclos_simd` 44.762, `ciclos_referencia` 23.359. São medidas do processo da vencedora, feitas durante a busca (entre 02:31:44 e 02:41:30). Nas 48 medidas, `ciclos_simd/ciclos_referencia` vai de 1,624 a 1,985 (mediana 1,818) | Números confirmados. "Antes da corrida": inconsistente com os registros |
| 12 | O D com duas cláusulas: correta em todos os vetores; pelo menos 3% mais rápida, com resolução de 1% | E `D.clausulas`: `r_correto` (erro_de_ordenacao <= 0), `r_mais_rapida` (razao_vs_melhor <= 0.97, escala 0.1) e dois objetivos, `o_tempo` (resolucao 0.01) e `o_tamanho`. Todas têm `"origem": "ia"` e `"confirmada_por": "ia"`, com a justificativa "o pedido de Gabriel de 29/09; o limite de 3% foi posto pela IA pelo criador". `contadores.pedidos_criador`: 0 | Conteúdo confirmado (2 rígidas e 2 objetivos; a resolução de 1% é do objetivo). Omissão: quem formulou e confirmou foi a IA. O plano diz "confirmada pelo autor" |
| 13 | Medidor: blocos alternados de 256 vetores, revezando candidato, referência e cópia | FO e `.cpp`: `BL = 256, NB = 256`, ordem `(b + r) % 3`. No programa medido (FO), há um quarto passe em cada bloco, o AVX2 (`refs`), sempre depois dos três e sem rodízio | Confirmado, com essa diferença |
| 14 | Razão da referência contra a cópia: 1,000 | L seq 3: `razao_ref_contra_ref` 1.0, valor do processo da vencedora durante a busca. A conferência de antes (`respostas/007`) registrou `"desvio_ref_contra_ref": 0.0053`. Nas 48 medidas, o valor é exatamente 1.0 em 38. As outras vão de 0,99978 a 1,00431. O contador anda em degraus de cerca de 28 tiques (seção 7) | Valor confirmado. A atribuição ao "antes" é inconsistente. A resolução é limitada |
| 15 | Ruído de 0,46%, e por isso uma diferença de 3% é distinguível com folga | L seq 3: `ruido` 0.00457 (IQR/mediana das 21 repetições, no processo da vencedora). Antes da busca: `"ruido_medido": 0.0113`. Nas 48 medidas, o ruído vai de 0,00031 a 0,03823 (mediana 0,0073). Em 7 das 48 ele passa de 0,0113. Em 1 (seq 111) passa de 0,03 | O valor 0,46% é da vencedora durante a busca. A conferência de antes deu 1,13% + 0,53% = 1,66% < 3%, então a conclusão "3% distinguível" vale dentro do processo. Atribuição inconsistente |
| 16 | Correção nos 8^8 = 16.777.216 vetores e oráculo 0-1 que precisa concordar | No código, o laço passa por N^N vetores. L seq 3: `erro_de_ordenacao` 0.0. L seq 4: `oraculos` `[{"ok": true, "detalhe": "a medida concorda com o princípio 0-1 (a rede ordena)"}]`. O oráculo também exige `vetores_conferidos == n**n`. Meu script, independente: 0 falhas em 16.777.216 vetores (com a semântica exata do ternário), em 40.320 permutações e em 256 vetores 0-1 | Confirmado e reproduzido. Nota: o "oráculo independente" é um segundo método do mesmo autor (a IA), no mesmo executor (`avaliador: false`, `alternativo: null`) |
| 17 | Tabela: 23,359; 22,273; 0,957; 44,762; 1,916 | L seq 3: `ciclos_referencia` 23.359, `ciclos_por_vetor` 22.273, `razao_vs_rede` = `razao_vs_melhor` 0.95682, `ciclos_simd` 44.762. 1,916 = 44,762/23,359 (1,9163) | Valores confirmados. A tabela mistura dois estimadores (seção 3) |
| 18 | A vencedora usa a mesma rede ótima de 19 comparadores | Meu script: o mesmo multiconjunto de comparadores, as mesmas camadas como conjuntos (tamanhos 4, 4, 4, 2, 2, 3), cada camada com fios disjuntos. Só a ordem dentro das camadas muda. A troca é "ternario" nas duas. Registradores: false na vencedora, true na referência | Confirmado |
| 19 | Desfecho não demonstrado como o melhor, porque parte do espaço foi amostrada | `cobertura.busca_completa`: false; `amostrados`: ["rede", "a concorrência amostra L"] | Confirmado |
| 20 | Limite: D de 15% pedido logo depois e não cumprido | Não há registro no repositório. Só aparece em textos (este LEIA-ME e a seção 22 de `02_formula`, "Com D de 15%, não cumpriu") | Não verificável |
| 21 | Limite: 6 elementos com violação de 0,062, pedindo outra forma de linguagem | Não há registro de corrida de 6 elementos. A seção 22 de `02_formula` dá outro relato: "a tradução da rede ótima mediu 1,24 a 1,26 vez a referência (...) 0,92 (...). Nos dois casos, V não calibrou, e a corrida não começou". O 0,062 aparece só como valor de teste em `testes/test_compilador.py` | Não verificável. Os relatos divergem |
| 22 | Limite: efeito no cache de quem chama não medido e declarado como zero | E `modelo.numeros_excluidos.cache_de_instrucoes_de_quem_chama`: "premissa: ... não é medido nesta versão; vai declarado"; `efeito_no_meio`: {}; `ponto_fixo.voltas`: 0 | Confirmado |
| 23 | `.cpp`: "o programa exato que foi compilado e medido" (também no artigo) | RV `fonte_sha256_24` = `40cc63c9f9df2ba7bf0cecd7` = sha256[:24] do `.cpp` publicado. O fonte que FO gera para esta vencedora tem sha256[:24] `af8427daffe0407686dd5ec8` (minha reconstrução). Os dois diferem em 24 linhas: o publicado não tem `refs_` (AVX2), `razao_simd`, `melhor` nem a impressão de `razao_vs_simd`, `razao_vs_melhor` e `ciclos_simd`. A corrida exige esses campos (`metricas` em `respostas/004`) e o ledger os contém. O hash do fonte realmente medido não foi gravado | Inconsistente |
| 24 | `ledger.jsonl`: "o livro de cada avaliação" | 145 linhas: 1 `versoes` e 48 de cada tipo (`formulacao`, `veredito`, `evidencia`). São só os 48 da população final. `contadores.avaliacoes`: 48 | Inconsistente com a leitura "cada uma das 384" |
| 25 | Os arquivos da corrida são os registros da máquina, sem edição | Cadeia interna fechada (seção 6). Mas `exportacao` diz `{"ok": false, "erro": "NameError: name 'repr' is not defined"}`: o motor não exportou a vencedora, e RV e o `.cpp` foram feitos depois. O roteiro tem um trecho cortado no meio do JSON do desfecho. `intervencoes.jsonl` cita "experimentos/montar_desafio_motor.py", mas o conteúdo é o de `montar_ordenacao_motor.py` | Confirmado para os arquivos de `corrida_motor8/`. RV e o `.cpp` são posteriores |

## 3. A razão 0,957 contra 22,273/23,359 = 0,9535

Lendo o código do medidor (FO, constante `MOLDE`, e também o `.cpp` publicado), cada processo faz R = 21 repetições. Em cada uma, mede 256 blocos de 256 vetores com `__rdtsc`. Daí saem:

- `razao_vs_rede` = mediana, sobre as 21 repetições, da mediana, sobre os 256 blocos, de `tiques_cand / tiques_ref` do mesmo bloco. É a **mediana das razões por bloco**: 0,95682.
- `ciclos_por_vetor` = mediana dos 5.376 blocos do candidato (21 × 256, todos juntos) dividida por 256: 22,273, ou seja, 5.702 tiques. `ciclos_referencia` é o mesmo cálculo para a referência: 23,359, ou 5.980 tiques. Dividir um pelo outro dá a **razão das medianas**: 0,95351.
- `ruido` = (p75 − p25)/mediana das 21 medianas por repetição: 0,00457.
- `razao_vs_simd` = mediana das medianas de `tiques_cand / tiques_simd`: 0,49521. `razao_vs_melhor` = o maior entre `razao_vs_rede` e `razao_vs_simd`, que aqui é 0,95682.

As duas razões são estimadores diferentes do mesmo dado, e as duas estão certas pela sua definição. A diferença entre elas é de 0,0033. Nas 48 medidas do ledger, "mediana das razões menos razão das medianas" vai de −0,02308 a +0,00487 (mediana −0,0018). Na vencedora, a mediana das razões é a leitura mais conservadora: 4,3% de ganho, contra 4,65% pela razão das medianas.

A tabela do LEIA-ME mistura os dois critérios. A linha da vencedora usa a mediana das razões (0,957). A linha do AVX2 usa a razão das medianas (44,762/23,359 = 1,916). Pelo critério da vencedora, a linha do AVX2 daria cerca de 0,95682/0,49521 = 1,932. O artigo repete o problema: cita "22,27 contra 23,36 ciclos" ao lado de "4,3%", e quem fizer a conta acha 4,65%. Sugestão: uma nota na tabela explicando os dois critérios, ou uma coluna com a razão por bloco nas três linhas.

Há outro ponto. Com a resolução declarada no D (`o_tempo.resolucao` 0,01), 0,95682 arredonda para 0,96, e o motor trata 0,95682, 0,95727 e 0,96393 como iguais. Uma precisão de "4,3%" é mais fina do que o próprio D diz que a medida separa.

## 4. Prova independente da correção

Script: `verif/ordenacao/redes.py`; saída em `saida_redes.txt`. Os resultados:

- **Reconstrução.** Decodifiquei os genes do escolhido (E `criacoes[0].escolhido.formulacao`) pela regra documentada no decodificador da corrida: mantém os comparadores sem `rem_k` e ordena por (camada, `pri_k`, k), sobre a base "otima" da carga. O resultado é idêntico a `rede_vencedora`. Os genes `rem_` ativos (21, 23, 24 e 25) caem em índices maiores que 18 e não têm efeito numa base de 19 comparadores. A rede de referência da carga é idêntica a `rede_de_referencia`. Lidos do `.cpp`, os comparadores de `cand_` e `refe_` são idênticos a RV, e `refe2_` é idêntica a `refe_`.
- **(a) Princípio 0-1.** 0 falhas em 256, na vencedora e na referência.
- **(b) Permutações.** 0 falhas em 40.320, nas duas.
- **8^8.** 0 falhas em 16.777.216, nas duas. Testei com min/max e também simulando exatamente o ternário do C (`v[i] = a < b ? a : b; v[j] = a < b ? b : a`), conferindo a ordem e o multiconjunto. A versão AVX2 (permutação, min, max e mistura por camada), simulada nos vetores 0-1, também ordena.
- **(c) Tamanho e profundidade.** As duas têm 19 comparadores e profundidade 6, com camadas de 4, 4, 4, 2, 2 e 3 comparadores.
- **(d) Mesma rede.** As duas têm o mesmo multiconjunto de comparadores e as mesmas 6 camadas como conjuntos. Em cada camada os fios são disjuntos, então reordenar dentro dela não muda a função. A vencedora está em ordem de camada. Mudam só a ordem interna das camadas e o lugar da troca (memória em vez de registradores). O tipo de troca, "ternario", é o mesmo.

Camadas da referência: {(0,2),(1,3),(4,6),(5,7)}, {(0,4),(1,5),(2,6),(3,7)}, {(0,1),(2,3),(4,5),(6,7)}, {(2,4),(3,5)}, {(1,4),(3,6)}, {(1,2),(3,4),(5,6)}.

A referência é, de fato, uma rede de 19 comparadores e profundidade 6. Pela literatura (Knuth, TAOCP vol. 3, §5.3.4), 19 é o menor número de comparadores e 6 a menor profundidade para 8 entradas. Ela é ótima nas duas medidas, mas não é única: a rede de Batcher da própria carga ("batcher") também tem 19 comparadores e profundidade 6, e também passou nas três conferências. Uma confirmação a mais: no ledger, todas as 30 redes de 18 comparadores falham (`erro_de_ordenacao` > 0), o que bate com 19 ser o mínimo.

## 5. A ordem no tempo

Os carimbos estão todos em -03:00 e todos vêm do relógio da própria máquina.

| Hora (29/09) | Evento | Fonte |
|---|---|---|
| 02:31:33 | início (`iniciado`, `problema` ordenacao_8_motor_vps.json) | diário, roteiro |
| 02:31:34 a 02:31:35 | pedido e resposta de 001_formular_D e 002_confirmar_D | `pendentes/*.criado_em`, diário, roteiro |
| 02:31:35 a 02:31:38 | mapa de números (003, 005) e modelo m1 (004; `recebido_em` 02:31:37) | idem |
| 02:31:41 | modelo testado, 0 falhas; pedido 006_medir_alvo | diário |
| 02:31:42 | números do alvo medidos (`data` em E `numeros`) | E |
| 02:31:43 a 02:31:44 | 007_conferir_distinguibilidade respondido | diário |
| 02:33:01, 02:34:14, 02:35:28, 02:36:41, 02:37:52, 02:39:04, 02:40:19, 02:41:30 | os 8 lotes de 48, com intervalos de 71 a 75 s | diário |
| 02:41:30 | criação (586,14 s) e desfecho | diário, roteiro |

O que dá para afirmar:

- **D e distinguibilidade.** O D foi formulado e confirmado (02:31:34 a 02:31:35), e a distinguibilidade foi conferida (02:31:43 a 02:31:44), antes do primeiro lote (02:33:01). Os 77 s entre 02:31:44 e 02:33:01 batem com o lote de calibração de σ (4,4 s) mais 16 lotes de cerca de 4,4 s. As respostas 001 a 005 e 007 vêm de arquivos preparados antes, por `montar_ordenacao_motor.py` (`intervencoes.jsonl`: "resposta preparada pela IA pelo criador antes da corrida"). A 006 foi medida no alvo.
- **Medidor conferido antes.** Só em parte. A resposta 007 traz `ruido_medido` 0,0113 e `desvio_ref_contra_ref` 0,0053, números passados como argumento ao script de montagem (`sys.argv[1]` e `sys.argv[2]`). Os mesmos números aparecem para n = 6 e n = 8. A medida que os produziu não está no repositório. Além disso, um comentário em FO diz que a versão AVX2 "de 29/09 02h30" era 4 vezes mais lenta e foi corrigida. A forma final do medidor é, portanto, de minutos antes da corrida. Não dá para saber se a conferência de ruído foi feita com ela.
- **Plano.** `ORDENACAO_PLANO.md` não tem carimbo de máquina. Ele diz que foi escrito em 29/09 "antes de qualquer medida deste problema" e cita um estado "às 02h05". O conteúdo diverge do que rodou: previa n = 6 e depois 7 e 8; V pelas ordens fracas; calibração com as rotinas da AlphaDev; ponto fixo medido num laço maior; e a comparação com um evolutivo simples como "a prova da fórmula". Essa divergência é compatível com um plano escrito antes, mas não prova a data.
- **Commit.** "Commit 7edc5af gravado oito segundos antes" (LEIA-ME de 03 e artigo) não é verificável sem o histórico do repositório de trabalho. Detalhe: em `03_motor_de_29-09/saida/.../motor_respostas_8/`, `formular_D.json` e `propor_modelo.json` são versões anteriores, sem a referência SIMD e com `razao_vs_rede`. Elas não batem com os sha256 que o diário registrou ao copiar. As usadas na corrida estão em `06/.../respostas/` e batem com o script publicado (seção 6).

**Franqueza sobre os carimbos.** Todos esses horários foram gravados pela própria máquina. São coerentes entre si, mas não são prova externa de data: um conjunto coerente de arquivos pode ser gerado ou regravado a qualquer momento. O `MANIFESTO.sha256` é da montagem de 16/10 e prova integridade desde então, não a data da corrida. Prova externa seria, por exemplo, um commit enviado a um servidor de terceiros em 29/09, um carimbo RFC 3161 ou OpenTimestamps, ou um hash publicado num lugar datado por terceiros. Nada disso está no repositório.

## 6. Coerência interna

Scripts: `coerencia.py`, `ledger.py` e `montagem.py`.

**Bate:**

- Os sha256 do diário (`resposta_copiada`) conferem com os bytes dos 7 arquivos de `respostas/`.
- Os sha256 do evento `resposta` conferem com o JSON de cada resposta, pela serialização declarada em `motor.sha`.
- O hash do modelo, recalculado de `respostas/004`, é `889c906d…`, igual ao de E.
- Os hashes de D (`a2cdf9eb…`) e de Π (`f58e13d3…`), recalculados de E, são iguais aos do ledger (`seq` 1).
- O decodificador, as métricas e o oráculo da corrida são idênticos aos de `experimentos/montar_ordenacao_motor.py`. A rede "otima" é igual a `OTIMAS[8]`.
- O escolhido do estado, da auditoria e do roteiro é o `seq` 3 do ledger. Ele é igual a `descricao_do_candidato` de RV, e todas as medidas de RV são iguais às do ledger.
- O ledger tem `seq` contínua de 1 a 145, 48 ids distintos, custo somado de `"medicoes_no_alvo": 48` e `"medidas_reusadas": 0`.
- Contadores iguais em estado, roteiro e auditoria (`avaliacoes` 48, `passos` 8, `pedidos_ia` 7, `pedidos_criador` 0).
- `segundos_motor` é 590,0 no estado e 3,64 na auditoria. Não é erro: a auditoria é gravada dentro do último passo, antes de somar os 586,36 s dele.
- 3 válidos e 45 nulos, todos `candidato_falho`: 15 em `r_mais_rapida` e 30 em `r_correto`.
- Minha conferência 0-1 concorda com o `erro_de_ordenacao` registrado nos 48 casos (0 discordâncias).

**Não esconde erro:**

- Nenhum veredito do ledger é `modelo_incerto` ou "não roda".
- Os 30 reprovados por correção têm o oráculo dizendo "a rede não ordena" e são redes de 18 comparadores.
- Nenhuma reprovação foi omitida. Elas estão no ledger e na auditoria (`cadaveres_na_conta`: 45).

**Não bate, ou falta:**

- O ledger guarda só os 48 finais, não os 384 (alegação 24).
- A exportação do motor falhou (alegação 25).
- O `.cpp` publicado não é o fonte medido (alegação 23).
- `intervencoes.jsonl` cita o script errado (`montar_desafio_motor.py`).
- O roteiro está cortado no meio do JSON do desfecho, na linha "02:41:30 ia contra a cópia…".
- O campo `melhor_violacao_por_ordem` não traz os melhores: é uma amostra de 1 a cada 19 avaliações, na ordem em que foram feitas (código em `motor._concorrencia`).

## 7. Provas extras extraídas dos registros

1. **Distribuição na população final (48).** A razão vai de 0,93695 a 0,99604 (mediana 0,96913). Todas as 48 estão abaixo de 1. 24 estão em 0,97 ou menos: 3 corretas e 21 incorretas. 18 redes estão corretas, todas de 19 comparadores, com razões de 0,95682 a 0,99604. As 30 incorretas têm 18 comparadores. Por variante: otima/ternario/memória são 21 (mediana 0,96091); otima/ternario/registradores são 17 (mediana 0,97226); as demais têm de 1 a 3.
2. **Sobre os 384.** Só há rastros:
   - O mínimo de violação por lote no diário: 0,3595; 0,4678; 0,1831; 0,0178; 0; 0,0968; 0; 0. Como uma rede correta com razão r tem violação (r − 0,97)/0,1, isso dá um piso para as corretas de cada lote: lote 0, ≥ 1,0059; lote 1, ≥ 1,0168; lote 2, ≥ 0,9883; lote 3, ≥ 0,97178. Esse último valor é atingido pelo `seq` 15, que nasceu nesse lote. No lote 5, o piso é ≥ 0,9797. Nos lotes 4, 6 e 7, pelo menos um candidato cumpriu o D. Ou seja: nos dois primeiros lotes nenhuma rede correta mediu mais rápido que a referência, e a melhora apareceu aos poucos.
   - A amostra de 1 em 19 tem valores de 0,151 a 18,9. Os valores acima de 1 indicam candidatos pelo menos 10% mais lentos (provavelmente as variantes SIMD e inserção) ou incorretos.
   - Quantos dos 384 passaram na correção não está registrado.
3. **Margem do vencedor.** Entre os 3 válidos: 0,95682 (`seq` 3), 0,95727 (`seq` 9) e 0,96393 (`seq` 6). A margem sobre o segundo é de 0,00045, ou 0,047 ponto percentual. Isso é cerca de 10 vezes menos que o ruído do próprio processo (0,46%) e 20 vezes menos que a resolução do D. Pela razão das medianas, a ordem se mantém: 0,95351, 0,95862 e 0,96689. Na fronteira do estado estão os três (`pareto` com faixas de ±0,005 não separa nenhum), e o escolhido foi o primeiro da lista (`motor._criar`, `ordem = list(range(...))`).
4. **Estabilidade da medida do vencedor.** Há uma única medida, de um único processo: `rodadas` 1, `repeticoes` 1, `tempo_mediana_s_intervalo` degenerado [3,094, 3,094]. A população final reaproveitou a medida da busca pelo cache (`adaptador_maquina._garantir`). Dentro do processo, a dispersão das 21 repetições é de 0,46%. Não há remedição em processo novo.
5. **Indício indireto de estabilidade entre processos (fraco).**
   - A vencedora (`seq` 3) e o `seq` 9 diferem só na ordem de duas camadas (a 1ª e a 6ª). Medidas em processos separados, deram 0,95682 e 0,95727.
   - Por outro lado, códigos que diferem na ordem de uma única camada (7 pares) têm diferença mediana de 0,0081 e máxima de 0,0189. Exemplos: `seq` 69 e 123, com 0,9534 e 0,97226; `seq` 24 e 48, ambos corretos, com 0,97754 e 0,98565.
   - Ou a ordem dentro da camada pesa até cerca de 2%, ou a variação entre processos é dessa ordem, de 2 a 4 vezes o "ruído" de 0,46%. Os registros não separam as duas hipóteses.
6. **Variação do meio entre processos.** O código da referência é idêntico nos 48 binários, mas `ciclos_referencia` vai de 22,598 a 30,789 (mediana 25,219). Há ainda um processo inteiro cerca de 2 vezes mais lento (`seq` 81: 50,652 de referência, 48,359 de candidato e 92,25 de SIMD). Nesse processo a razão ficou em 0,95461, perto das outras. Isso conta a favor da razão medida no mesmo processo, que cancela a lentidão comum.
7. **Granularidade do contador.** As contagens por bloco (ciclos × 256: 5.673, 5.701, 5.729, 5.757…) andam em degraus de cerca de 27 a 29 tiques (`relogio.py`). Num bloco de cerca de 6.000 tiques, um degrau equivale a cerca de 0,46%. Duas consequências:
   - O "ruído" da vencedora (0,00457) é da ordem de um degrau, isto é, o piso do instrumento, e não uma medida do meio.
   - O A/A "1,000" sai exato em 38 de 48 processos porque as duas cópias da referência gastam o mesmo número de degraus. Ele não detecta vieses menores que cerca de meio degrau.
   - Os 4,3% equivalem a cerca de 9 a 10 degraus, bem acima da granularidade.
8. **O AVX2 e o std::sort nas 48 medidas.** AVX2/escalar vai de 1,62 a 1,99 (mediana 1,82). O 1,916 da tabela é do processo da vencedora, perto do topo da faixa. `ns_std_sort` vai de 80,7 a 130,3 ns. O 104,5 da vencedora também está no alto.

## 8. Fraquezas que um especialista apontaria

Nenhuma delas desmente a correção da rotina. Elas tratam do tamanho e da generalidade do ganho.

1. **Um só processador, uma só corrida, uma só medida por candidato.** É uma VPS de 6 núcleos lógicos, com 3 medidas em paralelo e, segundo o LEIA-ME, o problema de 6 elementos nos outros 3. O modelo do processador, o microcódigo, o hipervisor e a versão do gcc não foram gravados.
2. **Seleção do mínimo entre centenas de medidas únicas (a maldição do vencedor).** O vencedor foi escolhido como o mais rápido entre 384 candidatos medidos uma vez cada, e não foi medido de novo depois de escolhido. O "ruído" de 0,46% é dentro do processo e está no piso do contador. A variação entre processos e binários, que é a que importa quando se escolhe o mínimo, não foi medida, e os pares de códigos quase iguais sugerem que ela pode chegar a 1% ou 2%. Os 4,3% são, por construção, uma estimativa otimista. A pergunta fica em aberto: quanto sobra numa remedição cega?
3. **Controle A/A incompleto.** O A/A compara só duas cópias da referência. Não há a referência no lugar do candidato, uma calibração fácil de fazer, porque a referência é um ponto do próprio L (base otima, ordem original, ternario, registradores). A própria fórmula 4.3 exige isso antes de buscar ("Cal(V)" e "Ref(D)", com "trazer a referência para L"). Segundo `02_formula`, no caso de 6 elementos essa calibração falhou: a mesma rede mediu de 1,24 a 1,26 vez a referência.
4. **A escolha da referência.**
   - É uma única implementação, escrita pela mesma parte que fez a busca (a IA). Não foi ajustada com o mesmo esforço. A busca explorou 384 variações em torno dela; a referência teve uma forma só. O degrau "Medido" da própria fórmula pede "referências ajustadas com o mesmo esforço, escritas por outra parte".
   - A forma escolhida (valores em variáveis locais) não é a do libc++. Pelo que conheço do libc++ (`sort.h`), as rotinas sem desvio de 3 a 5 elementos usam `__cond_swap` e `__partially_sorted_swap` pelos iteradores, isto é, na memória, com seleção por ternário. A AlphaDev ganhou instruções no assembly dessas rotinas, aproveitando ordem parcial já conhecida. Assim, a "troca na memória" da vencedora se parece mais com a forma do LLVM do que a referência.
   - O plano previa calibrar a bancada com as rotinas da AlphaDev, e isso não aparece nos registros.
   - A variante `minmax` (std::min/std::max) saiu do L da corrida.
   - Não houve outro compilador (clang).
5. **O SIMD como régua.** A versão AVX2 ordena um único vetor de 256 bits por chamada, com `vpermd` e `vpblendvb` em cada camada. Isso fica preso à latência e é fraco no Zen 1, que divide as operações de 256 bits em duas metades. A versão com imediatos (`simd_imediato`, que existe na ferramenta mas não foi usada na referência), SSE de 128 bits ou várias redes processadas em lote (o que bibliotecas vetoriais como a vqsort, do Highway, e a x86-simd-sort fazem nos blocos pequenos) seriam réguas mais fortes. "A mais forte naquele meio" não está estabelecido.
6. **O contexto da medida.** Mede-se a vazão de um laço com `memcpy`, chamada não inline e soma de conferência. A diferença entre "em registradores" e "na memória" pode depender desse contexto: com a rotina inline, o gcc pode gerar o mesmo código para as duas formas. Sem o assembly gerado (`objdump`), não se sabe o que mudou no código de máquina. Os "ciclos" são tiques do TSC, não ciclos do núcleo.
7. **O título público.** "4,3% mais rápida que a rede ótima conhecida" (artigo e LEIA-ME de 03), e também "que a melhor referência conhecida" (primeiro parágrafo deste LEIA-ME), dizem mais do que a evidência:
   - a vencedora é a própria rede ótima; o que é mais rápido é uma implementação, contra outra implementação da mesma rede, num processador, num compilador, numa medida;
   - pela resolução do próprio D, o resultado é "cerca de 4%" (três candidatos empatados, de 3,6% a 4,3%), e pela razão das medianas seriam 4,65%;
   - a "referência conhecida" é a desta pesquisa, não uma referência de terceiros.

   O corpo do LEIA-ME já diz isso com cuidado ("não traz uma rede nova e não marca fronteira"). Também não está nos registros a ideia de que 6 a 8 elementos "ainda são fronteira" (plano); há rotinas sem desvio e vetoriais conhecidas para esses tamanhos.
8. **Papéis colapsados e a prova da fórmula.**
   - Quem formulou e confirmou o D foi a IA; foi ela também que pôs o limite de 3% e escreveu a referência, o medidor e o oráculo. Houve 0 pedidos ao criador.
   - A própria fórmula 4.3 diz que "um resultado com papéis colapsados não conta como prova" e que nenhum resultado passou do degrau "medido".
   - A comparação com um evolutivo simples, que o plano chamava de "a prova da fórmula", não está no repositório.
   - Nesta corrida, quem achou a rotina foi o NSGA-II genérico do motor (`gerar.nsga2`), sobre respostas preparadas antes. As voltas próprias da fórmula quase não agiram: `ponto_fixo.voltas` 0, sem reformulação. "É a fórmula funcionando num meio real" vale como "a máquina rodou de ponta a ponta", não como prova de que a fórmula ganha de uma busca simples.

## 9. O que tornaria a prova mais forte (curto)

- Remedir em processos novos, por exemplo 30 vezes cada, alternados: a vencedora; a referência no lugar do candidato (A/A no lugar do candidato); e os outros dois empatados. Publicar o intervalo de confiança.
- Gravar `/proc/cpuinfo`, `gcc --version`, o caminho e o sha256 do g++, e o `objdump` de `cand_` e `refe_`.
- Publicar o fonte exato que foi medido, com o AVX2, ou dizer claramente que o `.cpp` é uma versão reduzida.
- Medir também com clang, com a rotina inline e em outro processador. Pedir a uma terceira parte que reproduza.
- Uma referência ajustada com o mesmo esforço: a mesma busca na família da referência, a forma do libc++ estendida a 8 elementos e um SIMD em lote. E a comparação com o evolutivo simples prevista no plano.

## 10. Scripts usados (todos meus, rodados com `python3 -I`)

Pasta: `/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/verif/ordenacao/`

| Script | O que faz | Saída |
|---|---|---|
| `redes.py` | decodifica os genes; compara com RV e com o `.cpp`; 0-1, permutações e 8^8 (com min/max e com o ternário exato); camadas; reconstrói o fonte da ferramenta e compara os sha256[:24] | `saida_redes.txt` |
| `ledger.py` | recontagem do ledger: tipos, aprovados, nulos, 0-1 próprio contra `erro_de_ordenacao`, distribuições, válidos, os dois estimadores | `saida_ledger.txt` |
| `coerencia.py` | hashes do diário contra as respostas; hashes de D, Π e modelo; contadores; tempos; regra de σ; ordem dos eventos | `saida_coerencia.txt` |
| `relogio.py` | granularidade das contagens do TSC | `saida_relogio.txt` |
| `ordens.py` | ordem dos candidatos corretos comparada com a da referência | `saida_ordens.txt` |
| `montagem.py` | decodificador, métricas e oráculo da corrida contra o script publicado (lido por `ast`); redes dos 3 da fronteira | `saida_montagem.txt` |
| `vizinhos.py` | pares de códigos quase iguais e a diferença das razões medidas | `saida_vizinhos.txt` |

Exemplo de chamada: `python3 -I redes.py <RV> <estado.json> <rotina_8_vencedora_e_referencia.cpp> <ferramenta_ordenacao.py>`. Os caminhos de dados apontam para `main_ro`, que não foi alterado.
