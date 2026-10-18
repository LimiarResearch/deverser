# Verificação da comparação com o CEGIS e da auditoria do z3

Repositório LimiarResearch/deverser, ramo main, commit a28eec9, cópia somente leitura em
`/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/main_ro`.
Verificação feita em 17/10/2026, só pelos registros.

## Como foi feito

- Li os seis arquivos de `06_evidencias/cegis_e_z3/`, o artigo (`01_artigo/A_ENGENHARIA_REVERSA_DO_ACASO.md`), a fórmula (`02_formula/A_FORMULA_DO_DEVER_SER_v4.3.md`), o README e o código das máquinas (03, 04, 05, 08), só lendo.
- Nada do repositório foi executado: nenhum .py dele, nenhum teste, nada compilado, nenhum z3. Nada em main_ro foi alterado.
- Todas as contas são de scripts meus, em `/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/verif/cegis/`, rodados com `python3 -I` de fora da pasta do repositório, recebendo os arquivos de dados como argumento. A lista está no fim.
- Os 8 arquivos usados (os 6 da evidência, o artigo e a fórmula) batem com o `MANIFESTO.sha256` (8 de 8, `saida_manifesto.txt`).
- Não consultei nada fora do repositório: nem o PyPI, nem o histórico do GitHub. Tentei ler o histórico de commits pelo conector do GitHub, e o acesso foi negado porque o repositório não está liberado nesta sessão. A cópia local não tem `.git`.

## Resumo

Todos os números da comparação e da auditoria batem com os registros, caso a caso, e não achei nenhuma contradição numérica. O "15×" do post só vale contra o CEGIS com poda (17.588/1.152 = 15,27). Contra o CEGIS sem poda, a razão é 13,99. O que os registros não sustentam é a interpretação. A "formulação" não é definida no protocolo e não é a mesma coisa nos dois métodos: no CEGIS, 94% das formulações são buscas vazias, uma por classe estrutural. Medida em verificações, a vantagem cai para 1,25×, e em segundos, para 1,04×. O código do CEGIS, da regra f e do auditor não está no repositório. As especificações dos casos também não. A data do protocolo não pode ser provada com o que está ali.

## Tabela de alegações e vereditos

