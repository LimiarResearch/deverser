"""O trabalho longo fora da caixa: um comando que a IA declarou (um treino, uma simulação pesada, uma biblioteca grande que a caixa não
carrega), rodado só depois de o criador autorizar aquele trabalho exato.

A autorização vale para um hash: o comando, o hash de cada arquivo que vai junto, o teto de tempo, o teto de memória e as saídas
esperadas. Qualquer mudança em qualquer um deles é outro trabalho e pede outra autorização. O trabalho roda numa pasta própria, com as
permissões do usuário e fora da caixa: por isso a autorização é do criador, e não do motor nem da IA. As saídas voltam com o SHA-256.

  {"nome": "treino_da_cabeca", "comando": ["{python}", "treinar.py", "--epocas", "3"], "arquivos": {"treinar.py": "..."},
   "teto_s": 7200, "teto_mb": 8000, "saidas": ["metricas.json", "pesos.safetensors"], "descricao": "..."}

"{python}" vira o Python que roda o motor. O teto de memória só é aplicado em sistemas POSIX (RLIMIT_AS); o resultado diz se foi.
"""
import hashlib
import json
import os
import subprocess
import sys
import time


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def descrever(t):
    """A forma canônica do trabalho e o hash que o criador autoriza."""
    arqs = {os.path.basename(n): _sha(v.encode("utf-8")) for n, v in sorted((t.get("arquivos") or {}).items())}
    d = {"comando": [str(c) for c in t["comando"]], "arquivos": arqs, "teto_s": int(t.get("teto_s", 3600)),
         "teto_mb": int(t["teto_mb"]) if t.get("teto_mb") else None, "saidas": sorted(os.path.basename(s) for s in t.get("saidas", [])),
         "descricao": t.get("descricao", "")}
    return d, _sha(json.dumps(d, sort_keys=True, ensure_ascii=False).encode("utf-8"))


def rodar(t, pasta, autorizados):
    d, h = descrever(t)
    if h not in autorizados:
        raise PermissionError(f"trabalho sem autorização do criador: {h[:12]}")
    wd = os.path.join(pasta, "trabalhos", h[:16])
    os.makedirs(wd, exist_ok=True)
    for n, v in (t.get("arquivos") or {}).items():
        with open(os.path.join(wd, os.path.basename(n)), "w", encoding="utf-8", newline="\n") as f:
            f.write(v)
    cmd = [sys.executable if c == "{python}" else c for c in d["comando"]]
    pre = None
    if d["teto_mb"] and os.name == "posix":
        import resource
        lim = d["teto_mb"] * 2 ** 20
        pre = lambda: resource.setrlimit(resource.RLIMIT_AS, (lim, lim))  # noqa: E731
    t0 = time.perf_counter()
    with open(os.path.join(wd, "saida_padrao.txt"), "wb") as so, open(os.path.join(wd, "erros.txt"), "wb") as se:
        try:
            r = subprocess.run(cmd, cwd=wd, stdout=so, stderr=se, timeout=d["teto_s"], preexec_fn=pre)
            codigo, estourou = r.returncode, False
        except subprocess.TimeoutExpired:
            codigo, estourou = None, True
    seg = round(time.perf_counter() - t0, 2)
    saidas = {}
    for n in d["saidas"]:
        c = os.path.join(wd, n)
        if os.path.exists(c):
            with open(c, "rb") as f:
                saidas[n] = {"sha256": _sha(f.read()), "bytes": os.path.getsize(c)}
        else:
            saidas[n] = None
    with open(os.path.join(wd, "erros.txt"), encoding="utf-8", errors="replace") as f:
        erros = f.read()[-1500:]
    return {"hash": h, "ok": codigo == 0 and not estourou and all(saidas.values()), "codigo_de_saida": codigo, "estourou_o_tempo": estourou,
            "segundos": seg, "saidas": saidas, "pasta": wd, "erros_finais": erros,
            "teto_de_memoria": "aplicado (RLIMIT_AS)" if pre else ("não aplicado neste sistema" if d["teto_mb"] else "não pedido")}
