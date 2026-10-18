"""Conferencia independente das redes de 8 elementos (vencedora e referencia) do repositorio deverser.

Nao importa nem executa nada do repositorio. Le os arquivos como dados:
  argv[1] rede_vencedora.json
  argv[2] estado.json            (genes do escolhido e a carga com as redes base)
  argv[3] rotina_8_vencedora_e_referencia.cpp
  argv[4] ferramenta_ordenacao.py (lido so com ast.parse: extrai as constantes MOLDE e VARIANTES, sem executar)

Uso: python3 -I redes.py <os 4 caminhos>
"""
import ast
import difflib
import hashlib
import itertools
import json
import re
import sys

import numpy as np

N = 8


def niveis_asap(rede, n=N):
    """Nivel de cada comparador pela regra 'o mais cedo possivel' (o mesmo criterio que o texto descreve)."""
    ultimo, out = [0] * n, []
    for i, j in rede:
        nv = max(ultimo[i], ultimo[j]) + 1
        ultimo[i] = ultimo[j] = nv
        out.append(nv)
    return out


def camadas(rede, n=N):
    nv = niveis_asap(rede, n)
    d = {}
    for c, k in zip(rede, nv):
        d.setdefault(k, []).append(tuple(c))
    return [d[k] for k in sorted(d)]


def aplica(rede, v):
    v = list(v)
    for i, j in rede:
        if v[i] > v[j]:
            v[i], v[j] = v[j], v[i]
    return v


def zero_um(rede, n=N):
    falhas = 0
    for x in itertools.product((0, 1), repeat=n):
        y = aplica(rede, x)
        if any(y[q] > y[q + 1] for q in range(n - 1)):
            falhas += 1
    return falhas


def permutacoes(rede, n=N):
    falhas = 0
    alvo = list(range(n))
    total = 0
    for p in itertools.permutations(range(n)):
        total += 1
        if aplica(rede, p) != alvo:
            falhas += 1
    return total, falhas


def todos_n_a_n(rede, n=N):
    """Os n^n vetores com valores 0..n-1, vetorizado: cada coluna e um fio. Min/max preservam o multiconjunto, entao basta conferir a ordem."""
    total = n ** n
    idx = np.arange(total, dtype=np.int64)
    cols = []
    for q in range(n):
        cols.append((idx % n).astype(np.int8))
        idx //= n
    for i, j in rede:
        a, b = cols[i], cols[j]
        cols[i], cols[j] = np.minimum(a, b), np.maximum(a, b)
    ok = np.ones(total, dtype=bool)
    for q in range(n - 1):
        ok &= cols[q] <= cols[q + 1]
    # conferencia do multiconjunto (redundante para min/max, mas explicita): soma e soma dos quadrados por vetor
    return total, int((~ok).sum())


def ternario_em_memoria(rede, n=N):
    """Simula a semantica exata da troca 'ternario' do C gerado (a = v[i], b = v[j]; v[i] = a<b?a:b; v[j] = a<b?b:a) nos n^n vetores."""
    total = n ** n
    idx = np.arange(total, dtype=np.int64)
    v = np.empty((n, total), dtype=np.int8)
    for q in range(n):
        v[q] = idx % n
        idx //= n
    cont0 = np.stack([(v == k).sum(axis=0) for k in range(n)])
    for i, j in rede:
        a, b = v[i].copy(), v[j].copy()
        lt = a < b
        v[i] = np.where(lt, a, b)
        v[j] = np.where(lt, b, a)
    ok = np.ones(total, dtype=bool)
    for q in range(n - 1):
        ok &= v[q] <= v[q + 1]
    cont1 = np.stack([(v == k).sum(axis=0) for k in range(n)])
    ok &= (cont0 == cont1).all(axis=0)
    return total, int((~ok).sum())


def decodifica(genes, base):
    """A regra documentada no CANDIDATO (respostas/004_propor_modelo.json): mantidos = k sem rem_k; ordena por (nivel, pri_k, k)."""
    niv = niveis_asap(base)
    mantidos = [k for k in range(len(base)) if not int(genes.get(f"rem_{k}", 0))]
    mantidos.sort(key=lambda k: (niv[k], float(genes.get(f"pri_{k}", 0.5)), k))
    return [tuple(base[k]) for k in mantidos]