| # | Alegação (onde) | O que os registros mostram (arquivo, campo, valor literal) | Veredito |
|---|---|---|---|
| 1 | 192 casos (LEIA-ME, artigo) | `protocolo.json` `"casos": 192`; `resumo.json` `"casos": 192`; `resultados.jsonl` 192 linhas, ids 0 a 191 sem repetição, 192 rótulos distintos; `auditoria_z3.json` `resumo.casos` 192 e 192 entradas em `casos` | confirmado |
| 2 | A fórmula usou 1.152 formulações (LEIA-ME, artigo) | soma de `f.formulacoes` = 1152; `resumo.json` `f.formulacoes_total: 1152` | confirmado |
| 3 | CEGIS com poda: 17.588 (LEIA-ME, artigo) | soma de `cegis_poda.formulacoes` = 17588; `resumo.json` `cegis_poda.formulacoes_total: 17588` | confirmado |
| 4 | CEGIS: 16.120 (LEIA-ME, artigo) | soma de `cegis.formulacoes` = 16120; `resumo.json` `cegis.formulacoes_total: 16120`. Mas 72 casos do CEGIS sem poda terminaram em `"tipo": "timeout"` (corte por nós), e o total desses casos fica truncado | confirmado (número); o texto omite os 72 cortes |
| 5 | 82, 82 e 50 soluções (LEIA-ME, artigo) | `tipo == "solucao"`: f 82, cegis_poda 82, cegis 50; igual a `resumo.json` `desfechos`. 48 das 82 soluções, e 48 das 50 do CEGIS sem poda, são máquinas de 1 estado da família `autorizado` com o sensor `s_autorizado` | confirmado (número); o texto omite a composição |
| 6 | Nenhum dos três falhou na conferência (LEIA-ME) | nenhum `"conferido": false`; `conferido: true` em 155 (f), 82 (cegis_poda) e 50 (cegis); `resumo.json` `falhas_de_conferencia: 0` nos três. Os vereditos negativos do CEGIS e os `over_budget` da f têm `conferido: null` | confirmado, com o alcance dito ao lado |
| 7 | O z3 confirmou os 192 vereditos: 54 memória insuficiente, 82 soluções, 37 acima do orçamento, 19 não observáveis (LEIA-ME, artigo) | `auditoria_z3.json` `casos[].tipo_da_regra_f`: insufficient_memory 54, solucao 82, over_budget 37, unobservable 19; `resumo.por_desfecho` com `confirmados` igual a `casos` em cada um | confirmado (o arquivo diz isso); confirma os vereditos da f, não os do CEGIS |
| 8 | 0 discordâncias (LEIA-ME, artigo) | todas as 192 listas `discordancias` vazias; `resumo.discordancias: []`; `desconhecidos` 0 em todos; `tabelas_sat_conferidas: true` em 192 | confirmado |
| 9 | 2.870 perguntas ao z3 (LEIA-ME) | soma de `perguntas_ao_z3` = 2870; `resumo.perguntas_ao_z3: 2870` | confirmado |
| 10 | O hash dos casos é o mesmo do protocolo (LEIA-ME) | `protocolo.json` `hash_dos_casos` e `auditoria_z3.json` `resumo.hash_dos_casos` são ambos `aef6c8a1500fbc6a40cddab5cd4adcc5b8b24560f51e8b1b16ba73579c01ef9c` | confirmado como igualdade das duas cadeias; não recalculável (o protocolo não diz como se calcula, e as definições dos casos não estão no repositório) |
| 11 | Protocolo "congelado antes de rodar" (LEIA-ME) | `protocolo.json` `"congelado_em": "2026-09-28T02:46:25"`, sem fuso; resultados, resumo e auditoria não têm carimbo; `hash_do_codigo` não é recalculável (o código não está no repositório) | não verificável só com o repositório |
| 12 | O z3 "recebeu os 192 casos por outro caminho, sem ver a busca" (LEIA-ME, artigo) | nenhum registro do caminho; a auditoria guarda `tipo_da_regra_f` e `custo_da_regra_f` de cada caso, ou seja, tinha o veredito da f para comparar; o único elo com o protocolo é o hash | não verificável |
| 13 | z3 5.1.0, roda com sha256 `1561efd3...` (PROCEDENCIA) | `PROCEDENCIA.md` e `auditoria_z3.json` `"z3": "5.1.0 (dados/z3/PROCEDENCIA.md)"` concordam; a roda não está no repositório | não verificável só com o repositório (coerente entre os dois arquivos) |
| 14 | O z3 roda num processo à parte, `bancada/adaptadores/mealy/z3_limite.py` (PROCEDENCIA) | esse arquivo não existe no repositório; `03_motor_de_29-09/bancada/adaptadores/` só tem `componente` | não verificável |
| 15 | "o CEGIS, a síntese guiada por contraexemplo da literatura" (artigo) | nenhuma linha de código do CEGIS no repositório; nenhuma ferramenta externa nomeada; os números indicam uma implementação própria que percorre classes (item 4) | não verificável que seja o CEGIS padrão |
| 16 | "15× fewer formulations than CEGIS across..." (post) | 17588/1152 = 15,27; 16120/1152 = 13,99 | confirmado só contra o CEGIS com poda; contra o CEGIS sem poda, 14×; impreciso como frase (ver item 3) |
| 17 | Concordância de custo e nenhuma contradição (`resumo.json`) | f x cegis_poda: 82 com máquina, 82 com o mesmo custo; f x cegis e cegis_poda x cegis: 50 e 50; recontei também estados e sensores: idênticos em todos; nenhuma solução com custo acima de B; `contradicoes_entre_metodos: []` confirmado | confirmado |
| 18 | Construção de máquinas de estados finitos (LEIA-ME, artigo) | campos `estados` (1, 3 ou 4 nas soluções) e `sensores`; rótulos `k2` a `k5`; as especificações não estão no repositório | compatível; o detalhe não é verificável |

Inconsistências: nenhuma de número. O que há são imprecisões e omissões de texto: o "15×" sem dizer "com poda", os 72 cortes do CEGIS sem poda, as 48 soluções triviais e a escolha da métrica (itens 3, 4 e 7).

## 1. Recontagem (script `recontagem.py`, saída `saida_recontagem.txt`)

| método | formulações | verificações | buscas | nós | segundos | desfechos | conferido true / false |
|---|---|---|---|---|---|---|---|
| f | 1.152 | 817 | 1.152 | 54.014 | 153,3 | insufficient_memory 54, solucao 82, over_budget 37, unobservable 19 | 155 / 0 |
| cegis_poda | 17.588 | 1.018 | 17.588 | 201.129 | 159,0 | solucao 82, over_budget 61, sem_maquina_na_familia 49 | 82 / 0 |
| cegis | 16.120 | 2.912 | 16.192 | 42.826.972 | 362,7 | solucao 50, over_budget 44, sem_maquina_na_familia 26, timeout 72 | 50 / 0 |

