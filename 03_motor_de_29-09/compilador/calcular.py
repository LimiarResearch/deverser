"""Calcular antes de buscar: a região que cumpre D, deduzida do modelo antes de sortear candidatos.

O acaso itera no mundo e paga com cadáveres. Aqui a iteração fica dentro da conta, e o motor conta os cadáveres: cada candidato calculado
e descartado. Para cada arquétipo, o cálculo percorre a grade da representação por caixas:
- se o modelo é monótono em cada variável para a medida que uma cláusula rígida julga, o canto mais favorável à cláusula decide a caixa
  inteira: se ele não passa (falha ou fica incerto), nenhum ponto da caixa passa, e a caixa cai sem ser calculada;
- se o canto menos favorável de cada cláusula passa, a caixa inteira cumpre as cláusulas, e os pontos dela vão para o cálculo normal
  (os objetivos ainda precisam ser calculados);
- senão, a caixa se divide ao meio na variável mais longa, até virar um ponto.

A monotonia é uma hipótese declarada que o motor mede no próprio modelo da IA, em amostras em linha (o centro e os dois extremos da faixa
de Π). Ela é propriedade do cálculo, e não número do meio: o D e o Π continuam vindo só do usuário e da IA. O que cai por ela fica marcado
como condicional a essa hipótese. O escolhido é sempre calculado de verdade, e nada é aprovado sem ser calculado.
"""
import itertools
import random

from . import gerar
from .avaliar import julgar

OPS = ("<=", ">=", "<", ">", "==")
TETO_DA_GRADE = 200000
HIPOTESE = "monotonia amostrada: o modelo é monótono, em cada variável, nas medidas que D julga (medida pelo motor em amostras em linha)"


def _combinar(sinais):
    s = set(sinais)
    if not s or "misto" in s:
        return "misto"
    if s == {"0"}:
        return "0"
    if s <= {"+", "0"}:
        return "+"
    if s <= {"-", "0"}:
        return "-"
    return "misto"


def _sinal(seq):
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) for v in seq):
        return "misto"
    if all(a == b for a, b in zip(seq, seq[1:])):
        return "0"
    if all(a <= b for a, b in zip(seq, seq[1:])):
        return "+"
    if all(a >= b for a, b in zip(seq, seq[1:])):
        return "-"
    return "misto"


def _quantidades(res, m):
    """O centro e os dois extremos da faixa de uma medida, ou None quando o modelo não calculou."""
    if not res or res.get("erros") or res.get("fora_de_validade") or not isinstance(res.get("centro"), dict):
        return None
    if m not in res["centro"]:
        return None
    c = res["centro"][m]
    lo, hi = (res.get("faixa") or {}).get(m, [c, c])
    return c, lo, hi


