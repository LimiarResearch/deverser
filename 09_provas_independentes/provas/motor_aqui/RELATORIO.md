# O motor de 29/09 contra um sorteio cego, nesta máquina

Verificação feita em 17/10/2026 sobre a cópia de LimiarResearch/deverser (ramo main, commit 316ea4f), em `run/03_motor_de_29-09`. Gabriel Santos autorizou rodar o código. Máquina: Intel Xeon 2,1 GHz (família 6, modelo 207, com AVX2 e AVX-512), 4 núcleos, 16 GB, Linux, g++ 13.3.0, Python 3.13.16, numpy 2.5.3. Só este trabalho rodou enquanto se media. O motor e o nulo mediram com 3 processos em paralelo (`paralelo_no_alvo` = 3, como em 29/09). A remedida mediu em sequência.

Pasta de tudo: `provas/motor_aqui/` (os caminhos abaixo são relativos a ela, salvo indicação).

## Resumo em cinco linhas

1. **O meio mudou o problema.** Neste Xeon, a referência vetorial (a mesma rede ótima em AVX2) roda a cerca de 10 a 11 ciclos por vetor, contra 15 a 16 da referência escalar. Na VPS (Zen 1) era o contrário: 44,8 contra 23,4. O D de 29/09 pede "3% mais rápida que a mais rápida das referências". Aqui isso significa vencer a rede AVX2, e não a escalar.
2. **O motor achou solução, mas só na segunda busca.** A primeira (L0, 291 candidatos) empacou sem nenhum válido. Depois da abertura de L preparada antes da corrida, a segunda (435 candidatos) achou a rede ótima com a troca `simd_imediato`: razão 0,804 na busca, remedida em 0,844 contra a referência mais rápida.
3. **Contra o sorteio cego pedido** (726 sorteios uniformes na mesma L, mesmo medidor, mesmo D), **a seleção ganhou com folga.** Melhor remedida: motor 0,842 [0,792; 0,891] contra nulo 1,452 [1,452; 1,453]. A margem de 0,61 é muito maior que a variação entre rodadas (0,10 no pior caso), e a diferença pareada foi de 0,61 a 0,66 em todas as 5 rodadas. O sorteio achou 1 rede que ordena e nenhuma que cumpre o D. O motor registrou 18 redes que ordenam e 15 que cumprem o D. Os tempos foram parecidos: 534,5 s no motor e 569,0 s no nulo.
4. **Mas o ganho todo está em duas escolhas discretas:** manter os 19 comparadores e usar a troca `simd_imediato`. Num sorteio suplementar e exploratório, com todos os comparadores mantidos, o mesmo orçamento achou 126 válidos. Os 5 melhores dele e os 5 do motor são **os mesmos dois binários**, e a remedida dá empate: 0,8417 contra 0,8418, com diferenças pareadas que trocam de sinal. A ordem dentro dos níveis e o gene `registradores` não mudam nem uma linha do C++ das variantes SIMD.
5. **A vencedora de 29/09, aqui:** razão 0,964 contra a referência escalar (o ganho de 29/09 reaparece em parte: 3,6% em vez de 4,3%), mas 1,41 contra a referência AVX2. Neste meio ela não cumpre o D.

## 1. O que mudou no protocolo, e por quê

O protocolo novo é `run/03_motor_de_29-09/protocolos/calculadora/ordenacao_8_motor_xeon.json`, uma cópia de `ordenacao_8_motor_vps.json`. O registro completo está em `mudancas_no_protocolo.json`.

| campo | antes | depois | por quê |
|---|---|---|---|
| `id` | ordenacao_8_motor_vps | ordenacao_8_motor_xeon | outro id, para não confundir com a corrida de 29/09 |
| `alvos[0].python` | /home/iro/bancada-criacao/venv/bin/python | /usr/bin/python3 | o caminho do servidor não existe aqui |
| `alvos[0].descricao` | a VPS: AMD EPYC, 3 dos 6 núcleos | esta máquina: Intel Xeon 2,1 GHz com AVX-512, 4 núcleos, 3 para este problema | o texto antigo seria falso aqui; não é executável e não entra em conta nenhuma |

Mantido de propósito: `alvos[0].id` continua `vps-local`, porque a resposta `formular_D` de 29/09 aponta para esse id (`escopo.alvo`). Trocar o id obrigaria a editar a resposta. É só um rótulo. Todo o resto (paralelo 3, rodadas 1, repetições 1, orçamento, busca por concorrência, população por σ, teto, `reformulacoes_max` 5, conferir a distinguibilidade) ficou idêntico.