Tudo igual ao `resumo.json`, campo a campo (`formulacoes_total`, `verificacoes_total`, `nos_total`, `segundos_total`, `desfechos`, `conferidos`, `falhas_de_conferencia`). O campo `buscas` não está no resumo. Na f e no CEGIS com poda, ele é igual a `formulacoes` nos 192 casos. No CEGIS sem poda, é igual nos 120 casos sem timeout e vale `formulacoes + 1` nos 72 com timeout.

Os números do LEIA-ME e do artigo (1.152, 17.588, 16.120, 82, 82, 50, nenhuma falha) são os do resumo e os da recontagem.

O alcance da conferência: na f, ela aparece nas soluções e nos dois impossíveis (memória insuficiente e não observável), mas não nos 37 "acima do orçamento" (`conferido: null`). No CEGIS, só nas soluções. "Nenhum falhou" é verdade, mas os vereditos negativos do CEGIS nunca passaram por conferência.

Tabela cruzada dos desfechos (f, cegis_poda, cegis):

| f | cegis_poda | cegis | casos |
|---|---|---|---|
| solucao | solucao | solucao | 50 |
| solucao | solucao | timeout | 32 |
| insufficient_memory | sem_maquina_na_familia | sem_maquina_na_familia | 24 |
| insufficient_memory | over_budget | over_budget | 22 |
| over_budget | over_budget | over_budget | 22 |
| unobservable | sem_maquina_na_familia | timeout | 17 |
| over_budget | over_budget | timeout | 15 |
| insufficient_memory | sem_maquina_na_familia | timeout | 6 |
| insufficient_memory | over_budget | timeout | 2 |
| unobservable | sem_maquina_na_familia | sem_maquina_na_familia | 2 |

Em nenhum caso um método acha máquina e outro nega. Os 24 casos em que a f diz memória insuficiente e o CEGIS com poda diz acima do orçamento são todos de orçamento curto. Isso é coerente: se não existe máquina, também não existe uma dentro do orçamento. Só que o CEGIS dá o veredito mais fraco.

## 2. A auditoria do z3 (`recontagem.py` seções 5 e 6, `auditoria_tempo.py`)

Recontagem do `auditoria_z3.json`:
- 192 casos, ids únicos, em ordem de id.
- `tipo_da_regra_f`: insufficient_memory 54, solucao 82, over_budget 37, unobservable 19. Igual a `resumo.por_desfecho`.
- Soma de `perguntas_ao_z3` = 2.870. As perguntas se distribuem assim: memória insuficiente, 4 por caso (216); não observável, 4 por caso (76); soluções, de 3 a 50 (1.701); acima do orçamento, de 8 a 58 (877).
- Discordâncias 0, desconhecidos 0, `tabelas_sat_conferidas` true nos 192.
- `usa_s_autorizado` true em 48 casos, todos soluções. Bate com `resumo.solucoes_com_s_autorizado: 48`.
- O hash dos casos na auditoria é igual ao do protocolo (cadeia idêntica).

Caso a caso, auditoria contra `resultados.jsonl`: `rotulo`, `B`, `tipo_da_regra_f` contra `f.tipo`, `custo_da_regra_f` contra `f.custo` e `usa_s_autorizado` contra a presença de `s_autorizado` em `f.sensores` batem nos 192 casos, sem nenhuma diferença.

O veredito confirmado pelo z3, comparado com o desfecho de cada CEGIS:
- cegis_poda: solução com o mesmo custo nos 82 casos; memória insuficiente dá sem_maquina 30 e over_budget 24; acima do orçamento dá over_budget 37; não observável dá sem_maquina 19. É compatível em 192 de 192.
- cegis: solução com o mesmo custo em 50; os outros 32 casos com solução terminam em timeout; nenhum veredito negativo do CEGIS contraria um veredito confirmado. Compatível em 192 de 192.

O que a auditoria registra é a confirmação dos vereditos da regra f. O veredito próprio do z3 não fica gravado à parte: só existe a lista de discordâncias, vazia. O arquivo também não traz as perguntas (fórmulas), as respostas, os modelos SAT nem as provas UNSAT. As 2.870 perguntas não podem ser refeitas a partir do repositório.

