"""Os candidatos a partir da representação que a IA propôs: arquétipos (formas estruturais diferentes), cada um com variáveis de domínio
declarado. Nada aqui sabe do domínio.

- grade: o produto das variáveis (reais em níveis igualmente espaçados, 5 por padrão ou o passo declarado), quando cabe no orçamento;
- amostra: hipercubo latino com semente fixa, quando a grade não cabe;
- nsga2: o evolutivo multiobjetivo genérico sobre a mesma representação (a linha de base (c), e o refino opcional).
"""
import itertools
import json
import random


def niveis(v, n=5):
    t = v["tipo"]
    if t == "categoria":
        return list(v["valores"])
    if t == "inteiro":
        lo, hi = int(v["min"]), int(v["max"])
        passo = int(v.get("passo") or max(1, (hi - lo) // (n - 1) if n > 1 else 1))
        return list(range(lo, hi + 1, passo))
    lo, hi = float(v["min"]), float(v["max"])
    if v.get("passo"):
        k = int(round((hi - lo) / float(v["passo"]))) + 1
        return [round(lo + i * float(v["passo"]), 10) for i in range(k)]
    return [round(lo + (hi - lo) * i / (n - 1), 10) for i in range(n)]


def _id(arq, x):
    return arq + "|" + "|".join(f"{k}={json.dumps(x[k], sort_keys=True) if isinstance(x[k], (list, dict)) else x[k]}" for k in sorted(x))


# L como linguagem que compõe (fórmula 4.0): além dos arquétipos, a representação pode declarar
#   "composicao": {"primitivas": [{"nome", "variaveis"}], "min_pecas": 1, "max_pecas": k, "variaveis": [genes do corpus inteiro]}
# e cada candidato é um corpus feito de peças: {"pecas": [{"primitiva": nome, ...variáveis}], ...genes}, com _arquetipo "composicao".
# As formas que cabem em L são todas as listas de peças até max_pecas, e não só as que alguém listou.
def _valor_novo(v, r):
    if v["tipo"] == "real":
        return round(float(v["min"]) + (float(v["max"]) - float(v["min"])) * r.random(), 6)
    n = niveis(v)
    return n[r.randrange(len(n))]


def _mutar_valor(v, atual, r):
    if v["tipo"] == "real":
        lo, hi = float(v["min"]), float(v["max"])
        return round(min(hi, max(lo, atual + r.gauss(0, (hi - lo) / 6))), 6)
    return r.choice(niveis(v))


def _peca_nova(prims, r):
    p = prims[r.randrange(len(prims))]
    return dict({"primitiva": p["nome"]}, **{v["nome"]: _valor_novo(v, r) for v in p.get("variaveis", [])})


def _composto(comp, pecas, genes):
    x = dict(genes, pecas=pecas)
    return dict(x, _arquetipo="composicao", _id=_id("composicao", x))


def compostos(comp, n, semente=7):
    r = random.Random(semente + 101)
    prims, out, vistos = comp["primitivas"], [], set()
    lo, hi = int(comp.get("min_pecas", 1)), int(comp["max_pecas"])
    for _ in range(4 * n):
        if len(out) >= n:
            break
        pecas = [_peca_nova(prims, r) for _ in range(r.randint(lo, hi))]
        c = _composto(comp, pecas, {v["nome"]: _valor_novo(v, r) for v in comp.get("variaveis", [])})
        if c["_id"] not in vistos:
            vistos.add(c["_id"])
            out.append(c)
    return out


def _mutar_composto(x, comp, r, taxa):
    prims = {p["nome"]: p for p in comp["primitivas"]}
    pecas = [dict(p) for p in x["pecas"]]
    for p in pecas:
        for v in prims[p["primitiva"]].get("variaveis", []):
            if r.random() < taxa:
                p[v["nome"]] = _mutar_valor(v, p[v["nome"]], r)
    if r.random() < taxa and len(pecas) < int(comp["max_pecas"]):
        pecas.insert(r.randrange(len(pecas) + 1), _peca_nova(comp["primitivas"], r))
    if r.random() < taxa and len(pecas) > int(comp.get("min_pecas", 1)):
        pecas.pop(r.randrange(len(pecas)))
    if r.random() < taxa:
        pecas[r.randrange(len(pecas))] = _peca_nova(comp["primitivas"], r)
    genes = {k: v for k, v in x.items() if not k.startswith("_") and k != "pecas"}
    for v in comp.get("variaveis", []):
        if r.random() < taxa:
            genes[v["nome"]] = _mutar_valor(v, genes[v["nome"]], r)
    return _composto(comp, pecas, genes)


def grade_ou_amostra(representacao, orcamento, semente=7):
    """Todas as formulações que cabem no orçamento, repartido entre os arquétipos."""
    arqs = representacao["arquetipos"]
    comp = representacao.get("composicao")
    cota = max(1, orcamento // max(1, len(arqs) + (1 if comp else 0)))
    out = compostos(comp, cota, semente) if comp else []
    for a in arqs:
        vs = a.get("variaveis", [])
        nv = [niveis(v) for v in vs]
        total = 1
        for n in nv:
            total *= len(n)
        if total <= cota:
            combos = itertools.product(*nv) if vs else [()]
            for c in combos:
                x = dict(zip([v["nome"] for v in vs], c))
                out.append(dict(x, _arquetipo=a["nome"], _id=_id(a["nome"], x)))
        else:
            r = random.Random(semente)
            colunas = []
            for v, n in zip(vs, nv):
                if v["tipo"] == "real":
                    faixas = [(i + r.random()) / cota for i in range(cota)]
                    r.shuffle(faixas)
                    colunas.append([round(float(v["min"]) + (float(v["max"]) - float(v["min"])) * f, 6) for f in faixas])
                else:
                    colunas.append([n[r.randrange(len(n))] for _ in range(cota)])
            vistos = set()
            for i in range(cota):
                x = {v["nome"]: colunas[j][i] for j, v in enumerate(vs)}
                k = _id(a["nome"], x)
                if k not in vistos:
                    vistos.add(k)
                    out.append(dict(x, _arquetipo=a["nome"], _id=k))
    return out


def mutar(x, arq, r, taxa=0.25):
    y = dict(x)
    # a engrenagem do motor como gene: quando a representação declara taxa_de_mutacao, o passo da variação é herdado e muta junto
    taxa = float(x.get("taxa_de_mutacao", taxa))
    if x.get("_arquetipo") == "composicao":
        return _mutar_composto(x, arq, r, taxa)
    for v in arq.get("variaveis", []):
        if r.random() < taxa:
            if v["tipo"] == "real":
                lo, hi = float(v["min"]), float(v["max"])
                y[v["nome"]] = round(min(hi, max(lo, y[v["nome"]] + r.gauss(0, (hi - lo) / 6))), 6)
            else:
                y[v["nome"]] = r.choice(niveis(v))
    y["_id"] = _id(arq["nome"], {k: y[k] for k in y if not k.startswith("_")})
    return y


def nsga2(representacao, avaliar_lote, objetivos, violacao, orcamento, semente=1, populacao=40, parar_sem_melhora=None, teto_s=None):
    """avaliar_lote(lista de candidatos) -> lista de (objetivos como vetor a minimizar, violação >= 0), na mesma ordem.
    parar_sem_melhora: a concorrência para quando a primeira fronteira da população fica igual por esse número de gerações seguidas
    (a máquina parou de achar concorrente melhor); orcamento e teto_s ficam como tetos de segurança."""
    import time as _tempo
    _t0 = _tempo.perf_counter()
    _parada = {"motivo": "orçamento", "geracoes": 0, "sem_melhora": 0}
    r = random.Random(semente)
    arqs = {a["nome"]: a for a in representacao["arquetipos"]}
    if representacao.get("composicao"):
        arqs["composicao"] = dict(representacao["composicao"], nome="composicao")
    inicio = grade_ou_amostra(representacao, populacao, semente)
    r.shuffle(inicio)
    pop = inicio[:populacao]
    memo = {}

    def aval(cs):
        novos = [c for c in cs if c["_id"] not in memo]
        for c, v in zip(novos, avaliar_lote(novos) if novos else []):
            memo[c["_id"]] = v
        return [memo[c["_id"]] for c in cs]

    def domina(a, b):
        if a[1] < b[1]:
            return True
        if a[1] > b[1] or a[1] > 0:
            return False
        return all(x <= y for x, y in zip(a[0], b[0])) and any(x < y for x, y in zip(a[0], b[0]))
    aval(pop)
    frente_antes = None
    while len(memo) < orcamento:
        if teto_s and _tempo.perf_counter() - _t0 > teto_s:
            _parada["motivo"] = "teto de tempo"
            break
        filhos = []
        for _ in range(populacao):
            a, b = r.sample(pop, 2), r.sample(pop, 2)
            pa = a[0] if domina(memo[a[0]["_id"]], memo[a[1]["_id"]]) else a[1]
            pb = b[0] if domina(memo[b[0]["_id"]], memo[b[1]["_id"]]) else b[1]
            if pa["_arquetipo"] == pb["_arquetipo"] == "composicao":
                # o cruzamento de dois corpos compostos: o começo de um com o fim do outro
                i, j = r.randint(0, len(pa["pecas"])), r.randint(0, len(pb["pecas"]))
                filho = {k: (pa[k] if r.random() < 0.5 else pb[k]) for k in pa if not k.startswith("_") and k != "pecas"}
                filho["pecas"] = (pa["pecas"][:i] + pb["pecas"][j:])[: int(arqs["composicao"]["max_pecas"])] or pa["pecas"][:1]
                filho["_arquetipo"] = "composicao"
            elif pa["_arquetipo"] == pb["_arquetipo"]:
                filho = {k: (pa[k] if r.random() < 0.5 else pb[k]) for k in pa if not k.startswith("_")}
                filho["_arquetipo"] = pa["_arquetipo"]
            else:
                filho = {k: v for k, v in pa.items() if not k.startswith("_id")}
            filhos.append(mutar(filho, arqs[filho["_arquetipo"]], r))
        filhos = [f for f in filhos if f["_id"] not in memo][: max(0, orcamento - len(memo))]
        if not filhos:
            break
        aval(filhos)
        uniao = {c["_id"]: c for c in pop + filhos}
        cs = list(uniao.values())
        nova, restantes = [], cs
        while restantes and len(nova) < populacao:
            frente = [c for c in restantes if not any(domina(memo[d["_id"]], memo[c["_id"]]) for d in restantes if d is not c)]
            if len(nova) + len(frente) > populacao:
                frente = sorted(frente, key=lambda c: (memo[c["_id"]][1], memo[c["_id"]][0]))[:populacao - len(nova)]
            nova += frente
            restantes = [c for c in restantes if c not in frente]
        pop = nova
        _parada["geracoes"] += 1
        # a fronteira parada é a dos VALORES (violação e objetivos), não a dos nomes: concorrentes novos que só empatam com os da frente não
        # são concorrentes melhores (achado em 29/09: com empates, a lista de nomes mudava a cada geração e o laço nunca perguntava a causa)
        frente = frozenset((round(float(memo[c["_id"]][1]), 9), tuple(round(float(x), 9) for x in memo[c["_id"]][0]))
                           for c in pop if not any(domina(memo[d["_id"]], memo[c["_id"]]) for d in pop if d is not c))
        _parada["sem_melhora"] = _parada["sem_melhora"] + 1 if frente == frente_antes else 0
        frente_antes = frente
        if parar_sem_melhora and _parada["sem_melhora"] >= parar_sem_melhora:
            _parada["motivo"] = f"a primeira fronteira ficou igual por {parar_sem_melhora} gerações seguidas"
            break
    nsga2.ultima_parada = dict(_parada, avaliados=len(memo), segundos=round(_tempo.perf_counter() - _t0, 1))
    return [dict(c, _avaliacao=memo[c["_id"]]) for c in pop], len(memo)
