# Uma rotina de ordenação mais rápida no mesmo servidor (29/09/2026)

## O resultado em uma frase

Na madrugada de 29/09/2026, a máquina do dever-ser, no motor fechado da fórmula 4.0, rodou no próprio servidor de pesquisa e procurou uma rotina de ordenação de 8 elementos mais rápida para aquele processador. Em 9,7 minutos e 384 candidatos, achou uma rotina com 4,3% menos ciclos por vetor que a referência, que é a mesma rede ótima de 19 comparadores com a troca feita nos registradores. A rotina é correta em todos os 16.777.216 vetores possíveis e roda no mesmo hardware. O ganho foi medido naquele processador, um AMD EPYC de primeira geração (Zen 1), com o gcc 13; a seção "O que ela é, sem exagero" diz por que ele pode não valer em outro.

## O problema escolhido

As rotinas curtas de ordenação sem desvio são as redes de comparadores que ordenam poucos números com tempo fixo. Elas estão dentro de praticamente todo programa que ordena dados. Em 2023 a DeepMind (AlphaDev, Nature) melhorou as de 3 a 5 elementos, e o resultado entrou na biblioteca padrão do C++ do LLVM. O problema daqui é a continuação natural: 6 e 8 elementos, medidos no processador real onde vão rodar.

O meio foi o servidor de pesquisa: AMD EPYC de primeira geração (Zen 1), 6 núcleos, dos quais 3 ficaram para cada problema, 12 GB de memória, sem GPU. O compilador foi o gcc 13, declarado por caminho e sha256, com `-O2 -march=native`.

A referência foi a rede ótima conhecida de 19 comparadores, com a troca mais simples e os valores em registradores. Antes da corrida ela foi medida contra duas alternativas:
- o `std::sort` da biblioteca padrão, que ficou cerca de 6 vezes mais lento;
- a versão vetorial em AVX2, que nesse processador ficou cerca de 2 vezes mais lenta (44,8 contra 23,4 ciclos).

Por isso a régua ficou na rede escalar, a mais forte naquele meio.

## O que se pediu e o que se mediu antes

O pedido (o D) tinha duas cláusulas:
- ser correta em todos os vetores;
- ser pelo menos 3% mais rápida que a referência, medida no próprio servidor, com resolução de 1%.

O medidor (o Π) foi construído e conferido antes da busca:
- conta ciclos do processador em blocos alternados de 256 vetores, revezando o candidato, a referência e uma cópia idêntica da referência;
- a razão da referência contra a própria cópia dá a distorção do meio sozinho, e deu 1,000;
- o ruído das medidas ficou em 0,46%, e por isso uma diferença de 3% é distinguível com folga.

A correção é conferida de forma exaustiva: todos os 8⁸ = 16.777.216 vetores com valores de 0 a 7, que cobrem todas as ordens possíveis, inclusive com empates. Um oráculo independente confere a mesma rede pelo princípio 0-1 e exige que as duas conferências concordem.

## O que a máquina fez

O candidato nunca manda código ao compilador. Ele passa só uma descrição: que rede usar, a ordem dos comparadores dentro de cada nível, o tipo de troca e se os valores ficam em registradores ou na memória. A ferramenta declarada gera o C++ a partir dessa descrição, compila, confere a correção e mede no mesmo processo que a referência.

A busca rodou com população de 48 e parou quando a melhor fronteira ficou igual por 3 gerações seguidas. Foram 7 gerações, 384 candidatos e 581,7 segundos. O desfecho registrado foi "solução: melhor encontrado e verificado". Ele não foi demonstrado como o melhor possível, porque parte do espaço foi amostrada.

## Os números

| rotina | ciclos por vetor | razão contra a referência |
|---|---|---|
| referência: rede ótima, troca em registradores | 23,359 | 1,000 |
| vencedora | 22,273 | 0,957 (4,3% mais rápida) |
| versão vetorial AVX2 | 44,762 | 1,916 |

A vencedora errou 0 dos 16.777.216 vetores, e o oráculo concordou.

## O que ela é, sem exagero

A vencedora usa a mesma rede ótima de 19 comparadores da referência. Duas coisas mudaram: a ordem dos comparadores dentro de cada nível, e o lugar da troca, que passou a ser feita na memória e não nos registradores. O ganho vem do meio, isto é, da forma como o Zen 1 e o gcc 13 executam esse código. Ele não traz uma rede nova e não marca fronteira. Em outro processador, o ganho pode ser outro ou não existir.

Os limites registrados no mesmo dia:
- **D de 15%:** pedido logo depois, não foi cumprido.
- **6 elementos:** a busca empacou numa violação de 0,062 e pediu outra forma de linguagem.
- **Cache de quem chama:** o efeito sobre o cache do programa que chama a rotina não foi medido e ficou declarado como zero.

## Por que isso importa

É a fórmula funcionando num meio real. O pedido e os números do meio (o processador, o compilador, o ruído do medidor) foram medidos antes. A máquina procurou dentro do que esse meio permite e entregou uma rotina conferida em todos os casos e mais rápida no mesmo hardware. Esse é o formato de uso que o resultado demonstra: a mesma infraestrutura, um código mais rápido, prova de correção exaustiva e uma medida contra o ruído do próprio servidor.

## Onde está cada evidência

- `ORDENACAO_PLANO.md`: o plano, escrito antes de rodar.
- `01_resultado_8_elementos/`
  - `rotina_8_vencedora_e_referencia.cpp`: o programa exato que foi compilado e medido. Tem a vencedora, a referência, a conferência exaustiva e o medidor de ciclos.
  - `rede_vencedora.json`: a descrição registrada do candidato, a rede reconstruída, as medidas no servidor e o desfecho.
  - `corrida_motor8/`: o estado da corrida (`estado.json`), o livro de cada avaliação (`ledger.jsonl`), o diário, a auditoria e as respostas de cada etapa (formular D, mapear os números, propor o modelo, medir o alvo, conferir a distinguibilidade).
  - `corrida_motor8_roteiro.log`: o registro da corrida no servidor.

Os arquivos da corrida são os registros que a máquina gravou, sem nenhuma edição. O código do motor que os produziu está em `03_motor_de_29-09/`.

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

Num Zen 1 com gcc 13, a razão esperada fica perto de 0,957. Em outro processador ela muda, e a própria saída mostra quanto.

Os registros da corrida não contêm endereço de servidor nem chave.