Fora do protocolo, no ambiente (`scripts/ambiente.sh`):
- `FERRAMENTA_GXX=/usr/bin/g++` e `FERRAMENTA_GXX_SHA256=1353e9bdd29a7295c7226bf6c63abccce056d8cac31f112e5cdbecc3f28c2769`. É o g++ 13.3.0 desta máquina (`/usr/bin/g++` aponta, via /etc/alternatives, para `/usr/bin/x86_64-linux-gnu-g++-13`). A ferramenta declarada lê o compilador dessas duas variáveis, e não do protocolo.
- `TMPDIR` dentro de `provas/motor_aqui`. A ferramenta guarda o C++ gerado e o binário em `tempfile.gettempdir()`. Com isso, nada foi escrito fora das pastas permitidas, e cada etapa começou com o cache de binários vazio. Isso não muda a medida.

### O que não estava como o LEIA-ME diz (registrado, sem alterar código)

- **As respostas em `03_motor_de_29-09/saida/calculadora/ordenacao/motor_respostas_8/` não são as que a corrida usou.** `formular_D.json` e `propor_modelo.json` de lá são de uma versão anterior: medida `razao_vs_rede`, variantes ternario, minmax e mascara, sem SIMD. A corrida de 29/09 consumiu outra versão: medida `razao_vs_melhor`, variantes ternario, mascara, simd e simd_imediato. Prova: o sha256 de cada arquivo em `06_evidencias/.../corrida_motor8/respostas/` bate com o evento `resposta_copiada` do `diario.jsonl` de 29/09, e os de `saida/` não batem nesses dois. O script `experimentos/montar_ordenacao_motor.py` do repositório, rodado (numa cópia isolada, `montar_caixa/`) com os números da VPS `0.0113 0.0053`, reproduz byte a byte as respostas da corrida e o `problema.json` dela. Usei as respostas da corrida. O `revisar_1.json` de `saida/` também está defasado: as métricas dele não produzem `razao_vs_melhor`, e o teste de cobertura do motor o recusaria.
- O LEIA-ME não menciona as variáveis `FERRAMENTA_GXX` e `FERRAMENTA_GXX_SHA256`. Sem elas, a ferramenta recusa ("ferramenta não declarada"). Eu as declarei desde o início, então esse erro não ocorreu.
- A exportação do escolhido falhou com `NameError: name 'repr' is not defined`, a mesma falha registrada no `estado.json` de 29/09. O código de exportação usa `repr`, que a caixa isolada não oferece. Não afeta a busca.
- O arquivo publicado `rotina_8_vencedora_e_referencia.cpp` (sha256[:24] 40cc63c9f9df2ba7bf0cecd7, o mesmo valor de `fonte_sha256_24` em `rede_vencedora.json`) não é a fonte completa que a ferramenta gera. Falta nele a referência AVX2 (`refs_`) e a medida contra ela. Mas as medidas registradas da vencedora em 29/09 trazem `razao_vs_simd` e `ciclos_simd`, que só essa referência produz. A fonte que a ferramenta gera aqui para a mesma descrição tem sha256[:24] af8427daffe0407686dd5ec8. Os corpos da vencedora e da referência escalar são idênticos nos dois arquivos.

## 2. A corrida do motor

Pasta: `corrida/` (estado, ledger, diário, auditoria, pendentes e respostas). Roteiro com horários: `corrida_roteiro.log`. Respostas usadas: `respostas_usadas/`.

**As etapas de 29/09 se repetiram iguais.** Os pedidos 001 a 007 têm o mesmo conteúdo dos de 29/09; só o alvo difere (o Python e a descrição). O hash do modelo aceito é o mesmo (m1, 889c906d0b), e o sha256 de cada resposta aplicada é o mesmo do diário de 29/09. A IA respondeu pelo criador como lá: confirmar_D (4 cláusulas) e distinguibilidade, com as respostas preparadas antes da corrida. O D é o mesmo: correta em todos os 8⁸ vetores e `razao_vs_melhor` ≤ 0,97, com resolução de 1%. A medida do alvo (006) foi tirada com a ferramenta do motor, como em 29/09.

**Pedidos que não estavam nas respostas de 29/09**, cada um anotado no roteiro:

