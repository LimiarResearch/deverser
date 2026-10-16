# -*- coding: utf-8 -*-
import glob
import json
import math
import os
import zipfile
import numpy as np
from experimentos import nivel3b_aprendiz as A
OPERADORES = ('nova', 'alargar', 'refinar', 'degrau')
LARGURAS = (8, 16, 32, 64, 128)
CLIP_IPS = 8.0

class Banco:

    def __init__(self, teto=600, semente=0):
        self.teto = int(teto)
        self.g = np.random.default_rng(semente + 555)
        self.itens = []
        self.vistas = 0

    def __len__(self):
        return len(self.itens)

    def adicionar(self, X, a, prop, y, n, seq):
        self.vistas += 1
        it = (np.asarray(X, np.float16).copy(), int(a), float(prop), float(y), int(n), int(seq))
        if len(self.itens) < self.teto:
            self.itens.append(it)
        else:
            j = int(self.g.integers(self.vistas))
            if j < self.teto:
                self.itens[j] = it

    def salvar(self, caminho):
        tmp = caminho + '.tmp.npz'
        if self.itens:
            Xc = np.concatenate([it[0] for it in self.itens])
            off = np.cumsum([0] + [len(it[0]) for it in self.itens])
        else:
            Xc, off = (np.zeros((0, A.N_CARACTERISTICAS), np.float16), np.zeros(1, int))
        np.savez_compressed(tmp, Xc=Xc, off=off, a=np.array([it[1] for it in self.itens], int), prop=np.array([it[2] for it in self.itens], float), y=np.array([it[3] for it in self.itens], float), n=np.array([it[4] for it in self.itens], int), seq=np.array([it[5] for it in self.itens], int), vistas=np.asarray([self.vistas]))
        os.replace(tmp, caminho)

    @staticmethod
    def ler(caminho):
        z = np.load(caminho)
        Xc, off = (z['Xc'], z['off'])
        return [(Xc[off[i]:off[i + 1]], int(z['a'][i]), float(z['prop'][i]), float(z['y'][i]), int(z['n'][i]), int(z['seq'][i])) for i in range(len(z['y']))]

    @classmethod
    def carregar(cls, caminho, teto=600, semente=0):
        b = cls(teto, semente)
        if caminho and os.path.exists(caminho):
            try:
                b.itens = Banco.ler(caminho)[:teto]
                b.vistas = max(len(b.itens), int(np.load(caminho)['vistas'][0]))
            except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
                pass
        return b

def ler_externos(pasta, proprio, teto=900, g=None):
    itens = []
    for c in sorted(glob.glob(os.path.join(pasta, 'banco_*.npz'))):
        if c.endswith('.tmp.npz') or os.path.basename(c) == f'banco_{proprio}.npz':
            continue
        try:
            itens.extend(Banco.ler(c))
        except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
            continue
    if len(itens) > teto:
        g = g or np.random.default_rng(0)
        itens = [itens[i] for i in g.choice(len(itens), teto, replace=False)]
    return itens