O hash: o protocolo não diz como `hash_dos_casos` é calculado, e as definições dos casos (as especificações das máquinas) não estão no repositório, só o rótulo e B. Testei 108 formas plausíveis com id, rótulo e B (`hash_tentativas.py`) e nenhuma bate, como era de esperar sem as especificações. Esse erro não prova nada. A igualdade dos dois hashes só mostra que o protocolo e a auditoria citam a mesma cadeia. Não mostra que ela venha dos mesmos casos.

O tempo: `resumo.segundos` = 173,7, mas a soma de `segundos` por caso dá 755,76 (688,95 só de z3). Os dois números são compatíveis com uma execução paralela de pelo menos 4,35 processos. Uma fila simulada com 5 processos termina em 158,5 s, e com 4, em 192,9 s. O arquivo não declara o paralelismo. Isso não é inconsistência, mas fica sem documentação.

## 3. A razão: a que comparação o "15×" se aplica e de onde ele vem (`razoes.py`, `nao_triviais.py`, `poda.py`)

**Agregado.** 17.588/1.152 = **15,27** (CEGIS com poda). 16.120/1.152 = **13,99** (CEGIS sem poda). "15×" só vale contra o CEGIS com poda. Contra o CEGIS sem poda, o certo seria "14×". E o total do CEGIS sem poda é truncado: 72 casos pararam no limite de nós, e por isso ele soma menos formulações que a variante com poda.

**Caso a caso (CEGIS com poda contra f, em formulações).**
- A f usou menos formulações em 192 de 192 casos e nunca empatou nem usou mais.
- A razão por caso vai de 2 a 197. O primeiro quartil é 9,46, a mediana 19,0, o terceiro quartil 47,0, e a média geométrica 21,8.
- O ganho não vem de poucos casos grandes. Os 10% de casos com maior diferença somam 26,4% da diferença total, os 25% maiores somam 51,9%, e a metade maior, 77,5%.
- Contra o CEGIS sem poda, a f também usou menos em 192 de 192, com mediana de 20,75.

**Por desfecho da f (CEGIS com poda):**

| desfecho da f | casos | formulações f | cegis_poda | razão | parte da diferença |
|---|---|---|---|---|---|
| memória insuficiente | 54 | 54 | 4.180 | 77,4 | 25,1% |
| acima do orçamento | 37 | 181 | 3.558 | 19,7 | 20,5% |
| não observável | 19 | 199 | 1.415 | 7,1 | 7,4% |
| solução | 82 | 718 | 8.435 | 11,75 | 47,0% |

Os 110 casos sem solução entram na soma e respondem por 53,0% da diferença. Em 69 casos, a f decidiu com uma formulação só: os 54 de memória insuficiente e 15 de acima do orçamento. Neles, o CEGIS com poda gastou 5.062. Sem esses 69 casos, a razão cai para 11,57. Só nos 82 casos que os dois resolveram, ela é 11,75 (mediana por caso de 12,5). Nas 34 soluções fora da família `autorizado`, as que não são máquinas de 1 estado, ela é 10,75.

**As outras métricas que o próprio registro guarda** (razão do CEGIS sobre a f, nos 192 casos):

| métrica | cegis_poda / f | cegis / f |
|---|---|---|
| formulações | 15,27 | 13,99 |
| verificações | 1.018/817 = **1,25** | 2.912/817 = 3,56 |
| nós | 201.129/54.014 = 3,72 | 42.826.972/54.014 = 792,9 |
| segundos | 159,0/153,3 = **1,04** | 362,7/153,3 = 2,37 |

Em verificações, caso a caso, a f usou menos em 120 casos, igual em 72 e nunca mais (mediana da razão 1,11). Nos 82 casos resolvidos pelos dois, a razão é de 1,13 em verificações e de 0,99 em segundos: o CEGIS com poda gastou um pouco menos de tempo. Em segundos, a f foi mais lenta que o CEGIS com poda em 48 dos 192 casos. O protocolo lista oito métricas (`"metricas": ["tipo", "custo", "formulacoes", "verificacoes", "buscas", "nos", "segundos", "conferido"]`) e não declara qual delas é a principal. Contra o CEGIS com poda, a métrica escolhida para a manchete é a que dá a maior razão.

