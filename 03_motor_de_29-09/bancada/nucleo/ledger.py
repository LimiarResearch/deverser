"""O ledger N: só de acréscimo, com a regra de transferência.

Entradas: versões de D e de Π, formulações, veredictos (com o nulo classificado) e evidências. Cada evidência leva as hipóteses de que
depende:
- d: as cláusulas (id -> hash do que a cláusula exige);
- pi: os números (nome -> o valor usado e o intervalo dentro do qual a evidência continua valendo);
- escopo: itens do escopo de D (a carga, o período);
- rigidas (opcional): o conjunto inteiro das cláusulas rígidas, quando uma cláusula nova pode mudar o sentido das outras.

A regra de transferência: quando D ou Π mudam, uma evidência só volta a valer se todas as hipóteses dela continuam de pé. Uma
cláusula que sumiu ou mudou, um número ausente ou fora do intervalo, derrubam a evidência, e a queda fica registrada. Nada é
reaproveitado em silêncio.
"""
import json
import os

from bancada.nucleo.modelo import hash_clausula

CLASSES_DE_NULO = ("d_contraditorio", "meio_insuficiente", "orcamento_insuficiente", "modelo_incerto", "candidato_falho",
                   "busca_interrompida")


class Ledger:
    def __init__(self, caminho=None):
        self.caminho = caminho
        self.entradas = []
        if caminho and os.path.exists(caminho):
            with open(caminho, encoding="utf-8") as f:
                self.entradas = [json.loads(l) for l in f if l.strip()]

    def acrescentar(self, tipo, corpo):
        e = {"seq": len(self.entradas) + 1, "tipo": tipo, **corpo}
        self.entradas.append(e)
        if self.caminho:
            with open(self.caminho, "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(e, ensure_ascii=False, default=str) + "\n")
        return e

    def evidencias(self):
        return [e for e in self.entradas if e["tipo"] == "evidencia"]

    @staticmethod
    def hipoteses(D, clausulas=(), Pi=None, numeros=(), escopo=(), rigidas_exatas=False):
        """As hipóteses de uma evidência: as cláusulas, os números e os itens do escopo de D (por exemplo, a carga) de que ela depende,
        no estado atual de D e Π. Com rigidas_exatas, a evidência depende do conjunto inteiro das cláusulas rígidas: uma cláusula que
        entra ou sai derruba a evidência, mesmo que as listadas não mudem (uma cláusula nova pode mudar o sentido das outras)."""
        d = {c["id"]: hash_clausula(c) for c in D.dados["clausulas"] if c["id"] in set(clausulas)}
        esc = {k: D.dados.get("escopo", {}).get(k) for k in escopo}
        if rigidas_exatas:
            return {"d": d, "pi": Ledger._pi(Pi, numeros), "escopo": esc, "rigidas": sorted([c["id"], hash_clausula(c)] for c in D.rigidas())}
        return {"d": d, "pi": Ledger._pi(Pi, numeros), "escopo": esc}

    @staticmethod
    def estado(nome, Pi, tolerancia_rel):
        """Uma hipótese de estado declarada pelo verificador: a evidência vale enquanto o valor central do número ficar dentro de
        ±tolerancia_rel do valor medido agora (uma medida ruidosa do estado de uma máquina, por exemplo). A tolerância é escolha declarada
        do verificador, e não é tirada da amostra."""
        x = Pi.numero(nome) if Pi else None
        v = (x or {}).get("valor")
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return (nome, "igual")
        return (nome, "estado", [v * (1 - tolerancia_rel), v * (1 + tolerancia_rel)])

    @staticmethod
    def _pi(Pi, numeros):
        """numeros: nomes, ou (nome, modo) ou (nome, modo, validade). O modo diz como a evidência usou o número:
        - "igual" (o padrão): a evidência só continua valendo com o mesmo número: a mesma unidade, o mesmo tipo, a mesma grandeza, o
          mesmo método, a mesma fonte, o mesmo valor e o mesmo intervalo de incerteza. Qualquer diferença a derruba. É o único modo que
          garante veredito igual ao de uma corrida sem reuso quando o verificador calcula sobre o intervalo inteiro;
        - "estado": a unidade, o tipo, a grandeza, o método e a fonte iguais, e o valor central dentro da validade que o verificador
          DECLAROU (Ledger.estado). É para medidas ruidosas de estado, e não é exato: uma medida nova daria outro valor;
        - "declarado": a unidade, o tipo, a grandeza, o método e a fonte iguais, e o intervalo atual inteiro dentro da validade que o
          verificador declarou, quando ele certifica que a evidência é a mesma para qualquer valor nessa região.
        (O modo antigo "centro_no_intervalo" é lido como "estado" com a validade igual ao intervalo gravado.)"""
        pi = {}
        for item in numeros:
            if isinstance(item, str):
                n, modo, validade = item, "igual", None
            else:
                n, modo = item[0], item[1]
                validade = item[2] if len(item) > 2 else None
            x = Pi.numero(n) if Pi else None
            if x is not None:
                lo, hi = (x.get("incerteza") or [x["valor"], x["valor"]]) if x["tipo"] != "ausente" else (None, None)
                pi[n] = {"valor": x["valor"], "tipo": x["tipo"], "intervalo": [lo, hi], "unidade": x.get("unidade"), "grandeza": x.get("grandeza"),
                         "metodo": x.get("metodo"), "fonte": x.get("fonte"), "modo": modo, "validade": validade}
            else:
                pi[n] = {"valor": None, "tipo": "ausente", "intervalo": [None, None], "unidade": None, "grandeza": None, "metodo": None,
                         "fonte": None, "modo": modo, "validade": validade}
        return pi

    @staticmethod
    def vale(e, D, Pi):
        """A evidência continua valendo em (D, Π)? Devolve (sim, motivo)."""
        h = e.get("hipoteses", {})
        atuais = {c["id"]: c for c in D.dados["clausulas"]}
        for cid, hc in h.get("d", {}).items():
            c = atuais.get(cid)
            if c is None:
                return False, f"a cláusula {cid} saiu de D"
            if hash_clausula(c) != hc:
                return False, f"a cláusula {cid} mudou"
        if "rigidas" in h and sorted([c["id"], hash_clausula(c)] for c in D.rigidas()) != h["rigidas"]:
            antes, agora = {x[0] for x in h["rigidas"]}, {c["id"] for c in D.rigidas()}
            return False, f"o conjunto de cláusulas rígidas mudou (entrou {sorted(agora - antes)}, saiu {sorted(antes - agora)})"
        for k, v in h.get("escopo", {}).items():
            if D.dados.get("escopo", {}).get(k) != v:
                return False, f"o escopo {k} mudou de {v} para {D.dados.get('escopo', {}).get(k)}"
        for n, info in h.get("pi", {}).items():
            x = Pi.numero(n)
            if info["tipo"] == "ausente":
                if x is not None and x["tipo"] != "ausente":
                    return False, f"{n} deixou de estar ausente"
                continue
            if x is None or x["tipo"] == "ausente":
                return False, f"{n} ficou ausente"
            # a unidade, o tipo, a grandeza, o método e a fonte têm de ser os mesmos: o mesmo valor em outra unidade, com outro
            # estatuto, medindo outra coisa, por outro método ou de outra fonte é outro número
            if "unidade" not in info:
                return False, f"{n}: a evidência não registrou a unidade (regra antiga), e não pode ser conferida"
            if x.get("unidade") != info["unidade"]:
                return False, f"{n} mudou de unidade ({info['unidade']} para {x.get('unidade')})"
            if x["tipo"] != info["tipo"]:
                return False, f"{n} mudou de tipo ({info['tipo']} para {x['tipo']})"
            if x.get("grandeza") != info.get("grandeza"):
                return False, f"{n} passou a descrever outra grandeza"
            if "metodo" in info and x.get("metodo") != info.get("metodo"):
                return False, f"{n} mudou de método"
            if "fonte" in info and x.get("fonte") != info.get("fonte"):
                return False, f"{n} mudou de fonte"
            modo = info.get("modo", "contido")
            v = x["valor"]
            lo, hi = info["intervalo"]
            numerico = isinstance(v, (int, float)) and not isinstance(v, bool)
            nlo, nhi = (x.get("incerteza") or [v, v]) if numerico else (None, None)
            if modo in ("estado", "centro_no_intervalo"):
                vlo, vhi = info.get("validade") or [lo, hi]
                if not (numerico and vlo <= v <= vhi):
                    return False, f"{n} = {v} saiu da validade declarada [{vlo}, {vhi}]"
            elif modo == "declarado":
                vlo, vhi = info["validade"]
                if not (numerico and vlo <= nlo and nhi <= vhi):
                    return False, f"{n}: o intervalo [{nlo}, {nhi}] não cabe na validade declarada [{vlo}, {vhi}]"
            elif modo == "contido":
                # evidências gravadas antes da emenda de 28/09 (o intervalo novo dentro do antigo)
                if numerico and isinstance(lo, (int, float)):
                    if not (lo <= nlo and nhi <= hi):
                        return False, f"{n}: o intervalo novo [{nlo}, {nhi}] não cabe no intervalo [{lo}, {hi}] em que a evidência foi tirada"
                elif v != info["valor"]:
                    return False, f"{n} mudou de {info['valor']} para {v}"
            else:
                # "igual": o mesmo valor e o mesmo intervalo
                if v != info["valor"]:
                    return False, f"{n} mudou de valor ({info['valor']} para {v})"
                if numerico and [nlo, nhi] != [lo, hi]:
                    return False, f"{n}: o intervalo mudou de [{lo}, {hi}] para [{nlo}, {nhi}]"
        return True, "ok"

    def transferir(self, D, Pi):
        """As evidências que valem em (D, Π) e as que caíram, com o motivo."""
        validas, caidas = [], []
        for e in self.evidencias():
            ok, motivo = self.vale(e, D, Pi)
            (validas if ok else caidas).append(e if ok else dict(e, caiu_porque=motivo))
        return validas, caidas
