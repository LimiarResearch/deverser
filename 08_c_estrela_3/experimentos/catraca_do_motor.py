# -*- coding: utf-8 -*-
import functools
import hashlib
import inspect
import json
import math
import numpy as np
from experimentos import nivel3b_meta as M
FRACAO_CEGA_MINIMA = 0.25

def espaco_a_partir_de(cfg0, total_avaliado):
    pool0, k0 = (int(cfg0['pool']), int(cfg0['k_cega']))
    return {'pool': sorted({max(16, pool0 // 2), pool0, pool0 * 2}), 'k_cega': sorted({k for k in (k0 - 1, k0, k0 + 1, k0 + 2) if 1 <= k <= max(total_avaliado - 1, 1)} | {k0}), 'temperatura': sorted({0.7, 1.0, 1.4, float(cfg0['temperatura'])}), 'epsilon': sorted({0.05, 0.1, 0.2, float(cfg0['epsilon'])})}

def fracao_cega_total(K, total_avaliado, k_cega, n_bracos_de_controle=2):
    cegas = K + k_cega
    return cegas / float(K * n_bracos_de_controle + total_avaliado)

def cfg_valida(cfg, espaco, K, total_avaliado):
    return all((cfg[k] in espaco[k] for k in espaco)) and fracao_cega_total(K, total_avaliado, int(cfg['k_cega'])) >= FRACAO_CEGA_MINIMA

def vetor_cfg(cfg, espaco):
    return np.array([espaco[k].index(cfg[k]) / max(len(espaco[k]) - 1, 1) for k in sorted(espaco)], float)

class MetaDeConfig:

    def __init__(self, espaco, largura=0.5, premio=0.05, prior=1.0):
        self.espaco, self.largura, self.premio, self.prior = (espaco, largura, premio, prior)

    def vizinha(self, cfg, g):
        nova = dict(cfg)
        chaves = sorted(self.espaco)
        for k in g.choice(chaves, int(g.integers(1, 3)), replace=False):
            opcoes = [v for v in self.espaco[k] if v != cfg[k]]
            if opcoes:
                nova[k] = opcoes[int(g.integers(len(opcoes)))]
        return nova

    def notas(self, H, propostas):
        V = np.stack([vetor_cfg(p, self.espaco) for p in propostas])
        if not H:
            return np.zeros(len(propostas))
        Vh = np.stack([vetor_cfg(e['cfg_candidata'], self.espaco) for e in H])
        d = np.array([e['d_dev'] for e in H], float)
        K = np.exp(-((V[:, None, :] - Vh[None, :, :]) ** 2).sum(-1) / (2 * self.largura ** 2))
        soma = K.sum(1)
        return (K * d[None, :]).sum(1) / (soma + self.prior) - self.premio / (1.0 + soma)

    def propor(self, H, cfg, g, anterior=None, amostras=16, fracao_cega=FRACAO_CEGA_MINIMA, p_volta=0.15, valida=None):
        if anterior is not None and anterior != cfg and (g.random() < p_volta):
            return (dict(anterior), False, 0.0, True)
        props = []
        for _ in range(8 * amostras):
            p = self.vizinha(cfg, g)
            if p != cfg and (valida is None or valida(p)):
                props.append(p)
            if len(props) >= amostras:
                break
        if not props:
            return (dict(cfg), False, 0.0, False)
        notas = self.notas(H, props)
        if g.random() < fracao_cega:
            i = int(g.integers(len(props)))
            return (props[i], True, float(notas[i]), False)
        i = int(np.argmin(notas))
        return (props[i], False, float(notas[i]), False)
ERRO_ACUMULADO_MAXIMO = 0.05
FOLGA_MINIMA = 2.0

def _beta_continuada(a, b, x):
    pequeno = 1e-300
    qab, qap, qam = (a + b, a + 1.0, a - 1.0)
    c, d = (1.0, 1.0 - qab * x / qap)
    d = 1.0 / (d if abs(d) > pequeno else pequeno)
    h = d
    for m in range(1, 400):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > pequeno else pequeno)
        c = 1.0 + aa / c
        c = c if abs(c) > pequeno else pequeno
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > pequeno else pequeno)
        c = 1.0 + aa / c
        c = c if abs(c) > pequeno else pequeno
        de = d * c
        h *= de
        if abs(de - 1.0) < 1e-14:
            break
    return h

def _beta_incompleta(a, b, x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lb = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lb + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _beta_continuada(a, b, x) / a
    return 1.0 - bt * _beta_continuada(b, a, 1.0 - x) / b

def cauda_t(t, df):
    return 0.5 * _beta_incompleta(df / 2.0, 0.5, df / (df + float(t) * float(t)))

def quantil_t(p, df):
    lo, hi = (0.0, 1.0)
    while cauda_t(hi, df) > p and hi < 1000000000000.0:
        hi *= 2.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if cauda_t(mid, df) > p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)

def nivel_da_proposta(n, total=ERRO_ACUMULADO_MAXIMO):
    n = max(int(n), 1)
    return float(total) / (n * (n + 1.0))

@functools.lru_cache(maxsize=None)
def folga_da_proposta(n, K, total=ERRO_ACUMULADO_MAXIMO, portas=2):
    p = nivel_da_proposta(n, total) ** (1.0 / max(int(portas), 1))
    return max(FOLGA_MINIMA, quantil_t(p, max(int(K) - 1, 1)))

def passa_com_folga(d, minimo, folga):
    r = M.resumo(d)
    return bool(r['K'] >= minimo and r['media'] + folga * r['erro_padrao'] < 0)

def decidir(d_dev, d_conf, minimo_dev, minimo_conf, n_proposta=1):
    rd = M.resumo(d_dev)
    folga_dev = folga_da_proposta(n_proposta, len(d_dev))
    ok_dev = passa_com_folga(d_dev, minimo_dev, folga_dev)
    medidos = len(d_conf) > 0
    rr = M.resumo(d_conf)
    folga_conf = folga_da_proposta(n_proposta, len(d_conf))
    ok_conf = bool(medidos and passa_com_folga(d_conf, minimo_conf, folga_conf))

    def r6(x):
        return round(x, 6) if np.isfinite(x) else None
    motivo = '' if ok_dev and ok_conf else 'a porta pareada (desenvolvimento)' if not ok_dev else 'o ganho não passou na confirmação (moldes de uso único)' if medidos else 'os moldes de confirmação não foram medidos'
    return {'n_da_proposta': int(n_proposta), 'nivel_da_proposta': round(nivel_da_proposta(n_proposta), 8), 'K_dev': rd['K'], 'd_dev': r6(rd['media']), 'se_dev': r6(rd['erro_padrao']), 'folga_dev': round(folga_dev, 4), 'passa_a_porta': bool(ok_dev), 'K_conf': rr['K'], 'd_conf': r6(rr['media']) if medidos else None, 'se_conf': r6(rr['erro_padrao']) if medidos else None, 'folga_conf': round(folga_conf, 4) if medidos else None, 'passa_na_confirmacao': ok_conf, 'adota': bool(ok_dev and ok_conf), 'motivo_da_recusa': motivo}

def selo_do_que_nao_muda(extra=None):
    partes = [inspect.getsource(M.passa_a_porta), inspect.getsource(M.resumo), inspect.getsource(passa_com_folga), inspect.getsource(folga_da_proposta), inspect.getsource(nivel_da_proposta), inspect.getsource(quantil_t), inspect.getsource(cauda_t), inspect.getsource(_beta_incompleta), inspect.getsource(_beta_continuada), inspect.getsource(decidir), repr(FRACAO_CEGA_MINIMA), repr(ERRO_ACUMULADO_MAXIMO), repr(FOLGA_MINIMA), json.dumps(extra, sort_keys=True, default=str)]
    return hashlib.blake2b('\n'.join(partes).encode('utf-8'), digest_size=8).hexdigest()