| pedido | o que o motor pediu | o que respondi | por quê |
|---|---|---|---|
| 008_revisar | nenhum candidato cumpre D; proponha forma nova | `revisar_1` gerado pelo script que reproduz as respostas da corrida: m2 = o arquétipo rede mais a rede livre que compõe (17 a 38 comparadores) | é a abertura de L preparada antes da corrida para este caso ("ordem das causas: L primeiro"); a versão de `saida/` está defasada |
| 009_mapear_numeros | os números do meio da forma nova `composicao:comparador` | `{"numeros": {}}`, com o motivo escrito no arquivo | escrita por mim nesta verificação: a rede livre roda na mesma ferramenta e depende dos números que o mapa já tem |
| 010_medir_alvo | o perfil do alvo de novo (o modelo mudou) | a ferramenta do motor, como no 006 | mesmo método de 29/09 |

**As duas buscas:**

| | busca 1 (m1, L0) | busca 2 (m2, L1) | 29/09 na VPS (para comparar) |
|---|---|---|---|
| lote do σ (3 candidatos) | 2,829 s | 1,970 s | 4,403 s |
| população | 48 | 48 | 48 |
| gerações depois da inicial | 5 | 8 | 7 |
| candidatos na concorrência | 288 | 432 | 384 |
| candidatos medidos, com o lote do σ | 291 | 435 | 387 |
| tempo da concorrência | 218,3 s | 316,2 s | 581,7 s |
| tempo da criação (passo) | 221,2 s | 318,2 s | 586,1 s |
| parada | fronteira igual por 3 gerações | fronteira igual por 3 gerações | igual |
| válidos na população final | 0 de 48 | 15 de 48 | 3 de 48 |
| menor violação | 0,183 | 0 | 0 |

Total do motor: **726 candidatos medidos** e **534,5 s de concorrência** (539,4 s nas duas criações). Do primeiro passo ao desfecho foram 11 min 21 s de parede (23:09:00 a 23:20:21 UTC), contando as etapas de pergunta e resposta.

**Por que a busca 1 empacou.** O melhor da população final (violação 0,183) é uma rede `simd_imediato` sem um comparador. Ela é rápida, mas erra 18% dos vetores. As 2 redes que ordenavam na população final eram `simd` comum, com razão 1,003. A violação soma o erro com escala 1,0 e o excesso de razão com escala 0,1. Por isso uma rede que erra 18% e é rápida (violação 0,18) fica à frente de uma rede correta a 1,003 (violação 0,33), e a seleção se prende às incorretas rápidas.

**Desfecho:** `solucao`, "melhor encontrado e verificado; não demonstrado como o melhor, porque parte de L foi amostrada".

**A vencedora:** arquétipo `rede` (já existia em L0), base `otima` (a rede ótima de 19 comparadores, a mesma da referência), troca `simd_imediato`, `registradores` = 1. Nenhum comparador é retirado: `rem_21`, `rem_23` e `rem_27` valem 1, mas a rede ótima só tem 19 comparadores, então esses genes não agem. É a rede de referência em AVX2, com dois ajustes: o embaralhamento por constante (`_mm256_shuffle_epi32`) nos níveis que ficam dentro de cada metade de 128 bits, e a mistura por constante (`_mm256_blend_epi32`) no lugar da mistura por máscara (`_mm256_blendv_epi8`). Fonte gerada: sha256[:24] de7c37a0a475882f96b5ed12.
- Na busca: erro 0, `razao_vs_melhor` 0,8035, razão contra a escalar 0,609, ruído 0,073 (uma medida ruidosa: a referência AVX2 mediu 15,1 ciclos naquele processo, contra os 10 a 11 de costume).
- Remedida: **0,8444** [0,8071; 0,8907].
- Nenhuma composição ficou na população final da busca 2. A abertura de L não produziu a vencedora. O que mudou entre a busca 1 e a 2 foi a amostra inicial: com a composição, a cota do arquétipo rede caiu de 48 para 24, e a semente é a mesma.

## 3. O nulo: sorteio cego na mesma L

