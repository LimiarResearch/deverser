# -*- coding: utf-8 -*-
import json
import zlib
import numpy as np

def _mlp(r, d, h, c):
    return {'W1': r.normal(0, 1 / np.sqrt(d), (d, h)).astype(np.float32), 'b1': np.zeros(h, np.float32), 'W2': r.normal(0, 1 / np.sqrt(h), (h, c)).astype(np.float32), 'b2': np.zeros(c, np.float32)}

def _frente(P, X):
    H = np.maximum(0, X @ P['W1'] + P['b1'])
    return (H, H @ P['W2'] + P['b2'])

def _grad_lote(P, X, Y):
    H, Z = _frente(P, X)
    Z = Z - Z.max(axis=1, keepdims=True)
    E = np.exp(Z)
    Pr = E / E.sum(axis=1, keepdims=True)
    G = Pr.copy()
    G[np.arange(len(Y)), Y] -= 1
    G /= len(Y)
    GH = G @ P['W2'].T * (H > 0)
    return ({'W1': X.T @ GH, 'b1': GH.sum(0), 'W2': H.T @ G, 'b2': G.sum(0)}, H, Pr)

def _empacotar(obj):
    bufs = []

    def enc(o):
        if isinstance(o, np.ndarray):
            bufs.append(np.ascontiguousarray(o).tobytes())
            return {'__a': [len(bufs) - 1, list(o.shape), str(o.dtype)]}
        if isinstance(o, dict):
            return {str(k): enc(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [enc(v) for v in o]
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        return o
    cab = json.dumps({'o': enc(obj), 't': [len(b) for b in bufs]}).encode()
    return zlib.compress(len(cab).to_bytes(4, 'little') + cab + b''.join(bufs), 6)

def _desempacotar(b):
    raw = zlib.decompress(b)
    n = int.from_bytes(raw[:4], 'little')
    cab = json.loads(raw[4:4 + n].decode())
    pos, bufs = (4 + n, [])
    for t in cab['t']:
        bufs.append(raw[pos:pos + t])
        pos += t

    def dec(o):
        if isinstance(o, dict):
            if '__a' in o:
                k, forma, tipo = o['__a']
                return np.frombuffer(bufs[k], dtype=tipo).reshape(forma).copy()
            return {k: dec(v) for k, v in o.items()}
        if isinstance(o, list):
            return [dec(v) for v in o]
        return o
    return dec(cab['o'])

def _rodar(entrada, fabrica, restaurar):
    out = {'respostas': [], 'etiquetas': [], 'bytes_por_interrupcao': [], 'restauracao_fiel': [], 'diagnostico': []}
    d, c = (entrada['d_entrada'], entrada['classes'])
    for k, f in enumerate(entrada['fluxos']):
        a = fabrica(d, c, np.random.default_rng(100 + k))
        sombra = None
        ler, resp, etq, bts, fiel = (f['abrir'](), [], [], [], [])
        while True:
            ev = ler()
            if ev is None:
                break
            if ev[0] == 'treino':
                a.aprender(ev[1], ev[2])
                if sombra is not None:
                    sombra.aprender(ev[1], ev[2])
            elif ev[0] == 'sonda':
                p, e = a.prever(ev[1])
                if sombra is not None:
                    ps, es = sombra.prever(ev[1])
                    fiel.append(bool(np.array_equal(np.asarray(p), np.asarray(ps)) and np.array_equal(np.asarray(e), np.asarray(es))))
                    sombra = None
                resp.append(np.asarray(p, np.int8))
                etq.append(np.asarray(e, np.int8))
            else:
                b = a.estado()
                bts.append(len(b))
                sombra = a
                a = restaurar(b, d, c)
        out['respostas'].append(resp)
        out['etiquetas'].append(etq)
        out['bytes_por_interrupcao'].append(bts)
        out['restauracao_fiel'].append(fiel)
        if hasattr(a, 'diagnostico'):
            out['diagnostico'].append(a.diagnostico())
    return out

def _etiquetas_por_confianca(Pr, limiar_validado=0.8, limiar_investigar=0.4):
    m = Pr.max(1)
    return np.where(m >= limiar_validado, 0, np.where(m < limiar_investigar, 3, 1)).astype(np.int8)
