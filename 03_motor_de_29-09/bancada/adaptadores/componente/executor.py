"""O executor que roda na máquina de destino, sozinho: só a biblioteca padrão, e o NumPy quando ele existe lá.

  python executor.py perfil
  python executor.py medir '{"impl": ..., "bits": ..., "k": ..., "n": ..., "semente": ..., "partes": ["fp", "mem", "lat"], ...}'
  python executor.py rodadas '{... "rodadas": 3}'

O perfil devolve o que a máquina é: a versão do Python, o NumPy (se há e qual), os núcleos, a memória e dois microbenchmarks, cada um
com a mediana e o intervalo de 7 repetições. A medida constrói o componente com n ids distintos e mede, conforme as partes pedidas:
- fp: os falsos negativos sobre todos os membros e a taxa de falsos positivos sobre consultas_fp ids novos, com o intervalo de Wilson;
- mem: a memória que o componente retém depois de soltar a entrada, medida pelo tracemalloc numa construção à parte (o rastreio
  atrasa o Python puro, e por isso o tempo vem de outra construção);
- lat: a latência de lotes de consultas (metade de membros, metade de ids novos), mediana e p95 dos lotes.
As rodadas de latência rodam cada uma num processo novo.
"""
import gc
import json
import os
import platform
import random
import subprocess
import sys
import time
import tracemalloc
from bisect import bisect_left

M64 = (1 << 64) - 1


def _mix(x):
    """splitmix64: o espalhamento dos hashes, igual nas duas versões do filtro de Bloom."""
    x = (x + 0x9E3779B97F4A7C15) & M64
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & M64
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & M64
    return x ^ (x >> 31)


class Conjunto:
    def __init__(self, ids, **_):
        self.s = set(ids)

    def consultar(self, lote):
        s = self.s
        return [x in s for x in lote]


class Ordenado:
    def __init__(self, ids, **_):
        self.v = sorted(ids)

    def consultar(self, lote):
        v, n = self.v, len(self.v)
        out = []
        for x in lote:
            i = bisect_left(v, x)
            out.append(i < n and v[i] == x)
        return out