O plano (`nulo/plano.json`) foi escrito antes de ver o resultado de cada busca. A emenda 1 foi registrada durante a busca 2, antes de ver o resultado dela. O script é `scripts/nulo.py`.
- **Geração:** cada variável é sorteada com `compilador.gerar._valor_novo`, a função do próprio motor. As categorias saem uniformes sobre a lista declarada; como `rem_k` tem a lista [0, 0, 0, 1], cada comparador sai com probabilidade 1/4, o mesmo domínio da população inicial e da mutação do motor. Os reais (`pri_k` em [0, 1] e a taxa em [0,1; 0,6]) saem uniformes. A composição foi sorteada como em `gerar.compostos`.
- **Medida:** o mesmo caminho do motor. `AdaptadorMaquina.medir_lote`, depois o executor genérico, depois `ferramenta_ordenacao.medir`. Mesmo modelo, mesmo alvo, rodadas 1, repetições 1, paralelo 3, em lotes de 48.
- **Julgamento:** o mesmo D, via `avaliar.julgar` e `Motor._violacao_pior`. Atenção: o campo `correto` do motor é só o oráculo, que confere a integridade da medida. Ordenar é `erro_de_ordenacao` = 0, a cláusula r_correto.
- **Espelho do orçamento:** parte 1 com N = 291 em L0 (semente 20261017); parte 2 com N = 435 em L1, metade rede e metade composição, como a população inicial do motor em m2 (semente 20261019). Cada parte começou com cache de binários vazio.

| | motor | nulo principal | nulo suplementar (exploratório) |
|---|---|---|---|
| L | L0, depois L1 | L0 (291), depois L1 (435: 221 rede, 214 composição) | arquétipo rede, todos os `rem_k` = 0 |
| semente | `semente_da_concorrencia` = 1 | 20261017 e 20261019 | 20261018 |
| candidatos medidos | 726 | 726 | 726 |
| erros de execução | 0 | 0 | 0 |
| redes que ordenam | 18 nas populações finais (2 na busca 1, 16 na busca 2); o motor não grava as medidas dos que saíram da população, então 18 é piso | **1** (ótima, troca `mascara`, `registradores` 1: razão 1,453) | 726 |
| cumprem D | 15 (todos na busca 2: 7 ótima e 8 Batcher, todos `simd_imediato`), 2 programas distintos | **0** | 126 (67 ótima e 59 Batcher, todos `simd_imediato`), 2 programas distintos |
| melhor `razao_vs_melhor` na busca | 0,8035 | 1,4529 | 0,7836 |
| menor violação | 0 | 0,417 | 0 |
| tempo | 534,5 s de concorrência | 569,0 s (220,6 + 348,4) | 505,3 s |

Conta de apoio. Um sorteio do arquétipo rede ordena com probabilidade (2 × 0,75¹⁹ + 0,75²⁸) / 3 ≈ 0,29%: retirar qualquer dos 19 comparadores da rede ótima ou da de Batcher, ou dos 28 da inserção, quebra a ordenação. Com 512 sorteios do arquétipo rede, o esperado era 1,5 rede que ordena; saiu 1. A chance de um sorteio cair num dos dois programas vencedores (base ótima ou Batcher, troca `simd_imediato`, nenhum comparador retirado) é (2/3) × (1/4) × 0,75¹⁹ ≈ 0,07%. A chance de pelo menos um em 512 sorteios é de cerca de **30%**. Este sorteio não achou, mas um sorteio cego com o mesmo orçamento empataria com o motor em cerca de 3 de cada 10 vezes.

## 4. A remedida

Script: `scripts/remedir.py`. Resultados: `remedida/rodada_unica/` (medidas, resumo e plano com as ordens). Foram 5 rodadas. Em cada uma, cada candidato foi medido uma vez, em processo novo (executor genérico, depois a ferramenta e o binário, com 21 repetições da carga), em sequência, sem paralelo. A ordem dos candidatos mudou a cada rodada, por rotação e inversão alternadas (as ordens estão no plano). O cache de binários começou vazio. A rede da vencedora de 29/09 foi decodificada da formulação escolhida no `estado.json` de 29/09 e conferida contra `rede_vencedora.json` (iguais). Duração: 93,4 s.

Os "5 melhores do motor" saíram dos vereditos do ledger, que guarda as populações finais. O nulo principal só tinha 1 rede que ordena, então só ela entrou. `razao_vs_melhor` é a medida do D, contra a mais rápida das referências (aqui sempre a AVX2). "busca" é o valor medido na busca; para a vencedora de 29/09, é o valor de 29/09 na VPS.

