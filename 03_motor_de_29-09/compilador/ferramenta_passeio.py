"""Ferramenta declarada do executor (emenda 2 do motor, 29/09/2026, pedida por Gabriel): o passeio pelo grafo de flips compilado em C.

O código do candidato continua sem os, subprocess nem open. Ele pode importar só este módulo, e este módulo só roda o binário cujo
caminho e cujo sha256 foram declarados por quem lançou o motor (FERRAMENTA_PASSEIO e FERRAMENTA_PASSEIO_SHA256). Qualquer outro
binário, ou um binário mudado depois da declaração, é recusado. Os argumentos são conferidos pelo tipo antes de ir para a linha de comando.
"""
import hashlib
import json
import os
import subprocess
import tempfile


def _binario():
    caminho, esperado = os.environ.get("FERRAMENTA_PASSEIO"), os.environ.get("FERRAMENTA_PASSEIO_SHA256")
    if not caminho or not esperado:
        raise RuntimeError("ferramenta não declarada: FERRAMENTA_PASSEIO e FERRAMENTA_PASSEIO_SHA256")
    with open(caminho, "rb") as f:
        visto = hashlib.sha256(f.read()).hexdigest()
    if visto != esperado:
        raise RuntimeError(f"o binário mudou depois da declaração: sha256 {visto[:12]} contra {esperado[:12]}")
    return caminho


def disponivel():
    try:
        _binario()
        return True
    except (RuntimeError, OSError):
        return False


def passear(n, inicio, alvo, segundos, semente, plato, chance_mais, folga, reinicio, orbita=0.0):
    b = _binario()
    n, alvo, semente, plato, folga = int(n), int(alvo), int(semente), int(plato), int(folga)
    segundos, chance_mais, reinicio, orbita = float(segundos), float(chance_mais), float(reinicio), float(orbita)
    if not (2 <= n <= 5 and 0 < segundos <= 86400 and len(inicio) <= 160):
        raise ValueError("argumentos fora da faixa da ferramenta")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(str(len(inicio)) + "\n" + "".join(f"{int(a)} {int(b_)} {int(c)}\n" for a, b_, c in inicio))
    try:
        out = subprocess.run([b, str(n), str(alvo), str(segundos), str(semente), str(plato), str(chance_mais), str(folga), str(reinicio), f.name, str(orbita)],
                             capture_output=True, text=True, timeout=segundos + 300)
    finally:
        os.unlink(f.name)
    return json.loads(out.stdout)
