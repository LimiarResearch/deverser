# A engenharia reversa do acaso

*Notas de uma pesquisa em andamento. Gabriel Santos, Limiar Research, 16 de outubro de 2026.*

## Este texto

Este texto apresenta uma pesquisa em andamento desde 22/09/2026: a fórmula do dever ser, as máquinas que a executam e o que elas acharam, inclusive o que deu errado. As datas estão no fim. A tese está no método: a fórmula transforma um problema num cálculo verificado, com a intenção escrita em cláusulas, os números do meio medidos, um verificador fixo calibrado por controles, cinco desfechos declarados e o registro do que falhou, e a busca é uma peça trocável dentro dele. Cada resultado aponta para a pasta do repositório onde está a evidência, e o README da raiz reúne os resultados numa tabela, com o alcance e o limite de cada um.

## A ideia

A pesquisa partiu de uma ideia que eu tive em 22/09 e que virou a pergunta que deu nome a tudo: qual é a engenharia reversa do cálculo que a natureza fez? O acaso calcula sobre os números do mundo inúmeras vezes, e o que não serve morre no mundo. A intenção pode fazer a mesma conta uma vez só, partindo do que o ser deve ser.

```
o acaso:     ser = acaso     ⊗ números do meio, iterado sem fim
a intenção:  ser = dever ser ⊗ números do meio, uma vez só
```

No mesmo dia a equação estava escrita:

```
S★ = C★(D, Π)
```

D é o dever ser, a intenção escrita em cláusulas. Π são os números do meio onde o ser vai existir, medidos, cada um com a sua incerteza e a sua procedência. C★ é a conta, e S★ é o corpus que melhor atende D dentro do que o meio admite. A busca continua existindo e corre sobre formulações, nunca sobre corpos, com cada fracasso anotado num registro de nulos. Chamei isso de seleção selecionada.

O custo também tem nome. O acaso paga com falhas no mundo. A intenção paga com falhas dentro da conta, os candidatos reprovados na medida, e exige zero falhas fora dela.

```
K_conta = candidatos calculados que não cumprem D      quanto menos, melhor
K_mundo = artefatos entregues que falham fora           o critério é zero
```

## A fórmula

*No repositório: `02_formula`.*

Em 28/09 a equação virou fórmula executável. Dado um D, os números do meio e um orçamento, uma máquina constrói um candidato finito, confere que ele cumpre cada cláusula com uma prova que outra pessoa possa verificar e declara o que encontrou. Em 29/09 eu fechei a fórmula, e daí em diante ela só muda por emenda datada. A versão publicada é a 4.3, com as emendas de 30/09 e 01/10.

A imagem que eu uso é a de um motor montado num eixo. O eixo é V, a verificação, a única peça presa. As outras giram em volta dele, e cada ida e volta entre duas peças passa por V.

| Peça | O que é |
|---|---|
| V | o critério do que é cumprir, calibrado por controles antes de julgar |
| D | a intenção: cláusulas rígidas, objetivos e preferência; só muda com a confirmação do criador |
| Π | os números do meio, com incerteza e procedência; só mudam por medida |
| L | a linguagem das formas, primitivas que se compõem |
| M | o modelo, ou a medida no alvo, com o seu domínio de validade |
| f | o jeito de procurar: uma regra declarada e, se ligado, um aprendiz |
| S★ | o corpus escolhido |

Em cada volta, V julga os candidatos e aponta o que falta. Quando nenhum cumpre D, a máquina pergunta pela causa numa ordem fixa: primeiro o instrumento (V passou nos controles?), depois a busca (reinícios independentes dão o mesmo valor?), depois a linguagem, depois os números do meio, e só no fim a hipótese de que o D contradiz o meio. Ela para quando uma volta não muda mais nada e declara um de cinco estados: solução, impossível nesta forma, impossível no meio, não encontrado no orçamento, ou indeterminado.

A fórmula tem dezesseis laços escritos. Os que mais pesam:

- **O meio limita o que pode ser.** A forma do corpo é resultado da conta, nunca premissa.
- **V calibrada antes de julgar**, com controles positivos e negativos e o piso de ruído medido.
- **O resultado volta ao criador**, e esse ok é sempre humano.
- **A catraca.** O motor também é objeto da conta, e uma versão nova dele só substitui a atual se ganha em problemas retidos que nenhuma decisão viu.
- **A integridade de V**, que é o ponto único de falha.
- **A foto atômica, regra pétrea.** Cada candidato é a sua constituição na menor unidade do meio, no digital o bit. O aprendiz classifica essas fotos pelo quanto cumprem D, guarda o padrão das melhores e escreve sementes novas unidade por unidade.

