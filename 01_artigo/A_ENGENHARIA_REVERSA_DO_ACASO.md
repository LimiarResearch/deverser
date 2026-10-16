# A engenharia reversa do acaso

*Notas de uma pesquisa em andamento. Gabriel Santos, Limiar Research, 16 de outubro de 2026.*

## Por que eu publico isto hoje

Hoje, 16 de outubro de 2026, a Anthropic publicou um artigo contando que um modelo interno de pesquisa descobriu, em menos de meia hora, como foram geradas as sementes das curvas elípticas do NIST: as cinco curvas primas, de P-192 a P-521, e quatro das binárias. Essas sementes chegaram ao padrão em 2000 sem explicação e passaram mais de duas décadas sem que ninguém soubesse dizer de onde vinham. Segundo o artigo, elas saíram do `lrand48`, um gerador pseudoaleatório da biblioteca C, iniciado pelo relógio do computador entre maio de 1997 e abril de 1998.

Eu li o artigo inteiro e fiquei surpreso. Desde setembro eu trabalho numa pesquisa que batizei, em 22/09, de a engenharia reversa do acaso. Ela usa sementes sorteadas, uma verificação que julga cada candidato e buscas guiadas por uma intenção declarada antes. E trabalhei o mês inteiro com uma bancada de inteligências artificiais em que duas são da própria Anthropic: o Claude, que fez a execução, e o Fable, que fez parte do planejamento.

O método deles é outro. Eles fizeram criptoanálise clássica: uma hipótese sobre geradores antigos, um varredor de 34 combinações de gerador e fatia de saída, força bruta sobre 2¹⁷ valores e redução de reticulado. Ali não há uma intenção escrita em cláusulas nem uma seleção de candidatos por um verificador. O que coincide é o tema, e a palavra. Eu não sei dizer o que essa coincidência significa. Sei o que eu fiz e quando, e como eu ia publicar esse trabalho de qualquer forma, publico agora, do jeito que está, com as datas e as provas.

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

O custo também tem nome. O acaso paga com cadáveres no mundo. A intenção paga com cadáveres dentro da conta, os candidatos reprovados na medida, e exige zero falhas fora dela.

```
K_conta = candidatos calculados que não cumprem D      quanto menos, melhor
K_mundo = artefatos entregues que falham fora           o critério é zero
```

## A fórmula

Em 28/09 a equação virou fórmula executável. Dado um D, os números do meio e um orçamento, uma máquina constrói um candidato finito, confere que ele cumpre cada cláusula com uma prova que outra pessoa possa verificar e declara o que encontrou. Em 29/09 eu fechei a fórmula, e daí em diante ela só muda por emenda datada. A versão vigente é a 4.3, de 01/10.

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

Todas as máquinas têm o mesmo coração, a seleção julgada por V: sortear variações dos candidatos, medir cada uma contra D, guardar as melhores e repetir até a fronteira parar de mudar. Algumas versões ganharam depois um aprendiz, que tenta escrever variações melhores que as sorteadas.

- **A primeira máquina (28/09)** constrói máquinas de estados finitos, o tipo de controlador que decide, a cada entrada, se libera ou bloqueia uma ação. Contra o CEGIS, a síntese guiada por contraexemplo da literatura, ela achou as mesmas máquinas nos 64 casos de um domínio enumerado inteiro, com cerca de quatro vezes menos formulações ali e cerca de quinze vezes menos numa bateria de 192 casos. Um resolvedor isolado, o z3, confirmou os 192 vereditos.
- **O motor fechado da fórmula 4.0 (29/09)** é a seleção com os laços da fórmula: a parada pela fronteira e a pergunta pela causa quando a busca empaca. Ele não tem aprendiz, e é dele o resultado da ordenação.
- **A Máquina do Dever-Ser 4.3.1 (01/10)** serve a qualquer D: basta escrever a codificação do candidato em bits e o V. A verificação completa passou 428 de 433 provas.
- **A C★1, a C★2 e a C★3 (01 a 05/10)** são a Máquina do Dever-Ser aplicada a um desafio proposto pelo Codex, o Ser: uma inteligência digital que aprende coisas novas sem recomeçar e sem guardar todo o histórico, julgada por 28 cláusulas em 15 vidas.
- **O Tear (04 e 05/10)** é a máquina do leito: uma ilha de 64 candidatos que seleciona por torneio e mutação, e um leito que julga cada candidato numa vida inteira, por 15 cláusulas.

