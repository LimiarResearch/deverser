# A Máquina do Dever-Ser 4.3.1, só com a seleção

A Máquina do Dever-Ser 4.3.1 (01/10/2026) sem a rede que aprende: a fórmula com a variação às cegas, que é a condição F0 da própria fórmula.

**O que faz.** Dado um D (cláusulas que um medidor V sabe julgar) e uma codificação do candidato em bits (a foto atômica), a máquina:

1. sorteia 64 fotos de partida e as mede por V;
2. a cada rodada escolhe um pai entre as fotos medidas, pelo posto de distância a D ou, numa fração das rodadas, ao acaso;
3. deixa cada braço propor 10 filhos do mesmo pai, e V mede todos;
4. guarda toda foto medida;
5. para quando uma foto cumpre D inteiro e espera o Ok de uma pessoa.

V é o único juiz.

- **Os braços:**
  - `cega`: a escrita às cegas da 4.3.1. Reescreve um campo, alguns bits, uma unidade ou uma janela da foto com bits sorteados.
  - `operador`: o operador de mutação da codificação.
  - `sorteio` (opcional): fotos novas, sem pai. É o acaso puro, a condição R0 da fórmula.
- **As regras da 4.3.1 continuam:**
  - nada é lançado sem `--autorizacao`;
  - a codificação passa pela bateria do contrato da foto atômica antes de qualquer medida;
  - se V traz controles, a corrida só começa se ele passa neles;
  - se V traz hash, o hash é conferido na partida e no fim.

**De onde veio cada peça:**

| arquivo | origem |
|---|---|
| `experimentos/foto_atomica.py` | o da 4.3.1, com o mesmo código; só o cabeçalho foi reescrito como decisão formal |
| `experimentos/problema_de_d.py` | o da 4.3.1, sem as duas funções que montavam o Ser e o L2, cujos V não vêm neste pacote |
| `experimentos/variacao.py` | a escrita às cegas, o operador e o mapa da codificação, copiados sem mudança de `escritor_de_fotos.py` da 4.3.1 (sha256 do original `ee71d10e…67ff65d`); a classe `Molde` é nova e guarda do pai só o que a escrita às cegas lê |
| `experimentos/condutor_de_selecao.py` | novo, escrito em 16/10/2026: o condutor da 4.3.1 sem a rede, a memória de edições, a biblioteca, os motivos, as piscinas, as sementes da rede, a catraca e a retomada |
| `exemplos/novo_d_do_zero.py` | idêntico ao da 4.3.1: o D de exemplo, uma lista de 8 números com seis cláusulas |

O condutor foi escrito agora, a partir da 4.3.1, e não rodou antes desta data.

**Conferir.** Com Python 3.11 ou mais novo e numpy (`pip install -r requirements.txt`):

```
python -B testes/test_selecao.py
```

O resultado esperado é "11 de 11 provas passaram", em alguns segundos.

**Rodar o exemplo:**

```
python -B -m experimentos.condutor_de_selecao --problema exemplos.novo_d_do_zero:criar --saida corrida_exemplo --semente 2 --max-rodadas 3000 --autorizacao "seu nome, a data"
```

Na montagem, com a semente 2, a máquina achou o D do exemplo em 12 rodadas e 300 medidas de V, parou e gravou `candidata_296.json`.

**Um D seu.** Escreva um módulo com uma função sem argumentos que devolva `(problema, avaliador)`, como em `exemplos/novo_d_do_zero.py`:
- a codificação em bits, que herda de `foto_atomica.CodificacaoBase`;
- as cláusulas de D;
- o medidor;
- o `Problema`.

A pasta da corrida recebe:
- `declaracao.json`, com a corrida inteira e a conta de V por finalidade e por braço;
- `fotos.jsonl`, com cada foto medida;
- `eventos.jsonl`;
- `candidata_<k>.json`, quando D é cumprido.
