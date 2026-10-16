"""O executor genérico que vai até a máquina alvo e mede um candidato que a IA escreveu. Só a biblioteca padrão (e o NumPy, se o alvo
tiver). Nada aqui sabe do problema.

  python executor_generico.py medir <trabalho.json>
  python executor_generico.py rodada <trabalho.json> <indice>

O trabalho: {"carga": código com gerar_carga(semente) -> entrada, "candidato": código com executar(entrada, **params) -> saída,
"metricas": código com metricas(entrada, saida) -> dict (opcional), "oraculos": [código com conferir(entrada, saida) -> (ok, detalhe)],
"params", "semente", "repeticoes", "rodadas"}.
Cada rodada roda num processo novo: gera a carga, mede o tempo de cada repetição de executar, mede o pico de memória numa execução à
parte (tracemalloc), calcula as métricas da saída e passa a saída por cada oráculo.
O código do trabalho só importa o que está na lista PERMITIDOS: cálculo, texto, compressão e estruturas de dados. Nada de sistema, rede,
arquivo ou processo. Do io, só BytesIO e StringIO (o io.open abriria arquivos).
"""
import base64
import builtins
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import tracemalloc
import traceback
import types
import zlib

PERMITIDOS = {"math", "cmath", "statistics", "itertools", "functools", "operator", "numbers", "fractions", "decimal", "random", "bisect",
              "heapq", "collections", "array", "struct", "copy", "dataclasses", "enum", "typing", "abc", "string", "re", "textwrap",
              "unicodedata", "json", "binascii", "base64", "hashlib", "hmac", "zlib", "bz2", "lzma", "datetime", "time", "numpy", "io",
              # emenda 2 (29/09): a ferramenta declarada; ela só roda o binário cujo caminho e sha256 quem lançou o motor declarou
              "ferramenta_passeio",
              # emenda 3 (29/09): o medidor declarado das rotinas de ordenação; gera o C++ da descrição estruturada e compila com o g++ declarado
              "ferramenta_ordenacao"}
_imp = builtins.__import__
_IO = types.SimpleNamespace(BytesIO=io.BytesIO, StringIO=io.StringIO)


def _importar(nome, globais=None, locais=None, lista=(), nivel=0):
    raiz = nome.split(".")[0]
    if nivel != 0 or raiz not in PERMITIDOS:
        raise ImportError(f"importação fora da lista de permitidos no alvo: {nome}")
    if raiz == "io":
        return _IO
    return _imp(nome, globais, locais, lista, nivel)


def _carregar(codigo, funcao):
    b = dict(vars(builtins))
    for n in ("open", "exec", "eval", "compile", "input", "__import__", "breakpoint", "exit", "quit"):
        b.pop(n, None)
    b["__import__"] = _importar
    g = {"__builtins__": b, "__name__": "candidato"}
    exec(compile(codigo, "<candidato>", "exec"), g)
    return g[funcao]


