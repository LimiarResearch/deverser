# -*- coding: utf-8 -*-
import numpy as np
from experimentos import l_ser_lang as L
E = L.E
programa = L.programa

def _politica_por_confianca(alto=0.8, baixo=0.4):
    return dict(POL1=E('sub', E('k', c=baixo), 'conf'), POL2=E('sub', E('k', c=alto), 'conf'), rotulos={'POL1': 3, 'POL2': 1})

def _tecido(largura=64, lote=4, **extra):
    t = {'camadas': [largura], 'ativ': 'relu', 'lote': lote}
    t.update(extra)
    return t

def sgd(lr=0.05, largura=64, lote=4):
    pol = _politica_por_confianca()
    return programa(tecido=_tecido(largura, lote), W_SAIDA=E('mulk', 'P', c=lr), W_OCULTA=E('mulk', 'P', c=lr), RETRO=E('mul', 'T', E('thr', 's')), rotulos=pol.pop('rotulos'), **pol)

def ewc(lr=0.05, lam=2.0, beta=0.02, largura=64, lote=4, limiar=0.15):
    penal = E('mulk', E('mul', 'S1', E('sub', 'w', 'S2')), c=lam)
    regra = E('sub', E('mulk', 'P', c=lr), penal)
    imp = E('ema', 'S1', 'P2', c=beta)
    gate = E('thr', E('sub', E('sub', 'G1', 'G2'), E('k', c=limiar)))
    ancora = E('add', 'S2', E('mul', gate, E('sub', 'w', 'S2')))
    pol = _politica_por_confianca()
    return programa(tecido=_tecido(largura, lote, init_S2='copia_de_w'), W_SAIDA=regra, W_OCULTA=regra, RETRO=E('mul', 'T', E('thr', 's')), S1=imp, S2=ancora, G1=E('ema', 'g1', 'perda', c=0.05), G2=E('ema', 'g2', 'perda', c=0.002), rotulos=pol.pop('rotulos'), **pol)

def cbp(lr=0.05, largura=64, lote=4, eta=0.01, limiar=0.0005):
    contrib = E('mul', 'post', 'outn')
    util = E('ema', 'u1', contrib, c=eta)
    guarda = E('sub', E('k', c=limiar), 'u1')
    pol = _politica_por_confianca()
    return programa(tecido=_tecido(largura, lote, init_U1='zeros', cada=1), W_SAIDA=E('mulk', 'P', c=lr), W_OCULTA=E('mulk', 'P', c=lr), RETRO=E('mul', 'T', E('thr', 's')), U1=util, REINIT=guarda, rotulos=pol.pop('rotulos'), **pol)

def sp(lr=0.05, largura=64, lote=4, encolhe=0.0005, ruido=0.001):
    regra = E('add', E('sub', E('mulk', 'P', c=lr), E('mulk', 'w', c=encolhe)), E('mulk', 'xi', c=ruido))
    pol = _politica_por_confianca()
    return programa(tecido=_tecido(largura, lote), W_SAIDA=regra, W_OCULTA=regra, RETRO=E('mul', 'T', E('thr', 's')), rotulos=pol.pop('rotulos'), **pol)

def testemunhas(largura=64):
    return {'sgd': sgd(largura=largura), 'ewc': ewc(largura=largura), 'cbp': cbp(largura=largura), 'sp': sp(largura=largura)}

def testemunhas_em_bits(largura=64):
    return {nome: L.codificar_programa(p) for nome, p in testemunhas(largura).items()}