def particoes(proprios, externos):
    ordem = sorted(proprios, key=lambda it: it[5])
    n = len(ordem)
    return (ordem[n // 2:], ordem[:int(n * 0.3)] + list(externos))

def empilhar(itens):
    if not itens:
        return (np.zeros((0, A.N_CARACTERISTICAS), np.float32), np.zeros(1, int))
    return (np.concatenate([it[0] for it in itens]).astype(np.float32), np.cumsum([0] + [len(it[0]) for it in itens]))

def cortar(v, off):
    return [v[off[i]:off[i + 1]] for i in range(len(off) - 1)]

def pesos_de_notas(notas, itens, tau, fracao_cega=A.FRACAO_CEGA, clip=CLIP_IPS):
    w = np.zeros(len(itens))
    for i, it in enumerate(itens):
        m = len(notas[i])
        pg = A.softmax_de_menor(notas[i], tau)
        w[i] = min((fracao_cega / m + (1 - fracao_cega) * pg[it[1]]) / max(it[2], 1e-09), clip)
    return w

def diferenca_pareada(w_nova, w_atual, itens):
    return (np.asarray(w_nova) - np.asarray(w_atual)) * np.array([it[3] for it in itens])

def resumo(d):
    d = np.asarray(d, float)
    K = len(d)
    if K == 0:
        return {'K': 0, 'media': 0.0, 'erro_padrao': float('inf')}
    return {'K': K, 'media': float(d.mean()), 'erro_padrao': float(d.std(ddof=1) / math.sqrt(K)) if K > 1 else float('inf')}

def passa_a_porta(d_dev, minimo=40):
    r = resumo(d_dev)
    return r['K'] >= minimo and r['media'] + 2 * r['erro_padrao'] < 0

def passa_a_retencao(d_ret, minimo=20):
    r = resumo(d_ret)
    return r['K'] >= minimo and r['media'] - 2 * r['erro_padrao'] <= 0

def ganho_de_decisao_contra_o_cego(w_atual, itens):
    m = np.array([len(it[0]) for it in itens], float)
    prop = np.array([it[2] for it in itens], float)
    w_cego = np.minimum(1.0 / np.maximum(m, 1) / np.maximum(prop, 1e-09), CLIP_IPS)
    return resumo((np.asarray(w_atual) - w_cego) * np.array([it[3] for it in itens]))

def amostrar_params(g, n_membros):
    op = OPERADORES[int(g.integers(len(OPERADORES)))]
    p = {'op': op}
    if op == 'nova':
        prof = int(g.integers(1, 4))
        p['esc'] = [int(LARGURAS[int(g.integers(len(LARGURAS)))]) for _ in range(prof)]
        p['lr'] = float(10 ** g.uniform(-2.5, -1.3))
        p['l2'] = float(g.choice([0.0, 0.0001, 0.001]))
    elif op == 'degrau':
        p['esc'] = [int(g.choice([8, 16, 32]))]
        p['lr'] = float(10 ** g.uniform(-2.7, -1.5))
        p['l2'] = float(g.choice([0.0, 0.0001]))
    else:
        p['membro'] = int(g.integers(max(n_membros, 1)))
        p['extra'] = int(g.choice([4, 8, 16])) if op == 'alargar' else 0
        p['lr'] = float(10 ** g.uniform(-3, -1.7))
        p['l2'] = 0.0
    return p

def vetor(p):
    esc = p.get('esc', [])
    return np.array([p['op'] == 'nova', p['op'] == 'alargar', p['op'] == 'refinar', p['op'] == 'degrau', len(esc) / 3.0, math.log2(sum(esc)) / 8.0 if esc else 0.0, -math.log10(p['lr']) / 3.0, float(p.get('l2', 0) > 0), p.get('extra', 0) / 16.0], float)

class MetaModelo:

    def __init__(self, largura=0.6, premio=0.004, prior=1.0):
        self.largura, self.premio, self.prior = (largura, premio, prior)

    def notas(self, H, propostas):
        V = np.stack([vetor(p) for p in propostas])
        if not H:
            return (np.zeros(len(propostas)), np.zeros(len(propostas)))
        Vh = np.stack([vetor(e['params']) for e in H])
        d = np.array([e['d_dev'] for e in H], float)
        K = np.exp(-((V[:, None, :] - Vh[None, :, :]) ** 2).sum(-1) / (2 * self.largura ** 2))
        soma = K.sum(1)
        return ((K * d[None, :]).sum(1) / (soma + self.prior) - self.premio / (1.0 + soma), soma)

    def propor(self, H, g, n_membros, amostras=16, fracao_cega=A.FRACAO_CEGA):
        props = [amostrar_params(g, n_membros) for _ in range(amostras)]
        notas, _ = self.notas(H, props)
        if g.random() < fracao_cega:
            i = int(g.integers(amostras))
            return (props[i], True, float(notas[i]))
        i = int(np.argmin(notas))
        return (props[i], False, float(notas[i]))

def ler_historia(pasta):
    H = []
    caminho = os.path.join(pasta, 'historia.jsonl') if pasta else None
    if not caminho or not os.path.exists(caminho):
        return H
    for ln in open(caminho, encoding='utf-8'):
        if '"evento": "candidata"' not in ln:
            continue
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        if 'params' in e and isinstance(e.get('d_dev'), (int, float)) and (not e.get('pulou')):
            H.append(e)
    return H

def construir(params, conj, foto, g, passos=150, lote=256):
    substituida = None
    if params['op'] == 'degrau':
        rede = conj.novo_degrau(params['esc'], int(g.integers(1 << 30)), params['lr'], params.get('l2', 0.0))
        for _ in range(passos):
            X, y, w = foto.lote(lote, g)
            mu, sd = conj.prever(X)
            rede.passo(np.concatenate([np.asarray(X, np.float64), mu[:, None], sd[:, None]], axis=1), y - mu, w)
        return (rede, None)
    if params['op'] == 'nova':
        rede = A.Rede(conj.entrada, params['esc'], int(g.integers(1 << 30)), params['lr'], params['l2'])
        idx = foto.treino[g.integers(0, len(foto.treino), min(len(foto.treino), 2048))]
        mu, _ = conj.prever_com(foto.X[idx], degraus=[])
        um = np.ones(len(idx))
        Xi = foto.X[idx]
        for _ in range(passos):
            j = g.integers(0, len(idx), lote)
            rede.passo(Xi[j], mu[j], um[j])
    else:
        substituida = params['membro'] % len(conj.redes)
        rede = conj.redes[substituida].copiar()
        rede.lr, rede.l2 = (params['lr'], params.get('l2', 0.0))
        if params['op'] == 'alargar':
            rede.alargar(params['extra'], g)
    for _ in range(passos):
        X, y, w = foto.lote(lote, g)
        rede.passo(X, y, w)
    return (rede, substituida)

def rodada_de_selecao(conj, banco, externos, H, meta, g, tau=0.25, minimo_dev=40, minimo_ret=20, max_degraus=8):
    dev, ret = particoes(banco.itens, externos)
    reg = {'evento': 'candidata', 'K_dev': len(dev), 'K_ret': len(ret), 'degraus_antes': len(conj.degraus)}
    foto = conj.mem.instantaneo()
    if len(dev) < minimo_dev or len(foto.treino) < 200:
        return dict(reg, pulou='poucas decisões guardadas ou pouca memória')
    params, cego, nota = meta.propor(H, g, len(conj.redes))
    if params['op'] == 'degrau' and len(conj.degraus) >= max_degraus:
        params = dict(params, op='alargar', membro=int(g.integers(len(conj.redes))), extra=8)
    rede, substituida = construir(params, conj, foto, g)
    Xd, offd = empilhar(dev)
    Xr, offr = empilhar(ret)
    if params['op'] != 'degrau' and substituida is None:
        erros = []
        for r in conj.redes:
            P = cortar(r.prever(Xd), offd)
            erros.append(float(np.mean([(P[i][it[1]] - it[3]) ** 2 for i, it in enumerate(dev)])))
        substituida = int(np.argmax(erros))

    def notas(X, off, com_candidata):
        if not com_candidata:
            return cortar(conj.prever_com(X)[0], off)
        if params['op'] == 'degrau':
            return cortar(conj.prever_com(X, degraus=list(conj.degraus) + [rede])[0], off)
        redes = list(conj.redes)
        redes[substituida] = rede
        return cortar(conj.prever_com(X, redes=redes)[0], off)
    w_at_dev, w_no_dev = (pesos_de_notas(notas(Xd, offd, False), dev, tau), pesos_de_notas(notas(Xd, offd, True), dev, tau))
    if ret:
        w_at_ret, w_no_ret = (pesos_de_notas(notas(Xr, offr, False), ret, tau), pesos_de_notas(notas(Xr, offr, True), ret, tau))
        d_ret = diferenca_pareada(w_no_ret, w_at_ret, ret)
    else:
        d_ret = np.zeros(0)
    d_dev = diferenca_pareada(w_no_dev, w_at_dev, dev)
    ok_dev, ok_ret = (passa_a_porta(d_dev, minimo_dev), passa_a_retencao(d_ret, minimo_ret))
    adotou = bool(ok_dev and ok_ret)
    gd_antes = ganho_de_decisao_contra_o_cego(w_at_dev, dev)
    gd_depois = ganho_de_decisao_contra_o_cego(w_no_dev, dev)
    if adotou:
        if params['op'] == 'degrau':
            conj.degraus.append(rede)
        else:
            conj.redes[substituida] = rede
    rd, rr = (resumo(d_dev), resumo(d_ret))

    def r6(x):
        return round(x, 6) if math.isfinite(x) else None
    reg.update(params=params, cego=bool(cego), nota_do_meta_modelo=round(nota, 5), substituida=None if substituida is None else int(substituida), arquitetura=list(rede.esc), d_dev=r6(rd['media']), se_dev=r6(rd['erro_padrao']), d_ret=r6(rr['media']), se_ret=r6(rr['erro_padrao']), passa_a_porta=bool(ok_dev), passa_a_retencao=bool(ok_ret), adotou=adotou, degraus_depois=len(conj.degraus), ganho_de_decisao_contra_o_cego={'antes': {'media': r6(gd_antes['media']), 'erro_padrao': r6(gd_antes['erro_padrao']), 'K': gd_antes['K']}, 'depois': {'media': r6(gd_depois['media']), 'erro_padrao': r6(gd_depois['erro_padrao']), 'K': gd_depois['K']}}, exemplos={'proprios': foto.n_proprio, 'externos': len(foto) - foto.n_proprio})
    return reg
CONFIG_ESPACO = {'stall': [30000, 100000, 300000], 'fcol': [3, 4, 6], 'gap': [1000, 2000, 5000], 'cosecha_max': [8, 16, 32], 'mix': [(45, 20, 15, 20), (30, 20, 10, 40), (60, 15, 10, 15), (35, 35, 15, 15)], 'temp': [0.0, 0.3, 1.0], 'tau': [0.15, 0.25, 0.4]}

def cfg_padrao():
    return {'stall': 100000, 'fcol': 4, 'gap': 2000, 'cosecha_max': 16, 'mix': (45, 20, 15, 20), 'temp': 0.0, 'tau': 0.25}

def cfg_de_json(d):
    c = cfg_padrao()
    for k in c:
        if k in d:
            c[k] = tuple(d[k]) if k == 'mix' else d[k]
    return c

def vetor_cfg(cfg):
    return np.array([CONFIG_ESPACO[k].index(cfg[k]) / max(len(CONFIG_ESPACO[k]) - 1, 1) for k in sorted(CONFIG_ESPACO)], float)

def pontuacao_de_uma_tentativa(novas, segundos):
    return novas / max(segundos, 0.001)

def diferencas_relativas(pontos_atual, pontos_nova):
    a, b = (np.asarray(pontos_atual, float), np.asarray(pontos_nova, float))
    escala = max(float(a.mean()), 1e-09) if len(a) else 1.0
    return -(b - a) / escala

def passa_a_retencao_de_ganho(d_ret, minimo=8):
    r = resumo(d_ret)
    return r['K'] >= minimo and r['media'] < 0

class MetaConfig:

    def __init__(self, largura=0.5, premio=0.05, prior=1.0):
        self.largura, self.premio, self.prior = (largura, premio, prior)

    @staticmethod
    def vizinha(cfg, g):
        nova = dict(cfg)
        for k in g.choice(sorted(CONFIG_ESPACO), int(g.integers(1, 3)), replace=False):
            opcoes = [v for v in CONFIG_ESPACO[k] if v != cfg[k]]
            nova[k] = opcoes[int(g.integers(len(opcoes)))]
        return nova

    def notas(self, H, propostas):
        V = np.stack([vetor_cfg(p) for p in propostas])
        if not H:
            return np.zeros(len(propostas))
        Vh = np.stack([vetor_cfg(cfg_de_json(e['cfg_candidata'])) for e in H])
        d = np.array([e['d_dev'] for e in H], float)
        K = np.exp(-((V[:, None, :] - Vh[None, :, :]) ** 2).sum(-1) / (2 * self.largura ** 2))
        soma = K.sum(1)
        return (K * d[None, :]).sum(1) / (soma + self.prior) - self.premio / (1.0 + soma)

    def propor(self, H, cfg, g, anterior=None, amostras=16, fracao_cega=A.FRACAO_CEGA, p_volta=0.15):
        if anterior is not None and g.random() < p_volta:
            return (dict(anterior), False, 0.0, True)
        props = [self.vizinha(cfg, g) for _ in range(amostras)]
        notas = self.notas(H, props)
        if g.random() < fracao_cega:
            i = int(g.integers(amostras))
            return (props[i], True, float(notas[i]), False)
        i = int(np.argmin(notas))
        return (props[i], False, float(notas[i]), False)

def ler_historia_cfg(pasta, n=None):
    H = []
    caminho = os.path.join(pasta, 'historia.jsonl') if pasta else None
    if not caminho or not os.path.exists(caminho):
        return H
    for ln in open(caminho, encoding='utf-8'):
        if '"evento": "config"' not in ln:
            continue
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        if 'cfg_candidata' in e and isinstance(e.get('d_dev'), (int, float)) and (not e.get('pulou')):
            H.append(e)
    return H
