"""A seleção entre corpos válidos: os requisitos rígidos já foram cumpridos por todos; aqui entram os objetivos de D.

- pareto: os corpos que nenhum outro domina em todos os objetivos, e, para cada dominado, um corpo que o domina;
- preferir: a ordem que o criador declarou (lexicográfica ou por pesos explícitos), com a explicação de cada posição.
Nenhuma utilidade escondida: sem objetivos declarados, todos os válidos ficam na fronteira.

A dominância respeita a incerteza: quando a medida vem com intervalo (medida + "_intervalo" nas medidas do veredito), um corpo só é
melhor que outro nesse objetivo se os intervalos não se tocam; e o objetivo pode declarar uma resolução (teste["resolucao"]), abaixo da
qual duas medidas contam como iguais. Diferença que a medida não separa não decide nada.
"""


def _faixa(v, o):
    m = v["veredito"]["medidas"]
    x = m.get(o["teste"]["medida"])
    if x is None:
        return None
    lo, hi = m.get(o["teste"]["medida"] + "_intervalo") or [x, x]
    r = o["teste"].get("resolucao", 0) / 2
    lo, hi = lo - r, hi + r
    return (lo, hi) if o["teste"]["sentido"] == "min" else (-hi, -lo)


def _domina(a, b):
    """a domina b: em todo objetivo a não é pior (as faixas se tocam ou a está abaixo), e em algum a é separadamente melhor."""
    if None in a or None in b:
        return False
    nao_pior = all(x[0] <= y[1] for x, y in zip(a, b))
    melhor = any(x[1] < y[0] for x, y in zip(a, b))
    return nao_pior and melhor


def pareto(validos, objetivos):
    fx = [[_faixa(v, o) for o in objetivos] for v in validos]
    fronteira, dominados = [], []
    for i, a in enumerate(fx):
        quem = next((j for j, b in enumerate(fx) if j != i and _domina(b, a)), None)
        (fronteira if quem is None else dominados).append(i if quem is None else (i, quem))
    return {"fronteira": fronteira, "dominados": [{"corpo": i, "dominado_por": j} for i, j in dominados]}


def preferir(validos, preferencia):
    """preferencia: {"ordem": [(medida, "min"|"max"), ...]} (lexicográfica) ou {"pesos": {medida: peso}} (soma ponderada declarada).
    A ordem usa o valor central da medida; a fronteira de Pareto é que diz quais diferenças a medida separa."""
    def chave(v):
        m = v["veredito"]["medidas"]
        if "ordem" in preferencia:
            return tuple((m[k] if s == "min" else -m[k]) for k, s in preferencia["ordem"])
        return sum(w * m[k] for k, w in preferencia["pesos"].items())
    ordem = sorted(range(len(validos)), key=lambda i: chave(validos[i]))
    return {"ordem": ordem, "criterio": preferencia}
