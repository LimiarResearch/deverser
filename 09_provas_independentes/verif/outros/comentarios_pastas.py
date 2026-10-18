# -*- coding: utf-8 -*-
"""Conta comentarios e docstrings dos .py de cada pasta e comentarios do C/C++ (so leitura).
Uso: python3 -I comentarios_pastas.py <main_ro>"""
import ast
import io
import os
import re
import sys
import tokenize

R = sys.argv[1]
for pasta in ('03_motor_de_29-09', '04_maquina_do_dever_ser_selecao', '05_tear_selecao', '07_conta_15', '08_c_estrela_3'):
    n_py = n_com = n_doc = 0
    com_arq = []
    for dp, _, fs in os.walk(os.path.join(R, pasta)):
        for f in fs:
            c = os.path.join(dp, f)
            if f.endswith('.py'):
                s = open(c, encoding='utf-8').read()
                n_py += 1
                k = sum(1 for t in tokenize.generate_tokens(io.StringIO(s).readline) if t.type == tokenize.COMMENT and not t.string.startswith('# -*- coding'))
                d = 0
                for no in ast.walk(ast.parse(s)):
                    if isinstance(no, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and ast.get_docstring(no, clean=False) is not None:
                        d += 1
                n_com += k
                n_doc += d
                if k or d:
                    com_arq.append((os.path.relpath(c, R), k, d))
            elif f.endswith(('.c', '.cpp', '.h')):
                s = open(c, encoding='utf-8', errors='replace').read()
                bl = len(re.findall(r'/\*.*?\*/', s, re.S))
                ln = len(re.findall(r'(?<!:)//[^\n]*', s))
                com_arq.append((os.path.relpath(c, R), 'C: blocos /* */ = %d, linhas // = %d' % (bl, ln), ''))
    print(f'{pasta}: {n_py} .py; comentarios (fora a linha de codificacao) = {n_com}; docstrings = {n_doc}')
    for x in com_arq[:12]:
        print('   ', x)
    if len(com_arq) > 12:
        print('    ... mais', len(com_arq) - 12)