E a fórmula diz o que se pode afirmar de um resultado, em degraus: definido, rodou, medido, generaliza, verificado por terceiros, aceito. Cada degrau exige o de baixo.

## As máquinas

Todas as máquinas têm o mesmo coração, a seleção julgada por V: sortear variações dos candidatos, medir cada uma contra D, guardar as melhores e repetir até a fronteira parar de mudar. Algumas versões ganharam depois um aprendiz, que tenta escrever variações melhores que as sorteadas. As três primeiras vão só com a seleção. A C★3 vai com o aprendiz, como rodou.

- **O motor de 29/09** *(`03_motor_de_29-09`)* é o motor fechado da fórmula 4.0: a seleção com os laços da fórmula, a parada pela fronteira e a pergunta pela causa quando a busca empaca. Ele nunca teve aprendiz, e é dele o resultado da ordenação. O código publicado é o do commit gravado oito segundos antes de a corrida começar, num repositório de trabalho que não é público, e as 26 provas dele passam, também numa verificação independente em Linux.
- **A Máquina do Dever-Ser 4.3.1 só com a seleção** *(`04_maquina_do_dever_ser_selecao`)* serve a qualquer D: basta escrever a codificação do candidato em bits e o V. As peças vêm da 4.3.1, a escrita às cegas e o operador, sem a rede que aprende. Ela acha o D de exemplo em poucas rodadas, e as 11 provas dela passam.
- **O Tear só com a seleção** *(`05_tear_selecao`)* é a máquina do leito: uma ilha de 64 candidatos que seleciona por torneio e mutação, e um leito que julga cada candidato numa vida inteira, por 15 cláusulas. A mesma semente, rodada pelo pacote e pela árvore original, dá os mesmos recordes; os registros dessa conferência não estão no repositório.
- **A C★3** *(`08_c_estrela_3`)* é a Máquina do Dever-Ser 4.3.1 aplicada a um D de aprendizado contínuo, o Ser: um programa que aprende coisas novas sem rodadas de treinamento e sem guardar todo o histórico, julgado por 28 cláusulas em 15 vidas. Ela traz a rede que lê, julga e escreve as fotos, uma piscina de vidas com os oráculos calculados antes, a pior de três medidas para tudo o que decide e as testemunhas (SGD, EWC, CBP e SP) como comparação.

## Os resultados

A tabela completa, com a máquina, o alcance e o limite de cada resultado e as provas independentes de 17 e 18/10, está no README da raiz e na pasta `09_provas_independentes`.

O que deu certo, no tamanho em que se mediu:

- **Uma rotina de ordenação com 4,3% menos ciclos no mesmo servidor** *(`06_evidencias/ordenacao_29-09`)*. Em 29/09, o motor fechado, sem aprendiz, procurou uma rotina de ordenação de 8 elementos para o processador do servidor de pesquisa. Em 9,7 minutos e 384 candidatos, achou uma rotina com razão de 0,957 contra a referência, correta nos 16.777.216 vetores possíveis. Esse 0,957 é a mediana, em 21 repetições, das medianas das razões por bloco; a razão das medianas, 22,27 contra 23,36 ciclos por vetor, dá 0,9535. É a mesma rede ótima com outra ordem e a troca feita na memória, e o ganho vem do jeito como aquele processador executa o código. A vencedora foi medida uma vez, como a menor entre 384, e três candidatos cabem na resolução de 1% do D. O limite de 3% do D foi posto pela IA no lugar do criador. Numa verificação independente, o mesmo programa deu razão de 0,960 a 0,961 num Intel Xeon de 2,1 GHz e de 0,990 a 0,993 num Xeon de 2,8 GHz. O arquivo da pasta tem a vencedora e a referência idênticas às medidas; o programa que rodou também media a versão AVX2.
- **Menos formulações que uma implementação própria do CEGIS** *(`06_evidencias/cegis_e_z3`)*. Numa bateria própria de 192 casos de construção de máquinas de estados finitos, a fórmula usou 1.152 formulações, contra 17.588 do CEGIS com poda e 16.120 do CEGIS sem poda, que parou 72 vezes no limite de nós. A fórmula usou menos formulações em todos os 192 casos, com mediana de 19 vezes por caso. A unidade não mede a mesma coisa nos dois métodos: em chamadas ao verificador, a vantagem é de 1,25 vez, e em tempo, de 1,04 vez. A fórmula e o CEGIS com poda acharam as mesmas 82 máquinas, 48 delas triviais, de 1 estado; o CEGIS sem poda achou 50. O z3, rodado à parte, confirmou os 192 vereditos da fórmula, com 0 discordâncias.
- **A catraca em miniatura** *(`02_formula`, seção 22)*. Nas redes de comparadores de 5 a 8 fios, a catraca adotou uma mudança, uma troca de operador pequena e conhecida, que foi melhor em 32 problemas retidos e pior em nenhum. Os registros dessa corrida não estão no repositório, e a própria fórmula diz que nenhum resultado passou do degrau "medido".
- **O tecido que aprende** *(`07_conta_15`)*. Na conta 15, as premissas de um pequeno ser de teste foram calculadas a partir do dever ser, com a previsão registrada antes de cada vida. O tecido aprendeu sozinho e esqueceu o que deixou de valer em parte das premissas. Várias previsões caíram, e `07_conta_15/A_CONTA_15.md` lista as que este texto omitia.

