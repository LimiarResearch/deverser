"""A2: um componente de pertença (dizer se um id já foi visto) criado para uma máquina de destino.

O que é do domínio fica aqui; o núcleo só vê formulações, vereditos, restrições e evidências.

Formulações: cinco implementações (conjunto, lista ordenada, arranjo ordenado em NumPy, filtro de Bloom em Python puro e em NumPy), e
no filtro de Bloom os parâmetros bits por item {6, 8, 10, 12, 14, 16} e número de hashes k de 2 a 8. São 87 formulações completas.

Verificador: o executor roda na máquina de destino, com o Python de lá, e mede. As medidas e o juiz de cada uma:
- fn (falsos negativos) sobre todos os membros; fp (falsos positivos) sobre consultas_fp ids novos, julgado pelo intervalo de Wilson
  a 95%: passa se o intervalo inteiro cumpre o limite, falha se nenhum ponto cumpre, e fica incerto quando o intervalo atravessa;
- memoria_mb: o que o componente retém depois de soltar a entrada (tracemalloc), determinística;
- p95_lote_ms: o p95 da latência de um lote, em várias rodadas, cada uma num processo novo; o juiz usa o intervalo entre rodadas
  (o menor e o maior p95), com a mesma regra do fp.

Evidências de medida, com as hipóteses de que dependem (a regra de transferência do núcleo decide se ainda valem):
- fp e fn dependem só da carga (n, semente, consultas_fp) e das posições que o código põe; as duas versões do filtro de Bloom põem os
  mesmos bits (premissa conferida em testes/test_componente.py), e por isso a medida de uma vale para a outra, em qualquer máquina;
- a memória depende da carga, da implementação do Python e da versão dele (e da versão do NumPy nas implementações que o usam); no
  filtro de Bloom ela não depende de k (o arranjo tem n × bits bits; premissa conferida em testes);
- a latência depende da máquina (maquina_id), do estado dela (a alimentação e os microbenchmarks do perfil, dentro do intervalo
  medido), da versão do Python e da carga. O estado entrou depois da primeira campanha: com só o maquina_id, uma latência medida na
  bateria valia na tomada, e o veredito do Bloom em Python puro sob 2 ms virava de uma campanha para outra.
Toda medida leva o hash do executor, e uma medida tirada por outro executor não é reusada.

Restrições tiradas de nulos, cada uma com a premissa que a sustenta (premissas de modelo, e não medidas; a campanha mede se alguma
eliminou um corpo que seria válido):
- requer_numpy: sem NumPy no alvo, as implementações que precisam dele caem (meio insuficiente);
- fp_monotona: no filtro de Bloom, com k fixo, menos bits por item não baixa o fp;
- memoria_monotona: no filtro de Bloom da mesma implementação, mais bits por item não baixa a memória;
- latencia_monotona: na mesma implementação e nos mesmos bits, mais hashes não baixam a latência.
"""
import hashlib
import inspect
import json
import os

from bancada.nucleo.adaptador import Adaptador
from bancada.nucleo.ledger import Ledger

# a validade declarada de uma medida de estado da máquina: o microbenchmark do perfil a ±15% do valor com que a medida foi tirada
# (escolha declarada do verificador, emenda de 28/09; antes, a validade era o intervalo de 7 repetições, tirado da amostra)
TOLERANCIA_DE_ESTADO = 0.15

from . import executor as EX

EXECUTOR = os.path.abspath(EX.__file__)
BITS = (16, 14, 12, 10, 8, 6)
KS = (2, 3, 4, 5, 6, 7, 8)
EXATAS = ("conjunto", "ordenado", "ordenado_np")
BLOOM = ("bloom_np", "bloom_py")
MEDIDAS = ("fn", "fp", "memoria_mb", "p95_lote_ms")


