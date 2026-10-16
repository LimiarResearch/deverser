# O motor de 29/09

O motor fechado da fórmula do dever ser 4.0, só com a seleção, exatamente como estava quando achou a rotina de ordenação de 8 elementos 4,3% mais rápida que a rede ótima conhecida, no servidor de pesquisa, em 29/09/2026.

**De onde veio.** Este é o código do commit `7edc5af` do repositório de trabalho, gravado oito segundos antes de a corrida de 8 elementos começar. O aprendiz da variação só entrou no motor depois, no commit `8c47301`, e não está aqui. O código executável é o daquele commit. Mudaram duas coisas, nenhuma delas executável. Os comentários que transcreviam conversas foram reescritos como decisões formais. E na fixture de desenvolvimento `protocolos/dev/dev_maquina.json`, o endereço do servidor, a chave e a pasta remota viraram exemplos.

**O que é.** O motor recebe um problema (`problema.json`), monta D com as respostas de quem responde pelo criador, mapeia os números do meio, mede o alvo e confere a distinguibilidade. Depois busca por seleção: uma população de candidatos é variada, cada candidato é julgado por V, e as melhores formas ficam. A busca para quando a fronteira dos valores fica igual por gerações seguidas, e quando empaca ela pergunta pela causa. No fim, declara um dos cinco estados da fórmula.

| pasta ou arquivo | o que tem |
|---|---|
| `compilador/motor.py` | o motor: as voltas da fórmula, a seleção, a parada e os cinco estados |
| `compilador/` (demais) | a geração de candidatos, o cálculo antes da busca, a avaliação, as unidades, a caixa que isola o candidato e a ferramenta de medida da ordenação |
| `bancada/nucleo/` | D, Π, o livro de cada avaliação (ledger) e a seleção por Pareto |
| `experimentos/montar_ordenacao_motor.py` | a montagem do problema de ordenação (6 e 8 elementos) e das respostas que a IA deu pelo criador |
| `protocolos/calculadora/ordenacao_*_motor_vps.json` | os dois problemas de ordenação |
| `saida/calculadora/ordenacao/motor_respostas_*` | as respostas de cada etapa, marcadas como dadas pela IA |
| `testes/` | as provas |

**Conferir.** Com Python 3.11 ou mais novo e numpy:

```
python -B testes/test_nucleo.py
python -B testes/test_compilador.py
```

As duas devem terminar com 8 e 18 provas em `ok`.

**Rodar a ordenação.** A medida do alvo compila o candidato com o g++ (`compilador/ferramenta_ordenacao.py`) e mede ciclos no próprio processador, em Linux x86-64. Os caminhos de Python gravados nos protocolos são os do servidor onde a corrida rodou; troque-os pelos seus. Cada etapa do motor avança assim:

```
python -B -m compilador iniciar <pasta> protocolos/calculadora/ordenacao_8_motor_vps.json
python -B -m compilador passo <pasta>
python -B -m compilador responder <pasta> <id> saida/calculadora/ordenacao/motor_respostas_8/<arquivo>.json
```

A corrida completa daquela madrugada, com o estado, o livro de avaliações e o programa vencedor, está em `06_evidencias/ordenacao_29-09/`.
