"""O adaptador que o compilador monta sozinho, a partir do modelo que a IA propôs: nenhuma linha dele sabe do domínio.

Ele cumpre o contrato da bancada (bancada/nucleo/adaptador.py), e por isso a 𝔉, o ledger, a transferência, a seleção e o manifesto
são os mesmos dos quatro adaptadores escritos à mão.
- formulacoes: os candidatos da representação (compilador/gerar.py);
- verificar: o modelo calculado em lote na caixa, com a incerteza de Π; o modelo alternativo, quando existe, cruza as saídas; o
  veredito usa as cláusulas rígidas de D sobre as saídas;
- evidências: a saída calculada de cada candidato, com as hipóteses dos números de Π de entrada e do hash do modelo (que entra em Π como
  o número "modelo_de_calculo", do tipo escolha, e por isso um modelo novo derruba as evidências do velho);
- nenhuma restrição de poda aqui: a poda por monotonia é feita antes, pelo cálculo (compilador/calcular.py), com a hipótese declarada.
"""
from bancada.nucleo.adaptador import Adaptador
from bancada.nucleo.ledger import Ledger

from . import avaliar


class AdaptadorCompilado(Adaptador):
    nome = "compilado"

    def __init__(self, modelo, candidatos, p_base, intervalos, entradas_usadas, alternativo=None, tolerancias=None, usar_ledger=True,
                 precalculados=None):
        self.modelo = modelo
        self.cand = candidatos
        self.p_base, self.intervalos = p_base, intervalos
        self.entradas = entradas_usadas
        self.alt = alternativo
        self.tol = tolerancias or {}
        self.usar_ledger = usar_ledger
        # as saídas que o cálculo antes da busca já calculou (compilador/calcular.py): calculadas uma vez só
        self.pre = dict(precalculados or {})
        self._calc, self._alt = {}, {}
        self.nome = f"compilado:{modelo['id']}"

    def formulacoes(self, D, Pi):
        for c in self.cand:
            yield dict(c, id=c["_id"])

    def _garantir(self, contexto):
        """Calcula em lote tudo o que falta, pelo modelo e pelo alternativo; reaproveita as saídas que o ledger ainda dá por válidas."""
        if self._calc:
            return
        validas = {}
        if self.usar_ledger:
            for e in contexto.get("evidencias", []):
                m = e.get("medida") or {}
                if m.get("tipo") == "saida_compilada" and m.get("modelo") == self.modelo["hash"]:
                    validas[m["chave"]] = e
        falta = [c for c in self.cand if c["_id"] not in validas and c["_id"] not in self.pre]
        self.reusadas = validas
        r = avaliar.propagar(self.modelo["codigo"], falta, self.p_base, self.intervalos) if falta else {"avaliados": []}
        if "erro" in r:
            raise RuntimeError("o modelo não roda: " + r["erro"])
        self._calc = {x["id"]: x for x in r["avaliados"]}
        self._calc.update({k: v for k, v in self.pre.items() if k not in validas})
        # as saídas reusadas também ficam à mão, para a sensibilidade e a escolha (a conta do custo continua separando as duas)
        for k, e in validas.items():
            self._calc.setdefault(k, e["medida"]["valores"])
        self.calculados = len(falta) + sum(1 for k in self.pre if k not in validas)
        if self.alt:
            ra = avaliar.propagar(self.alt["codigo"], self.cand, self.p_base, {})
            self._alt = {x["id"]: x for x in ra.get("avaliados", [])}

    def construir(self, f, D, Pi, contexto):
        return {"formulacao": f}

    def verificar(self, corpo, f, D, Pi, contexto=None):
        contexto = contexto or {}
        self._garantir(contexto)
        novas, reusadas, custo = [], [], {"modelo_calculado": 0, "medidas_reusadas": 0}
        if f["_id"] in getattr(self, "reusadas", {}):
            e = self.reusadas[f["_id"]]
            x = e["medida"]["valores"]
            reusadas.append(e["seq"])
            custo["medidas_reusadas"] = 1
        else:
            x = self._calc[f["_id"]]
            custo["modelo_calculado"] = 1
            novas.append({"medida": {"tipo": "saida_compilada", "chave": f["_id"], "modelo": self.modelo["hash"], "valores": x},
                          "hipoteses": Ledger.hipoteses(D, (), Pi, list(self.entradas) + ["modelo_de_calculo"])})
        medidas = dict(x["centro"] or {})
        for k, v in (x.get("faixa") or {}).items():
            medidas[k + "_intervalo"] = v
        base = {"medidas": medidas, "custo": custo, "evidencias": novas, "medidas_reusadas_de": reusadas,
                "escopo": f"modelo {self.modelo['id']} ({self.modelo['hash'][:10]}), Π nos cantos do intervalo"}
        if x["erros"] or not isinstance(x["centro"], dict):
            return dict(base, aprovado=False, nulo={"classe": "modelo_incerto", "clausula": None, "condicao": "o modelo não calculou",
                                                     "medida": {"erros": x["erros"]}, "motivo": "o modelo falhou neste candidato: " + "; ".join(x["erros"])[:300]})
        if x.get("fora_de_validade"):
            return dict(base, aprovado=False, nulo={"classe": "modelo_incerto", "clausula": None, "condicao": "fora do domínio de validade",
                                                     "medida": {}, "motivo": "o próprio modelo declarou o candidato fora do domínio de validade"})
        julg = {}
        falha = incerto = None
        for c in D.rigidas():
            j = avaliar.julgar(c["teste"], x["centro"], x.get("faixa") or {})
            julg[c["id"]] = j
            if j == "falha" and falha is None:
                falha = c
            if j in ("incerto", "sem_medida") and incerto is None:
                incerto = (c, j)
        # o modelo alternativo: uma discordância nas saídas que D julga torna o veredito incerto
        disc = []
        if self._alt:
            y = self._alt.get(f["_id"])
            saidas = [c["teste"]["medida"] for c in D.rigidas()]
            disc = avaliar.cruzar([x], [y] if y else [], saidas, self.tol) if y else [{"id": f["_id"], "saida": "*", "motivo": "o alternativo não calculou"}]
        base["julgamento"] = julg
        base["discordancias"] = disc
        if falha is not None and not disc:
            return dict(base, aprovado=False, nulo={"classe": "candidato_falho", "clausula": falha["id"],
                                                     "condicao": f"{falha['teste']['medida']} {falha['teste']['op']} {falha['teste']['valor']}",
                                                     "medida": {falha["teste"]["medida"]: x["centro"].get(falha["teste"]["medida"])}, "motivo": "não cumpre D"})
        if disc:
            return dict(base, aprovado=False, nulo={"classe": "modelo_incerto", "clausula": None, "condicao": "os modelos discordam",
                                                     "medida": {"discordancias": disc[:4]}, "motivo": "o modelo e o alternativo discordam além da tolerância"})
        if incerto is not None:
            c, j = incerto
            return dict(base, aprovado=False, nulo={"classe": "modelo_incerto", "clausula": c["id"], "condicao": j,
                                                     "medida": {c["teste"]["medida"]: x["centro"].get(c["teste"]["medida"])},
                                                     "motivo": "o modelo não calcula a medida que D julga" if j == "sem_medida" else "o intervalo atravessa o limite"})
        return dict(base, aprovado=True, nulo=None)

    def medidas_de_objetivo(self, ver):
        return ver["medidas"]