def rodada(t, i):
    out = {"indice": i}
    try:
        carga = _carregar(t["carga"], "gerar_carga")
        executar = _carregar(t["candidato"], "executar")
        entrada = carga(t.get("semente", 1))
        tempos, cpus, saida = [], [], None
        for _ in range(int(t.get("repeticoes", 5))):
            t0, c0 = time.perf_counter(), time.process_time()
            saida = executar(entrada, **t.get("params", {}))
            tempos.append(time.perf_counter() - t0)
            cpus.append(time.process_time() - c0)
        # o pico de memória é medido só na primeira rodada: a execução sob tracemalloc custa de 2,5 a 2,8 vezes mais, e o pico não muda
        # entre rodadas de um candidato determinístico
        if i == 0:
            tracemalloc.start()
            executar(entrada, **t.get("params", {}))
            out["pico_memoria_mb"] = tracemalloc.get_traced_memory()[1] / 2 ** 20
            tracemalloc.stop()
        out.update(tempos_s=tempos, cpu_s=cpus)
        np_ = sys.modules.get("numpy")
        out["numpy"] = getattr(np_, "__version__", None)
        if t.get("metricas"):
            out["metricas"] = _carregar(t["metricas"], "metricas")(entrada, saida)
        if t.get("foto") and i == 0:
            # a foto: o comportamento completo do candidato, declarado pela IA (foto(entrada, saida)), determinístico, com hash;
            # as métricas podem ser recalculadas dela sem rodar o candidato de novo
            foto = _carregar(t["foto"], "foto")(entrada, saida)
            b = json.dumps(foto, sort_keys=True, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)).encode()
            out["foto_sha256"] = hashlib.sha256(b).hexdigest()
            out["foto_b64"] = base64.b64encode(zlib.compress(b, 6)).decode()
        out["oraculos"] = []
        for o in t.get("oraculos", []):
            try:
                r = _carregar(o, "conferir")(entrada, saida)
                ok, det = r if isinstance(r, tuple) else (bool(r), "")
                out["oraculos"].append({"ok": bool(ok), "detalhe": str(det)[:300]})
            except Exception as e:  # noqa: BLE001
                out["oraculos"].append({"ok": False, "detalhe": f"o oráculo quebrou: {type(e).__name__}: {e}"[:300]})
    except Exception:  # noqa: BLE001
        out["erro"] = traceback.format_exc(limit=3)[-1200:]
    return out


def medir(caminho):
    with open(caminho, encoding="utf-8") as f:
        t = json.load(f)
    rodadas = []
    for i in range(int(t.get("rodadas", 3))):
        # o meio de medida fixado: uma thread na álgebra do numpy, senão as threads ociosas inflam o tempo de CPU do processo (o mapa
        # independente mediu de 1,7 a 1,9 vezes na VPS) e punem quem calcula em lote
        amb = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
        r = subprocess.run([sys.executable, "-B", os.path.abspath(__file__), "rodada", caminho, str(i)], capture_output=True, text=True,
                           timeout=float(t.get("tempo_limite_s", 300)), env=amb)
        try:
            rodadas.append(json.loads(r.stdout.strip().splitlines()[-1]))
        except Exception:  # noqa: BLE001
            rodadas.append({"indice": i, "erro": (r.stderr or "sem saída")[-800:]})
    erros = [x["erro"] for x in rodadas if "erro" in x]
    if erros:
        return {"erro": erros[0]}
    todos = sorted(s for x in rodadas for s in x["tempos_s"])
    medianas = [sorted(x["tempos_s"])[len(x["tempos_s"]) // 2] for x in rodadas]
    p95s = [sorted(x["tempos_s"])[int(0.95 * (len(x["tempos_s"]) - 1))] for x in rodadas]
    mets = rodadas[0].get("metricas") or {}
    foto = {k: rodadas[0][k] for k in ("foto_sha256", "foto_b64") if k in rodadas[0]}
    cpu_med = [sorted(x["cpu_s"])[len(x["cpu_s"]) // 2] for x in rodadas]
    cpu_todos = sorted(c for x in rodadas for c in x["cpu_s"])
    return {"tempo_mediana_s": todos[len(todos) // 2], "tempo_mediana_s_intervalo": [min(medianas), max(medianas)],
            "cpu_mediana_s": cpu_todos[len(cpu_todos) // 2], "cpu_mediana_s_intervalo": [min(cpu_med), max(cpu_med)],
            "tempo_p95_s": todos[int(0.95 * (len(todos) - 1))], "tempo_p95_s_intervalo": [min(p95s), max(p95s)],
            "pico_memoria_mb": max(x["pico_memoria_mb"] for x in rodadas if "pico_memoria_mb" in x),
            "oraculos_ok": all(o["ok"] for x in rodadas for o in x["oraculos"]),
            "oraculos": rodadas[0]["oraculos"], "metricas": mets, "python": sys.version.split()[0], "threads_do_blas": 1,
            "numpy": rodadas[0].get("numpy"), **foto}


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "rodada":
        with open(a[1], encoding="utf-8") as f:
            print(json.dumps(rodada(json.load(f), int(a[2]))))
    else:
        print(json.dumps(medir(a[1])))