## Os resultados

O que deu certo, no tamanho em que se mediu:

- **Uma rotina de ordenação 4,3% mais rápida no mesmo servidor.** Em 29/09, o motor fechado, sem aprendiz, procurou uma rotina de ordenação de 8 elementos para o processador do servidor de pesquisa. Em 9,7 minutos e 384 candidatos, achou uma rotina 4,3% mais rápida que a rede ótima conhecida, com 22,27 contra 23,36 ciclos por vetor e ruído de 0,46%, correta nos 16.777.216 vetores possíveis, sem trocar hardware. É a mesma rede ótima com outra ordem e a troca feita na memória, e o ganho vem do jeito como aquele processador executa o código.
- **A PONTE.** Em 04/10, no Tear, uma peça deduzida pelo fluxo de informação substituiu uma peça escrita à mão e chegou ao mesmo ponto com 7,3 mil medidas, contra 24,8 mil. Em duas famílias de mundos novas, ficou à frente da peça escrita em 8 de 8 sementes numa e em 6 de 8 na outra.
- **A catraca em miniatura.** Nas redes de comparadores de 5 a 8 fios, o motor que muda a si mesmo ganhou nos problemas retidos, com 32 melhoras e nenhuma piora. O ganho foi uma troca de operador pequena e conhecida, que ele achou sozinho.

O que caiu:

- **No D do Ser, nenhuma máquina achou o corpus.** A cláusula de aprender pede 0,10. As fotos de recorde da C★2 mediram de 0,096 a 0,118 nela durante a busca e caíram para 0,056 a 0,076 nas vidas seladas. Quanto melhor a foto na busca, pior ela ficava fora, com correlação de −0,70: a maldição do vencedor.
- **O ruído.** A verificação do Ser tem um ruído intrínseco de centenas de pontos, e boa parte das melhoras da C★2 cabia dentro dele.
- **O aprendiz não transferiu.** Dentro de uma corrida ele foi de cinco a seis vezes melhor que a variação cega nos programas atômicos, e de um problema para o seguinte não levou nada.
- **A alegação central ainda não foi medida.** Falta saber se a fórmula inteira ganha de uma busca sem os laços, com o mesmo V e o mesmo orçamento. Na bancada da C★2, a evolução simples empatou ou chegou antes.

Pela régua da própria fórmula, quase tudo está no degrau "rodou", e uma parte pequena no "medido". Eu não afirmo fronteira nem objeto novo. O que eu proponho é a conta que liga peças conhecidas, a busca evolutiva, a síntese por contraexemplo e as máquinas que se modificam, partindo de uma intenção escrita e dos números medidos do meio, presa a uma verificação calibrada.

## O Sismo e o aprendiz de sinapses

O Sismo, o detector da Limiar com o conector que leva a ele os dados de cada sistema, e o aprendiz de sinapses têm a mesma origem: um tecido do Iro, o ser digital com que a pesquisa começou. Esse tecido foi calculado pela conta ainda à mão, antes de existir a máquina que a executa. É o tecido de um pequeno ser de teste, a conta 15, de 26/09, construído por premissas. A conta achou ali a origem dos dois, a semente: o aprendiz de associações da primeira premissa, que pedia que o tecido aprendesse sozinho, sem professor e sem nada fora da sinapse e da unidade. Eu reformei essa semente, e dela saíram o Sismo e o aprendiz de sinapses. A segunda premissa pedia que o próprio tecido cortasse e guardasse o sinal que chega: era a orelha, a entrada dos experimentos, e no produto essa entrada é o conector. Em 06 e 07/10 o aprendiz de associações virou um detector de mudança, e o mecanismo passou a observar dados de sistemas.

Em cada premissa a conta escreveu a previsão antes da vida, e a previsão subiu ao repositório antes da medida:

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

Duas previsões caíram. Os esquecimentos falsos foram 8, contra 0,8 previstos, todos por palavras parecidas. E com a orelha o tecido aprendeu mais devagar do que a conta dizia, entre o 18º e o 43º anúncio, contra 3 a 20.

Já como detector, ele foi medido contra a concorrência com o critério escrito antes, em 340 rodadas com sementes novas e 13 fluxos:

- Detectou 96% das mudanças (231 de 240), com 0,6% de alarmes falsos, e disse o campo que mudou em todas. O CJSD detectou 76%, o DDM 48% e o ADWIN 40%, este com 26% de alarmes falsos.
- Na confirmação final congelada, com sementes novas, deu 0 alertas em 5,04 milhões de itens sem mudança.
- Reprovou no dado real em ordem de tempo, a base INSECTS: pegou as 5 mudanças, mas soltou 90 alarmes fora das janelas. A versão seguinte baixou para 10 alarmes fora, pegando 2 das 5.
- Os limites ficaram declarados: a mudança lenta real, a mudança só na combinação de categorias e o XOR.

O aprendiz de sinapses é um aprendiz de aprendizagem contínua. Ele aprende ao vivo, numa passada só, ligações com atraso entre sinais que disparam, do tipo "B costuma vir cerca de L minutos depois de A". A ligação nasce quando a evidência contra o acaso passa de um limiar e se desfaz quando ela cai abaixo dele. O que nenhuma leitura futura alcança vira contagem, e assim a memória fica limitada e a resposta sai idêntica à de quem guardasse tudo. Numa empresa simulada, contra cinco métodos conhecidos (correlograma cruzado, Hawkes, Granger, entropia de transferência e coocorrência), em vidas de 90 dias e três sementes, ele achou 13 de 33 pares de defeito, no meio do grupo e mais tarde que os métodos condicionais. Foi o que menos voltou atrás depois de afirmar um par e o que menos cresceu em memória: de 79 para 97 MiB entre 30 e 90 dias, contra perto de 600 MiB do Hawkes e do Granger.

Para mim isso é uma prova também: dois aparelhos que vão para o mundo saíram de uma conta feita sobre um dever ser e os números do meio, com a previsão escrita antes da medida. O Sismo e o aprendiz de sinapses vão ser publicados.

## Os arquivos

Junto com este texto vão as máquinas só com a seleção, sem os aprendizes, e as evidências dos resultados:

- **a fórmula do dever ser**, na versão 4.3;
- **o motor de 29/09**, exatamente como estava quando achou a rotina de ordenação, com as provas dele;
- **a Máquina do Dever-Ser 4.3.1 só com a seleção**: a codificação da foto atômica, o V, a escrita às cegas e o operador da 4.3.1, sem a rede, com um D de exemplo e as provas;
- **o Tear só com a seleção**: a ilha e o leito, sem as ferramentas e sem a mente;
- **as evidências** da rotina de ordenação e da comparação com o CEGIS;
- **a conta 15**, a origem do Sismo e do aprendiz de sinapses: como foi feita, as previsões registradas antes de cada vida, os resultados e os registros.

O Sismo e o aprendiz de sinapses têm publicação própria.

## Datas e provas

A ideia e a equação são de 22/09. O tecido de onde vieram o Sismo e o aprendiz de sinapses é de 26/09, e o detector, de 06 e 07/10. A fórmula executável é de 28/09, e a fórmula fechada e a rotina de ordenação, de 29/09. A Máquina do Dever-Ser 4.3 e a 4.3.1 são de 01/10, com as tags `v4.3-final` e `v4.3.1` no repositório. Os pacotes que guardam a pesquisa:

| pacote | sha256 |
|---|---|
| bancada de laboratório, 15/10 | `e521562df39b413a71a5d35576b83f02a1187e7ecc7c502cbf3e46eba0a3e93d` |
| C★3 completa, com o manual e a fórmula | `e3dac67605cc14a6b598e5e964293e13bf91cd1a6b594942b992c3b04a08161f` |
| Tear, a máquina do leito | `89b60ffc6f5f3a5f634d609b1c70b2e021e31f12d5f99b562977f63c788be885` |
| evidências da rotina de ordenação, 29/09 | `8d8fc98af8ff76e9d432791df0591aafb347245667a28d41e0804ead11e8bb42` |
| cópia completa do servidor de pesquisa, 14/10 | `0aa1871b11b8bb9a892028ea7669586c42f38f8ef037ebccbd5168be9c8c70db` |

Publicar essas somas hoje fixa que esses arquivos existiam hoje, sem expor o conteúdo.

Hoje alguém reconstruiu o acaso de uma máquina antiga. O acaso que eu tento inverter é o que a natureza usa sobre os números do mundo, e a conta que eu procuro é a da intenção que faria o mesmo trabalho uma vez só. Estou trabalhando nisso.

*Gabriel Santos, Limiar Research*
