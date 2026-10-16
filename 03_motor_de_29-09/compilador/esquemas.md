# Os formatos das respostas ao motor

Este é o protocolo entre o motor do compilador e quem responde aos pedidos dele: a IA do usuário, o criador e o avaliador independente. Cada pedido chega como um arquivo JSON em `pendentes/`. A resposta é **um objeto JSON**, no formato da seção do tipo do pedido. Ela é copiada sem edição para `respostas/<id>.json`.

**Regras gerais:**
- Unidades: escritas com `*`, `/` e `^` ("m/s", "kg*m/s^2", "W/m^2", "kWh/m^2/d", "MB", "ms").
- Nada é inventado sem ser marcado. Um número sem fonte vai como `"tipo_de_fonte": "ia"`, e o motor o trata como hipótese.

**Onde roda o código:**
- **Modelos, testes e exportação:** funções Python puras que o motor roda numa caixa isolada. Só podem importar `math`, `numpy` (já disponível como `np`), `statistics`, `itertools`, `functools`, `random`, `bisect`, `heapq`, `collections`, `fractions`, `decimal`, `operator`. Não abrem arquivos nem acessam a rede.
- **Candidatos de problemas de máquina:** o código roda na máquina alvo. Não pode importar `os`, `sys`, `subprocess`, `socket`, `shutil`, `ctypes`, `multiprocessing`, `threading`, `urllib`, `http`, `pathlib`, `importlib`, `tempfile`, `glob`, nem usar `open`.

## formular_D (para a IA)

O pedido traz a intenção do criador, o tipo do problema ("maquina" ou "lugar"), os alvos e o lugar. A resposta:

```json
{
 "clausulas": [
  {"id": "r_...", "tipo": "rigida", "enunciado": "texto por extenso", "teste": {"medida": "nome_da_saida", "op": "<=", "valor": 2.0, "unidade": "ms"}},
  {"id": "o_...", "tipo": "objetivo", "enunciado": "...", "teste": {"medida": "nome_da_saida", "sentido": "min", "resolucao": 0.0}},
  {"id": "p_...", "tipo": "preferencia", "enunciado": "...", "teste": {"ordem": [["saida_a", "min"], ["saida_b", "max"]]}}
 ],
 "escopo": {"...": "o que delimita o problema: carga, lugar, período, alvo"},
 "ambiguidades": [{"id": "a1", "pergunta": "...", "opcoes": ["...", "..."]}],
 "condicoes_de_uso": ["..."]
}
```

- `op` pode ser `<=`, `>=`, `<`, `>` ou `==`.
- As medidas são os nomes das saídas que o modelo terá de calcular, e têm de ser os mesmos depois.

## confirmar_D (para o criador)

```json
{"clausulas": {"r_x": {"acao": "confirmar"}, "r_y": {"acao": "corrigir", "clausula": {"enunciado": "...", "teste": {"...": "..."}}}, "r_z": {"acao": "recusar"}},
 "acrescentar": [{"id": "...", "tipo": "rigida", "enunciado": "...", "teste": {"...": "..."}}],
 "ambiguidades": {"a1": "a resposta"},
 "escopo": {"...": "correções do escopo, se houver"}}
```

## mapear_numeros (para a IA e, sem ver o dela, para o avaliador)

Logo depois de o criador confirmar o D, a IA lista, cláusula por cláusula, **todos** os números do meio que decidem cada uma. São as constantes do meio. No silício: CPU, memória, disco (custo de `fsync`), rede, versões, cargas. No mundo real: clima e séries, solo, vento de projeto, propriedades dos materiais, normas. O mapa vem do D, e não de um modelo já escolhido. Com avaliador, ele faz o mapa dele sem ver o da IA, e o motor usa a união das duas listas.

```json
{"numeros": {"vento_de_projeto": {"clausulas": ["r_estrutura"], "unidade": "m/s", "grandeza": {"quantidade": "velocidade do vento", "estatistica": "rajada 3 s", "periodo_de_retorno_anos": 50},
                                  "onde": "norma de vento do país ou série de rajadas da estação mais próxima", "por_que": "a carga na cobertura cresce com o quadrado do vento"}}}
```

Depois, o modelo usa cada número do mapa como entrada ou o põe em `"numeros_excluidos": {"nome": "justificativa"}`. Se não fizer nenhum dos dois, o teste do modelo falha por cobertura, e o motor pede revisão.

## propor_modelo e revisar (para a IA)

