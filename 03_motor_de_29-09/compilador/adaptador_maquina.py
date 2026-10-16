"""O adaptador que o compilador monta para "algo que roda numa máquina": cada candidato é o código de um arquétipo que a IA escreveu,
com os parâmetros da representação, e é medido no alvo pelo executor genérico (compilador/executor_generico.py).

As medidas: o tempo de execução (mediana e p95, com o intervalo entre rodadas), o pico de memória, as métricas que a IA declarou sobre
a saída, e os oráculos: o da própria IA e, quando existe, o do avaliador independente. Um oráculo que falha reprova o candidato; os
dois discordando tornam o veredito incerto. Evidência: a medida no alvo, com as hipóteses do estado da máquina (a alimentação e os
microbenchmarks no modo de estado), da versão do Python e dos hashes do código, da carga e dos oráculos.
"""
import base64
import gzip
import hashlib
import json
import os
import zlib
import tempfile
from concurrent.futures import ThreadPoolExecutor

from bancada.nucleo.adaptador import Adaptador
from bancada.nucleo.ledger import Ledger

# a validade declarada de uma medida de estado da máquina: o microbenchmark do perfil a ±15% do valor com que a medida foi tirada
# (escolha declarada do verificador, emenda de 28/09; antes, a validade era o intervalo de 7 repetições, tirado da amostra)
TOLERANCIA_DE_ESTADO = 0.15

from . import avaliar

EXECUTOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "executor_generico.py")


def _h(*partes):
    return hashlib.sha256("\0".join(partes).encode()).hexdigest()


