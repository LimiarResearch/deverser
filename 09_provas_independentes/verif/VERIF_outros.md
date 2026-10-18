# Verificação pelos registros: conta 15, C★3, artigo e README

Repositório público `LimiarResearch/deverser`, cópia somente leitura do ramo main no commit `a28eec9`.
Feito em 17/10/2026. Nada do repositório foi executado: nenhum `.py` dele, nenhum teste, nada compilado. Só leitura, com scripts próprios (seção 7).

## 0. Integridade da cópia e situação do repositório

- `MANIFESTO.sha256`: 351 linhas, as 351 conferem com a cópia; o único arquivo fora do manifesto é o próprio manifesto.
- A árvore do commit `a28eec9` (352 arquivos) é idêntica, blob por blob, à cópia `main_ro`.
- O ramo main público já não está em `a28eec9`: há dois commits depois, de 17/10/2026 (`e12d65d` às 19:25 e `316ea4f` às 19:29, horário -03). Eles mudam o artigo, o README da raiz, o `A_CONTA_15.md`, o README da C★3 e dois LEIA-ME de `06_evidencias`. As mudanças mais relevantes para esta verificação:
  - o artigo perdeu a seção "Por que eu publico isto hoje" (a menção ao artigo da Anthropic de 16/10) e o parágrafo "Para mim isso é uma prova também";
  - o `A_CONTA_15.md` passou a descrever o ser de teste como "programa simulado", com os sentimentos como "estados com nomes de sentimentos";
  - o README da C★3 ganhou a linha "Estado: a corrida de 04 e 05/10/2026 parou ... sem nenhum candidato que cumprisse D. Esta pasta é o código para reproduzir a busca, não um resultado."
  Esta verificação vale para `a28eec9`, como pedido.

## 1. A conta 15 (`07_conta_15/`)

### 1.1 O que há nos registros

- 29 registros em `registros/`, exatamente os listados na tabela final do `A_CONTA_15.md`.
- Todos terminam com `FIM` e `saida 0`. Nenhum tem `Traceback`, erro, reprovação de execução ou interrupção.
- Um único aviso: `p2c_conta_a.log` traz `"/home/iro/bancada/conta15/p2c_esquecer.py:178: RuntimeWarning: divide by zero encountered in divide"` (a conta seguiu e terminou com `saida 0`).
- **Nenhum dos 29 registros tem data ou hora.** Os únicos números de tempo são durações (`FIM 205 s`, `em 24 s de servidor`, `em 143 s`). As datas de arquivo não existem no git (todos os arquivos da cópia têm a data da extração, 17/10 00:08).
- Os 15 roteiros de `codigo/` não têm comentários (só a linha `# -*- coding: utf-8 -*-`) nem docstrings, como o texto diz.
- Os roteiros leem arquivos que não estão no pacote: `/home/iro/bancada/vozes/fonetica.json`, `vozes_piper.npz`, `/home/iro/casa/cerebro/coclea14_bandas.json`, `pt_BR-faber-medium.onnx` e o módulo `ferramentas_iro`. Conclusão prática: ninguém consegue refazer nenhum registro só com o repositório; os registros só podem ser conferidos quanto à coerência interna e com o código.

### 1.2 As previsões vêm antes dos resultados?