A resposta tem `"modelo"`, completo a cada vez: uma revisão substitui o modelo inteiro. Pode ter também `"motivo"`, e pode ter `"mudar_D": {"clausulas": [...], "motivo": "..."}`, que volta ao criador.

**Problemas de lugar ou de cálculo:**

```json
{"modelo": {
  "entradas": [
   {"nome": "rajada_projeto", "unidade": "m/s", "descricao": "...", "forma": "escalar",
    "grandeza": {"quantidade": "velocidade do vento", "estatistica": "rajada 3 s", "periodo_de_retorno_anos": 50, "altura_m": 10,
                 "local": {"lat": -23.5, "lon": -46.6, "raio_km": 30}}},
   {"nome": "chuva_diaria", "unidade": "mm/d", "forma": "serie", "grandeza": {"quantidade": "precipitação", "estatistica": "total diário",
    "periodo": ["2015-01-01", "2024-12-31"], "local": {"lat": -23.5, "lon": -46.6, "raio_km": 30}}}
  ],
  "representacao": {"arquetipos": [
   {"nome": "forma_a", "descricao": "...", "variaveis": [
     {"nome": "largura_m", "tipo": "real", "min": 1.0, "max": 4.0, "passo": 0.5, "unidade": "m"},
     {"nome": "material", "tipo": "categoria", "valores": ["aco", "madeira"]},
     {"nome": "n_modulos", "tipo": "inteiro", "min": 1, "max": 6}]}
  ]},
  "modelos": [{"id": "principal", "saidas": [{"nome": "massa_kg", "unidade": "kg"}],
               "codigo": "def calcular(x, p):\n    # x: o candidato (x['_arquetipo'] e as variáveis); p: os números de Π pelo nome, na unidade declarada\n    ...\n    return {'massa_kg': ..., '_fora_de_validade': False}",
               "hipoteses": ["..."], "validade": "o domínio em que o modelo vale"}],
  "testes": [{"id": "t1", "funcao": "teste_caso_limite", "descricao": "...",
              "codigo": "def teste_caso_limite(calcular, p):\n    r = calcular({...}, p)\n    return (r['massa_kg'] > 0, 'detalhe')"}],
  "exportacao": {"codigo": "def exportar(x, p, saidas):\n    return {'primitivas': [...], 'descricao': {...}}"}
}}
```

- Uma série (`"forma": "serie"`) chega ao modelo como a lista que o arquivo contém: JSON carregado, ou as linhas de um CSV como dicionários com os números convertidos.
- `calcular` pode devolver `"_fora_de_validade": true` quando o candidato sai do domínio do modelo.
- Cada entrada pode ter `"valor_de_ensaio"`: um valor plausível, só para o motor testar o modelo antes de os números chegarem. Numa série, é uma lista curta no mesmo formato. Ele nunca entra na criação.
- **As primitivas** da exportação:
  - `{"tipo": "caixa", "centro": [x, y, z], "dimensoes": [a, b, c], "rotacao_z_graus": 0, "nome": "...", "cor": [r, g, b]}`;
  - `{"tipo": "cilindro", "de": [...], "ate": [...], "raio": r, "nome": "...", "cor": [...]}`;
  - em metros, com z para cima.

**Problemas de máquina:**

```json
{"modelo": {
  "entradas": [],
  "representacao": {"arquetipos": [
   {"nome": "implementacao_a", "descricao": "...", "codigo": "def executar(entrada, **params):\n    ...\n    return saida",
    "variaveis": [{"nome": "nivel", "tipo": "inteiro", "min": 1, "max": 9}]}
  ]},
  "carga": "def gerar_carga(semente):\n    # a entrada realista do problema, determinística pela semente\n    ...",
  "metricas": "def metricas(entrada, saida):\n    return {'razao': ..., 'bytes_saida': ...}",
  "oraculo": "def conferir(entrada, saida):\n    return (ok, 'detalhe')",
  "modelos": [{"id": "principal", "saidas": [{"nome": "tempo_p95_s", "unidade": "s"}, {"nome": "razao", "unidade": "1"}], "codigo": "def calcular(x, p):\n    return {}"}],
  "testes": [],
  "exportacao": {"codigo": "def exportar(x, p, saidas):\n    return {'arquivos': {'artefato.py': '...'}}"}
}}
```

