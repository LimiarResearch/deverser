"""D e Π: a vontade do criador em cláusulas, e os números do meio com procedência. Os dois são versionados e imutáveis: mudar cria a
versão seguinte, ligada à anterior pelo hash, e a anterior continua existindo.

Cláusula:
- tipo: "rigida" (tem de valer), "objetivo" (melhor quanto mais, num sentido) ou "preferencia" (o criador escolhe entre válidos);
- teste: o que o adaptador sabe medir, por exemplo {"medida": "p95_us", "op": "<=", "valor": 3.0} ou {"medida": "massa_kg", "sentido": "min"};
- origem: "criador", "ia" ou "derivada"; uma cláusula da IA só entra na verificação depois de confirmada pelo criador.

Número de Π:
- tipo: "medido", "calibrado", "aproximacao", "escolha", "hipotese" ou "ausente";
- valor, unidade, incerteza (intervalo), método, fonte, licença, data, e a que máquina ou lugar ele vale.
"""
import copy
import hashlib
import json

TIPOS_DE_CLAUSULA = ("rigida", "objetivo", "preferencia")
TIPOS_DE_NUMERO = ("medido", "calibrado", "aproximacao", "escolha", "hipotese", "ausente")


def _canon(x):
    """A forma canônica para o hash: um número real inteiro vira inteiro (2500 e 2500.0 são a mesma exigência)."""
    if isinstance(x, float) and x.is_integer():
        return int(x)
    if isinstance(x, dict):
        return {k: _canon(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_canon(v) for v in x]
    return x


def _hash(obj):
    return hashlib.sha256(json.dumps(_canon(obj), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def hash_clausula(c):
    """O hash do que a cláusula exige (tipo e teste). O enunciado e a origem não mudam o que ela exige."""
    return _hash({"id": c["id"], "tipo": c["tipo"], "teste": c["teste"]})


class D:
    def __init__(self, dados):
        self.dados = copy.deepcopy(dados)
        for c in self.dados["clausulas"]:
            assert c["tipo"] in TIPOS_DE_CLAUSULA, c
            c.setdefault("origem", "criador")
            c.setdefault("confirmada", c["origem"] == "criador")
        self.dados.setdefault("versao", 1)
        self.dados.setdefault("pai", None)
        self.dados.setdefault("pendencias", [])

    @property
    def versao(self):
        return self.dados["versao"]

    def hash(self):
        return _hash(self.dados)

    def clausulas(self, tipo=None, confirmadas=True):
        return [c for c in self.dados["clausulas"] if (tipo is None or c["tipo"] == tipo) and (c["confirmada"] or not confirmadas)]

    def rigidas(self):
        return self.clausulas("rigida")

    def objetivos(self):
        return self.clausulas("objetivo")

    def nao_confirmadas(self):
        return [c for c in self.dados["clausulas"] if not c["confirmada"]]

    def incompleto(self):
        """D está incompleto quando há pendência aberta ou cláusula sem confirmação; continua explicitamente incompleto."""
        return bool(self.dados["pendencias"] or self.nao_confirmadas())

    def nova_versao(self, mudar=None, acrescentar=(), retirar=(), motivo="", escopo=None):
        """A versão seguinte: as cláusulas mudadas, acrescentadas ou retiradas (e o escopo, quando muda), ligada à anterior pelo hash."""
        novo = copy.deepcopy(self.dados)
        if escopo is not None:
            novo["escopo"] = dict(novo.get("escopo", {}), **copy.deepcopy(escopo))
        novo["clausulas"] = [c for c in novo["clausulas"] if c["id"] not in set(retirar)]
        for c in novo["clausulas"]:
            if mudar and c["id"] in mudar:
                c.update(copy.deepcopy(mudar[c["id"]]))
        novo["clausulas"] += [copy.deepcopy(c) for c in acrescentar]
        novo["versao"] = self.versao + 1
        novo["pai"] = self.hash()
        novo["motivo_da_versao"] = motivo
        return D(novo)


class Pi:
    def __init__(self, dados):
        self.dados = copy.deepcopy(dados)
        for n, x in self.dados["numeros"].items():
            assert x["tipo"] in TIPOS_DE_NUMERO, (n, x)
        self.dados.setdefault("versao", 1)
        self.dados.setdefault("pai", None)
        self.dados.setdefault("catalogo", [])

    @property
    def versao(self):
        return self.dados["versao"]

    def hash(self):
        return _hash(self.dados)

    def numero(self, nome):
        return self.dados["numeros"].get(nome)

    def valor(self, nome, padrao=None):
        x = self.numero(nome)
        return padrao if x is None or x["tipo"] == "ausente" else x["valor"]

    def nova_versao(self, numeros=None, catalogo=None, motivo=""):
        novo = copy.deepcopy(self.dados)
        for n, x in (numeros or {}).items():
            novo["numeros"][n] = copy.deepcopy(x)
        if catalogo is not None:
            novo["catalogo"] = copy.deepcopy(catalogo)
        novo["versao"] = self.versao + 1
        novo["pai"] = self.hash()
        novo["motivo_da_versao"] = motivo
        return Pi(novo)

    def procedencia(self):
        """Quantos números de cada tipo: o que foi medido, estimado, escolhido e o que falta."""
        out = {}
        for x in self.dados["numeros"].values():
            out[x["tipo"]] = out.get(x["tipo"], 0) + 1
        return out