O que caiu:

- **O aprendiz de fora não transferiu** *(`02_formula`, seção 22)*. O aprendiz que levava o que aprendeu de um problema para o seguinte deu três nulos nas redes de ordenação mínimas, e um positivo numa corrida só, não replicado.
- **O corpo inteiro do ser de teste não aprendeu** *(`07_conta_15`)*. As premissas aprenderam cada uma no seu teste, e o tecido montado a partir do D inteiro, com 10.905 unidades, deu nulo numa vida de 6 horas.
- **A orelha calculada não superou a anterior** *(`07_conta_15`)*. Ela acertou 59,4% nas vozes de fora, contra 59,9% do comparador, e a causa estava na formulação do D.
- **No D do Ser, nenhuma foto cumpriu D** *(`08_c_estrela_3`)*. A corrida da C★3 de 04 e 05/10 parou com estado retomável depois de 1.488 fotos e 2.033 medidas de V, sem nenhuma foto que cumprisse D. Os registros dessa corrida não estão no repositório.
- **A busca por seleção não mostrou vantagem sobre alternativas simples** *(`09_provas_independentes`)*. Num Intel Xeon, o motor de 29/09 ganhou de um sorteio cego com o mesmo orçamento, mas empatou com um sorteio que mantém os 19 comparadores. Num D de compressão sem perda, a Máquina 4.3.1 sem mudança não cumpriu o D e terminou atrás do melhor codec único achado por busca exaustiva; numa segunda versão, atrás também do sorteio cego.
- **A alegação central ainda não foi medida** *(`02_formula`, seções 15 e 21)*. Falta saber se a fórmula inteira ganha de uma busca sem os laços, com o mesmo V e o mesmo orçamento. O teste exige dois controles, a fórmula com a variação cega e o acaso puro.

Pela régua da própria fórmula, quase tudo está no degrau "rodou", e uma parte pequena no "medido". Eu não afirmo fronteira nem objeto novo. O que eu proponho é a conta que liga peças conhecidas, a busca evolutiva, a síntese por contraexemplo e as máquinas que se modificam, partindo de uma intenção escrita e dos números medidos do meio, presa a uma verificação calibrada.

## O Sismo e o aprendiz de sinapses

*No repositório: `07_conta_15`.*

O Sismo, o detector da Limiar com o conector que leva a ele os dados de cada sistema, e o aprendiz de sinapses têm a mesma origem: o tecido de um pequeno ser de teste simulado, calculado à mão na conta 15, de 26/09, antes de existir a máquina que executa a fórmula. Esse tecido foi construído por premissas. A conta achou ali a origem dos dois, a semente: o aprendiz de associações da primeira premissa, que pedia que o tecido aprendesse sozinho, sem professor e sem nada fora da sinapse e da unidade. Eu reformei essa semente, e dela saíram o Sismo e o aprendiz de sinapses. A segunda premissa pedia que o próprio tecido cortasse e guardasse o sinal que chega: era a orelha, a entrada dos experimentos, e no produto essa entrada é o conector. Em 06 e 07/10 o aprendiz de associações virou um detector de mudança, e o mecanismo passou a observar dados de sistemas.