def _sha_executor():
    with open(EXECUTOR, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def formulacao(impl, bits=0, k=0):
    if impl in EXATAS:
        return {"id": impl, "impl": impl, "bits": 0, "k": 0, "chave_fp": f"exata|{impl}", "chave_mem": impl}
    return {"id": f"{impl}|b{bits}|k{k}", "impl": impl, "bits": bits, "k": k,
            "chave_fp": f"bloom-splitmix64|b{bits}|k{k}", "chave_mem": f"{impl}|b{bits}"}


def julgar(teste, medidas):
    """passa, falha ou incerto: o intervalo inteiro da medida contra o limite da cláusula."""
    m = teste["medida"]
    lo, hi = medidas.get(m + "_intervalo") or [medidas[m], medidas[m]]
    op, lim = teste["op"], teste["valor"]
    ok = {"<=": lambda x: x <= lim, "==": lambda x: x == lim, ">=": lambda x: x >= lim, "<": lambda x: x < lim}[op]
    a, b = ok(lo), ok(hi)
    return "passa" if a and b else ("falha" if not a and not b else "incerto")


class AdaptadorComponente(Adaptador):
    nome = "componente_pertenca"

    def __init__(self, alvo, usar_ledger=True):
        self.alvo = alvo
        self.usar_ledger = usar_ledger
        self.sha = _sha_executor()

    # ---- a família ----
    def formulacoes(self, D, Pi):
        for impl in EXATAS:
            yield formulacao(impl)
        for impl in BLOOM:
            for b in BITS:
                for k in KS:
                    yield formulacao(impl, b, k)

    def elimina(self, r, f):
        if not self.usar_ledger:
            return False
        t = r["tipo"]
        if t == "requer_numpy":
            return f["impl"] in EX.PRECISA_NUMPY
        if f["impl"] not in BLOOM:
            return False
        if t == "fp_monotona":
            return f["k"] == r["k"] and f["bits"] <= r["bits_max"]
        if t == "memoria_monotona":
            return f["impl"] == r["impl"] and f["bits"] >= r["bits_min"]
        if t == "latencia_monotona":
            return f["impl"] == r["impl"] and f["bits"] == r["bits"] and f["k"] >= r["k_min"]
        return False

    # ---- o corpo ----
    def construir(self, f, D, Pi, contexto):
        assert Pi.valor("maquina_id") == self.alvo.id, "o Π é de outra máquina"
        if f["impl"] in EX.PRECISA_NUMPY and not Pi.valor("numpy_disponivel"):
            return {"_veredito": True, "aprovado": False, "medidas": {}, "custo": {},
                    "escopo": "decidido pelo Π, sem medir",
                    "nulo": {"classe": "meio_insuficiente", "clausula": None, "condicao": "numpy_disponivel == False",
                             "medida": "numpy_disponivel", "motivo": f"o alvo {self.alvo.id} não tem NumPy, e {f['impl']} precisa dele"}}
        return {"impl": f["impl"], "bits": f["bits"], "k": f["k"], "executor_sha": self.sha}

    # ---- o verificador ----
    def _buscar(self, contexto, tipo, chave):
        if not self.usar_ledger:
            return None
        for e in reversed(contexto.get("evidencias", [])):
            m = e.get("medida")
            if m and m["tipo"] == tipo and m["chave"] == chave and m["executor_sha"] == self.sha:
                return e
        return None

    def _hip(self, tipo, f, D, Pi):
        np_ = ["numpy_versao"] if f["impl"] in EX.PRECISA_NUMPY else []
        if tipo == "fp":
            return Ledger.hipoteses(D, (), Pi, (), escopo=("n", "semente", "consultas_fp"))
        if tipo == "mem":
            return Ledger.hipoteses(D, (), Pi, ["python_implementacao", "python_versao"] + np_, escopo=("n", "semente"))
        # a latência depende da máquina e do estado dela: a alimentação e os dois microbenchmarks do perfil, cada um dentro do
        # intervalo medido quando a latência foi tirada (a campanha de 28/09 mostrou o notebook quase 2× mais rápido na tomada)
        return Ledger.hipoteses(D, (), Pi, ["maquina_id", "python_versao", "alimentacao", Ledger.estado("ns_por_hash_splitmix", Pi, TOLERANCIA_DE_ESTADO),
                                                   Ledger.estado("ns_por_insercao_em_conjunto", Pi, TOLERANCIA_DE_ESTADO)] + np_,
                                escopo=("n", "semente", "lote", "lotes", "rodadas"))

    def verificar(self, corpo, f, D, Pi, contexto=None):
        contexto = contexto or {}
        esc = D.dados["escopo"]
        rigidas = {c["teste"]["medida"]: c for c in D.rigidas()}
        medidas, novas, custo, reusadas = {}, [], {"medicoes_no_alvo": 0, "medidas_reusadas": 0}, []
        base = {"impl": f["impl"], "bits": f["bits"], "k": f["k"], "n": esc["n"], "semente": esc["semente"]}

        def veredito(escopo):
            julg = {m: julgar(rigidas[m]["teste"], medidas) for m in MEDIDAS if m in rigidas and m in medidas}
            falha = next((m for m in MEDIDAS if julg.get(m) == "falha"), None)
            incerto = next((m for m in MEDIDAS if julg.get(m) == "incerto"), None)
            nulo = None
            if falha or incerto:
                m = falha or incerto
                c = rigidas[m]
                intervalo = medidas.get(m + "_intervalo")
                nulo = {"classe": "candidato_falho" if falha else "modelo_incerto", "clausula": c["id"],
                        "condicao": f"{m} {c['teste']['op']} {c['teste']['valor']}", "medida": {m: medidas[m], "intervalo": intervalo},
                        "motivo": (f"{m} = {medidas[m]} não cumpre {c['teste']['op']} {c['teste']['valor']}" if falha else
                                   f"o intervalo {intervalo} de {m} atravessa o limite {c['teste']['valor']}: a medida não decide")}
            return {"aprovado": nulo is None and all(m in julg for m in rigidas), "medidas": dict(medidas), "julgamento": julg,
                    "escopo": escopo, "nulo": nulo, "custo": custo, "evidencias": novas, "medidas_reusadas_de": reusadas}

        def decidido():
            return any(julgar(rigidas[m]["teste"], medidas) == "falha" for m in MEDIDAS if m in rigidas and m in medidas)

        # fp e fn, e a memória: da evidência que vale, ou medidos agora numa chamada só
        partes = []
        for tipo, chave in (("fp", f["chave_fp"]), ("mem", f["chave_mem"])):
            e = self._buscar(contexto, tipo, chave)
            if e:
                medidas.update(e["medida"]["valores"])
                custo["medidas_reusadas"] += 1
                reusadas.append(e["seq"])
            else:
                partes.append(tipo)
        if partes:
            r = self.alvo.executar(EXECUTOR, "medir", json.dumps(dict(base, partes=partes, consultas_fp=esc["consultas_fp"])))
            custo["medicoes_no_alvo"] += 1
            if "erro" in r:
                raise RuntimeError(f"o executor falhou no alvo {self.alvo.id}: {r}")
            if "fp" in partes:
                v = {"fn": r["fn"], "fp": r["fp"], "fp_intervalo": r["fp_ic95"], "fp_contagem": r["fp_contagem"]}
                medidas.update(v)
                novas.append({"medida": {"tipo": "fp", "chave": f["chave_fp"], "valores": v, "executor_sha": self.sha,
                                         "medida_em": self.alvo.id, "implementacao_medida": f["impl"]},
                              "hipoteses": self._hip("fp", f, D, Pi)})
            if "mem" in partes:
                v = {"memoria_mb": r["memoria_mb"]}
                medidas.update(v)
                novas.append({"medida": {"tipo": "mem", "chave": f["chave_mem"], "valores": v, "executor_sha": self.sha,
                                         "medida_em": self.alvo.id, "k_medido": f["k"]},
                              "hipoteses": self._hip("mem", f, D, Pi)})
        if decidido():
            return veredito(f"fp e memória em {self.alvo.id}; a latência não foi medida porque o corpo já falhou")
        # a latência, em rodadas
        e = self._buscar(contexto, "lat", f["id"])
        if e:
            medidas.update(e["medida"]["valores"])
            custo["medidas_reusadas"] += 1
            reusadas.append(e["seq"])
        else:
            r = self.alvo.executar(EXECUTOR, "rodadas", json.dumps(dict(base, lote=esc["lote"], lotes=esc["lotes"], rodadas=esc["rodadas"])))
            custo["medicoes_no_alvo"] += 1
            if "erro" in r:
                raise RuntimeError(f"o executor falhou no alvo {self.alvo.id}: {r}")
            v = {"p95_lote_ms": r["p95_lote_ms"], "p95_lote_ms_intervalo": r["p95_intervalo_ms"], "p95_rodadas_ms": r["p95_rodadas_ms"],
                 "mediana_lote_ms": r["mediana_lote_ms"], "construcao_ms": r["construcao_ms"]}
            medidas.update(v)
            novas.append({"medida": {"tipo": "lat", "chave": f["id"], "valores": v, "executor_sha": self.sha, "medida_em": self.alvo.id},
                          "hipoteses": self._hip("lat", f, D, Pi)})
        return veredito(f"medido em {self.alvo.id} ({Pi.valor('sistema')}, Python {Pi.valor('python_versao')}), carga de {esc['n']} ids, "
                        f"semente {esc['semente']}, {esc['rodadas']} rodadas de latência")

    # ---- o que um nulo elimina ----
    def restricoes(self, ver, f, D, Pi):
        if not self.usar_ledger:
            return []
        n = ver["nulo"]
        if n["classe"] == "meio_insuficiente" and n["medida"] == "numpy_disponivel":
            return [{"restricao": {"tipo": "requer_numpy"}, "hipoteses": Ledger.hipoteses(D, (), Pi, ["numpy_disponivel"]),
                     "premissa": "medida: o import do NumPy falhou no alvo"}]
        if n["classe"] != "candidato_falho" or f["impl"] not in BLOOM:
            return []
        c = n["clausula"]
        m = next(x["teste"]["medida"] for x in D.rigidas() if x["id"] == c)
        if m == "fp":
            return [{"restricao": {"tipo": "fp_monotona", "k": f["k"], "bits_max": f["bits"]},
                     "hipoteses": Ledger.hipoteses(D, [c], Pi, (), escopo=("n", "semente", "consultas_fp")),
                     "premissa": "modelo: com k fixo, menos bits por item não baixa o fp do filtro de Bloom"}]
        if m == "memoria_mb":
            return [{"restricao": {"tipo": "memoria_monotona", "impl": f["impl"], "bits_min": f["bits"]},
                     "hipoteses": Ledger.hipoteses(D, [c], Pi, ["python_implementacao", "python_versao"], escopo=("n",)),
                     "premissa": "construção: o arranjo tem n × bits bits, e a memória não depende de k"}]
        if m == "p95_lote_ms":
            return [{"restricao": {"tipo": "latencia_monotona", "impl": f["impl"], "bits": f["bits"], "k_min": f["k"]},
                     "hipoteses": Ledger.hipoteses(D, [c], Pi, ["maquina_id", "python_versao", "alimentacao", Ledger.estado("ns_por_hash_splitmix", Pi, TOLERANCIA_DE_ESTADO),
                                                                    Ledger.estado("ns_por_insercao_em_conjunto", Pi, TOLERANCIA_DE_ESTADO)],
                                                   escopo=("n", "semente", "lote", "lotes", "rodadas")),
                     "premissa": "modelo: com os mesmos bits, mais hashes não baixam a latência de um lote"}]
        return []

    def medidas_de_objetivo(self, ver):
        return {m: ver["medidas"].get(m) for m in MEDIDAS}

    # ---- o artefato ----
    def exportar(self, corpo, f, pasta, D=None, Pi=None, ver=None):
        """Um módulo Python autossuficiente com a implementação escolhida e os parâmetros verificados."""
        classe = {c.__name__: c for c in EX.IMPLS.values()}[EX.IMPLS[f["impl"]].__name__]
        partes = ["M64 = (1 << 64) - 1", inspect.getsource(EX._mix)]
        if f["impl"] in EX.PRECISA_NUMPY:
            partes.append(inspect.getsource(EX._mix_np))
        partes.append(inspect.getsource(classe))
        nome = f"componente_{hashlib.sha256(f['id'].encode()).hexdigest()[:8]}.py"
        texto = (f'"""Componente de pertença gerado pela bancada de criação.\n\nFormulação {f["id"]}; executor {self.sha[:12]}.\n'
                 f'Uso: c = construir(ids); c.consultar(lote) devolve, para cada id, se ele já foi visto.\n"""\n'
                 + ("from bisect import bisect_left\n\n" if f["impl"] == "ordenado" else "\n")
                 + "\n\n".join(partes)
                 + f"\n\nPARAMETROS = {json.dumps({'impl': f['impl'], 'bits_por_item': f['bits'], 'k': f['k']})}\n\n\n"
                 + f"def construir(ids):\n    return {classe.__name__}(ids, bits_por_item={f['bits']}, k={f['k']})\n")
        caminho = os.path.join(pasta, nome)
        with open(caminho, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(texto)
        return [caminho]

    def conferir_exportado(self, arquivos, corpo, f, D=None, Pi=None, ver=None):
        """Roda o módulo exportado no alvo com a mesma carga e confere que as contagens são as do corpo verificado."""
        esc = D.dados["escopo"]
        remoto = self.alvo.enviar(arquivos[0])
        r = self.alvo.executar(EXECUTOR, "conferir", json.dumps({"modulo": remoto, "n": esc["n"], "semente": esc["semente"],
                                                                "consultas_fp": esc["consultas_fp"]}))
        esperado = ver["medidas"]["fp_contagem"]
        ok = r.get("fn") == 0 and r.get("fp_contagem") == esperado
        return ok, {"no_alvo": self.alvo.id, "obtido": r, "esperado": {"fn": 0, "fp_contagem": esperado}}