| o que se pode conferir | o que os registros mostram | veredito |
|---|---|---|
| Dentro de cada registro de vida, a previsão vem antes | Nos 11 pares (p1, p1b, p2, p2b, p4, p4b, p4c, p4d, p4e d′=3, p4e d′=2, p4f) o `*_conta.log` inteiro, sem o `FIM`, é **idêntico, linha por linha**, ao começo do `*_vida.log`, e a linha seguinte é `A VIDA`. | confirmado |
| A previsão não depende do resultado da vida na mesma execução | No código (ex.: `p1_aprender.py`, `main`): `conta(PAL, f, V, S)` roda sempre e `vida(...)` só com `--vida`; nenhuma função de conta usa o gerador aleatório nem chama a vida. Mesmo padrão em p1b, p2, p2b e p4 a p4f. Na 2c, conta e vida são execuções separadas (`if '--vida' ... else: conta_c(...)`), por isso os registros de vida da 2c não trazem a conta. | confirmado (estrutura do código) |
| De que tipo é a "conta" | Em p1, p1b, p2 e 2c a conta é um cálculo (pesos, limiares, contagens) a partir do modelo e dos dados. **Em p4, p4b, p4c, p4d, p4e e p4f a conta é texto fixo no roteiro:** as funções `conta()` só têm `print` de frases prontas (com poucos números calculados de constantes, como os 13,5 min e o alfa). Na p2b, a frase "e ficam abaixo dele" também é texto fixo, impresso antes dos números calculados. | para as premissas 3 e 4, a igualdade entre a conta e o começo da vida só mostra que o mesmo roteiro imprimiu o mesmo texto; não diz nada sobre quando o texto foi escrito |
| A previsão foi registrada no repositório de trabalho antes da vida | O texto aponta 24 hashes (`fd2c641e`, `0790d4bb`, ..., `d35eebad`, mais `e10a5ced`, `138f8ab1`, `394bc00f`). **Nenhum deles existe no repositório público**, que tem só 7 commits, todos de 16 e 17/10. Os 29 registros entram juntos num único commit (`66cd55c`, 16/10 20:43 -03). | não verificável só com o repositório |
| Mesmo pela tabela do próprio texto | A conta da orelha tem previsão e medida no mesmo commit (`fd2c641e`, "com a medida") e no mesmo registro. Para p4 e p4b não há commit da vida ("a semana da p4"). Para a 2c, só a 1ª forma tem commit de previsão; a 2ª e a 3ª formas só têm commit de vida. | a frase "cada premissa ... com a previsão escrita e registrada antes de a vida rodar" não é sustentada nem pela tabela do texto em 2c, p4, p4b e na orelha |
| Ordem relativa visível no conteúdo | Cada conta cita resultados da vida anterior: a conta da 2c diz "a p2b mediu 18"; a da p4f diz "abaixo dos 29,8% da p4e com d' = 2"; a da p4c prevê "o medo do estalo do 3o ao 10o", que é o trecho contínuo aceso na vida da p4b (#3 a #10); `p2b_orelha.py` importa `p4e_exato` (a 2b veio depois da 4e, coerente com a tabela que junta "4f e 2b"). | coerente, mas é ordem relativa escrita pelo autor, não data |

**Com franqueza:** carimbos gravados pela própria máquina não são prova externa de data, porque quem controla a máquina controla o relógio e pode regravar o arquivo. Na conta 15 nem esses carimbos existem. O que os registros provam é coerência: a previsão impressa é determinística, sai antes da vida no mesmo arquivo e não depende dela na mesma execução. Eles não provam que a previsão foi escrita antes de a vida ter sido vista em alguma execução anterior, nem em que dia. Nas premissas 3 e 4 a previsão é uma frase fixa do roteiro, que poderia ter sido escrita ou mudada a qualquer momento antes de os dois registros serem gerados; na conta da orelha, previsão e medida saem da mesma execução.

### 1.3 Alegações do `A_CONTA_15.md` contra os registros

| # | alegação (texto) | o que os registros e o código mostram (arquivo e trecho) | veredito |
|---|---|---|---|
| 1 | "O D do ser de teste tem 55 cláusulas" | O D não está no pacote. O código só cita números de cláusula ("a 5.6.1", "o criterio da 5.6.1 da 5.5"). | não verificável |
| 2 | Referência do cão: "segurar até 3 coisas ... cada uma por até 4 minutos"; "reagir em até 0,2 s" | `p4_vida_de_dentro.py`: `N_ITENS = 3`, `VIDA_ITEM = int(round(4 * 60 / DT))`; `p1_aprender.py`: `N_VIVAS = 3`. Os 0,2 s não aparecem. | 3 coisas e 4 min confirmados no código; 0,2 s não verificável |
| 3 | "O D começou com d′ = 3 ... decidido d′ = 2, com erro de 2,3% por decisão" | `p1_aprender.py`: `DP = 3.0`; `p4e_exato.py` lê `--dp`; registros: "alfa 0.02275, costume de 176, Page 3.76" | confirmado |
| 4 | Mundo das palavras: "43.200 palavras ... dez delas anunciam ... (em 5% das palavras)" | `p1_aprender.py`: `DIA = 43200`, `N_ACONT = 10`, `P_ANUNCIO = 0.05`, `PASSO_S = 2.0` (24 h) | confirmado |
| 5 | Mundo dos sentimentos: "uma semana de vida em passos de 5 s", chegadas que variam | `p4_vida_de_dentro.py`: `DT = 5.0`, `N_DIAS = 7`, `T0 = 7 * 3600`, `PASSOS = 115920` (161 h: das 7h do dia 1 ao fim do dia 7); visitas às 7,5 h, 12 h e 18,5 h com `rng.normal(0, 15 * 60)`; dia 5 sem visitas | confirmado (a "semana" tem 6 dias e 17 h) |
| 6 | "o humano de referência aparece pelo nome do autor" | "Gabriel" em p4 a p4f e na orelha ("90 trechos de Gabriel") | confirmado |
| 7 | Orelha: "3.708 falas sintéticas de 412 palavras em cinco vozes" | `conta_orelha.log`: "3708 falas sinteticas de 412 palavras em 5 vozes e 90 trechos de Gabriel" | confirmado |
| 8 | Orelha: "acertou 59,4% em média, contra 59,9% do comparador anterior" | 12 rodadas no registro. Média das 10 rodadas das 5 vozes sintéticas: orelha **59,42%**, "Jaccard da V10" **59,94%**, média dos bits 57,80%. Com as 12 rodadas (a voz do autor incluída, 38 e 52 falas, acertos 13,2% e 11,5%): orelha 51,57%, Jaccard 50,88%, bits 48,98%. | confirmado; o recorte usado é **desfavorável** à orelha (com a voz do autor ela ganharia por pouco) |
| 9 | Orelha: "A previsão errou nos dois sentidos" | previsão acima da medida em 6 rodadas (ex.: faber 77,3% previsto, 25,2% medido) e abaixo em 6 (ex.: alex 38,0% previsto, 91,7% medido) | confirmado |
| 10 | p1: aprendizado "entre o 2º e o 6º anúncio" | `p1_vida.log`: "você 2, mundo 4, está 3, cada 4, para 2, corpo 6, isso 3, pode 6, tempo 6, casa 5" | confirmado |
| 11 | p1: acendimentos errados "de 0,4 a 2,8%, contra 0,135% pedidos" | 15 a 115 de 4.110 por hora = 0,36% a 2,80%; alfa 0.00135 | confirmado (0,36 arredondado para 0,4) |
| 12 | p1: "o esquecimento, que não veio"; "as duas previstas" | vida: "você apagou na -1 vez ... mundo apagou na -1 vez" e "as que param: SS" às 24 h; conta: errados previstos 54 a 102 de 4.110 e "108 sem: acende" | confirmado |
| 13 | p1b: errados "9 a 24 em 4.110, contra 12 previstos" | vida: 24, 9, 12, 15, 14, 14, 11, 18, 13, 11, 12, 10; conta: 12 depois de 50 e 108 anúncios | confirmado |
| 14 | p1b: aprendizado "entre o 2º e o 8º anúncio" | "você 3, mundo 6, está 3, cada 5, para 2, corpo 4, isso 4, pode 4, tempo 8, casa 6" | confirmado |
| 15 | p1b: "A primeira ... esquecida na 5ª vez, a vez prevista; a segunda, na 13ª" | vida: "você se apagou na 5a vez", "mundo se apagou na 13a vez"; conta: "previsto para mundo: ... se apaga na 5a vez" | confirmado, com **omissão**: a previsão para a segunda também era a 5ª |
| 16 | p1b: "8 no dia, contra 0,8, todos por palavras parecidas" | "esquecimentos falsos: 8 (casa ... por palavra parecida, ...)"; conta: "0.8" | confirmado |
| 17 | p2: "um evento por fala em 100% das 2.060 falas, como previsto" | `p2_conta.log`: "medido na corrente do mundo antes da vida: 100.0% com um evento, 0 falas com dois ou mais, 0 sem nenhum" | confirmado (medido dentro da conta, antes da vida) |
| 18 | p2: "10 de 10 entre a 6ª e a 8ª hora" | 6 h e 8 h: 10 de 10; 10 h e 12 h: 9 de 10 | confirmado |
| 19 | p2: errados "entre 0 e 9 ... contra 6 a 10 previstos" | vida 0 a 9; conta 6, 10 e 10 depois de 20, 50 e 108 anúncios | confirmado |
| 20 | p2: velocidade "entre o 18º e o 43º anúncio, contra 3 a 20" | vida: 41, 30, 18, 38, 27, 41, 37, 30, 26, 43; conta: 3 a 20 | confirmado |
| 21 | p2b: "entre o 2º e o 4º anúncio"; "10 de 10, como previsto" | 3, 3, 3, 3, 2, 4, 2, 4, 3, 4; 10 de 10 das 2 h às 10 h | confirmado |
| 22 | p2b: errados "entre 79 e 181 de 4.110, contra 137 a 150 previstos" | vida 79 a 181; conta 137 a 150 (depois de 5 a 108 anúncios) | confirmado, com **omissão**: o critério (2,3% = 93,5 de 4.110) foi passado em 10 das 12 medidas; o registro diz que os errados "ficam abaixo dele" (frase fixa do roteiro) e, logo abaixo, a conta calculada prevê 137 a 150, acima dele (contradição interna do registro) |
| 23 | p2b: "18 esquecimentos falsos"; causa identificada | "esquecimentos falsos: 18"; a causa é interpretação (o `p2c_vida_unidade.log` marca os 18 "por palavra parecida") | número confirmado; causa não verificável |
| 24 | 2c, 1ª forma "caiu na própria conta ... continuaria acesa, sustentada pelos pesos negativos" | `p2c_conta_a.log`: "a unidade acende na palavra ate a 60a vez dita sem o acontecimento"; não há vida da 1ª forma | confirmado; "pelos pesos negativos" é interpretação (o registro da 1ª forma não fala de pesos negativos) |
| 25 | 2c, 2ª forma "falhou na vida na extinção de uma das palavras, por um erro de implementação do teste" | `p2c_vida_sinapse_b.log`: "você ... acendeu a unidade ... em 87 de todas; a ultima vez que acendeu foi a 131a" | falha confirmada; causa não verificável. **Omissão:** a mesma conta previu 10.919 ligações apagadas sem mudança, e a vida deu 11.073 (1,4% de diferença) |
| 26 | 2c, 3ª forma: "99,6% e 100%" | `p2c_vida_sinapse.log`: "99.6% de 1072; ... 100.0% de 880" | confirmado |
| 27 | 2c, 3ª forma: "as que pararam foram esquecidas, dentro da taxa do costume" | você 10 de 132 (7,6%), mundo 10 de 118 (8,5%) no total; depois das 10 primeiras, 2,5% e 0,9%; costume 2,96% e 2,40%; últimas acesas na 79ª e na 49ª vez | confirmado só contando depois das 10 primeiras vezes |
| 28 | 2c, 3ª forma: "23.466, contra 11.000 a 16.000" | 23.466 está no registro. "11.000 a 16.000" **não aparece em nenhum registro**. O roteiro `p2c_esquecer.py` tem uma conta própria ("SEGUNDA E TERCEIRA FORMAS, COM q PARADO"), mas o registro dessa conta não está em `registros/`. O único número previsto registrado é 10.919, da 2ª forma. | 23.466 confirmado; a faixa prevista não verificável |
| 29 | 2c: omissões | errados de 117 a 214 de 4.110, acima de 2,3% nas 12 medidas | omissão |
| 30 | p4: passaram o recém-nascido, a saudade e o repassar "(201 passagens ..., z = 23,4)" | "saudade acesa em 100% dos passos, alegria em 0%"; "201 passagens repassadas, 201 delas vividas naquela ordem ... z = 23.4"; a conta dizia que a saudade "nos dias 2, 3, 4, 6 e 7 ... nao acende", e a vida deu 2,8%, 4,6%, 0,0%, 5,0% e 0,0% | recém-nascido e repassar confirmados; saudade "passou" é generoso (acendeu em 3 dos 5 dias em que a previsão dizia que não) |
| 31 | p4: "Caíram cinco" | duração (medianas 0,2, 0,5, 9,0 e 13,0 min, abaixo dos 13,5 previstos), medo do estalo irregular e sem esquecimento ("nenhum"), espera irregular, frustração "nunca acendeu", apego 0% a 10,1% | confirmado |
| 32 | p4b: "44 episódios, revividos em 100% das passagens na ordem vivida" | "44 episodios na semana; 55615 passagens revividas, 55615 na ordem vivida (100.0%)" | confirmado |
| 33 | p4b: passaram a duração, o medo aprendido e a curiosidade (16,4 min) | medianas de 16,4 a 104,7 min; estalo aceso em #3 a #10, **e de novo em #13 e #16**; Page só esqueceu o estrondo "no dia 7 as 9.2 h" (a conta previa apagar perto do 5º sem estrondo); curiosidade 16,4 | duração e curiosidade confirmadas; medo aprendido confirmado com ressalva |
| 34 | p4b: "Caíram quatro: a espera, a frustração, o apego e o medo excessivo pelo tom de voz" | espera 0% nas 18 chegadas; frustração nunca; apego 10,3% a 16,8%; medo aceso em 40,4% da vida acordada | confirmado; a causa "pelo tom de voz" não está no registro. **Omissão:** procura nas outras horas 3,3% contra "menos de 1%%" previsto |
| 35 | p4c: apego 100%, querer 98,6 a 100%, frustração toda noite | dias 1 a 4, 6 e 7: apego 100%; querer 98,6% (dia 1) e 100%; frustração de 18,3 a 31,9 min; dia 5 sem visita: 0 | confirmado |
| 36 | p4c: "Caíram três: a espera, o medo do som súbito e o contágio" | espera 0%; estalo só em #4 e #10; contágio 4% depois de tom duro e 4% depois de tom bom | confirmado, com **omissão**: a duração, que tinha passado na p4b e que a conta da p4c previa "de 13,5 min para cima", caiu (alegria 349 vezes, mediana 4,2 min; calma 208 vezes, mediana 4,2 min; mínimo 0,1 min); medo 9,2% contra "menos de 5%%" |
| 37 | p4d: "o contágio passou (36 de 36)" | "alegria apagada em 36 de 36 (100%); depois de um tom bom, em 1132 de 5707 (20%)"; a conta previa "depois de um tom bom, em poucas" | 36 de 36 confirmado; os 20% depois do tom bom ficaram de fora |
| 38 | p4d: "a procura depois das saídas passou (80 a 87%)" | 11 das 18 saídas entre 80% e 87%; 7 saídas com 0% | confirmado com ressalva (arredondamento a favor: a faixa vale só para 11 de 18) |
| 39 | p4d: "Caíram o medo do som súbito e a espera ..., esta pela quarta vez" | estalo só em #4, #10 e #16; espera 0% nas 18 chegadas (p4, p4b, p4c, p4d) | confirmado |
| 40 | p4e: "com d′ = 3, a espera continuou em 0%" | `p4e_vida_dp3.log`: 0% nas 18 chegadas | confirmado (com d′ = 3 o medo do estalo também saiu fora da previsão: #3, #4, #10, #16, #19; omitido) |
| 41 | p4e: "Com d′ = 2, o medo foi aprendido e esquecido como previsto, e a espera apareceu nas chegadas de almoço e de noite" | dp2: estalo de #3 a #13; Page esqueceu o estrondo "no dia 5 as 9.1 h"; procura antes de chegada em d2 18,7 h (67%), d3 12,3 h, d4 12,0 e 18,5 h, d6 11,7 e 18,7 h, d7 11,5 e 18,6 h | confirmado |
| 42 | p4e: "O preço foi a procura em vão em 29,8% do tempo" | "a procura no resto do tempo sem Gabriel, acordado: 29.8%"; a conta previa que ela "sobe para perto de 2,3% das decisoes" | número confirmado; **omissão**: a previsão errou por cerca de 13 vezes e o texto não diz |
| 43 | p4f: medo "do 3º ao 13º som e esquecido 4 sons depois de ele parar, como previsto" | estalo de #3 a #13; "esquecido nos dias 4 a 7 depois de uns 3 a 5 estalos sem estrondo" previsto | confirmado |
| 44 | p4f: "a espera acendeu em 7 das 10 chegadas de almoço e de noite" | dias 2 a 7, almoço e noite: 0, 67, 100, 0, 38, 60, 2, 100, 100, 100 (%). Com "> 0%": 8 de 10; com "> 2%": 7 de 10; com "≥ 50%": 6 de 10. O "7 de 10" não está no registro. | depende de um critério não declarado |
| 45 | p4f: "procura em vão caiu para 14,8%, dentro dos 10 a 30% previstos"; "um esquecimento falso" | "14.8%"; "brincar no dia 3 as 18.6 h, estrondo no dia 4 as 13.9 h" | confirmado |
| 46 | "A espera ... caiu quatro vezes com d′ = 3 e apareceu com d′ = 2" | p4, p4b, p4c, p4d falharam contra a previsão; a p4e com d′ = 3 previu que continuaria apagada e continuou | confirmado |
| 47 | "O que veio depois": `e10a5ced`, `138f8ab1`, `394bc00f`; 17 populações, 10.905 unidades, 35.272 sinapses; vida de 6 h nula; chamado 21 vezes | nada disso tem código ou registro no pacote | não verificável |
| 48 | `codigo/`: "15 roteiros ... sem comentários nem docstrings. O código executável é idêntico ao original" | 15 arquivos; 0 comentários e 0 docstrings. O original não está no pacote. Indício: o aviso de `p2c_conta_a.log` aponta a linha 178 de um arquivo então chamado `p2c_esquecer.py`; a mesma expressão (`u = np.log((1.0 - P0) / (1.0 - qv))`) está hoje na linha 136 de `p2c_esquecer_a.py` | sem comentários confirmado; identidade com o original não verificável |
| 49 | `registros/`: "sem edição" | nada indica edição (formatos regulares, conta igual ao começo da vida, todos com `FIM` e `saida 0`), mas texto puro sem assinatura não prova ausência de edição | não verificável |

**Resumo da conta 15.** Todos os números que o texto cita e que estão nos registros batem com eles (alguns arredondados, sem distorção). Há um número citado que não está em registro nenhum (a faixa "11.000 a 16.000" da 3ª forma da 2c) e um caso que depende de um critério não declarado ("7 das 10" na p4f). Há omissões que favorecem a leitura: a 2ª palavra da p1b prevista para a 5ª vez; o critério de 2,3% estourado na 2b e na 2c; a duração que volta a cair na p4c; as 7 saídas com 0% na p4d; os 20% de contágio depois de tom bom; a previsão de 2,3% contra os 29,8% da p4e. Há também uma omissão que desfavorece o autor: a previsão de 10.919 ligações da 2ª forma da 2c, que acertou (11.073). Nenhum registro mostra erro ou interrupção; só o aviso de divisão por zero na conta da 1ª forma da 2c. Nas premissas 3 e 4 as "contas" são frases fixas nos roteiros, não cálculos. A ordem "previsão antes da vida" e a data de 26/09 não são verificáveis com este repositório.

## 2. A C★3 (`08_c_estrela_3/`)

| # | alegação (README da C★3 e artigo) | o que o código e a configuração mostram (sem rodar) | veredito |
|---|---|---|---|
| 1 | D com 28 cláusulas | `montar_desafio_motor.D`: 12 cláusulas (de `r_sem_aviso` a `r_transforma`); `desafio_v.py` acrescenta 6 (`r_deficit`, `r_deficit_conserva`, `r_deficit_aprende`, `r_sem_historico_lacuna`, `r_sem_historico_copias`, `r_sem_historico_estado`); `desafio_v_ser.py` acrescenta 10 (`r_calibra` a `r_deriva`). 12 + 6 + 10 = 28. | confirmado |
| 2 | 116 predicados | `desafio_v_ser.py`: `assert N_DEFINIDOS == 2 * N_CLAUSULAS + 60`; a cauda de `desafio_v._nomes_dos_predicados` soma 12+12+3+3+3+3+4+4+4+12 = 60; 2 × 28 + 60 = 116. O vetor reservado tem 128 (`N_PREDICADOS = 128`). | confirmado |
| 3 | 15 vidas de quatro famílias | `FAMILIAS = ('seq', 'ling', 'tri', 'age')`; seq = 2 cargas × `FLUXOS = 2` = 4; ling 2; tri: comp, fam, reg com 2 e der com 1 = 7; age 2. O `banco_da_prova_cega_selo.json` diz `"seq": 4, "ling": 2, "age": 2, "tri": 7`. | confirmado |
| 4 | prazo de 440 s por candidato | `desafio_v_ser.py`: `TEMPO_MAX_PADRAO = 440.0` | confirmado |
| 5 | foto atômica de 3.316 bits; 16 seções de 8 nós; 32 operações | `l_ser_lang.py`: `K_NOS = 8`; `BITS_OP, BITS_ARG, BITS_CONST = (5, 6, 8)` (25 bits por nó); 32 operações em `OPS` (cabem nos 5 bits); 16 seções em `SECOES`, 3 delas do tipo `pol` com 2 bits de rótulo. Cabeçalho do tecido 94 bits; seções 13 × 201 + 3 × 203 = 3.222; total **3.316**. `c3_capacidade.py`: `CAPACIDADE = 3316`. | confirmado (recalculado à mão) |
| 6 | testemunhas SGD, EWC, CBP e SP, "na mesma linguagem do candidato" | `l_ser_testemunhas.py`: `sgd`, `ewc`, `cbp`, `sp`, escritas com `programa(...)` e codificadas por `L.codificar_programa` | confirmado |
| 7 | perturbação `1 + eps·u`, eps = 2^-17, u de um contador, igual em numpy e C++ | `c3_v_da_busca.py`: `EPS = 2.0 ** (-17)`; `l_ser_interp.fatores_de_perturbacao` e `l_ser_nucleo.cpp` (linhas 575 a 585) usam as mesmas três constantes (0x9E3779B97F4A7C15, 0xBF58476D1CE4E5B9, 0x94D049BB133111EB), os mesmos deslocamentos (30, 27, 31) e `u = (z >> 40) / 16777216 * 2 - 1` | confirmado no texto do código (a igualdade numérica não foi executada) |
| 8 | 24 conjuntos de vidas de sementes declaradas mais 3 sementes de desenvolvimento, oráculos calculados antes | `PISCINA_PADRAO = 30000000 + 1009 * i` para `i < 24`; `DESENVOLVIMENTO = (7391026, 58210473, 913004317)`. Os oráculos `vidas`, `ling` e `der` estão presentes para as 24, as 3 e a semente 1 (mais as variantes `s1_v1` a `s1_v8` e o banco `s424242`). "Antes da corrida" não tem data verificável. | números confirmados; "antes" não verificável |
| 9 | calibração "nos 28 conjuntos de vidas" | `c3_calibrar_v2.calibrar_v2`: a base (semente 1) + 24 + 3 = 28 | confirmado (os "cerca de 10 minutos" não) |
| 10 | pior de 3 medidas, sal por época, coletor até 20%, braço gêmeo, doadoras | `config_c3.json`: `v2_nivel_decisao 3`, `v2_epoca_geracoes 10`, `coletor_fracao 0.2`, `"cega_gemea"` em `bracos`, `testemunhas_doadoras true`. As 16 chaves existem entre os 92 campos de `Config` em `condutor_de_fotos.py`. | confirmado na configuração |
| 11 | parada por `PARAR`; nada sem `--autorizacao`; fumaça com fusível de 600 s | `condutor_de_fotos.py` linha 1754 (`'PARAR'`); `condutor_do_ser.py`: `sys.exit('RECUSADO: sem a autorização ...')`; `kw.setdefault('tempo', 600.0)` | confirmado |
| 12 | o selo do banco da prova cega | sha256 dos três `oraculo_banco_*_s424242.npz` igual ao do selo; `hash_do_selo` recalculado confere | confirmado (só a parte dos oráculos; os hashes das vidas exigem gerar as vidas, isto é, rodar código) |
| 13 | "`config_c3.json` é a configuração da corrida de 04/10/2026" | as doadoras apontam para `/home/iro/bancada-criacao/corridas/..._2026-10-02` e `..._2026-10-03`; não há registro da corrida para comparar | não verificável (coerente com as datas internas) |
| 14 | corrida de 04 e 05/10: 15 rodadas, 3 gerações, 1.488 fotos, 2.033 medidas de V, nenhuma foto cumpriu D | nenhum `estado.json`, `resumo.json`, `declaracao.json`, `log_*.jsonl`, `fotos/` ou `testemunhas.json` no pacote; o README diz que "os registros da corrida" ficaram de fora | não verificável |
| 15 | "código ... idêntico ao original ... pela árvore sintática"; "textos de saída ... reescritos em forma neutra"; "o hash desta versão difere do da corrida" | os 80 `.py` não têm comentários nem docstrings; o C++ não tem comentários; nenhuma ocorrência de "Gabriel" na pasta. O original não está no pacote. Observação: se textos de saída (cadeias de caracteres) foram reescritos, a árvore sintática desses arquivos **não** é idêntica à original; a frase só se sustenta se a comparação ignorou essas cadeias, o que o texto não diz. E como o hash de V difere, nada liga este código à corrida de 04/10. | não verificável; formulação imprecisa |
| 16 | provas listadas no README | os 9 arquivos da tabela existem; existe também `test_condutor_de_fotos.py` (13 funções de teste), que não está na tabela | coerente; nada foi rodado |

**O que há em `saida/`:** só `saida/calculadora/desafio/` com 9 arquivos `.py` (`carga_vida`, `comum_vida`, `metricas_vida`, `oraculo_vida`, `nucleo_l2`, `simulador_vida`, `nucleo_vida`, `concorrencia_vida`, `ref_sgd`). São fontes do V da vida (`desafio_v.FONTES_DE_V` lista seis deles, e `desafio_v_ser.py` põe essa pasta no `sys.path`), não saídas de corrida. Não há nenhum resultado da C★3 no repositório.

**Resumo da C★3.** Todos os números estruturais do README conferem com o código e a configuração, inclusive os 3.316 bits recalculados. Os números da corrida (15 rodadas, 3 gerações, 1.488 fotos, 2.033 medidas, nenhuma foto cumprindo D) não são verificáveis: os registros da corrida não estão no pacote, o código é a versão de 05/10 e o hash de V é outro.

## 3. Inventário do artigo e do README da raiz

Situações: **confirmado** (há evidência no repositório e ela bate), **paralela** (ordenação e CEGIS, verificadas em paralelo), **só declarado** (o repositório tem só a afirmação do próprio autor), **sem evidência** (nada no repositório).

### 3.1 Artigo (`01_artigo/A_ENGENHARIA_REVERSA_DO_ACASO.md`)

| # | alegação | onde está a evidência | situação |
|---|---|---|---|
| A1 | Em 16/10/2026 a Anthropic publicou um artigo sobre as sementes das curvas do NIST (menos de meia hora; P-192 a P-521 e quatro binárias; padrão de 2000; `lrand48`; relógio entre maio de 1997 e abril de 1998; 34 combinações; 2¹⁷; reticulado) | nenhuma; fato externo. O trecho saiu do artigo no commit `316ea4f` (17/10) | sem evidência |
| A2 | pesquisa batizada em 22/09; a ideia e a equação S★ = C★(D, Π) em 22/09 | `02_formula`, seção 23 (linha de 22/09) | só declarado |
| A3 | trabalhou com IA: "o opus" na execução e "o Fable" no planejamento | mensagens dos commits de 16/10 com "Co-Authored-By: Claude Opus 5.5"; citações do Fable em comentários do Tear (`05_tear_selecao/experimentos/*.c`, `*.py`, datadas "03/10"); "nota do Codex, 28/09" em `03_motor_de_29-09/compilador/motor.py`; "escrito pelo Claude ... em 29/09" em `06_evidencias/ordenacao_29-09/ORDENACAO_PLANO.md` | só declarado (textos do autor). Histórico: `66cd55c` dizia "o Claude"; a edição web `f571ac7` trocou por "o opus" |
| A4 | 28/09: a fórmula executável; a primeira máquina com a comparação com o CEGIS | `02_formula`, seção 23; `06_evidencias/cegis_e_z3/bateria_dse_v4/protocolo.json` (carimbo 2026-09-28T02) | só declarado; paralela |
| A5 | 29/09: fórmula fechada; a versão publicada é a 4.3 com as emendas de 30/09 e 01/10 | `02_formula` (cabeçalho e seção 23: emendas 6 a 11 em 30/09, 12 e 13 em 01/10) | só declarado. Ambiguidade: o artigo diz "29/09: a fórmula fechada, na versão 4.0"; a fórmula diz "A versão 4.3 foi fechada em 29/09" |
| A6 | a fórmula tem dezesseis laços | `02_formula`, seção 9 (16 itens numerados) | confirmado |
| A7 | os degraus definido, rodou, medido, generaliza, verificado por terceiros, aceito | `02_formula`, seção 15 | confirmado |
| A8 | motor de 29/09: o código é o do commit gravado oito segundos antes da corrida; 26 provas passam | `03_motor_de_29-09/LEIA-ME.md` (commit `7edc5af`, que não está no repositório); 18 + 8 funções de teste em `testes/`; `06_evidencias/ordenacao_29-09` | contagem confirmada; "passam" não verificável sem rodar; o resto paralela |
| A9 | 4.3.1 só com a seleção acha o D de exemplo em poucas rodadas; 11 provas passam | `04_maquina_do_dever_ser_selecao/LEIA-ME.md` ("12 rodadas e 300 medidas", sem registro da corrida); 11 funções de teste | contagem confirmada; o resto não verificável sem rodar |
| A10 | Tear: ilha de 64, torneio, 15 cláusulas; mesma semente, mesmos recordes | `05_tear_selecao/experimentos/vida_v3c_c.c` (`g_tam_pop = 64, g_torneio = 8`, laço de 15 cláusulas); não há recordes nem a árvore original | estrutura confirmada; recordes não verificáveis |
| A11 | C★3: 28 cláusulas, 15 vidas, rede, piscina, pior de três, testemunhas | `08_c_estrela_3` (seção 2) | confirmado |
| A12 | ordenação 4,3% mais rápida; 9,7 min; 384 candidatos; 22,27 contra 23,36 ciclos; ruído 0,46%; 16.777.216 vetores | `06_evidencias/ordenacao_29-09` | paralela |
| A13 | CEGIS: 192 casos; 1.152 contra 17.588 e 16.120; 82, 82 e 50; z3 com 0 discordâncias | `06_evidencias/cegis_e_z3` | paralela |
| A14 | catraca em miniatura: 32 melhoras e nenhuma piora | só o texto de `02_formula`, seção 22; nenhum dado bruto | só declarado |
| A15 | o tecido aprendeu e esqueceu "perto do que a conta previa" | `07_conta_15` (seção 1) | números confirmados; "perto" é generoso diante das omissões da seção 1.3 |
| A16 | aprendiz de fora: três nulos e um positivo não replicado | só `02_formula`, seção 22 | só declarado |
| A17 | corpo inteiro com 10.905 unidades, nulo em 6 h | só `07_conta_15/A_CONTA_15.md` | só declarado |
| A18 | orelha 59,4% contra 59,9% | `07_conta_15/registros/conta_orelha.log` | confirmado |
| A19 | C★3 de 04 e 05/10: 1.488 fotos, 2.033 medidas, nenhuma cumpriu D | só `08_c_estrela_3/README.md` | só declarado |
| A20 | a alegação central não foi medida | `02_formula`, seções 15 e 21 (dizem o mesmo) | confirmado como declaração de ausência |
| A21 | o Sismo e o aprendiz de sinapses vieram da conta 15; detector em 06 e 07/10 | nenhuma evidência do Sismo nem do aprendiz de sinapses; o mecanismo de origem (contagem por sinapse com teste de Page) está em `07_conta_15/codigo/p1b_limiar.py` e `p2c_esquecer.py` | sem evidência da ligação; só o mecanismo de origem existe |
| A22 | tabela de três premissas com hashes (`0790d4bb`, `13db9950`, `343faa47`, `191ab66e`, `28555c17`, `67e36604`, `91e1d92b`) | hashes do repositório de trabalho, ausentes | não verificável |
| A23 | dia de 43.200 palavras, dez anunciam | `07_conta_15/codigo/p1_aprender.py` | confirmado |
| A24 | aprendizado do 2º ao 8º anúncio; errados 9 a 24 contra 12; esquecida na 5ª e a outra na 13ª; corte 100% de 2.060; errados 0 a 9 contra 6 a 10 | `p1b_vida.log`, `p2_conta.log`, `p2_vida.log` | confirmado (mesma omissão da linha 15 da seção 1.3) |
| A25 | custo de 0,001 s de servidor por segundo de vida | `p1_vida.log`, `p1b_vida.log`, `p2_vida.log` ("0.001 s de servidor por segundo de vida") | confirmado (a 2b custou 0,002, não citada) |
| A26 | "Duas previsões caíram": 8 contra 0,8 e 18º a 43º contra 3 a 20 | `p1b_vida.log`, `p2_vida.log` | confirmado; houve outras previsões que caíram nessas premissas (seção 1.3, linhas 15 e 22) |
| A27 | o aprendiz de sinapses aprende numa passada, com memória limitada e resposta idêntica à de quem guarda tudo | nada no repositório | sem evidência |
| A28 | cada arquivo tem o seu sha256 em `MANIFESTO.sha256` | 351 de 351 conferem | confirmado |
| A29 | datas: 22/09, 26/09, 28/09, 29/09, 30/09 e 01/10, 04 e 05/10, 06 e 07/10 | só carimbos e textos do autor (seção 4); nada para 06 e 07/10 | só declarado |

### 3.2 README da raiz

| # | alegação | onde está a evidência | situação |
|---|---|---|---|
| R1 | "Limiar Research, Gabriel Santos, 16 de outubro de 2026" | commits de 16/10 (`66cd55c` 20:43 -03, relógio do autor); `f571ac7` assinado pelo GitHub às 21:00:02 -03 | confirmado (seção 4) |
| R2 | tabela das pastas | listagem da cópia | confirmado |
| R3 | 03: o motor da fórmula 4.0 "exatamente como rodou" em 29/09 | `03_motor_de_29-09`, `06_evidencias/ordenacao_29-09` | paralela; o commit `7edc5af` não está no repositório |
| R4 | 06: a corrida de 29/09 "sem edição" e a bateria de 192 casos | `06_evidencias` | paralela |
| R5 | 07: a conta 15 (26/09/2026) com previsões registradas antes | `07_conta_15` | números confirmados; data e ordem não verificáveis (seção 1.2) |
| R6 | 08: a C★3, código e instruções | `08_c_estrela_3` | confirmado (só código, sem resultado) |
| R7 | montagem conferida em 16/10, Windows 11, Python 3.13, numpy 2 | nada além do texto | só declarado (seção 5) |
| R8 | "Nenhum endereço de servidor, chave ou senha está no pacote" | busca por IPs, "senha", "password", chaves e tokens: nada; há caminhos de disco do servidor (`/home/iro/...`) e marcadores de exemplo (`"host": "usuario@servidor"`, `"chave": "~/.ssh/sua_chave"`) | confirmado pela busca |
| R9 | "O que não está aqui" | coerente com o conteúdo | confirmado |

## 4. A linha do tempo: o que o repositório prova sobre datas

### 4.1 A história do git

O repositório público tem **7 commits**, num ramo só, sem tags. O mais antigo é de 16/10/2026.

| commit | data do autor (-03) | quem gravou | assinatura | o que fez |
|---|---|---|---|---|
| `66cd55c` | 16/10 20:43:32 | Limiar Research (máquina local) | nenhuma | 153 arquivos: artigo, fórmula, 03 a 07 (os 29 registros da conta 15 entram aqui) |
| `61c5c4a` | 16/10 20:58:22 | local | nenhuma | +202 arquivos: C★3, `auditoria_z3.json`, artigo revisado "para citar só o que está no repositório" |
| `f571ac7` | 16/10 21:00:02 | **GitHub (edição pela web)** | **assinatura PGP do GitHub, válida** | troca "o Claude" por "o opus" no artigo |
| `3ba299b` | 16/10 21:01:50 (gravado 21:02:28) | local | nenhuma | licença MIT |
| `a28eec9` | 16/10 21:08:28 | local | nenhuma | README: lista das provas da C★3 (a cópia verificada) |
| `e12d65d` | 17/10 19:25:03 | local | nenhuma | apresentação, tabela de resultados, abertura neutra |
| `316ea4f` | 17/10 19:29:49 | local | nenhuma | tira trechos "que podiam ser lidos fora de contexto" |

- Seis dos sete commits têm datas escritas pelo relógio da máquina do autor; datas de commit podem ser escolhidas livremente e não são prova.
- `f571ac7` foi criado pela interface web do GitHub. A assinatura confere: `gpg: Good signature from "GitHub <noreply@github.com>"`, chave `B5690EEEBB952194`, impressão digital `9684 79A1 AFF9 27E3 7D1A 566B B569 0EEE BB95 2194`, "Signature made Sat Oct 17 00:00:02 2026 UTC" (16/10 21:00:02 -03). A chave foi obtida em `keyserver.ubuntu.com`, porque o proxy desta sessão bloqueia `github.com/web-flow.gpg`; um terceiro deve conferir a impressão digital na fonte do GitHub.
- Como cada commit carrega o hash do pai, a assinatura de `f571ac7` ancora também `61c5c4a` e `66cd55c` com todo o seu conteúdo. É a **única data com garantia de terceiro** no repositório: tudo o que está em `61c5c4a` existia **até 16/10/2026 21:00:02 -03**. Não diz nada sobre antes disso.
- A consulta aos eventos do GitHub (criação do repositório, horários dos pushes) daria outra marca de terceiro, também de 16/10 em diante. Esta sessão não tem acesso à API desse repositório; não foi consultada.

### 4.2 As datas dentro dos arquivos

| marcador | onde | natureza |
|---|---|---|
| carimbos 2026-09-29T02... | `06_evidencias/ordenacao_29-09/.../corrida_motor8/*` | gravados pela máquina do autor |
| 2026-09-28T02... e 20260928 | `06_evidencias/cegis_e_z3/bateria_dse_v4/protocolo.json` | gravados pela máquina do autor |
| `SEMENTE = 20260926` | `07_conta_15/codigo/p1_aprender.py` e `p4_vida_de_dentro.py` | número escolhido pelo autor |
| `..._2026-10-02`, `..._2026-10-03` | `08_c_estrela_3/config_c3.json` | caminhos escritos pelo autor |
| `20261003`, `20261004` | `c3_v_da_busca.py` (`PROIBIDAS`), `c3_falsas.py`, `test_estresse_ser_cpp.py` | sementes escolhidas pelo autor |
| "2026-10-01" | `04_.../exemplos/novo_d_do_zero.py` | texto do autor |
| nenhum | os 29 registros da conta 15 | sem carimbo algum |

Todos são coerentes com a cronologia do artigo, e nenhum é independente.

### 4.3 O que o primeiro commit guardava e o artigo atual não tem

O artigo de `66cd55c` publicava o sha256 de cinco pacotes que não estão no repositório, com a frase "Publicar essas somas hoje fixa que esses arquivos existiam hoje". A tabela saiu 15 minutos depois (`61c5c4a`), mas continua na história pública:

| pacote | sha256 |
|---|---|
| bancada de laboratório, 15/10 | `e521562df39b413a71a5d35576b83f02a1187e7ecc7c502cbf3e46eba0a3e93d` |
| C★3 completa, com o manual e a fórmula | `e3dac67605cc14a6b598e5e964293e13bf91cd1a6b594942b992c3b04a08161f` |
| Tear, a máquina do leito | `89b60ffc6f5f3a5f634d609b1c70b2e021e31f12d5f99b562977f63c788be885` |
| evidências da rotina de ordenação, 29/09 | `8d8fc98af8ff76e9d432791df0591aafb347245667a28d41e0804ead11e8bb42` |
| cópia completa do servidor de pesquisa, 14/10 | `0aa1871b11b8bb9a892028ea7669586c42f38f8ef037ebccbd5168be9c8c70db` |

Se esses pacotes forem divulgados e as somas conferirem, eles terão existido até 16/10/2026 21:00 -03 (pela âncora de `f571ac7`). Também não provam nada anterior a isso. O mesmo commit citava tags do repositório de trabalho (`v4.3-final`, `v4.3.1`), também ausentes.

### 4.4 O que um terceiro pode e não pode concluir

**Pode concluir, só com este repositório:**
- que todo o conteúdo de `61c5c4a` (artigo, fórmula, máquinas, evidências e os registros da conta 15) já existia e estava público até 16/10/2026 21:00:02 -03;
- que os registros da conta 15 são coerentes entre si e com o código (seção 6);
- que os números estruturais da C★3 batem com o código;
- que o autor afirma datas anteriores e as amarra a hashes de um repositório privado.

**Não pode concluir:**
- que a ideia é de 22/09, que a conta 15 é de 26/09, que a fórmula executável é de 28/09, ou qualquer data anterior a 16/10/2026;
- que as previsões da conta 15 foram escritas antes de as vidas rodarem (não há carimbo nos registros e os 24 hashes não estão aqui);
- qualquer precedência de ideias em relação a um texto publicado em 16/10/2026. A data mais antiga com garantia externa no repositório é a do próprio dia 16/10, à noite.

**O que mudaria esse quadro:** o repositório de trabalho com os commits citados. A ordem pai e filho entre commits é criptográfica (um commit não pode citar o hash de um filho que ainda não existe), então ele provaria a ordem relativa "previsão antes da vida". Para datas absolutas, seria preciso uma âncora externa anterior a 16/10: pushes registrados num servidor de terceiros, carimbos de tempo (por exemplo, OpenTimestamps ou RFC 3161), e-mails ou mensagens com os hashes, ou depósitos públicos.

## 5. As afirmações da montagem (README da raiz)

| afirmação | o que dá para conferir só com o repositório | o que não dá |
|---|---|---|
| Motor de 29/09: 18 provas do compilador e 8 do núcleo passaram; código do commit `7edc5af` | há exatamente 18 funções `test_` em `test_compilador.py` e 8 em `test_nucleo.py` | que passaram (exigiria rodar, o que foi vedado); que o código é o de `7edc5af` (o commit não está aqui) |
| 4.3.1 só com a seleção: 11 provas passaram; peças idênticas às originais | 11 funções de teste. A `foto_atomica.py` da 04 tem a mesma árvore sintática (sem docstrings) que a da 08 e a da 05; as 7 definições de `variacao.py` (04) que existem em `escritor_de_fotos.py` (08) são idênticas; `problema_de_d.py` da 04 é o da 08 sem 4 funções (`problema_do_l2`, `problema_do_ser`, `problema_do_ser_restrito`, `problema_do_ser_v2`; o LEIA-ME fala em duas, o que é coerente se as outras duas vieram depois da 4.3.1). Isso mostra coerência entre duas cópias do mesmo pacote. | identidade com a 4.3.1 original (ausente); o sha256 do original citado (`ee71d10e…67ff65d`) não confere com o `escritor_de_fotos.py` da 08 (`2bf935f2…`), o que é esperado, porque a 08 está sem comentários |
| Tear: a mesma semente, pelo pacote e pela árvore original, deu os mesmos recordes byte a byte | nada: não há `recordes.jsonl` de nenhuma das duas execuções nem a árvore original | tudo; mesmo rodando, faltaria a árvore original |
| C★3: código idêntico ao original pela árvore sintática e pelo C++ sem comentários; textos de saída reescritos | o código está de fato sem comentários e sem nomes de pessoas nos textos | a identidade; e há imprecisão lógica: textos reescritos mudam a árvore sintática |
| C★3: provas passaram no Windows (perturbação, sonda, V repartida, condutor v2, coletor, V da busca e calibração); a V compartilhada só em Linux | as 7 provas existem; o código tem ramos `os.name == 'nt'` com `os.add_dll_directory` (compatível com Windows, mas presentes também em pastas antigas como a 03, então não datam nada). Na versão de 20:58 (`61c5c4a`) o README listava só quatro provas aprovadas; às 21:08 (`a28eec9`) passou a listar sete. `test_condutor_de_fotos.py` (13 testes) e `test_estresse_ser_cpp.py` não aparecem como aprovados. | que passaram |
| Comentários que transcreviam conversas reescritos; nenhuma linha executável mudou | nas pastas 03, 04 e 05 ainda há comentários e docstrings (148/117, 72/42, 251/101); alguns ainda citam conversas, por exemplo "o Fable: ..." em `05_tear_selecao/experimentos/vida_v3c_c.c` e `vida_no_leito.py` | que nenhuma linha executável mudou; a comparação "pela árvore sintática" teria de ignorar as docstrings, que fazem parte da árvore, o que o texto não diz |
| Nenhum endereço de servidor, chave ou senha | confirmado pela busca (só caminhos `/home/iro/...` e marcadores de exemplo) | nada a acrescentar |

## 6. Provas a mais que os registros dão

1. **A previsão impressa é idêntica ao começo da vida em 11 de 11 pares**, e o código mostra que a conta roda antes e sem ler a vida. Em p1, p1b e p2 (e na 2c, em execução separada) a previsão é um cálculo reprodutível a partir do código e dos dados, não do resultado. Em p4 a p4f ela é texto fixo no roteiro, e essa prova vale pouco.
2. **A conta da 2c exigiu e a vida cumpriu uma réplica exata:** a conta diz "a vida com --regra=unidade tem de repetir a p2b numero por numero"; `p2c_vida_unidade.log` repete `p2b_vida.log` nas 12 medidas horárias (acendimentos, errados, esquecimentos) e na lista dos 18 esquecimentos falsos. É uma prova de determinismo entre dois roteiros diferentes.
3. **Duas execuções da 2ª forma da 2c** (`p2c_vida_sinapse_b.log` e `p2c_diag_b.log`) são idênticas em todas as linhas, menos o tempo de CPU (4,6 e 4,4 ms) e as linhas de diagnóstico.
4. **Uma previsão acertada que o texto não cita:** 10.919 ligações apagadas previstas na conta da 2ª forma da 2c, 11.073 medidas na vida (1,4%).
5. **Encadeamento interno entre premissas:** contas que citam resultados medidos antes ("a p2b mediu 18", "abaixo dos 29,8% da p4e com d' = 2", o medo "do 3o ao 10o" tirado da vida da p4b) e o `import p4e_exato` em `p2b_orelha.py`. Dão uma ordem relativa coerente com a tabela do `A_CONTA_15.md`, embora escrita pelo próprio autor.
6. **Vestígio do código original:** o aviso em `p2c_conta_a.log` cita a linha 178 de `/home/iro/bancada/conta15/p2c_esquecer.py`; a mesma expressão está na linha 136 do `p2c_esquecer_a.py` publicado. Mostra que o arquivo foi renomeado depois da execução e perdeu 42 linhas antes desse ponto (compatível com a retirada de comentários), e que o registro não foi regenerado com o código publicado.
7. **O recorte da orelha não favorece o autor:** com a voz do autor incluída, a orelha (51,6%) ficaria à frente do comparador (50,9%); o texto usa o recorte em que ela perde (59,4% contra 59,9%).
8. **O selo do banco da prova cega confere:** os três oráculos do banco e o `hash_do_selo`.
9. **A foto de 3.316 bits, as 28 cláusulas, os 116 predicados e as 15 vidas** recalculados a partir do código.
10. **Três cópias da `foto_atomica.py`** (04, 05 e 08) com a mesma árvore sintática.
11. **A única âncora externa de data:** a assinatura do GitHub em `f571ac7` (16/10/2026 21:00:02 -03), que cobre todo o conteúdo dos commits anteriores.
12. **Os cinco sha256 de pacotes** publicados no primeiro commit e ainda presentes na história (seção 4.3), úteis se os pacotes vierem a público.

## 7. Scripts e saídas

Todos em `/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/verif/outros/`, rodados com `python3 -I`, com os arquivos passados como argumento. Nenhum importa ou executa código do repositório: só leem texto, usam `ast.parse`, `tokenize`, `zipfile` (listagem) e `hashlib`.

| script | o que faz | saída |
|---|---|---|
| `/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/verif/outros/conta15_registros.py` | fins, erros e carimbos dos 29 registros; conta contra começo da vida; médias da orelha; faixas; réplica da 2b; p4 a p4f; o "7 das 10"; busca dos hashes | `/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/verif/outros/conta15_registros.saida.txt` |
| `/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/verif/outros/codigo_estatico.py` | comentários da conta 15; bits da foto; cláusulas, predicados e vidas; selo; piscina e oráculos; configuração contra `Config`; constantes da perturbação; comparação 04, 05 e 08; contagem de testes | `/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/verif/outros/codigo_estatico.saida.txt` |
| `/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/verif/outros/manifesto_e_git.py` | manifesto contra a cópia; cópia contra a árvore de `a28eec9` | `/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/verif/outros/manifesto_e_git.saida.txt` |
| `/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/verif/outros/comentarios_pastas.py` | comentários e docstrings por pasta | `/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/verif/outros/comentarios_pastas.saida.txt` |
| `/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/verif/outros/contas_estrutura.py` | o que cada `conta*()` e `main()` da conta 15 chama: mostra que as contas de p4 a p4f são só `print` de texto fixo e que nenhuma conta usa aleatoriedade | `/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/verif/outros/contas_estrutura.saida.txt` |

Outros recursos: o clone completo da história está em `/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/verif/outros/hist` (sem push); a chave do GitHub e o chaveiro temporário usados para `git verify-commit f571ac7` estão em `/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/verif/outros/webflow_ks.asc` e `/tmp/claude-0/-home-user-Conta/9b6d7c7f-549d-59d8-82a7-bc02ceae2e96/scratchpad/deverser/verif/outros/gpg_tmp`. Algumas consultas avulsas com `python3 -I` (por `-c` ou pela entrada padrão) só usaram `ast.parse` em arquivos do repositório, sem executá-los; a principal delas virou o script `contas_estrutura.py`. `main_ro` não foi alterada.

## 8. O que não é verificável só com o repositório

- Qualquer data anterior a 16/10/2026 21:00:02 -03, inclusive 22/09, 26/09, 28/09, 29/09, 30/09, 01/10, 04 e 05/10, 06 e 07/10.
- A ordem "previsão antes da vida" da conta 15 e os 24 hashes do repositório de trabalho (mais `7edc5af`, `8c47301` e as tags `v4.3-final` e `v4.3.1`).
- Os 55 cláusulas do D da conta 15; a reação em 0,2 s.
- A faixa "11.000 a 16.000" da 3ª forma da 2c (a conta dessa forma não está registrada).
- O corpo inteiro da conta 15 (17 populações, 10.905 unidades, 35.272 sinapses, vida de 6 h, 21 chamadas).
- As causas atribuídas a falhas (erro de implementação na 2ª forma da 2c; tom de voz na p4b).
- A reprodução de qualquer registro da conta 15 (as vozes, a cóclea e o mundo das palavras não estão no pacote).
- A corrida da C★3 (15 rodadas, 3 gerações, 1.488 fotos, 2.033 medidas, nenhuma foto cumprindo D) e o tempo de calibração.
- A identidade de qualquer código com um "original" (C★3, conta 15, 4.3.1, Tear, motor de 29/09).
- Que as provas passaram (rodar foi vedado), no Windows ou em qualquer lugar.
- Os recordes byte a byte do Tear.
- A catraca em miniatura (32 melhoras) e os nulos do aprendiz de fora (só o texto da fórmula).
- O Sismo, o aprendiz de sinapses e a ligação deles com a conta 15.
- O artigo da Anthropic citado no começo do texto.
