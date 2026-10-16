"""O artefato e a proveniência: o que foi criado, de quê, por qual código, com quais testes e limites. Mudar D ou Π não apaga nada: cada
criação grava a sua pasta com o manifesto."""
import glob
import hashlib
import json
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def sha(caminho):
    with open(caminho, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def hash_do_codigo():
    h = hashlib.sha256()
    for p in sorted(glob.glob(os.path.join(RAIZ, "bancada", "**", "*.py"), recursive=True)):
        with open(p, "rb") as f:
            h.update(os.path.relpath(p, RAIZ).replace("\\", "/").encode() + b"\0" + f.read())
    return h.hexdigest()


def manifesto(pasta, D, Pi, extras=None):
    """Grava manifesto.json na pasta: os hashes de D, de Π, do código e de todo arquivo da pasta."""
    arquivos = {}
    for p in sorted(glob.glob(os.path.join(pasta, "**", "*"), recursive=True)):
        if os.path.isfile(p) and not p.endswith("manifesto.json"):
            arquivos[os.path.relpath(p, pasta).replace("\\", "/")] = sha(p)
    m = {"d_hash": D.hash(), "d_versao": D.versao, "pi_hash": Pi.hash(), "pi_versao": Pi.versao, "codigo": hash_do_codigo(),
         "arquivos": arquivos, **(extras or {})}
    with open(os.path.join(pasta, "manifesto.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    return m