- O motor mede no alvo, em rodadas, o tempo de cada chamada de `executar` e o pico de memória.
- Na exportação de máquina, `x["_codigo"]` traz o código do arquétipo escolhido. O arquivo exportado é rodado de novo no alvo com uma semente retida e tem de passar nos oráculos.
- **A foto (opcional, recomendada).** O modelo pode declarar três funções:
  - `"foto": "def foto(entrada, saida): ..."` devolve o comportamento completo do candidato, como listas e números. O executor a tira na primeira rodada, com hash, e o motor a guarda em `fotos/`;
  - `"metricas_da_foto": "def metricas_da_foto(foto): ..."` recalcula as métricas só da foto. Quando só as métricas ou o D mudam, o motor julga pela foto guardada, sem rodar o candidato de novo no alvo;
  - `"comparar_fotos": "def comparar_fotos(a, b): ..."` diz onde dois comportamentos diferem. O resultado vai no pedido de revisão (`diferencas_de_fotos`), para a variação seguinte ser dirigida pela diferença medida.
- As saídas medidas que D pode julgar:
  - `tempo_mediana_s`, `tempo_p95_s` e `pico_memoria_mb`;
  - `correto`, que vale 1 quando o oráculo passa;
  - as chaves de `metricas`.

## buscar_numero (para a IA)

O pedido traz, para cada número, a unidade, o descritor da grandeza exigida e, quando é uma segunda busca, por que ele decide e o que foi recusado antes. A resposta:

```json
{"numeros": {
  "rajada_projeto": {
   "candidatos": [{"valor": 38.0, "unidade": "m/s", "incerteza": [34.0, 42.0], "tipo_de_fonte": "estacao",
                   "metodo": "como o valor foi obtido", "origem": "URL", "data": "AAAA-MM-DD", "licenca": "...",
                   "alcance": {"lugar": "...", "periodo": "..."},
                   "grandeza": {"quantidade": "velocidade do vento", "estatistica": "rajada 3 s", "periodo_de_retorno_anos": 50, "altura_m": 10,
                                "local": {"lat": -23.62, "lon": -46.66}}}],
   "consultas": 3,
   "nao_encontrado": "se nada serve: o que foi procurado e por que não serve",
   "hipotese_sugerida": {"valor": 40.0, "incerteza": [30.0, 50.0], "metodo": "de onde vem a hipótese"}
  }
}}
```

- `tipo_de_fonte` é um de: `estacao`, `medicao`, `medido`, `norma`, `reanalise`, `modelo`, `estimativa`, `publicacao`, `ia`.
- Uma série vai como arquivo:
  - a IA baixa o dado público para `dados/` na pasta do problema;
  - o candidato leva `"arquivo": "dados/nome.csv"` e `"sha256"` no lugar de `valor`, e o motor confere o hash.
- A `hipotese_sugerida` só entra se o criador autorizar.

## autorizar_hipotese (para o criador)

```json
{"autorizacoes": {"rajada_projeto": true}}
```

## refutar (para a IA)

```json
{"testes": [{"id": "...", "funcao": "teste_...", "descricao": "...", "codigo": "def teste_...(calcular, p): ..."}]}
```

## medir_alvo (para a IA)

Nos problemas de máquina, o perfil do alvo é número do meio, e por isso vem da IA. O pedido traz a ferramenta `python -B -m compilador medir <pasta>`, que mede o perfil no alvo e imprime uma resposta pronta. A IA pode usá-la, conferir o que ela diz ou medir de outro jeito. Cada número precisa de valor e método; sem método, ele é recusado.

```json
{"numeros": {"ns_por_hash_splitmix": {"valor": 612.0, "unidade": "ns", "incerteza": [598.0, 640.0], "tipo": "medido",
             "metodo": "splitmix64 em Python puro, 20 mil chamadas, 7 repetições: mediana, intervalo mín-máx", "fonte": "executor no alvo vps-epyc",
             "data": "2026-09-28T18:00:00-03:00"}}}
```

## trabalhos e autorizar_trabalho (a IA declara, o criador autoriza)

Um modelo pode declarar `"trabalhos"`: comandos longos que rodam fora da caixa, como um treino, uma simulação pesada ou uma biblioteca grande que a caixa não carrega. Cada um roda só depois de o criador autorizar aquele trabalho exato. O hash cobre o comando, os arquivos, os tetos e as saídas, e qualquer mudança pede outra autorização. As saídas voltam com o SHA-256 em `estado.trabalhos` (ver `compilador/trabalho.py`).