class AdaptadorMaquina(Adaptador):
    nome = "compilado_maquina"

    def __init__(self, modelo, candidatos, alvo, oraculo_alternativo=None, rodadas=3, repeticoes=5, usar_ledger=True, paralelo=1, pasta_fotos=None):
        self.m, self.cand, self.alvo = modelo, candidatos, alvo
        # quantos candidatos o alvo mede ao mesmo tempo, um por núcleo; o tempo de CPU do processo é medido junto, porque a disputa
        # entre eles pesa menos nele do que no relógio
        self.paralelo = max(1, int(paralelo))
        self.pasta_fotos = pasta_fotos
        self.fotos = {}
        # o cache por código atômico (a chave do trabalho): a mesma medida nunca roda duas vezes na mesma criação, nem na concorrência
        self.cache = {}
        self._pre = None
        self.oalt = oraculo_alternativo
        self.rodadas, self.rep = rodadas, repeticoes
        self.usar_ledger = usar_ledger
        self.arqs = {a["nome"]: a for a in modelo["representacao"]["arquetipos"]}
        if modelo["representacao"].get("composicao"):
            self.arqs["composicao"] = dict(modelo["representacao"]["composicao"], nome="composicao")
        self.nome = f"compilado_maquina:{modelo['id']}:{alvo.id}"

    def formulacoes(self, D, Pi):
        for c in self.cand:
            yield dict(c, id=c["_id"])

    def construir(self, f, D, Pi, contexto):
        return {"formulacao": f}

    def _trabalho(self, f):
        a = self.arqs[f["_arquetipo"]]
        params = {k: v for k, v in f.items() if not k.startswith("_") and k != "id"}
        oraculos = [self.m["oraculo"]]
        return {"carga": self.m["carga"], "candidato": a["codigo"], "metricas": self.m.get("metricas"), "oraculos": oraculos, "foto": self.m.get("foto"),
                "params": params, "semente": self.m.get("semente", 1), "repeticoes": self.rep, "rodadas": self.rodadas,
                "tempo_limite_s": self.m.get("tempo_limite_s", 300)}

    @staticmethod
    def _chave(t):
        # a foto só entra na chave quando existe, para as medidas de antes da foto continuarem reutilizáveis
        return _h(t["candidato"], t["carga"], json.dumps(t["params"], sort_keys=True), *t["oraculos"], t.get("metricas") or "",
                  *([t["foto"]] if t.get("foto") else []))

    @staticmethod
    def _chave_da_foto(t):
        """A foto depende do candidato, da carga, dos parâmetros, do código da foto e dos oráculos, e não das métricas nem de D."""
        return _h("foto", t["candidato"], t["carga"], json.dumps(t["params"], sort_keys=True), t.get("foto") or "", *t["oraculos"])

    def _guardar_foto(self, r, fid):
        """Tira o blob da foto do resultado e o grava em pasta_fotos/<sha>.json.gz; o resultado fica só com o hash."""
        if "foto_b64" not in r:
            return r
        r = dict(r)
        b = zlib.decompress(base64.b64decode(r.pop("foto_b64")))
        sha = r.pop("foto_sha256")
        if hashlib.sha256(b).hexdigest() != sha:
            raise RuntimeError("a foto chegou corrompida do alvo")
        if self.pasta_fotos:
            os.makedirs(self.pasta_fotos, exist_ok=True)
            with gzip.open(os.path.join(self.pasta_fotos, sha + ".json.gz"), "wb") as f:
                f.write(b)
        self.fotos[fid] = sha
        r["foto"] = sha
        return r

    def ler_foto(self, sha):
        with gzip.open(os.path.join(self.pasta_fotos, sha + ".json.gz"), "rb") as f:
            return json.loads(f.read())

    def _executar(self, t, timeout):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8", newline="\n") as fh:
            json.dump(t, fh)
            caminho = fh.name
        destino = self.alvo.enviar(caminho) if self.alvo.tipo != "local" else caminho
        try:
            return self.alvo.executar(EXECUTOR, "medir", destino, timeout=timeout)
        finally:
            os.unlink(caminho)

    def medir_lote(self, cands):
        """A concorrência: mede em paralelo os candidatos do lote (pelo cache quando já medidos) e devolve {id: medidas}, sem veredito."""
        self._pre, antes = None, self.cand
        self.cand = cands
        self._garantir({"evidencias": []})
        self.cand = antes
        out = {}
        for c in cands:
            t = self._trabalho(c)
            r = (self._pre.get(self._chave(t)) or (None, None))[0]
            if r is None or "erro" in r:
                out[c["_id"]] = None
                continue
            med = {k: v for k, v in r.items() if k not in ("metricas", "oraculos", "python", "numpy", "foto_b64", "foto_sha256")}
            med.update(r.get("metricas") or {})
            med["correto"] = 1 if r.get("oraculos_ok") else 0
            out[c["_id"]] = med
        self._pre = None
        return out

    def _garantir(self, contexto):
        """Mede em paralelo, no alvo, todos os candidatos que não têm evidência reutilizável (e o oráculo alternativo de cada um)."""
        if self._pre is not None:
            return
        self._pre = {}
        if self.paralelo <= 1:
            return
        tem = set()
        if self.usar_ledger:
            for ev in (contexto or {}).get("evidencias", []):
                mm = ev.get("medida") or {}
                if mm.get("tipo") == "medida_no_alvo" and mm.get("alvo") == self.alvo.id:
                    tem.add(mm.get("chave"))
        pend = {}
        for c in self.cand:
            t = self._trabalho(c)
            k = self._chave(t)
            if k not in tem:
                pend[k] = t
        if not pend:
            return
        if self.alvo.tipo != "local":
            self.alvo._garantir(EXECUTOR)

        def um(item):
            k, t = item
            r, ralt = self.cache.get(k, (None, None))
            if r is None:
                r = self._executar(t, int(t["tempo_limite_s"]) * (self.rodadas + 1))
            if self.oalt and "erro" not in r and ralt is None:
                ralt = self._executar(dict(t, oraculos=[self.oalt], rodadas=1, repeticoes=1), int(t["tempo_limite_s"]) * 2)
            self.cache[k] = (r, ralt)
            return k, (r, ralt)
        with ThreadPoolExecutor(max_workers=self.paralelo) as ex:
            for k, v in ex.map(um, list(pend.items())):
                self._pre[k] = v

    def verificar(self, corpo, f, D, Pi, contexto=None):
        self._garantir(contexto)
        t = self._trabalho(f)
        chave = self._chave(t)
        novas, reusadas, custo = [], [], {"medicoes_no_alvo": 0, "medidas_reusadas": 0}
        e = None
        if self.usar_ledger:
            for ev in reversed((contexto or {}).get("evidencias", [])):
                m = ev.get("medida") or {}
                if m.get("tipo") == "medida_no_alvo" and m.get("chave") == chave and m.get("alvo") == self.alvo.id:
                    e = ev
                    break
        ef = None
        if not e and self.usar_ledger and t.get("foto") and self.m.get("metricas_da_foto") and self.pasta_fotos:
            cf = self._chave_da_foto(t)
            for ev in reversed((contexto or {}).get("evidencias", [])):
                mm = ev.get("medida") or {}
                if mm.get("tipo") == "foto_no_alvo" and mm.get("chave_da_foto") == cf and mm.get("alvo") == self.alvo.id:
                    ef = ev
                    break
        if e:
            r = e["medida"]["valores"]
            reusadas.append(e["seq"])
            custo["medidas_reusadas"] = 1
            if r.get("foto"):
                self.fotos[f["_id"]] = r["foto"]
        elif ef:
            from .executor_generico import _carregar
            r = dict(ef["medida"]["valores"])
            r["metricas"] = _carregar(self.m["metricas_da_foto"], "metricas_da_foto")(self.ler_foto(r["foto"]))
            reusadas.append(ef["seq"])
            custo["fotos_reusadas"] = 1
            self.fotos[f["_id"]] = r["foto"]
        else:
            pre = self._pre.get(chave)
            if pre:
                r = pre[0]
            else:
                if self.alvo.tipo != "local":
                    self.alvo._garantir(EXECUTOR)
                r = self._executar(t, int(t["tempo_limite_s"]) * (self.rodadas + 1))
            custo["medicoes_no_alvo"] = 1
            r = self._guardar_foto(r, f["_id"])
            if "erro" not in r and r.get("foto"):
                novas.append({"medida": {"tipo": "foto_no_alvo", "chave_da_foto": self._chave_da_foto(t), "alvo": self.alvo.id,
                                         "valores": {k: v for k, v in r.items() if k != "metricas"}},
                              "hipoteses": Ledger.hipoteses(D, (), Pi, ["maquina_id", "python_versao", "numpy_versao", "alimentacao",
                                                                        Ledger.estado("ns_por_hash_splitmix", Pi, TOLERANCIA_DE_ESTADO),
                                                                        Ledger.estado("ns_por_insercao_em_conjunto", Pi, TOLERANCIA_DE_ESTADO)])})
            if "erro" not in r:
                hip = Ledger.hipoteses(D, (), Pi, ["maquina_id", "python_versao", "numpy_versao", "alimentacao", Ledger.estado("ns_por_hash_splitmix", Pi, TOLERANCIA_DE_ESTADO),
                                                   Ledger.estado("ns_por_insercao_em_conjunto", Pi, TOLERANCIA_DE_ESTADO), "modelo_de_calculo"])
                novas.append({"medida": {"tipo": "medida_no_alvo", "chave": chave, "alvo": self.alvo.id, "valores": r}, "hipoteses": hip})
        # o oráculo do avaliador independente: um trabalho curto e à parte (uma rodada, uma repetição), com a evidência dele
        if self.oalt and "erro" not in r:
            chave_alt = _h(chave, self.oalt)
            ea = None
            if self.usar_ledger:
                for ev in reversed((contexto or {}).get("evidencias", [])):
                    mm = ev.get("medida") or {}
                    if mm.get("tipo") == "oraculo_alternativo" and mm.get("chave") == chave_alt and mm.get("alvo") == self.alvo.id:
                        ea = ev
                        break
            if ea:
                ralt = ea["medida"]["valores"]
                reusadas.append(ea["seq"])
            else:
                pre = self._pre.get(chave)
                ralt = pre[1] if pre and pre[1] is not None else self._executar(dict(t, oraculos=[self.oalt], rodadas=1, repeticoes=1), int(t["tempo_limite_s"]) * 2)
                custo["medicoes_no_alvo"] += 1
                if "erro" not in ralt:
                    novas.append({"medida": {"tipo": "oraculo_alternativo", "chave": chave_alt, "alvo": self.alvo.id, "valores": {"oraculos": ralt["oraculos"]}},
                                  "hipoteses": Ledger.hipoteses(D, (), Pi, ["maquina_id", "python_versao", "modelo_de_calculo"])})
            r = dict(r, oraculos=list(r["oraculos"]) + list(ralt.get("oraculos", [{"ok": False, "detalhe": "o oráculo alternativo não rodou"}])))
            r["oraculos_ok"] = all(o["ok"] for o in r["oraculos"])
        base = {"custo": custo, "evidencias": novas, "medidas_reusadas_de": reusadas, "escopo": f"medido em {self.alvo.id}"}
        if "erro" in r:
            return dict(base, aprovado=False, medidas={}, nulo={"classe": "candidato_falho", "clausula": None, "condicao": "não roda",
                                                               "medida": {"erro": r["erro"][-300:]}, "motivo": "o candidato quebrou no alvo"})
        med = {k: v for k, v in r.items() if k not in ("metricas", "oraculos", "python", "numpy")}
        med.update(r.get("metricas") or {})
        med["correto"] = 1 if r["oraculos_ok"] else 0
        base["medidas"] = med
        oks = [o["ok"] for o in r["oraculos"]]
        if len(oks) > 1 and len(set(oks)) > 1:
            return dict(base, aprovado=False, nulo={"classe": "modelo_incerto", "clausula": None, "condicao": "os oráculos discordam",
                                                     "medida": {"oraculos": r["oraculos"]}, "motivo": "o oráculo da IA e o do avaliador discordam"})
        if not r["oraculos_ok"]:
            return dict(base, aprovado=False, nulo={"classe": "candidato_falho", "clausula": None, "condicao": "oráculo",
                                                     "medida": {"oraculos": r["oraculos"]}, "motivo": "a saída não passa no oráculo"})
        julg, falha, incerto = {}, None, None
        for c in D.rigidas():
            j = avaliar.julgar(c["teste"], med, {k[:-10]: v for k, v in med.items() if k.endswith("_intervalo")})
            julg[c["id"]] = j
            if j == "falha" and falha is None:
                falha = c
            elif j in ("incerto", "sem_medida") and incerto is None:
                incerto = (c, j)
        base["julgamento"] = julg
        if falha:
            return dict(base, aprovado=False, nulo={"classe": "candidato_falho", "clausula": falha["id"], "condicao": str(falha["teste"]),
                                                     "medida": {falha["teste"]["medida"]: med.get(falha["teste"]["medida"])}, "motivo": "não cumpre D"})
        if incerto:
            c, j = incerto
            return dict(base, aprovado=False, nulo={"classe": "modelo_incerto", "clausula": c["id"], "condicao": j,
                                                     "medida": {c["teste"]["medida"]: med.get(c["teste"]["medida"])},
                                                     "motivo": "a medida que D julga não foi produzida" if j == "sem_medida" else "o intervalo entre rodadas atravessa o limite"})
        return dict(base, aprovado=True, nulo=None)

    def medidas_de_objetivo(self, ver):
        return ver["medidas"]
