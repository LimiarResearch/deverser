# -*- coding: utf-8 -*-
import numpy as np

def largura(n):
    return max(1, (int(n) - 1).bit_length())

def bits_da_unidade(n):
    return 2 * largura(n)

def codificar(n, rede):
    w = largura(n)
    m = len(rede)
    if m == 0:
        return np.zeros(0, np.uint8)
    a = np.asarray(rede, np.int64).reshape(m, 2)
    pos = np.arange(w - 1, -1, -1)
    bi = a[:, 0:1] >> pos[None, :] & 1
    bj = a[:, 1:2] >> pos[None, :] & 1
    return np.concatenate([bi, bj], axis=1).reshape(-1).astype(np.uint8)

def valores(n, bits):
    w = largura(n)
    b = np.asarray(bits, np.int64).reshape(-1, 2, w)
    pesos = 1 << np.arange(w - 1, -1, -1)
    return ((b[:, 0, :] * pesos).sum(1), (b[:, 1, :] * pesos).sum(1))

def decodificar(n, bits):
    w = largura(n)
    bits = np.asarray(bits)
    if len(bits) % (2 * w) != 0:
        return None
    if len(bits) == 0:
        return []
    i, j = valores(n, bits)
    if (i >= n).any() or (j >= n).any() or (i == j).any():
        return None
    lo, hi = (np.minimum(i, j), np.maximum(i, j))
    return [(int(a), int(b)) for a, b in zip(lo, hi)]

def e_concorrente(n, bits):
    return decodificar(n, bits) is not None

def inteiros_das_unidades(n, rede):
    w = largura(n)
    a = np.asarray(rede, np.int64).reshape(-1, 2)
    return a[:, 0] << w | a[:, 1]