| candidato | programa (fonte) | base e troca | busca | remedida: mediana [mín; máx] | as 5 rodadas | contra a escalar (mediana) |
|---|---|---|---|---|---|---|
| motor_1 (a escolhida) | de7c37a0a4 | ótima, simd_imediato | 0,8035 | **0,8444** [0,8071; 0,8907] | 0,8907; 0,8146; 0,8906; 0,8444; 0,8071 | 0,6104 |
| motor_2 | de7c37a0a4 | ótima, simd_imediato | 0,8273 | 0,8906 [0,8441; 0,8909] | 0,8905; 0,8909; 0,8906; 0,8441; 0,8909 | 0,6098 |
| motor_3 | ecc6497663 | Batcher, simd_imediato | 0,8404 | 0,8419 [0,8416; 0,8911] | 0,8416; 0,8419; 0,8911; 0,8421; 0,8417 | 0,5769 |
| motor_4 | ecc6497663 | Batcher, simd_imediato | 0,8413 | **0,8418** [0,8396; 0,8912] | 0,8418; 0,8396; 0,8416; 0,8420; 0,8912 | 0,5769 |
| motor_5 | ecc6497663 | Batcher, simd_imediato | 0,8415 | 0,8418 [0,7921; 0,8912] | 0,8912; 0,8419; 0,8404; 0,8419; 0,7921 | 0,5770 |
| nulo_1 (a única que ordena) | a5b1116d48 | ótima, mascara, registradores | 1,4529 | **1,4524** [1,4521; 1,4527] | 1,4524; 1,4524; 1,4521; 1,4524; 1,4527 | 0,9952 |
| vencedora de 29/09 | af8427daff | ótima, ternario, troca na memória | 0,9568 (VPS) | **1,4065** [1,2505; 1,4077] | 1,4060; 1,4066; 1,4065; 1,4077; 1,2505 | 0,9643 |
| suplementar_1 | de7c37a0a4 | ótima, simd_imediato | 0,7836 | 0,8444 [0,8438; 0,8910] | 0,8438; 0,8904; 0,8443; 0,8444; 0,8910 | 0,5788 |
| suplementar_2 | ecc6497663 | Batcher, simd_imediato | 0,7893 | 0,8422 [0,8401; 0,8919] | 0,8919; 0,8416; 0,8401; 0,8422; 0,8912 | 0,5788 |
| suplementar_3 | de7c37a0a4 | ótima, simd_imediato | 0,7924 | 0,8441 [0,7834; 0,8905] | 0,7946; 0,8905; 0,8443; 0,7834; 0,8441 | 0,5912 |
| suplementar_4 | ecc6497663 | Batcher, simd_imediato | 0,7949 | 0,8428 [0,8236; 0,8909] | 0,8909; 0,8428; 0,8418; 0,8236; 0,8909 | 0,6109 |
| suplementar_5 | ecc6497663 | Batcher, simd_imediato | 0,7971 | **0,8417** [0,8415; 0,8911] | 0,8416; 0,8911; 0,8422; 0,8415; 0,8417 | 0,5773 |

Todas as 60 medidas tiveram erro de ordenação 0 e o oráculo de acordo.

**A variação de um mesmo binário, juntando as linhas.** Ótima `simd_imediato` (de7c37a0a4): 20 medidas, mediana 0,8444, faixa 0,7834 a 0,8910, 9 acima de 0,87. Batcher `simd_imediato` (ecc6497663): 30 medidas, mediana 0,8419, faixa 0,7921 a 0,8919, 8 acima de 0,87. A medida dos programas AVX2 é bimodal: cada processo cai perto de 0,842 ou perto de 0,890, e às vezes em 0,78 a 0,81. O ruído que o medidor calcula dentro do processo fica em 0,1%, e a razão da referência contra a cópia dela fica em 1,002 a 1,003. Nenhum dos dois capta esse salto de cerca de 6% entre processos. Os programas escalares quase não variam entre processos (nulo_1: de 1,4521 a 1,4527), salvo um ponto fora na vencedora de 29/09 (1,2505).

**A maldição do vencedor aparece nos dois lados.** A escolhida do motor foi de 0,8035 na busca para 0,8444 remedida. A melhor do suplementar, de 0,7836 para 0,8444. É o mesmo binário. Entre os 15 válidos do motor, a escolha entre a ótima e a Batcher (0,8444 contra 0,8419) está dentro da variação; é ruído.

## 5. A comparação e a conclusão