def consts_do_fonte(caminho):
    arv = ast.parse(open(caminho, encoding="utf-8").read())
    out = {}
    for no in arv.body:
        if isinstance(no, ast.Assign) and len(no.targets) == 1 and isinstance(no.targets[0], ast.Name) and no.targets[0].id in ("MOLDE", "VARIANTES"):
            out[no.targets[0].id] = ast.literal_eval(no.value)
    return out


def corpo(rede, variante, registradores, VARIANTES, n=N):
    X = (lambda q: f"x{q}") if registradores else (lambda q: f"v[{q}]")
    linhas = []
    if registradores:
        linhas.append(" ".join(f"int32_t x{q} = v[{q}];" for q in range(n)))
    for i, j in rede:
        linhas.append(VARIANTES[variante].format(A=X(i), B=X(j)))
    if registradores:
        linhas.append(" ".join(f"v[{q}] = x{q};" for q in range(n)))
    return " ".join(linhas)


def simd(rede, n=8):
    L = ["__m256i x = _mm256_loadu_si256((const __m256i *)v), p, lo, hi;"]
    for nivel in camadas(rede, n):
        perm, alto = list(range(8)), [0] * 8
        for i, j in nivel:
            perm[i], perm[j], alto[j] = j, i, 1
        L.append("p = _mm256_permutevar8x32_epi32(x, _mm256_setr_epi32(" + ", ".join(map(str, perm)) + "));")
        L.append("lo = _mm256_min_epi32(x, p); hi = _mm256_max_epi32(x, p);")
        L.append("x = _mm256_blendv_epi8(lo, hi, _mm256_setr_epi32(" + ", ".join("-1" if b else "0" for b in alto) + "));")
    L.append("_mm256_storeu_si256((__m256i *)v, x);")
    return " ".join(L)


def simd_ordena(rede, n=8):
    """Simula a versao AVX2 (permutacao, min, max, mistura por nivel) nos 2^8 vetores 0-1."""
    falhas = 0
    for x in itertools.product((0, 1), repeat=n):
        v = list(x)
        for nivel in camadas(rede, n):
            perm, alto = list(range(8)), [0] * 8
            for i, j in nivel:
                perm[i], perm[j], alto[j] = j, i, 1
            p = [v[perm[k]] for k in range(8)]
            lo = [min(a, b) for a, b in zip(v, p)]
            hi = [max(a, b) for a, b in zip(v, p)]
            v = [hi[k] if alto[k] else lo[k] for k in range(8)]
        if any(v[q] > v[q + 1] for q in range(n - 1)):
            falhas += 1
    return falhas