**Com que orçamento cada método parou.** O protocolo traz `"limite_de_nos": 300000` e `"max_formulacoes": 400`, os mesmos para os três métodos.
- A f chegou a no máximo 25 formulações e 7.547 nós num caso. O CEGIS com poda, a 293 formulações e 15.696 nós. Nenhum dos dois chegou perto dos limites, então a comparação entre eles não é distorcida por corte.
- O CEGIS sem poda parou em 72 casos com `timeout`. Nos 72, os nós somam pelo menos 300.000 (o menor é 341.382) e `buscas = formulacoes + 1`. Cinco casos sem timeout passam de 300.000 nós no total. A leitura coerente é que o "timeout" é o limite de 300.000 nós aplicado a cada busca, e não um limite de tempo. 32 dos 72 cortes eram casos com solução. As 50 soluções do CEGIS sem poda medem o limite, não a incapacidade do método.
- O `B` de cada caso é o orçamento de custo da máquina, um parâmetro do problema. É o mesmo para os três métodos (há um só campo `B` por caso): 50,0 nos 96 casos "folgado" e entre 5,02 e 11,99 nos 96 "curto". "Acima do orçamento" é um veredito sobre o problema (não existe máquina de custo até B), não uma parada da busca.

## 4. O que é uma "formulação", e o CEGIS

**Onde a palavra aparece:**
- `protocolo.json`: só como nome de métrica (`"formulacoes"`), sem definição.
- Artigo: "A busca continua existindo e corre sobre formulações, nunca sobre corpos". É uma ideia, não uma regra de contagem.
- Fórmula, seção 23 (22/09/2026): "A busca corre sobre formulações, com os fracassos registrados". Também sem regra de contagem. A fórmula não fala do CEGIS em lugar nenhum.
- Código, a única definição operacional: `03_motor_de_29-09/bancada/nucleo/criacao.py`, no docstring. "A cada passo, a próxima formulação é a primeira da ordem do adaptador que nenhuma restrição válida do ledger elimina e que ainda não foi julgada." `cont["formulacoes"] += 1` só conta as formulações construídas e julgadas. As eliminadas por restrição vão para `puladas_por_restricao` e não contam. Uma formulação declarada impossível sem verificar conta como formulação, mas não como verificação (`impossiveis_sem_verificar`). Em `bancada/nucleo/adaptador.py`: "formulacoes(D, Pi): as formulações completas do domínio, na ordem em que vale tentá-las (a família declarada)". Só que o adaptador das máquinas de estados (`bancada/adaptadores/mealy/`) não está no repositório. Não dá para saber se a bateria usou esse núcleo. Os desfechos da bateria (`insufficient_memory`, `unobservable`) também não são os do núcleo (`d_contraditorio`, `meio_insuficiente`...). O que se vê é compatível: 335 das 1.152 formulações da f (29,1%) terminam sem verificação.

**O que os números mostram sobre a unidade no CEGIS** (`poda.py`, `classes.py`):
- Em todos os casos e nos três métodos, verificações ≤ formulações. No CEGIS com poda, 94,2% das formulações (16.570 de 17.588) terminam sem verificação. No CEGIS sem poda, 81,9%.
- Em todos os casos em que o CEGIS esgota a família (`sem_maquina_na_familia`: 49 de 49 com poda, 26 de 26 sem poda), formulações menos verificações é exatamente **k × `classes_no_limite`**. O k vem do rótulo e `classes_no_limite` vem da auditoria do z3. Exemplos: no caso 0 (k2, 32 classes), 65 − 1 = 64; no caso 40 (k2, 64 classes), 129 − 1 = 128; no caso 2 (k3, 32 classes), 101 − 5 = 96.
- Nos 120 casos sem timeout, formulações menos verificações é idêntico entre CEGIS com poda e CEGIS sem poda em 120 de 120.

Leitura (é inferência, porque o código não está no repositório): o CEGIS desta bateria conta uma "formulação" por busca do sintetizador em cada classe estrutural, isto é, cada número de estados de 1 a k combinado com cada conjunto de sensores dentro do limite. Cada classe termina numa busca vazia, e cada candidato achado é verificado. A contagem do CEGIS é, quase toda, o tamanho da família que ele percorre. A poda reduz os candidatos verificados (2.912 para 1.018) e os nós (42,8 milhões para 201 mil), mas não as classes visitadas. Os registros não dizem o que a poda é.

**É a mesma unidade?** Tem o mesmo nome e o mesmo campo, mas não mede a mesma coisa. Na f, uma formulação pode encerrar o caso sem busca nenhuma: memória insuficiente sai com uma formulação e uma verificação, e a f confere essa impossibilidade (`conferido: true`). No CEGIS, cada classe custa pelo menos uma formulação. O número de formulações do CEGIS depende de como quem o implementou partiu a família. Uma única consulta com a escolha de sensores como variável, por número de estados, daria cerca de k formulações por caso, e não k × 2^|S|.