**Motor contra o sorteio cego pedido (mesma L, mesmo orçamento de 726, mesmo medidor e mesmo D): a seleção ganhou.**
- Melhor remedida: motor 0,8418 [0,7921; 0,8912] (motor_4, a Batcher; a escolhida, a ótima, deu 0,8444) contra nulo 1,4524 [1,4521; 1,4527]. A margem é de **0,61** na razão: o melhor do sorteio leva cerca de 1,73 vez os ciclos do melhor do motor.
- Diferença pareada por rodada (nulo menos o melhor do motor na mesma rodada): 0,611; 0,638; 0,612; 0,611; 0,661. Sempre positiva, com mínimo de 0,61. A variação entre rodadas é de 0,10 no programa do motor (faixa total) e de 0,0006 no do nulo. A diferença é cerca de 6 vezes a maior faixa e muito maior que a variação entre rodadas.
- Candidatos corretos: o motor tem pelo menos 18 que ordenam, 15 que cumprem o D, 2 programas distintos. O nulo tem 1 que ordena e 0 que cumprem o D.
- Tempo das buscas: motor 534,5 s de concorrência; nulo 569,0 s. Equivalentes, porque os dois mediram 726 candidatos no mesmo paralelo.

**O tamanho do que a seleção acrescenta.**
- Contra o sorteio cego, a seleção acrescenta achar a correção (manter todos os comparadores) e a troca `simd_imediato`. São duas escolhas discretas, e o sorteio acerta as duas com 0,07% de chance por sorteio, ou cerca de 30% em 512 sorteios de rede.
- A seleção não acrescentou nada depois disso. No suplementar exploratório (todos os comparadores mantidos, o resto sorteado), a melhor remedida é 0,8417 contra 0,8418 do motor: **empate**. As diferenças pareadas por rodada (suplementar menos motor: −0,047; +0,027; −0,0003; −0,058; +0,050) trocam de sinal e ficam dentro da variação entre rodadas. Os binários são os mesmos.
- Os genes de ordem (`pri_k`) e o gene `registradores`, que em 29/09 fizeram a diferença no código escalar, não mudam o programa nas variantes SIMD.
- Na busca 1 (L0, 291 candidatos), o motor também não achou o programa vencedor. Achou na busca 2, que recomeçou de outra amostra inicial.

**A vencedora de 29/09 neste meio.** Contra a referência escalar, a razão é 0,9643 (mediana de 5 processos). É perto do 0,960 que o programa publicado deu aqui, e o ganho de 29/09 reaparece em parte (3,6% em vez de 4,3%). Contra a referência mais rápida deste processador, a AVX2, a razão é 1,4065. Ela não cumpre o D aqui, e é 1,67 vez mais lenta que a escolhida pelo motor nesta máquina (1,4065 / 0,8444).

**Limites.** Houve uma corrida do motor (semente fixa) e uma réplica de cada nulo. O "30%" é cálculo, não medida. O motor só grava as medidas da população final, então as contagens dele são piso. A referência AVX2 da ferramenta usa a mistura por máscara; a vantagem de `simd_imediato` sobre ela é de instrução, num meio com AVX2 rápido, e não traz rede nova. A variação bimodal entre processos (cerca de 6%) é maior que a resolução de 1% do D e que o ruído que a conferência de distinguibilidade usou. Neste meio, diferenças menores que cerca de 5% entre programas AVX2 não se decidem com uma medida por candidato.

## 6. sha256 dos arquivos principais

Caminhos relativos a `provas/motor_aqui/`, salvo os de `run/` e `/usr/bin/g++`.

