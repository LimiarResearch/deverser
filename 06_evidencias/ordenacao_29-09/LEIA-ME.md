# Uma rotina de ordenação mais rápida no mesmo servidor (29/09/2026)

## O resultado em uma frase

Na madrugada de 29/09/2026, a máquina do dever-ser, no motor fechado da fórmula 4.0, rodou no próprio servidor de pesquisa e procurou uma rotina de ordenação de 8 elementos mais rápida para aquele processador. Em 9,7 minutos e 384 candidatos, achou uma rotina com 4,3% menos ciclos por vetor que a referência, que é a mesma rede ótima de 19 comparadores com a troca feita nos registradores. A rotina é correta em todos os 16.777.216 vetores possíveis e roda no mesmo hardware. O ganho foi medido naquele servidor, declarado como um AMD EPYC de primeira geração, com o gcc 13; o modelo do processador e a versão do gcc não ficaram gravados nos registros. Numa verificação independente, o mesmo programa deu razão de 0,960 a 0,961 num Intel Xeon de 2,1 GHz e de 0,990 a 0,993 num Intel Xeon de 2,8 GHz (Cascade Lake). O ganho depende do processador, também entre dois Intel (`09_provas_independentes/provas/b1/`).

## O problema escolhido

As rotinas curtas de ordenação sem desvio são as redes de comparadores que ordenam poucos números com tempo fixo. Elas estão dentro de praticamente todo programa que ordena dados. Em 2023 a DeepMind (AlphaDev, Nature) melhorou as de 3 a 5 elementos, e o resultado entrou na biblioteca padrão do C++ do LLVM. O problema daqui é a continuação natural: 6 e 8 elementos, medidos no processador real onde vão rodar.

O meio foi o servidor de pesquisa, declarado no problema como um AMD EPYC: 6 núcleos lógicos, dos quais 3 ficaram para cada problema, e 11.960 MiB de memória (`corrida_motor8/problema.json` e `estado.json`). O compilador foi declarado por caminho e sha256, com `-O2 -march=native`; o texto da época diz gcc 13. O modelo do processador e a versão do compilador não ficaram gravados nos registros.

A referência foi a rede ótima conhecida de 19 comparadores, com a troca mais simples e os valores em registradores, escrita pela mesma parte que fez a busca. O processo que mediu a vencedora, durante a busca, mediu também duas alternativas:
- a versão vetorial em AVX2, cerca de 2 vezes mais lenta nesse processo (44,762 contra 23,359 ciclos, razão das medianas de 1,916); nas 48 medidas do ledger, essa razão vai de 1,62 a 1,99;
- o `std::sort` da biblioteca padrão, medido em nanossegundos (104,5 ns nesse processo); a frequência do contador não foi gravada, e por isso o fator contra a referência não pode ser conferido.

Por isso a régua ficou na rede escalar, a mais forte entre as medidas naquele meio. A versão vetorial com imediatos, que a ferramenta tem, não foi usada como referência.

## O que se pediu e o que se mediu antes

O pedido (o D) tinha duas cláusulas:
- ser correta em todos os vetores;
- ser pelo menos 3% mais rápida que a referência, medida no próprio servidor, com resolução de 1%.

O D foi formulado e confirmado pela IA no lugar do criador, e o limite de 3% foi posto por ela. Houve 0 pedidos ao criador (`corrida_motor8/estado.json`, campos `decisoes_da_ia_no_lugar_do_criador` e `contadores`).

O medidor (o Π) foi construído e conferido antes da busca:
- conta ciclos do processador em blocos alternados de 256 vetores, revezando o candidato, a referência e uma cópia idêntica da referência;
- a razão da referência contra a própria cópia dá a distorção do meio sozinho;
- a conferência registrada antes da busca deu ruído de 0,0113 e desvio da referência contra a cópia de 0,0053 (`corrida_motor8/respostas/007_conferir_distinguibilidade.json`); a soma, 1,66%, fica abaixo dos 3% pedidos.

Os valores de 1,000 e de 0,46% que aparecem na tabela abaixo foram medidos durante a busca, no processo da vencedora.

A correção é conferida de forma exaustiva: todos os 8⁸ = 16.777.216 vetores com valores de 0 a 7, que cobrem todas as ordens possíveis, inclusive com empates. Um oráculo, por outro método do mesmo autor, confere a mesma rede pelo princípio 0-1 e exige que as duas conferências concordem.

## O que a máquina fez

O candidato nunca manda código ao compilador. Ele passa só uma descrição: que rede usar, a ordem dos comparadores dentro de cada nível, o tipo de troca e se os valores ficam em registradores ou na memória. A ferramenta declarada gera o C++ a partir dessa descrição, compila, confere a correção e mede no mesmo processo que a referência.