class BloomPy:
    def __init__(self, ids, bits_por_item, k, **_):
        self.m = max(8, int(len(ids) * bits_por_item))
        self.k = k
        self.b = bytearray((self.m + 7) // 8)
        for x in ids:
            h1 = _mix(x)
            h2 = _mix(h1) | 1
            for i in range(k):
                p = ((h1 + i * h2) & M64) % self.m
                self.b[p >> 3] |= 1 << (p & 7)

    def consultar(self, lote):
        m, k, b = self.m, self.k, self.b
        out = []
        for x in lote:
            h1 = _mix(x)
            h2 = _mix(h1) | 1
            ok = True
            for i in range(k):
                p = ((h1 + i * h2) & M64) % m
                if not (b[p >> 3] >> (p & 7)) & 1:
                    ok = False
                    break
            out.append(ok)
        return out


def _mix_np(np, x):
    x = x + np.uint64(0x9E3779B97F4A7C15)
    x = (x ^ (x >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
    x = (x ^ (x >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
    return x ^ (x >> np.uint64(31))


class BloomNp:
    def __init__(self, ids, bits_por_item, k, **_):
        import numpy as np
        self.np = np
        self.m = max(8, int(len(ids) * bits_por_item))
        self.k = k
        self.b = np.zeros((self.m + 7) // 8, dtype=np.uint8)
        a = np.array(ids, dtype=np.uint64)
        with np.errstate(over="ignore"):
            h1 = _mix_np(np, a)
            h2 = _mix_np(np, h1) | np.uint64(1)
            for i in range(k):
                p = (h1 + np.uint64(i) * h2) % np.uint64(self.m)
                np.bitwise_or.at(self.b, (p >> np.uint64(3)).astype(np.int64), (np.uint8(1) << (p & np.uint64(7)).astype(np.uint8)))

    def consultar(self, lote):
        np = self.np
        a = np.array(lote, dtype=np.uint64)
        ok = np.ones(len(a), dtype=bool)
        with np.errstate(over="ignore"):
            h1 = _mix_np(np, a)
            h2 = _mix_np(np, h1) | np.uint64(1)
            for i in range(self.k):
                p = (h1 + np.uint64(i) * h2) % np.uint64(self.m)
                ok &= ((self.b[(p >> np.uint64(3)).astype(np.int64)] >> (p & np.uint64(7)).astype(np.uint8)) & 1).astype(bool)
        return ok.tolist()


class OrdenadoNp:
    def __init__(self, ids, **_):
        import numpy as np
        self.np = np
        self.v = np.sort(np.array(ids, dtype=np.uint64))

    def consultar(self, lote):
        np = self.np
        a = np.array(lote, dtype=np.uint64)
        i = np.searchsorted(self.v, a)
        i = np.minimum(i, len(self.v) - 1)
        return (self.v[i] == a).tolist()


IMPLS = {"conjunto": Conjunto, "ordenado": Ordenado, "bloom_py": BloomPy, "bloom_np": BloomNp, "ordenado_np": OrdenadoNp}
PRECISA_NUMPY = {"bloom_np", "ordenado_np"}


def _repetir(f, vezes=7):
    xs = []
    for _ in range(vezes):
        t0 = time.perf_counter()
        f()
        xs.append(time.perf_counter() - t0)
    xs.sort()
    return xs


def alimentacao():
    """Tomada ou bateria: num notebook, o estado de energia muda o desempenho (a campanha de 28/09 mediu quase 2× entre os dois)."""
    try:
        if os.name == "nt":
            import ctypes

            class S(ctypes.Structure):
                _fields_ = [("ac", ctypes.c_ubyte), ("flag", ctypes.c_ubyte), ("pct", ctypes.c_ubyte), ("saver", ctypes.c_ubyte),
                            ("vida", ctypes.c_ulong), ("cheia", ctypes.c_ulong)]
            st = S()
            ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(st))
            return {0: "bateria", 1: "tomada"}.get(st.ac, "desconhecida") + ("|economia" if st.saver else "")
        import glob
        for f in glob.glob("/sys/class/power_supply/*/online"):
            with open(f) as fh:
                return "tomada" if fh.read().strip() == "1" else "bateria"
        return "sem_bateria"
    except Exception as e:  # noqa: BLE001
        return f"erro: {e!r}"


def perfil():
    out = {"python": platform.python_version(), "implementacao": platform.python_implementation(), "sistema": platform.system(),
           "maquina": platform.machine(), "processador": platform.processor(), "cpus": os.cpu_count()}
    try:
        import numpy
        out["numpy"] = numpy.__version__
    except ImportError:
        out["numpy"] = None
    try:
        if hasattr(os, "sysconf"):
            out["ram_total_mb"] = round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2 ** 20)
            out["ram_livre_mb"] = round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_AVPHYS_PAGES") / 2 ** 20)
        else:
            import ctypes

            class M(ctypes.Structure):
                _fields_ = [("l", ctypes.c_ulong), ("c", ctypes.c_ulong), ("t", ctypes.c_ulonglong), ("a", ctypes.c_ulonglong),
                            ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong), ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong),
                            ("e", ctypes.c_ulonglong)]
            m = M()
            m.l = ctypes.sizeof(M)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            out["ram_total_mb"], out["ram_livre_mb"] = round(m.t / 2 ** 20), round(m.a / 2 ** 20)
    except Exception as e:  # noqa: BLE001
        out["ram_erro"] = repr(e)
    out["alimentacao"] = alimentacao()
    r = random.Random(1)
    xs = [r.getrandbits(62) for _ in range(100000)]
    t = _repetir(lambda: set(xs))
    out["ns_por_insercao_em_conjunto"] = [round(1e9 * t[len(t) // 2] / len(xs), 2), round(1e9 * t[0] / len(xs), 2), round(1e9 * t[-1] / len(xs), 2)]
    t = _repetir(lambda: [_mix(x) for x in xs[:20000]])
    out["ns_por_hash_splitmix"] = [round(1e9 * t[len(t) // 2] / 20000, 2), round(1e9 * t[0] / 20000, 2), round(1e9 * t[-1] / 20000, 2)]
    return out


def gerar_ids(semente, n):
    """n ids distintos de 62 bits, na ordem em que saem do gerador: o mesmo resultado em qualquer Python e sistema."""
    r = random.Random(semente)
    vistos, ids = set(), []
    while len(ids) < n:
        x = r.getrandbits(62)
        if x not in vistos:
            vistos.add(x)
            ids.append(x)
    return ids


def wilson(fp, total, z=1.96):
    if total == 0:
        return [0.0, 1.0]
    p = fp / total
    c = (p + z * z / (2 * total)) / (1 + z * z / total)
    h = z * ((p * (1 - p) / total + z * z / (4 * total * total)) ** 0.5) / (1 + z * z / total)
    return [round(max(0.0, c - h), 7), round(min(1.0, c + h), 7)]


def medir(a):
    """Uma rodada. a: impl, bits, k, n, semente, partes (lista de "fp", "mem", "lat"), lote, lotes, consultas_fp."""
    impl, bits, k, n, semente = a["impl"], a.get("bits", 0), a.get("k", 0), a["n"], a["semente"]
    if impl in PRECISA_NUMPY:
        try:
            import numpy  # noqa: F401
        except ImportError:
            return {"erro": "numpy_ausente"}
    out = {"python": platform.python_version()}
    if "mem" in a["partes"]:
        # a memória que o componente retém depois que a entrada é solta: os ids nascem já sob o rastreio, e o que sobra depois de
        # soltá-los é do componente (os inteiros que um conjunto guarda contam; o filtro de Bloom não guarda nenhum)
        gc.collect()
        tracemalloc.start()
        base = tracemalloc.get_traced_memory()[0]
        ids = gerar_ids(semente, n)
        c = IMPLS[impl](ids, bits_por_item=bits, k=k)
        del ids
        gc.collect()
        out["memoria_mb"] = round((tracemalloc.get_traced_memory()[0] - base) / 2 ** 20, 4)
        tracemalloc.stop()
        del c
        gc.collect()
    ids = gerar_ids(semente, n)
    t0 = time.perf_counter()
    c = IMPLS[impl](ids, bits_por_item=bits, k=k)
    out["construcao_ms"] = round(1000 * (time.perf_counter() - t0), 2)
    membros = set(ids)
    if "fp" in a["partes"]:
        out["fn"] = sum(1 for y in c.consultar(ids) if not y)
        r = random.Random(semente * 1000003 + 7)
        novos = []
        while len(novos) < a["consultas_fp"]:
            x = r.getrandbits(62)
            if x not in membros:
                novos.append(x)
        fp = sum(1 for y in c.consultar(novos) if y)
        out["fp"] = round(fp / len(novos), 7)
        out["fp_ic95"] = wilson(fp, len(novos))
        out["fp_contagem"] = [fp, len(novos)]
    if "lat" in a["partes"]:
        r = random.Random(semente ^ 0x5EED)
        tempos = []
        for _ in range(a["lotes"]):
            q = [ids[r.randrange(n)] if r.random() < 0.5 else r.getrandbits(62) for _ in range(a["lote"])]
            t0 = time.perf_counter()
            c.consultar(q)
            tempos.append(time.perf_counter() - t0)
        tempos.sort()
        out["mediana_lote_ms"] = round(1000 * tempos[len(tempos) // 2], 4)
        out["p95_lote_ms"] = round(1000 * tempos[int(0.95 * (len(tempos) - 1))], 4)
    return out


def medir_rodadas(a):
    """A latência em várias rodadas, cada uma num processo novo do mesmo interpretador: a unidade de amostra é a rodada."""
    rodadas = []
    for i in range(a["rodadas"]):
        b = dict(a, partes=["lat"])
        r = subprocess.run([sys.executable, "-B", os.path.abspath(__file__), "medir", json.dumps(b)], capture_output=True, text=True)
        if r.returncode != 0:
            return {"erro": "rodada", "stderr": r.stderr[-500:]}
        x = json.loads(r.stdout.strip().splitlines()[-1])
        if "erro" in x:
            return x
        rodadas.append(x)
    p95 = [x["p95_lote_ms"] for x in rodadas]
    return {"p95_rodadas_ms": p95, "p95_intervalo_ms": [min(p95), max(p95)], "p95_lote_ms": sorted(p95)[len(p95) // 2],
            "mediana_lote_ms": sorted(x["mediana_lote_ms"] for x in rodadas)[len(rodadas) // 2],
            "construcao_ms": sorted(x["construcao_ms"] for x in rodadas)[len(rodadas) // 2], "python": rodadas[0]["python"]}


def conferir(a):
    """Confere um componente exportado: importa o módulo, constrói com os mesmos ids e conta os falsos negativos e os falsos
    positivos nas mesmas consultas da verificação. O artefato é o corpo verificado quando as contagens são iguais."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("componente_exportado", a["modulo"])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ids = gerar_ids(a["semente"], a["n"])
    c = mod.construir(ids)
    membros = set(ids)
    fn = sum(1 for y in c.consultar(ids) if not y)
    r = random.Random(a["semente"] * 1000003 + 7)
    novos = []
    while len(novos) < a["consultas_fp"]:
        x = r.getrandbits(62)
        if x not in membros:
            novos.append(x)
    fp = sum(1 for y in c.consultar(novos) if y)
    return {"fn": fn, "fp_contagem": [fp, len(novos)], "parametros": getattr(mod, "PARAMETROS", None), "python": platform.python_version()}


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "perfil":
        print(json.dumps(perfil()))
    elif a[0] == "medir":
        print(json.dumps(medir(json.loads(a[1]))))
    elif a[0] == "rodadas":
        print(json.dumps(medir_rodadas(json.loads(a[1]))))
    elif a[0] == "conferir":
        print(json.dumps(conferir(json.loads(a[1]))))