class Calculo:
    """avaliar_pontos(lista de candidatos) -> {id: {"centro", "faixa", "erros", "fora_de_validade"}}; as mesmas saídas que a caixa dá."""

    # a forma do cálculo: cada parâmetro é uma escolha interna do motor, e quem escolhe os valores é o próprio cálculo, rodado sobre o
    # motor num banco de problemas com o D da calculadora como juiz (experimentos/motor_otimo.py)
    # escolhida pelo cálculo em 28/09 (saida/motor_otimo/resultado.json): entre 96 formas, a forma anterior (4 amostras, divisão ao meio)
    # perdia um aprovado nos problemas com ondulação; esta cumpre as rígidas no grupo de escolha, no grupo retido e em cinco sementes
    # com a C8 (a hipótese da poda testada no próprio problema, 90% de chance de perceber se 10% dos podados passassem), entre 384
    # formas (saida/motor_otimo/resultado_c8.json): a detecção barata de 2 pontos por linha, com 22 pontos auditados, que desfazem a
    # poda onde a monotonia cai; nenhum aprovado perdido em sete sementes, e o mesmo escolhido da grade inteira em 13 de 13 problemas
    FORMA = {"amostras": 1, "pontos_por_linha": 2, "divisao": "todas", "certificar": True, "amostrar_regiao": True, "auditoria": 22}

    def __init__(self, representacao, rigidas, avaliar_pontos, orcamento, amostras=None, semente=7, forma=None):
        self.rep = representacao
        self.rigidas = [t for t in rigidas if t.get("op") in OPS and isinstance(t.get("valor"), (int, float))]
        self.aval = avaliar_pontos
        self.orc = orcamento
        self.forma = dict(self.FORMA, **(forma or {}))
        if amostras is not None:
            self.forma["amostras"] = amostras
        self.m = self.forma["amostras"]
        self.r = random.Random(semente)
        self.cache = {}
        self.podados = []
        self.a_calcular = {}
        self.monotonia = {}
        # os cantos favoráveis das caixas que caíram: os melhores candidatos que não passam, calculados de verdade; o motor os mantém
        # para a sensibilidade (que número de Π faria um deles passar)
        self.melhores = []
        self._podados_pontos = {}
        self.auditoria = {}

    # ---------------------------------------------------------------- os pontos
    def _ponto(self, arq, cats, ords, niv, idx):
        x = dict(cats)
        for v, l, i in zip(ords, niv, idx):
            x[v["nome"]] = l[i]
        return dict(x, _arquetipo=arq["nome"], _id=gerar._id(arq["nome"], x))

    def _calcular(self, pontos):
        falta = {p["_id"]: p for p in pontos if p["_id"] not in self.cache}
        if falta:
            r = self.aval(list(falta.values()))
            for k in falta:
                self.cache[k] = r.get(k)
        return [self.cache[p["_id"]] for p in pontos]

    # ---------------------------------------------------------------- a monotonia
    def _medir_monotonia(self, arq, cats, ords, niv):
        n = [len(l) for l in niv]
        medidas = sorted({t["medida"] for t in self.rigidas})
        sinais = {m: [[] for _ in ords] for m in medidas}
        linhas = []
        for j, k in enumerate(n):
            if k < 2:
                continue
            for _ in range(self.m):
                base = [self.r.randrange(q) for q in n]
                trio = []
                n_l = max(2, int(self.forma["pontos_por_linha"]))
                for i in sorted({round(q * (k - 1) / (n_l - 1)) for q in range(n_l)}):
                    b = list(base)
                    b[j] = i
                    trio.append(self._ponto(arq, cats, ords, niv, b))
                linhas.append((j, trio))
        self._calcular([p for _, t in linhas for p in t])
        for j, trio in linhas:
            res = [self.cache[p["_id"]] for p in trio]
            for m in medidas:
                qs = [_quantidades(x, m) for x in res]
                if any(q is None for q in qs):
                    sinais[m][j].append("misto")
                    continue
                for q in range(3):
                    sinais[m][j].append(_sinal([x[q] for x in qs]) if len(qs) > 1 else "misto")
        out = {}
        for m in medidas:
            out[m] = [("0" if k < 2 else _combinar(s)) for s, k in zip(sinais[m], n)]
        return out

    # ---------------------------------------------------------------- as caixas
    def _canto(self, caixa, sinais_m, quer_max):
        idx = []
        for (lo, hi), s in zip(caixa, sinais_m):
            if s == "0":
                idx.append(lo)
            elif (s == "+") == quer_max:
                idx.append(hi)
            else:
                idx.append(lo)
        return idx

    def _caixas(self, arq, cats, ords, niv, sinais):
        pilha = [tuple((0, len(l) - 1) for l in niv)]
        while pilha:
            cx = pilha.pop()
            pontos_da_caixa = lambda: [self._ponto(arq, cats, ords, niv, list(i)) for i in itertools.product(*[range(a, b + 1) for a, b in cx])]
            caiu = None
            certas = 0
            for t in self.rigidas:
                s = sinais.get(t["medida"])
                if not s or "misto" in s:
                    continue
                maior = t["op"] in (">=", ">")
                if t["op"] == "==":
                    lo_p = self._ponto(arq, cats, ords, niv, self._canto(cx, s, False))
                    hi_p = self._ponto(arq, cats, ords, niv, self._canto(cx, s, True))
                    a, b = self._calcular([lo_p, hi_p])
                    qa, qb = _quantidades(a, t["medida"]), _quantidades(b, t["medida"])
                    if qa and qb and not (qa[1] <= t["valor"] <= qb[2]):
                        caiu = t
                        break
                    continue
                fav = self._ponto(arq, cats, ords, niv, self._canto(cx, s, maior))
                (rf,) = self._calcular([fav])
                q = _quantidades(rf, t["medida"])
                # passar exige o extremo desfavorável da faixa do lado certo do limite, e esse extremo é o melhor possível no canto
                # favorável: se o canto favorável não passa (falha ou fica incerto), nenhum ponto da caixa passa
                if q and julgar(t, rf["centro"], rf.get("faixa") or {}) != "passa":
                    caiu = t
                    self.melhores.append(fav)
                    break
                if not self.forma["certificar"]:
                    continue
                des = self._ponto(arq, cats, ords, niv, self._canto(cx, s, not maior))
                (rd,) = self._calcular([des])
                if _quantidades(rd, t["medida"]) and julgar(t, rd["centro"], rd.get("faixa") or {}) == "passa":
                    certas += 1
            if caiu is not None:
                for p in pontos_da_caixa():
                    self.podados.append({"id": p["_id"], "clausula": f"{caiu['medida']} {caiu['op']} {caiu['valor']}", "calculado": p["_id"] in self.cache})
                    self._podados_pontos[p["_id"]] = p
                continue
            unico = all(a == b for a, b in cx)
            if certas == len(self.rigidas) or unico:
                for p in pontos_da_caixa():
                    self.a_calcular[p["_id"]] = p
                continue
            if self.forma["divisao"] == "todas":
                partes = [[(a, b)] if a == b else [(a, (a + b) // 2), ((a + b) // 2 + 1, b)] for a, b in cx]
                pilha += [tuple(c) for c in itertools.product(*partes)]
            else:
                j = max(range(len(cx)), key=lambda i: cx[i][1] - cx[i][0])
                a, b = cx[j]
                meio = (a + b) // 2
                esq, dir_ = list(cx), list(cx)
                esq[j], dir_[j] = (a, meio), (meio + 1, b)
                pilha += [tuple(esq), tuple(dir_)]

    # ---------------------------------------------------------------- a auditoria da poda
    def _passa_tudo(self, res):
        if not res or res.get("erros") or res.get("fora_de_validade") or not isinstance(res.get("centro"), dict):
            return False
        return all(julgar(t, res["centro"], res.get("faixa") or {}) == "passa" for t in self.rigidas)

    def _auditar(self, arq, cats, ords, niv, ini):
        """A hipótese de monotonia testada no próprio problema: uma amostra dos pontos podados sem cálculo é calculada. Se algum passa,
        a hipótese caiu nesta região: a poda dela é desfeita, e a região inteira volta para o cálculo normal. Com k pontos auditados, se
        uma fração f dos podados passasse, a chance de perceber seria 1 - (1 - f)^k; uma ilha menor que isso pode escapar, e fica declarado."""
        chave = arq["nome"] + ("|" + "|".join(f"{k}={v}" for k, v in cats.items()) if cats else "")
        k = int(self.forma.get("auditoria") or 0)
        novos = self.podados[ini:]
        sem_calculo = [x["id"] for x in novos if not x["calculado"]]
        if not k or not sem_calculo:
            self.auditoria[chave] = {"auditados": 0, "podados_sem_calculo": len(sem_calculo)}
            return
        amostra = self.r.sample(sem_calculo, min(k, len(sem_calculo)))
        res = self._calcular([self._podados_pontos[i] for i in amostra])
        passaram = [i for i, x in zip(amostra, res) if self._passa_tudo(x)]
        info = {"auditados": len(amostra), "podados_sem_calculo": len(sem_calculo), "passaram": len(passaram),
                "deteccao_se_10_por_cento_passassem": round(1 - 0.9 ** len(amostra), 3)}
        if passaram:
            # a hipótese caiu aqui: desfaz a poda desta região e manda a região inteira para o cálculo normal
            ids = {x["id"] for x in novos}
            self.podados = self.podados[:ini]
            for i in ids:
                self.a_calcular[i] = self._podados_pontos[i]
            for idx in itertools.product(*[range(len(l)) for l in niv]):
                pnt = self._ponto(arq, cats, ords, niv, list(idx))
                self.a_calcular.setdefault(pnt["_id"], pnt)
            info.update(refutada=True, exemplo_que_passou=passaram[0])
        self.auditoria[chave] = info

    # ---------------------------------------------------------------- o todo
    def rodar(self):
        arqs = self.rep["arquetipos"]
        cota = max(1, self.orc // max(1, len(arqs)))
        for arq in arqs:
            ords, cs = [v for v in arq.get("variaveis", []) if v["tipo"] in ("real", "inteiro")], [v for v in arq.get("variaveis", []) if v["tipo"] == "categoria"]
            niv = [gerar.niveis(v) for v in ords]
            total = 1
            for l in niv + [gerar.niveis(v) for v in cs]:
                total *= len(l)
            if total > TETO_DA_GRADE or not ords or not self.rigidas:
                # grade grande demais, sem variável ordenada ou sem cláusula numérica: o cálculo não deduz nada, e a busca é a de sempre
                for p in gerar.grade_ou_amostra({"arquetipos": [arq]}, cota):
                    self.a_calcular[p["_id"]] = p
                if total > cota:
                    self.amostrou = getattr(self, "amostrou", []) + [arq["nome"]]
                continue
            # o cálculo percorre a grade inteira, mesmo quando ela passa da cota: ele só calcula os cantos que decidem
            antes = set(self.a_calcular)
            for combo in itertools.product(*[gerar.niveis(v) for v in cs]) if cs else [()]:
                cats = dict(zip([v["nome"] for v in cs], combo))
                sinais = self._medir_monotonia(arq, cats, ords, niv)
                self.monotonia[arq["nome"] + ("|" + "|".join(f"{k}={v}" for k, v in cats.items()) if cats else "")] = sinais
                ini = len(self.podados)
                self._caixas(arq, cats, ords, niv, sinais)
                self._auditar(arq, cats, ords, niv, ini)
            novos = [k for k in self.a_calcular if k not in antes]
            if len(novos) > cota and self.forma["amostrar_regiao"]:
                # a região que sobrou passa da cota: uma amostra dela, com semente fixa (os calculados no cálculo ficam todos)
                manter = set(self.r.sample(novos, cota)) | (set(novos) & set(self.cache))
                for k in novos:
                    if k not in manter:
                        del self.a_calcular[k]
                self.amostrou = getattr(self, "amostrou", []) + [arq["nome"]]
        melhores = {p["_id"]: p for p in self.melhores if p["_id"] not in self.a_calcular}
        return {"a_calcular": list(self.a_calcular.values()), "melhores_que_nao_passam": list(melhores.values()),
                "podados": self.podados, "calculados_no_calculo": len(self.cache),
                "monotonia": self.monotonia, "hipotese": HIPOTESE, "amostrou_a_regiao": getattr(self, "amostrou", []),
                "auditoria": self.auditoria, "forma": dict(self.forma)}