Em cada premissa a conta imprimiu a previsão antes da vida, no mesmo registro, e a previsão subiu ao repositório de trabalho antes da medida. Esse repositório não é público, e os registros não têm carimbo de tempo:

| premissa | previsão | vida |
|---|---|---|
| o tecido aprende, primeira formulação | `0790d4bb` | `13db9950` |
| o tecido aprende, segunda formulação | `343faa47` | `191ab66e` |
| a orelha no tecido | `28555c17` e `67e36604` | `91e1d92b` |

O mundo do teste era um dia de 43.200 palavras em que dez delas anunciavam, cada uma, um acontecimento que vinha logo depois. O que se mediu:

- Nascendo sem saber nada, as dez palavras passaram a acender a espera do acontecimento entre o 2º e o 8º anúncio.
- Os acendimentos errados ficaram entre 9 e 24 em 4.110, contra 12 previstos.
- Quando uma palavra parou de anunciar, a ligação se apagou na 5ª vez dita sem o acontecimento, a vez que a conta previa. A outra se apagou na 13ª.
- Com a orelha no tecido, o corte deu um evento por fala em 100% das 2.060 falas, como previsto, e os acendimentos errados ficaram entre 0 e 9 em 4.110, contra 6 a 10 previstos.
- O custo foi de 0,001 segundo de servidor por segundo de vida.

Previsões caíram. Os esquecimentos falsos foram 8, contra 0,8 previstos, todos por palavras parecidas. A segunda palavra que parou de anunciar estava prevista para ser esquecida na 5ª vez, como a primeira, e só foi na 13ª. E com a orelha o tecido aprendeu mais devagar do que a conta dizia, entre o 18º e o 43º anúncio, contra 3 a 20. As outras previsões que caíram estão em `07_conta_15/A_CONTA_15.md`. A pasta traz as demais premissas, com os estados que o D chama de sentimentos e o pensar sem língua, e o que passou e o que caiu em cada uma.

O aprendiz de sinapses é um aprendiz de aprendizagem contínua. Ele aprende ao vivo, numa passada só, ligações com atraso entre sinais que disparam, do tipo "B costuma vir cerca de L minutos depois de A", com memória limitada e a resposta idêntica à de quem guardasse tudo.

O Sismo e o aprendiz de sinapses vão ser publicados à parte, cada um com as suas medidas.

## O que está no repositório

| pasta | o que tem |
|---|---|
| `01_artigo` | este texto |
| `02_formula` | a fórmula do dever ser, versão 4.3, com as emendas 6 a 13, as decisões datadas e o que se mediu |
| `03_motor_de_29-09` | o motor fechado da fórmula 4.0, como rodou na ordenação, com as provas |
| `04_maquina_do_dever_ser_selecao` | a Máquina do Dever-Ser 4.3.1 só com a seleção, com um D de exemplo e as provas |
| `05_tear_selecao` | o Tear só com a seleção: a ilha e o leito em C |
| `06_evidencias` | a corrida da ordenação de 29/09, com o programa medido, e a bateria de 192 casos contra o CEGIS |
| `07_conta_15` | a conta 15: como foi feita, as premissas, as previsões, os resultados, o código e os registros |
| `08_c_estrela_3` | a C★3: o código e as instruções para rodar |

Cada arquivo tem o seu sha256 em `MANIFESTO.sha256`.

## Datas

- **22/09:** a ideia e a equação.
- **26/09:** a conta 15, o tecido de onde vieram o Sismo e o aprendiz de sinapses.
- **28/09:** a fórmula executável e a primeira máquina, com a comparação com o CEGIS.
- **29/09:** a fórmula fechada, na versão 4.0, e a rotina de ordenação.
- **30/09 e 01/10:** as emendas 6 a 13 e a Máquina do Dever-Ser 4.3.1.
- **04 e 05/10:** a corrida da C★3.
- **06 e 07/10:** o detector de mudança que deu o Sismo.
- **17 e 18/10:** a verificação e os testes independentes (`09_provas_independentes`).

A única data com garantia de terceiro é a do commit `f571ac7`, assinado pelo GitHub em 16/10/2026 às 21:00 (-03). As datas acima vêm de registros da própria máquina e de textos do autor.

O acaso que eu tento inverter é o que a natureza usa sobre os números do mundo, e a conta que eu procuro é a da intenção que faria o mesmo trabalho uma vez só. Estou trabalhando nisso.

*Gabriel Santos, Limiar Research*
