# -*- coding: utf-8 -*-
import math
import numpy as np
from experimentos import rede_de_fotos as RF
ARQUITETURAS = ((16, (128, 96)), (12, (96, 64)), (16, (128, 64)), (12, (64, 48)), (8, (96, 64)))
K_DO_DESACORDO = 5

class ConjuntoDeRedes:

    def __init__(self, membros):
        if not membros:
            raise ValueError('um conjunto precisa de ao menos uma rede')
        self.membros = list(membros)

    @classmethod
    def novo(cls, geo, n_clausulas, n_pred, membros, semente, reducao=1.0, **kw):
        r = max(float(reducao), 0.001)

        def esc(x, minimo=4):
            return max(minimo, int(round(x * r)))
        out = []
        for k in range(int(membros)):
            d_f, (h1, h2) = ARQUITETURAS[k % len(ARQUITETURAS)]
            out.append(RF.RedeUnica(geo, n_clausulas, n_pred, d_f=esc(d_f, 2), h=(esc(h1), esc(h2)), d_c=esc(96), d_w=esc(96), d_b=esc(64), d_e=esc(16, 2), d_vh=esc(96), semente=semente + 11 + 1009 * k, **kw))
        return cls(out)

    def __len__(self):
        return len(self.membros)

    def com_membro(self, j, rede):
        ms = list(self.membros)
        ms[int(j) % len(ms)] = rede
        return ConjuntoDeRedes(ms)

    def n_parametros(self):
        return sum((m.n_parametros() for m in self.membros))

    def estado(self):
        return {'conjunto': [m.estado() for m in self.membros]}

    @classmethod
    def de_estado(cls, geo, e):
        return cls([RF.RedeUnica.de_estado(geo, x) for x in e['conjunto']])

def teste_da_alocacao(desacordos, tetos, minimo=20):
    des, teto = (np.asarray(desacordos, float), np.asarray(tetos, float))
    if len(des) < minimo:
        return {'pulou': 'poucas piscinas', 'piscinas': int(len(des))}
    med = float(np.median(des))
    alta = des > med if (des > med).sum() >= 2 and (des <= med).sum() >= 2 else des >= med
    if alta.sum() < 2 or (~alta).sum() < 2:
        return {'pulou': 'o desacordo não separa as piscinas', 'piscinas': int(len(des))}
    a, b = (teto[alta], teto[~alta])
    dif = float(a.mean() - b.mean())
    ep = math.sqrt(float(a.var(ddof=1)) / len(a) + float(b.var(ddof=1)) / len(b))
    razao = float(a.mean() / b.mean()) if a.mean() > 0 and b.mean() > 0 else None
    return {'piscinas': int(len(des)), 'desacordo_mediano': round(med, 6), 'teto_na_metade_de_mais_desacordo': round(float(a.mean()), 5), 'teto_na_metade_de_menos_desacordo': round(float(b.mean()), 5), 'razao_dos_tetos': None if razao is None else round(razao, 3), 'diferenca': round(dif, 5), 'erro_padrao': round(ep, 5), 'vale': bool(dif - 2 * ep > 0)}
