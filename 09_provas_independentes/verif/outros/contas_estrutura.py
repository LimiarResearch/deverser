# -*- coding: utf-8 -*-
"""Mostra, pela arvore sintatica, o que cada funcao conta*() e main() da conta 15 chama (sem executar nada).
Uso: python3 -I contas_estrutura.py <pasta 07_conta_15/codigo>"""
import ast
import os
import sys

pasta = sys.argv[1]
FILTRO = ('print', 'np.', 'float', 'int', 'len', 'max', 'min', 'sum', 'range', 'round', 'sorted', 'enumerate', 'zip',
          'list', 'abs', 'dict', 'tuple', 'set', 'str', 'any', 'all', 'sqrt', 'log', 'exp', 'erf', 'ceil', 'math')
for f in sorted(os.listdir(pasta)):
    t = ast.parse(open(os.path.join(pasta, f), encoding='utf-8').read())
    for n in t.body:
        if isinstance(n, ast.FunctionDef) and (n.name.startswith('conta') or n.name == 'main'):
            src = ast.unparse(n)
            chamadas = sorted({ast.unparse(c.func) for c in ast.walk(n) if isinstance(c, ast.Call)})
            outras = [c for c in chamadas if not c.startswith(FILTRO)]
            prints = sum(1 for c in ast.walk(n) if isinstance(c, ast.Call) and ast.unparse(c.func) == 'print')
            aleat = any(k in src for k in ('rng', 'random'))
            print(f'{f:24s} {n.name:8s} prints={prints:3d} usa_aleatorio={aleat} outras_chamadas={outras}')