**É implementação própria? É CEGIS padrão?** Nenhuma linha de código do CEGIS está no repositório. Nenhuma ferramenta externa é nomeada. O protocolo tem um único `hash_do_codigo` para os três métodos, o que sugere uma base de código só, mas não dá para conferir. O laço de candidato e contraexemplo dentro de cada classe é o desenho clássico. Percorrer as classes de sensores uma a uma, sem nenhum teste prévio de impossibilidade, é uma escolha desta implementação. Pelos registros, é uma variante própria, em duas versões: "com poda" e "sem poda". A poda não é definida em nenhum arquivo.

## 5. A ordem no tempo

- `protocolo.json`: `"congelado_em": "2026-09-28T02:46:25"`, sem fuso; `"semente": 20260928`.
- `PROCEDENCIA.md`: a roda foi "baixada do PyPI em 28/09/2026".
- `resultados.jsonl`, `resumo.json` e `auditoria_z3.json` não têm carimbo de tempo. Nenhum arquivo datado registra o hash dos resultados. O `hash_do_codigo` do protocolo (`d04aeae1...`) não corresponde a nenhum arquivo do repositório e não pode ser recalculado, porque o código não está ali. O `hash_dos_casos` também não pode, porque os casos não estão ali.
- A cópia não tem `.git`, e o histórico do GitHub não foi acessível nesta sessão. A primeira data pública que o repositório mostra é a do README e do artigo, 16/10/2026.

Veredito: **não verificável**. Para ser franco, um carimbo gravado pela própria máquina, como `congelado_em` (ou a data de um commit, que o próprio autor define), não é prova externa de data. Qualquer pessoa pode escrever qualquer data num JSON. A semente igual à data também é escolha do autor. Uma prova de data teria de vir de um terceiro: um carimbo de tempo de uma autoridade (RFC 3161 ou OpenTimestamps) sobre o hash do protocolo, ou o hash publicado antes num lugar que um terceiro data (por exemplo, um push num servidor de terceiros com registro próprio, ou uma mensagem enviada a alguém).

## 6. A procedência do z3 e o "outro caminho"

O que o `PROCEDENCIA.md` diz:
- Pacote `z3-solver` 5.1.0.0, roda `z3_solver-5.1.0.0-py3-none-win_amd64.whl` de 17.040.097 bytes.
- sha256 `1561efd36e06f4cb7cbf11b63a2fba8fc8fdeb9c5754df90c84f9bd7a4864552`.
- `z3.get_version_string()` = 5.1.0.
- Instalado com `--no-deps --no-index` num ambiente `.venv-z3` (Python 3.13.3).
- O z3 roda num processo à parte (`bancada/adaptadores/mealy/z3_limite.py`), que recebe o problema em JSON.

A auditoria diz `"z3": "5.1.0 (dados/z3/PROCEDENCIA.md)"`, coerente com isso. O caminho `dados/z3/` é do repositório de trabalho e não existe no pacote público.

O que não dá para verificar com o repositório:
- A roda não está ali, e o próprio PROCEDENCIA diz que ela "não entra no git nem no pacote". Conferir se esse sha256 é o da roda publicada no PyPI exige consultar o PyPI, o que não fiz por ser fora dos registros. É o próximo passo natural: a API JSON do PyPI publica o sha256 de cada arquivo.
- O `z3_limite.py` não está no repositório.
- A auditoria não traz nenhum registro do canal pelo qual recebeu os casos. Ela guarda, caso a caso, `tipo_da_regra_f` e `custo_da_regra_f`, o que mostra que a etapa de comparação tinha o veredito da f. "Sem ver a busca" pode querer dizer sem ver o rastro da busca, mas nada nos registros mostra isso.
- "Isolado", pelo PROCEDENCIA, quer dizer processo e ambiente Python separados, com código na mesma árvore `bancada`, do mesmo autor. Na linguagem da própria fórmula, é um "oráculo de outro método" (laço 12), não um "verificador de outra parte" (seção 15, degrau 4).

O que os registros sustentam de fato: a auditoria e os resultados concordam caso a caso, e ela tem uma ligação estrutural com o CEGIS que não é cópia (a igualdade k × `classes_no_limite` do item 4).

## 7. O que um especialista apontaria (sem desmerecer)

