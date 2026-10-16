# -*- coding: utf-8 -*-
import glob
import gzip
import json
import math
import os
import numpy as np
PASTA = 'resultado_inteiro_de_V'

def _simples(x):
    if isinstance(x, dict):
        return {str(k): _simples(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_simples(v) for v in x]
    if isinstance(x, np.ndarray):
        return _simples(x.tolist())
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x

class AvaliadorQueGuarda:

    def __init__(self, avaliador, pasta_da_corrida, codificacao, por_parte=2000):
        self.avaliador, self.cod, self.por_parte = (avaliador, codificacao, int(por_parte))
        self.pasta = os.path.join(pasta_da_corrida, PASTA)
        os.makedirs(self.pasta, exist_ok=True)
        self.proxima = len(glob.glob(os.path.join(self.pasta, 'parte_*.jsonl.gz')))
        self.buffer, self.guardados = ([], 0)

    def __getattr__(self, nome):
        if nome == 'avaliador':
            raise AttributeError(nome)
        return getattr(self.avaliador, nome)

    def medir(self, lista_de_bits):
        res = self.avaliador.medir(lista_de_bits)
        for b, r in zip(lista_de_bits, res):
            c = self.cod.canonizar(b)
            self.buffer.append({'chave': int(self.cod.chave(c if c is not None else b)), 'resultado': _simples(r)})
        self.guardados += len(res)
        if len(self.buffer) >= self.por_parte:
            self.gravar()
        return res

    def gravar(self):
        if not self.buffer:
            return
        caminho = os.path.join(self.pasta, f'parte_{self.proxima:05d}.jsonl.gz')
        tmp = caminho + '.tmp'
        with gzip.open(tmp, 'wt', encoding='utf-8') as f:
            for linha in self.buffer:
                f.write(json.dumps(linha, ensure_ascii=False) + '\n')
        os.replace(tmp, caminho)
        self.proxima += 1
        self.buffer = []

    def fechar(self):
        self.gravar()
        fechar = getattr(self.avaliador, 'fechar', None)
        if callable(fechar):
            fechar()

def ler(pasta_da_corrida):
    out = {}
    for p in sorted(glob.glob(os.path.join(pasta_da_corrida, PASTA, 'parte_*.jsonl.gz'))):
        with gzip.open(p, 'rt', encoding='utf-8') as f:
            for linha in f:
                d = json.loads(linha)
                out.setdefault(int(d['chave']), []).append(d['resultado'])
    return out

def nomes_das_medidas(resultados):
    nomes = set()
    for r in resultados:
        for vida in r.get('por_vida') or []:
            nomes.update((k for k, v in vida.items() if isinstance(v, (int, float)) and (not isinstance(v, bool))))
    return sorted(nomes)

def medidas_por_vida(resultado, nomes):
    vidas = resultado.get('por_vida') or []
    m = np.full((len(vidas), len(nomes)), np.nan, np.float32)
    for i, vida in enumerate(vidas):
        for j, n in enumerate(nomes):
            v = vida.get(n)
            if isinstance(v, (int, float)) and (not isinstance(v, bool)) and math.isfinite(float(v)):
                m[i, j] = float(v)
    return m