A busca rodou com população de 48 e parou quando a melhor fronteira ficou igual por 3 gerações seguidas. Foram 7 gerações, 384 candidatos e 581,7 segundos. O ledger guarda os 48 vereditos da população final; os outros 336 candidatos estão apenas contados (`estado.json` e `diario.jsonl`). O desfecho registrado foi "solução: melhor encontrado e verificado". Ele não foi demonstrado como o melhor possível, porque parte do espaço foi amostrada.

## Os números

| rotina | ciclos por vetor | razão contra a referência | critério da razão |
|---|---|---|---|
| referência: rede ótima, troca em registradores | 23,359 | 1,000 | a referência contra a própria cópia, no processo da vencedora |
| vencedora | 22,273 | 0,957 (4,3% menos ciclos) | a mediana, em 21 repetições, das medianas das razões por bloco; a razão das medianas, 22,273/23,359, dá 0,9535 |
| versão vetorial AVX2 | 44,762 | 1,916 | a razão das medianas; pelo critério da vencedora, daria cerca de 1,932 |

A vencedora errou 0 dos 16.777.216 vetores, e o oráculo concordou.

A vencedora tem uma só medida, de um só processo. Ela foi escolhida como a menor entre 384 medidas únicas e não foi medida de novo. Pela resolução de 1% do D, três candidatos empatam (0,95682, 0,95727 e 0,96393), e o escolhido foi o primeiro da lista (`09_provas_independentes/verif/VERIF_ordenacao.md`, seções 3 e 7).

## O que ela é, sem exagero

A vencedora usa a mesma rede ótima de 19 comparadores da referência. Duas coisas mudaram: a ordem dos comparadores dentro de cada nível, e o lugar da troca, que passou a ser feita na memória e não nos registradores. O ganho vem do meio, isto é, da forma como aquele processador e aquele compilador executam esse código. Ele não traz uma rede nova e não marca fronteira. Em outro processador, o ganho pode ser outro ou não existir.

Os limites:
- **D de 15%:** pedido logo depois, não foi cumprido. Não há registro dessa corrida no repositório.
- **6 elementos:** este texto dizia que a busca empacou numa violação de 0,062. A seção 22 da fórmula diz que, nos 6 elementos, V não calibrou e a corrida não começou. Os dois relatos divergem, e não há registro de corrida de 6 elementos no repositório.
- **Cache de quem chama:** o efeito sobre o cache do programa que chama a rotina não foi medido e ficou declarado como zero.

## O que o resultado mostra

A máquina rodou de ponta a ponta num meio real. O D, os números do meio e o medidor foram montados antes, e ela entregou uma rotina conferida em todos os vetores, com menos ciclos que a referência naquele servidor. Isso não mostra que a seleção ganha de uma busca simples. Numa verificação independente num Intel Xeon (`09_provas_independentes/provas/motor_aqui/RELATORIO.md`), o mesmo motor ganhou de um sorteio cego com o mesmo orçamento e empatou com um sorteio que mantém os 19 comparadores.

## Onde está cada evidência

- `ORDENACAO_PLANO.md`: o plano, escrito antes de rodar.
- `01_resultado_8_elementos/`
  - `rotina_8_vencedora_e_referencia.cpp`: a vencedora e a referência, idênticas às medidas em 29/09, com a conferência exaustiva e o medidor de ciclos. O programa que rodou naquele dia media também a versão AVX2, que não está neste arquivo.
  - `rede_vencedora.json`: a descrição registrada do candidato, a rede reconstruída, as medidas no servidor e o desfecho.
  - `corrida_motor8/`: o estado da corrida (`estado.json`), o livro de cada avaliação (`ledger.jsonl`), o diário, a auditoria e as respostas de cada etapa (formular D, mapear os números, propor o modelo, medir o alvo, conferir a distinguibilidade).
  - `corrida_motor8_roteiro.log`: o registro da corrida no servidor.

Os arquivos de `corrida_motor8/` são os registros que a máquina gravou, sem nenhuma edição. O `rede_vencedora.json` e o `.cpp` foram montados depois da corrida, porque a exportação do motor falhou (`estado.json`, campo `exportacao`). O código do motor que os produziu está em `03_motor_de_29-09/`.

## Como reproduzir

No Linux, num processador x86-64:

```
g++ -O2 -march=native -std=c++17 -falign-functions=64 -falign-loops=64 rotina_8_vencedora_e_referencia.cpp -o rotina
./rotina 21
```

A saída é uma linha JSON com:
- o erro de ordenação e os vetores conferidos;
- os ciclos por vetor da vencedora e da referência;
- a razão entre elas e a razão da referência contra a própria cópia;
- o ruído.

No servidor de 29/09, a razão foi de 0,957. Em outro processador ela muda, e a própria saída mostra quanto. Na verificação independente, foi de 0,960 a 0,961 num Intel Xeon de 2,1 GHz e de 0,990 a 0,993 num Intel Xeon de 2,8 GHz (`09_provas_independentes/provas/b1/`).

Os registros da corrida não contêm endereço de servidor nem chave.