```json
{"trabalhos": [{"nome": "treino_da_cabeca", "comando": ["{python}", "treinar.py"], "arquivos": {"treinar.py": "..."},
                "teto_s": 7200, "teto_mb": 8000, "saidas": ["metricas.json"], "descricao": "o que o trabalho faz e por quê"}]}
```

A resposta do criador a `autorizar_trabalho` é `{"autorizado": true}` ou `{"autorizado": false, "motivo": "..."}`.

## modelo_alternativo (para o avaliador)

Ele recebe D, as entradas (nomes, unidades, grandezas), as saídas que D julga e a representação dos candidatos, e não recebe o modelo do outro. A resposta:

```json
{"modelo": {"modelos": [{"id": "alternativo", "saidas": [{"nome": "...", "unidade": "..."}], "codigo": "def calcular(x, p): ..."}],
            "tolerancias": {"nome_da_saida": 0.15}, "hipoteses": ["..."]}}
```

- Num problema de máquina, o avaliador manda `"oraculo": "def conferir(entrada, saida): ..."`, um oráculo próprio para as saídas dos candidatos.

## As voltas da emenda 1 da fórmula 4.0 (29/09)

**conferir_distinguibilidade (para o avaliador, ou para a IA sem avaliador).** Antes da busca. Resposta:
`{"clausulas": {"<id>": {"distinguivel": true|false, "prova": "...", "medida": {...}}}}`. Uma cláusula com `distinguivel: false` precisa de uma prova que não dependa de L (o meio não entrega a informação que a decide, para nenhuma forma); o desfecho é `impossivel_no_meio` e a pergunta vai ao criador.

**No modelo (propor_modelo e revisar):**
- `dominio`: `{"arquetipos": [...], "variaveis": {"<nome>": [min, max] ou [valores]}}`, o domínio em que M foi validado. Candidatos fora dele não contam em A e viram pedido de validação.
- nas medidas do candidato, `efeito_no_meio`: `{"<numero de Π>": variação}`, o quanto o corpus muda o meio. O escolhido é medido de novo em Π ⊕ ε até o efeito parar de mudar (o ponto fixo).

**No D:** `escopo.horizonte` (na unidade de tempo das derivas) e `escopo.alem_do_horizonte`. Um corpus que vive além do horizonte precisa de uma cláusula rígida marcada com `"recalcula": true` (o C★ interno, com o V dele); sem ela, o D volta ao criador.

**Em buscar_numero:** `deriva`, a variação do número por unidade de tempo; no horizonte, a incerteza cobre a trajetória.

**No problema:** `"populacao": "sigma"` (ou ausente) deixa σ escolher a população e a parada pelo custo medido de um lote; `"conferir_distinguibilidade": true` é o padrão.

**O mundo:** `python -B -m compilador mundo <pasta> <arquivo.json>` com `{"artefato", "resultado": "falhou" | "cumpriu", "detalhe", "medida"}`. Uma falha reabre o laço como revisar sobre M ou sobre Π.

**L que compõe (na representação):** `"composicao": {"primitivas": [{"nome", "variaveis"}], "min_pecas": 1, "max_pecas": k, "variaveis": [genes do corpo inteiro]}`. Cada candidato chega ao código como `pecas=[{"primitiva": nome, ...variáveis}]` mais os genes, com `_arquetipo` "composicao". O código do candidato monta o corpo a partir das peças.

**Natureza da cláusula (formular_D):** cada cláusula traz `"natureza": "intencao"` ou `"forma"`. Cláusula de forma só fica se o criador disser que é intenção; quando nenhuma forma de L cumpre D, elas voltam a ele antes de qualquer conclusão de impossibilidade.

**A escala da falta (no teste de uma cláusula rígida):** `"escala"` diz quanto vale uma unidade de falta na violação que ordena os que ainda não cumprem D. Sem ela, a falta é dividida pelo próprio limite. O veredito de cumprir ou não cumprir não muda com a escala.

**Emenda 2 do motor (29/09): a ferramenta declarada.** O código do candidato pode importar `ferramenta_passeio`, e só ele além da lista de sempre. A ferramenta roda apenas o binário cujo caminho e sha256 quem lançou o motor declarou (`FERRAMENTA_PASSEIO` e `FERRAMENTA_PASSEIO_SHA256`), com os argumentos conferidos pelo tipo. Sem a declaração, ou com o binário mudado, ela recusa; o candidato cai para a versão em Python, e V confere as duas do mesmo jeito.