- **Bateria própria.** São 192 casos gerados com semente própria, num desenho fatorial completo (J0/J1/J2 × livre/ordem × eventos/encerrar/autorizado/sem_reset × k2 a k5 × folgado/curto). As especificações não foram publicadas, só o rótulo e B. Não é um conjunto de referência da área, como os de síntese reativa ou de identificação de autômatos por SAT, e ninguém de fora consegue reproduzir.
- **CEGIS próprio, sem código.** A linha de base foi escrita pela mesma parte e não está publicada. A própria fórmula (seção 15, degrau "Medido") pede "referências ajustadas com o mesmo esforço, escritas por outra parte". Pela régua do próprio autor, esta comparação ainda não sobe a "medido". O artigo é coerente com isso quando diz que "quase tudo está no degrau 'rodou'".
- **Unidade própria.** "Formulação" não está definida no protocolo e, no CEGIS, conta sobretudo buscas vazias por classe. A f tem raciocínio de impossibilidade embutido (memória insuficiente com 1 formulação, não observável), e o CEGIS não. Por isso 53% da diferença vem dos casos sem solução. Uma comparação mais justa daria ao CEGIS os mesmos testes prévios, ou contaria verificações e tempo. Nessas métricas, a diferença contra o CEGIS com poda é de 1,25× e 1,04×.
- **Métrica não registrada antes.** O protocolo lista oito métricas sem marcar uma principal. A manchete usa a de maior razão contra a variante mais forte.
- **O tipo de problema.** São máquinas pequenas, de no máximo 4 estados nas soluções e k ≤ 5, com escolha de sensores por custo. 48 das 82 soluções são máquinas de 1 estado que leem o sensor `s_autorizado`, e a auditoria conta isso à parte (`solucoes_com_s_autorizado: 48`). O CEGIS sem poda resolveu só 2 dos 34 casos não triviais, e 48 das 50 soluções dele são as triviais.
- **A auditoria confere a correção, não a eficiência.** O z3 confirma que os vereditos da f estão certos. Isso não diz nada sobre o "15×".
- **A frase do post.** "15× fewer formulations than CEGIS" deixa de fora que é a variante com poda (contra o CEGIS sem poda é 14×) e que "formulação" é uma unidade interna, contada de forma diferente nos dois métodos. Um leitor da área vai entender "CEGIS" como o método padrão e "formulações" como um custo comparável. Nenhuma das duas leituras é sustentada pelos registros.
- **Ausência na fórmula.** A seção 22 da fórmula ("O que se mediu até 01/10/2026") não cita esta bateria, embora ela seja de 28/09.

E o que fala a favor, por justiça:
- As contas fecham.
- A f usou menos formulações em todos os 192 casos, e a mediana caso a caso (19×) é maior que a razão agregada, então não há efeito de poucos casos.
- A f e o CEGIS com poda acharam exatamente as mesmas máquinas.
- A auditoria registra por conta própria a ressalva do `s_autorizado`.

## 8. Provas extras extraídas dos registros

1. **Totais exatos.** Formulações, verificações, nós, segundos, desfechos e conferências de `resumo.json` saem exatamente da soma das 192 linhas (`recontagem.py`).
2. **Mesmas máquinas.** Nos 82 casos em que a f e o CEGIS com poda acham solução, coincidem custo, número de estados e lista de sensores (82 de 82). Entre os três métodos, 50 de 50. Nenhuma solução tem custo acima de B. É coerente com dois métodos exatos resolvendo os mesmos problemas.
3. **Auditoria igual aos resultados caso a caso.** Rótulo, B, desfecho, custo e uso de `s_autorizado` batem em 192 de 192.
4. **Ligação estrutural entre os arquivos.** Nos casos de família esgotada, formulações menos verificações do CEGIS (em `resultados.jsonl`) é igual a k × `classes_no_limite` (em `auditoria_z3.json`): 49 de 49 com poda e 26 de 26 sem poda. É uma quantidade que não foi copiada de um arquivo para o outro, e ela liga os dois (`classes.py`).
5. **A ordem das linhas confirma uma execução paralela com os tempos gravados.** As linhas de `resultados.jsonl` não estão em ordem de id (187 fora do lugar). Simulei uma fila em que P processos pegam os casos em ordem de id e cada linha é gravada quando o caso termina, com a duração de cada caso igual à soma dos `segundos` dos três métodos. Com P = 6, a simulação reproduz 175 das 192 posições, com tau de Kendall de 0,999 (9 pares invertidos em 18.336). Com outros P, o ajuste é muito pior: P = 4 dá 15 posições, e P = 8 dá 9. É um forte indício de que o arquivo saiu de uma execução real com 6 processos, e de que os tempos por caso são os medidos. Não é prova de data nem de correção (`ordem_das_linhas.py`).
6. **Os timeouts são coerentes.** Nos 72 timeouts, `buscas = formulacoes + 1` e nós ≥ 300.000. Nos 120 outros casos, `buscas = formulacoes`.
7. **O tempo da auditoria é plausível.** 173,7 s de total contra 755,8 s somados por caso cabem numa execução com cerca de 5 processos (`auditoria_tempo.py`).
8. **O desenho é completo e organizado em pares.** 3 × 2 × 4 × 4 × 2 = 192. Cada par folgado/curto do mesmo problema tem ids consecutivos, com o folgado par e o curto ímpar (96 de 96).
9. **Os pares são coerentes** (`pares.py`). A memória insuficiente se repete nos dois membros do par (27 de 27). Quando o folgado tem solução, o curto tem solução ou fica acima do orçamento, nunca outro desfecho. Quando os dois têm solução, a máquina (estados e sensores) é a mesma nos 28 pares. Os custos variam dentro do par, o que indica preços sorteados por caso. Em 11 pares, o folgado sai não observável e o curto, acima do orçamento. Isso aponta para uma ordem de prioridade entre os desfechos (orçamento antes de observabilidade), e não é contradição.
10. **As categorias da f e a fórmula** (interpretação): "memória insuficiente" e "não observável" correspondem aos estados "impossível nesta forma" e "impossível no meio" (laço 1a: o corpo não recebe do meio a informação que decide a cláusula). Isso explica por que a f encerra esses casos sem buscar.
11. **Manifesto.** Os 8 arquivos conferidos batem com o `MANIFESTO.sha256`.

