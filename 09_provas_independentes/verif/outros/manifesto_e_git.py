# -*- coding: utf-8 -*-
"""Confere o MANIFESTO.sha256 contra a copia e a copia contra o commit a28eec9 do clone.
Uso: python3 -I manifesto_e_git.py <main_ro> <clone hist>
Nada do repositorio e executado; o git so le objetos (ls-tree, cat-file)."""
import hashlib
import os
import subprocess
import sys

ro, hist = sys.argv[1], sys.argv[2]
man = {}
for l in open(os.path.join(ro, 'MANIFESTO.sha256'), encoding='utf-8'):
    l = l.rstrip('\n')
    if not l.strip():
        continue
    h, nome = l.split('  ', 1)
    man[nome] = h
arquivos = set()
for dp, _, fs in os.walk(ro):
    for f in fs:
        arquivos.add(os.path.relpath(os.path.join(dp, f), ro).replace(os.sep, '/'))
ok = ruim = 0
for nome, h in man.items():
    c = os.path.join(ro, nome)
    if not os.path.exists(c):
        print('  falta na copia:', nome)
        continue
    if hashlib.sha256(open(c, 'rb').read()).hexdigest() == h:
        ok += 1
    else:
        ruim += 1
        print('  sha256 difere:', nome)
print(f'MANIFESTO: {len(man)} linhas; conferem {ok}; diferem {ruim}')
print('  arquivos da copia fora do manifesto:', sorted(arquivos - set(man)))
print('  linhas do manifesto sem arquivo:', sorted(set(man) - arquivos))


def git(*a):
    return subprocess.run(['git', '-C', hist] + list(a), capture_output=True, text=True, check=True).stdout


arv = {}
for l in git('ls-tree', '-r', 'a28eec9').splitlines():
    meta, nome = l.split('\t', 1)
    if nome.startswith('"'):
        nome = nome.strip('"').encode('latin1').decode('unicode_escape').encode('latin1').decode('utf-8')
    arv[nome] = meta.split()[2]
dif = []
for nome, blob in arv.items():
    c = os.path.join(ro, nome)
    if not os.path.exists(c):
        dif.append(('falta', nome))
        continue
    dados = open(c, 'rb').read()
    h = hashlib.sha1(b'blob %d\0' % len(dados) + dados).hexdigest()
    if h != blob:
        dif.append(('difere', nome))
print(f'a28eec9: {len(arv)} arquivos na arvore; diferencas com a copia: {dif or "nenhuma"}; arquivos so na copia: {sorted(arquivos - set(arv))}')
for c in ('66cd55c', '61c5c4a', 'f571ac7', '3ba299b', 'a28eec9', 'e12d65d', '316ea4f'):
    n = len(git('ls-tree', '-r', '--name-only', c).splitlines())
    print(f'  commit {c}: {n} arquivos')