```
1353e9bdd29a7295c7226bf6c63abccce056d8cac31f112e5cdbecc3f28c2769  /usr/bin/g++
fe1147243cb19bf711c4e09adbfdc7bc550640ceb0da3edff4eb3ba93560ec9a  run/03_motor_de_29-09/protocolos/calculadora/ordenacao_8_motor_vps.json
6c5eaa92e01d00635a45db3c900e1ea17438730f9c9ed1ed06a785678ee4bb93  run/03_motor_de_29-09/protocolos/calculadora/ordenacao_8_motor_xeon.json
6c5eaa92e01d00635a45db3c900e1ea17438730f9c9ed1ed06a785678ee4bb93  corrida/problema.json
ea716101b6478885dbcd1555080c68fcf4f8f03c0ab935cae10dac75e14ae092  mudancas_no_protocolo.json
82e79fefb4c6a5a16b76cf8d7eb9a4acb6623db03f951f45977c6bae28beec08  respostas_usadas/001_formular_D.json
193d3e9a8c9c51c58d995dcf57b47340f0a5796ce7ef483e41025c59225efaf0  respostas_usadas/002_confirmar_D.json
b716000ff545a3282c40ce8571d9684489f5987ecdb584d3a41fbf8c1c8ca683  respostas_usadas/003_mapear_numeros.json
e531eb52c58e2531dd87a6938faaf70688db6d225e0a0fb25f0bb3c73ba8162d  respostas_usadas/004_propor_modelo.json
3c6a275636745f3bfcd756850206f05514dc109b85abea086c975f0683f9a215  respostas_usadas/005_mapear_numeros.json
3b77fb9c0820ae2624ab21630de554a05af2f876c7f4afd22acac674f1ebf2d8  respostas_usadas/006_medir_alvo.json
0ace4900b5d2d8dc795aeaadb9a5261fef2645bd9e298917e0f627e6ca8c6b61  respostas_usadas/007_conferir_distinguibilidade.json
341488af5886e04cb9d01350d9a68fa1122b31c10c2123a10912b11aa5352c6d  respostas_usadas/008_revisar.json
7b955269c2f2a3ea532132b3bb87c45e5aeecb3929a7f47c6a8bd36e3237e3c3  respostas_usadas/009_mapear_numeros.json
e780de44306ead4a86d603529dca136e290fc5e172be01f0c646dd3e8c7a9e40  respostas_usadas/010_medir_alvo.json
2fd5090f0d0fc8972d66325f3197637ab50ae58e1e5e00644d8c852dd7d27b36  corrida/estado.json
60c591a452c835e92dbcfdafdc018164e311003b4f7b3aafe4d0fad882e260de  corrida/ledger.jsonl
30dd967b522a3227cc328d167f11e89c9bb3d419691b317da8868b99fcfa9a8e  corrida/diario.jsonl
8077727f960550b6a38c0afb06a91cf2ef73f9ae244345317920aa1cd3c85a62  corrida/auditoria.json
3c9b164236bfeeebde88c3cdebe6e66bd2f6a859c4b36dd37bb3d83768f541a6  corrida_roteiro.log
ec8813c59465f4bc25a6959f4b9bf752a2c0eda6b1b1a7f6004c0c94227e7131  nulo/plano.json
79b1cb471cc7d55f8b524b14546af21d2a4d325bf809139b87f49fc620bb6d74  nulo/parte1_L0/medidas.jsonl
0b7165d7f0d05032011da630a53c154ddb5a8fda7f28aa0230a1c59247f269c9  nulo/parte1_L0/resumo.json
362a884c6b1c93103e6fa00a2f565092d82fdce99db5a40c59490be07b456cf2  nulo/parte2_L1/medidas.jsonl
9635e31bd55f6a8efd9a59e5f6c7c46ead985041d3ed3f9553e758fd324496fc  nulo/parte2_L1/resumo.json
2a2b82c4d32089e050745e16b003ce14d0cdd5c9d9b75eca314a278378f0b743  nulo/suplementar_todos_mantidos/medidas.jsonl
669b80cea4dc5ace8d026e15b358faf75335f763c2a948ad67876aaa66d034e2  nulo/suplementar_todos_mantidos/resumo.json
ad387d14696d82372f7caf07c43bf79686d6ea91b238fade1ba6d6d0e982a21c  remedida/rodada_unica/plano_rodado.json
d190cd095a98e8f568a08708b0c1ba293106b1bd073778af80db84b6c07b4c46  remedida/rodada_unica/medidas.jsonl
bda9726104c6920e7e51bb47d3e0ff735dd50ca8d1b4672a2b3cb573fb310a4b  remedida/rodada_unica/resumo.json
e6c9da8269035129e1749560dbc4f94bfebf783ffefc1f9d0b32f8b20d16e326  scripts/ambiente.sh
e0b9ee4d4d0acb16973d3993b897e5a4bff0a2da1a96ec8c7440a54d0a02601b  scripts/nulo.py
4fe2c952b5393d9ec5a06a627138c6a7a2eed345c5205f7e9f40eb93b4d537a2  scripts/remedir.py
```

Nada foi alterado fora de `run/03_motor_de_29-09` (só o protocolo novo foi acrescentado) e de `provas/motor_aqui`. Não houve push nem operação em git remoto.