## Fraquezas e o que falta para fechar

O que falta no repositório, e por isso fica sem verificação:
- O código da regra f para máquinas de estados, dos dois CEGIS, da poda, do gerador da bateria e do `z3_limite.py`.
- As especificações dos 192 casos.
- O registro das perguntas e respostas do z3.
- Uma prova externa de data.

Sem isso, só se verifica a coerência interna, e ela é boa. A reprodução não é possível. O que fecharia cada ponto:
1. Publicar o código cujo sha256 seja `d04aeae1...` e os casos cujo hash seja `aef6c8a1...`, com a regra de cálculo dos dois hashes.
2. Definir por escrito "formulação" para cada método.
3. Pôr verificações e segundos ao lado de formulações na manchete.
4. Comparar com uma ferramenta de síntese de terceiros, e com o CEGIS acrescido dos mesmos testes de impossibilidade da f.
5. Publicar as perguntas do z3 em SMT-LIB, com as respostas.
6. Conferir o sha256 da roda contra o PyPI.
7. Corrigir a frase do post para "15× menos formulações que a nossa implementação de CEGIS com poda (14× sem poda), na nossa bateria de 192 casos", ou equivalente.

## Scripts e saídas

Pasta: `/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/verif/cegis/`

| script | o que faz | saída |
|---|---|---|
| `recontagem.py` | totais por método contra o resumo, concordância de custo, contradições, tabela cruzada, auditoria recontada e caso a caso, limites do protocolo, razões agregadas | `saida_recontagem.txt` |
| `razoes.py` | distribuição caso a caso das razões, por desfecho e por fator, concentração da diferença, família autorizado | `saida_razoes.txt` |
| `nao_triviais.py` | razões nas soluções triviais (1 estado, `s_autorizado`) e nas não triviais | `saida_nao_triviais.txt` |
| `poda.py` | CEGIS com poda contra sem poda fora dos timeouts; fração de formulações sem verificação | `saida_poda.txt` |
| `classes.py`, `classes_por_familia.py` | formulações vazias do CEGIS contra k × `classes_no_limite` da auditoria | `saida_classes.txt`, `saida_classes2.txt` |
| `pares.py` | coerência dos pares folgado/curto | `saida_pares.txt` |
| `ordem_das_linhas.py` | simulação da fila paralela contra a ordem gravada | `saida_ordem.txt` |
| `auditoria_tempo.py` | tempo da auditoria e perguntas por desfecho | `saida_auditoria_tempo.txt` |
| `hash_tentativas.py` | 108 tentativas de recalcular `hash_dos_casos` com id, rótulo e B | `saida_hash.txt` |
| `rodar_tudo.sh` | roda tudo e confere 8 arquivos contra o MANIFESTO | `saida_manifesto.txt`, `sha_calc.txt` |

Para refazer tudo: `sh /tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/verif/cegis/rodar_tudo.sh /tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/main_ro`
