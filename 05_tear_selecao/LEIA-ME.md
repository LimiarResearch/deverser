# O Tear, só com a seleção

O Tear é a máquina do leito. Ele tem três órgãos ligados num circuito: o leito, que julga; a ilha, que seleciona; e a mente, que constrói. Este pacote traz só os dois primeiros, a seleção e o juiz, sem as ferramentas de composição e sem a mente.

- **A ilha** (`experimentos/vida_v3c_c.c`, funções `ilha_*`):
  - uma população de 64 programas;
  - o pai sai por torneio de 8;
  - o filho sai por mutação;
  - quem bate o recorde é confirmado em níveis, por remedidas, antes de contar.
- **O leito** (`experimentos/vida_v3c_c.c` e `vida_v3c.py`):
  - cada programa vive uma vida inteira, de degraus de aprender e responder;
  - a vida é julgada por 15 cláusulas;
  - a distância a D, em milésimos, sai da régua da C★;
  - o banco de vidas retidas é medido ao lado de cada recorde.
- **O candidato:** um programa de 128 instruções de uma máquina mínima (`maquina_minima.py`), escrito como foto atômica de bits (`foto_atomica.py`).

**De onde veio.** O código dos seis arquivos de `experimentos/` é idêntico ao da árvore do Tear de 05/10/2026, a versão empacotada em 15/10/2026; só os comentários que transcreviam conversas foram reescritos como decisões formais. `rodar_ilha.py` é novo e faz duas coisas: liga a ilha nesse leito e roda.

Na montagem, a mesma semente rodou duas vezes, pelo pacote e pela árvore original do Tear. Com 651407 e 5 mil medidas, as duas deram os mesmos recordes, byte a byte.

**Rodar.** Precisa de Python 3.11 ou mais novo, numpy e gcc com OpenMP. Em outubro ele rodou no Linux do servidor de pesquisa; na montagem do pacote, foi testado no Windows, com o gcc do MinGW. A vida em C é compilada na primeira vez.

```
python -B rodar_ilha.py <semente> <medidas> <pasta>
python -B rodar_ilha.py 651407 50000 corrida_teste
```

A pasta recebe:
- `recordes.jsonl`, com cada recorde, a medida em que apareceu e o banco;
- `melhor.json`;
- `progresso.json`;
- `estado.pkl`, que permite relançar com a mesma pasta para continuar;
- `fim.json`.

**O ambiente:** `rodar_ilha.py` fixa os mesmos valores das corridas de outubro:
- `VIDA_JANELA=2`;
- `VIDA_REGUA_V32=1`;
- `VIDA_FIOS=1`.

Sem `VIDA_JANELA=2`, a vida em C trata as operações 10 a 13 como nada, e o resultado sai errado sem aviso. Este pacote traz só o leito original, a família 0. As famílias sorteadas do degrau 1 ficam de fora.