def main():
    rv_path, estado_path, cpp_path, ferr_path = sys.argv[1:5]
    rv = json.load(open(rv_path, encoding="utf-8"))
    est = json.load(open(estado_path, encoding="utf-8"))
    W = [tuple(c) for c in rv["rede_vencedora"]]
    R = [tuple(c) for c in rv["rede_de_referencia"]]
    rel = {}

    # 1. decodificar os genes registrados no estado com a regra documentada
    carga = est["modelo"]["carga"]
    js = carga[carga.index("return ") + len("return "):].strip()
    carga_d = json.loads(js)
    base = carga_d["redes"]["otima"]
    genes = est["desfecho"] and est["criacoes"][-1]["escolhido"]["formulacao"]
    assert est["desfecho"]["escolhido"] == genes["_id"]
    Wd = decodifica(genes, base)
    rel["decodificada_igual_a_rede_vencedora_json"] = Wd == W
    rel["referencia_da_carga_igual_a_rede_de_referencia_json"] = [tuple(c) for c in carga_d["referencia"]] == R
    rel["base_otima_igual_a_referencia"] = [tuple(c) for c in base] == R
    rel["genes_rem_ativos"] = sorted(int(k[4:]) for k, v in genes.items() if k.startswith("rem_") and int(v))
    rel["base_tem_comparadores"] = len(base)
    rel["genes"] = {k: genes[k] for k in ("base", "variante", "registradores")}

    # 2. o .cpp publicado
    cpp = open(cpp_path, encoding="utf-8").read()

    def corpo_de(nome):
        m = re.search(r"static void " + nome + r"\(int32_t \*v\) \{(.*?)\}\nstatic inline", cpp, re.S)
        return m.group(1) if m else None
    cand = corpo_de("cand_")
    refe = corpo_de("refe_")
    refe2 = corpo_de("refe2_")
    Wc = [(int(a), int(b)) for a, b in re.findall(r"int32_t a = v\[(\d)\], b = v\[(\d)\];", cand)]
    Rc = [(int(a), int(b)) for a, b in re.findall(r"int32_t a = x(\d), b = x(\d);", refe)]
    rel["cpp_cand_igual_vencedora"] = Wc == W
    rel["cpp_refe_igual_referencia"] = Rc == R
    rel["cpp_refe2_igual_refe"] = refe == refe2
    rel["cpp_tem_simd_refs"] = "refs_" in cpp
    rel["cpp_imprime_razao_vs_melhor"] = "razao_vs_melhor" in cpp

    # 3. correcao
    for nome, rede in (("vencedora", W), ("referencia", R), ("batcher_da_carga", [tuple(c) for c in carga_d["redes"]["batcher"]])):
        tot, f = permutacoes(rede)
        t88, f88 = todos_n_a_n(rede)
        t88b, f88b = ternario_em_memoria(rede)
        rel[nome] = {"comparadores": len(rede), "profundidade": max(niveis_asap(rede)),
                     "camadas_tamanhos": [len(c) for c in camadas(rede)],
                     "falhas_0_1_de_256": zero_um(rede), "permutacoes": tot, "falhas_permutacoes": f,
                     "vetores_8a8": t88, "falhas_8a8_minmax": f88, "falhas_8a8_ternario_exato": f88b,
                     "falhas_simd_0_1": simd_ordena(rede)}

    # 4. mesmo conjunto, mesmas camadas, so a ordem dentro da camada muda
    cw, cr = camadas(W), camadas(R)
    rel["mesmo_multiconjunto"] = sorted(W) == sorted(R)
    rel["mesmas_camadas_como_conjuntos"] = [sorted(a) for a in cw] == [sorted(b) for b in cr]
    nvw = niveis_asap(W)
    rel["vencedora_em_ordem_de_camada"] = all(nvw[k] <= nvw[k + 1] for k in range(len(nvw) - 1))
    rel["camadas_disjuntas"] = all(len({x for c in cam for x in c}) == 2 * len(cam) for cam in cr)
    rel["camadas_referencia"] = [[list(c) for c in cam] for cam in cr]
    rel["camadas_vencedora"] = [[list(c) for c in cam] for cam in cw]

    # 5. o fonte que a ferramenta geraria e o sha256[:24] registrado
    k = consts_do_fonte(ferr_path)
    MOLDE, VAR = k["MOLDE"], k["VARIANTES"]
    src = (MOLDE.replace("__N__", "8").replace("__CAND__", corpo(W, "ternario", False, VAR))
           .replace("__REFE__", corpo(R, "ternario", True, VAR)).replace("__REFS__", simd(R)))
    h = hashlib.sha256(src.encode()).hexdigest()[:24]
    rel["sha24_reconstruido"] = h
    rel["sha24_registrado"] = rv.get("fonte_sha256_24")
    rel["sha24_confere"] = h == rv.get("fonte_sha256_24")
    rel["sha24_do_cpp_publicado"] = hashlib.sha256(cpp.encode()).hexdigest()[:24]
    rel["cpp_publicado_identico_ao_gerado"] = cpp == src or cpp.rstrip("\n") == src.rstrip("\n")
    # corpos do candidato e da referencia identicos?
    rel["corpo_cand_identico_ao_gerado"] = cand.strip() == corpo(W, "ternario", False, VAR).strip()
    rel["corpo_refe_identico_ao_gerado"] = refe.strip() == corpo(R, "ternario", True, VAR).strip()
    diff = list(difflib.unified_diff(src.splitlines(), cpp.splitlines(), "gerado_pela_ferramenta", "cpp_publicado", n=0, lineterm=""))
    rel["linhas_de_diferenca"] = len([l for l in diff if l[:1] in "+-" and not l.startswith(("+++", "---"))])
    print(json.dumps(rel, ensure_ascii=False, indent=1))
    print("\n==== diff (gerado -> publicado), linhas cortadas em 160 caracteres ====")
    for l in diff:
        print(l[:160])


if __name__ == "__main__":
    main()
