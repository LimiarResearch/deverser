# -*- coding: utf-8 -*-
import math
import numpy as np
KL_MAX = 63
MENOS_INF = -1000000000.0

class Geometria:

    def __init__(self, cod, mapa):
        self.cod, self.mapa = (cod, mapa)
        self.n_bits, self.nF, self.nG = (cod.n_bits, cod.n_campos, cod.n_grupos)
        nb = np.asarray(mapa.bits_do_campo, np.int64)
        papel = np.asarray(mapa.papel, np.int64)
        inicio = np.asarray(mapa.inicio, np.int64)
        self.larguras = sorted({int(x) for x in nb})
        self.por_largura = []
        for w in self.larguras:
            campos = np.flatnonzero(nb == w)
            papeis = sorted({int(papel[i]) for i in campos})
            local = {r: k for k, r in enumerate(papeis)}
            idx = inicio[campos][:, None] + np.arange(w)[None, :]
            self.por_largura.append((campos, np.array([local[int(papel[i])] for i in campos], np.int64), idx, len(papeis)))
        self.grupo_do_campo = np.asarray(mapa.grupo_de[inicio], np.int64)
        cont = np.maximum(np.bincount(self.grupo_do_campo, minlength=self.nG), 1)
        self.escala_do_campo = (1.0 / np.sqrt(cont[self.grupo_do_campo])).astype(np.float32)
        self.ordem_por_grupo = np.argsort(self.grupo_do_campo, kind='stable')
        ocupados, comeco = np.unique(self.grupo_do_campo[self.ordem_por_grupo], return_index=True)
        self.grupos_ocupados, self.comeco_do_grupo = (ocupados, comeco)
        ps, ks, tipos = ([], [], [])
        for i in range(self.nF):
            ps.append(int(inicio[i]))
            ks.append(int(nb[i]))
            tipos.append('gene')
        for u in mapa.unidades:
            ps.append(int(u['inicio']))
            ks.append(int(u['bits']))
            tipos.append('unidade')
        for j in mapa.pares:
            ps.append(int(mapa.unidades[j]['inicio']))
            ks.append(int(mapa.unidades[j]['bits']) + int(mapa.unidades[j + 1]['bits']))
            tipos.append('unidades')
        self.lugar_p, self.lugar_k, self.lugar_tipo = (np.array(ps, np.int64), np.array(ks, np.int64), tipos)
        self.nL = len(ps)
        nR = int(papel.max()) + 1 if len(papel) else 0
        cls = [int(papel[i]) for i in range(self.nF)]
        cls += [nR + int(u['grupo']) for u in mapa.unidades]
        cls += [nR + self.nG + int(mapa.unidades[j]['grupo']) for j in mapa.pares]
        self.lugar_classe = np.array(cls, np.int64)
        self.n_classes = nR + 2 * self.nG
        self.KL = int(min(self.lugar_k.max(), KL_MAX))
        self.id_do_lugar = {(int(p), int(k)): i for i, (p, k) in enumerate(zip(self.lugar_p, self.lugar_k))}
        self.campo_de = np.asarray(mapa.campo_de, np.int64)
        self.fim_do_campo = inicio + nb
        self.inicio_do_campo = inicio

    def lugar_da_edicao(self, p, k):
        i = self.id_do_lugar.get((int(p), int(k)))
        if i is not None:
            return i
        c = int(self.campo_de[p])
        if p + k <= self.fim_do_campo[c]:
            return self.id_do_lugar[int(self.inicio_do_campo[c]), int(self.fim_do_campo[c] - self.inicio_do_campo[c])]
        return -1

    def lugares_vivos(self, ativos):
        c = np.concatenate([[0], np.cumsum(np.asarray(ativos, np.int64))])
        return c[self.lugar_p + self.lugar_k] - c[self.lugar_p] > 0

def _bce_logits(z, t):
    perda = np.maximum(z, 0) - z * t + np.log1p(np.exp(-np.abs(z)))
    return (perda, 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30))) - t)

def _sigmoide(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))

class RedeUnica:

    def __init__(self, geo, n_clausulas, n_pred, d_f=16, h=(128, 96), d_c=96, d_w=96, d_b=64, d_e=16, d_vh=96, semente=0, lr=0.003, l2=0.0, peso_c=0.5, pesos_perda=None, dtype=np.float32):
        self.geo, self.NC, self.P = (geo, int(n_clausulas), int(n_pred))
        self.cfg = {'d_f': int(d_f), 'h': tuple((int(x) for x in h)), 'd_c': int(d_c), 'd_w': int(d_w), 'd_b': int(d_b), 'd_e': int(d_e), 'd_vh': int(d_vh)}
        self.dtype = dtype
        self.lr, self.l2, self.peso_c = (float(lr), float(l2), float(peso_c))
        self.pesos_perda = {'f': 1.0, 'c': 1.0, 'loc': 0.3, 'bits': 0.3, 'v': 0.5}
        self.pesos_perda.update(pesos_perda or {})
        self.dv = 4 + self.NC + self.P
        g = np.random.default_rng(semente)
        d_f, (h1, h2) = (self.cfg['d_f'], self.cfg['h'])
        self.h2 = h2
        nG = geo.nG
        self.W = {}

        def init(nome, forma, escala=None, valor=None):
            if valor is not None:
                self.W[nome] = np.full(forma, valor, dtype)
            else:
                self.W[nome] = g.normal(0, 1.0 / math.sqrt(forma[0]) if escala is None else escala, forma).astype(dtype)
        for k, w in enumerate(geo.larguras):
            init(f'Rw{w}', (geo.por_largura[k][3], w, d_f), 1.0 / math.sqrt(w))
        init('Rp', (geo.nF, d_f), 0.1)
        init('T1', (nG * d_f, h1))
        init('t1', (h1,), valor=0.0)
        init('T2', (h1, h2))
        init('t2', (h2,), valor=0.0)
        init('C1', (h2 + nG * d_f + self.dv, self.cfg['d_c']))
        init('c1', (self.cfg['d_c'],), valor=0.0)
        init('C2', (self.cfg['d_c'], 1 + self.P), 0.1 / math.sqrt(self.cfg['d_c']))
        init('c2', (1 + self.P,), valor=0.0)
        self.W['c2'][1:] = -2.0
        init('L1', (h2 + self.dv, self.cfg['d_w']))
        init('l1', (self.cfg['d_w'],), valor=0.0)
        init('L2', (self.cfg['d_w'], geo.nL), 0.1 / math.sqrt(self.cfg['d_w']))
        init('l2', (geo.nL,), valor=0.0)
        init('El', (geo.nL, self.cfg['d_e']), 0.1)
        init('Ec', (geo.n_classes, self.cfg['d_e']), 0.1)
        init('B1', (h2 + self.dv + geo.KL + self.cfg['d_e'], self.cfg['d_b']))
        init('b1', (self.cfg['d_b'],), valor=0.0)
        init('B2', (self.cfg['d_b'], 2 * geo.KL), 0.1 / math.sqrt(self.cfg['d_b']))
        init('b2', (2 * geo.KL,), valor=0.0)
        init('V1', (h2, self.cfg['d_vh']))
        init('v1', (self.cfg['d_vh'],), valor=0.0)
        init('V2', (self.cfg['d_vh'], 1 + self.NC + self.P), 0.1 / math.sqrt(self.cfg['d_vh']))
        init('v2', (1 + self.NC + self.P,), valor=0.0)
        self.W['v2'][1 + self.NC:] = -1.0
        self._zerar_adam()

    def _zerar_adam(self):
        self._m = {k: np.zeros_like(v) for k, v in self.W.items()}
        self._v = {k: np.zeros_like(v) for k, v in self.W.items()}
        self._t = 0

    def _adam(self, grad, lr=None):
        lr = self.lr if lr is None else lr
        self._t += 1
        for k, gr in grad.items():
            self._m[k] = 0.9 * self._m[k] + 0.1 * gr
            self._v[k] = 0.999 * self._v[k] + 0.001 * gr ** 2
            mh = self._m[k] / (1 - 0.9 ** self._t)
            vh = self._v[k] / (1 - 0.999 ** self._t)
            self.W[k] -= (lr * mh / (np.sqrt(vh) + 1e-08)).astype(self.dtype)
            if self.l2 and k[0] in 'RTCLBV' and (k != 'Rp'):
                self.W[k] -= (lr * self.l2 * self.W[k]).astype(self.dtype)

    def _campos(self, B):
        geo = self.geo
        N = B.shape[0]
        E = np.empty((N, geo.nF, self.cfg['d_f']), self.dtype)
        cache = []
        for k, w in enumerate(geo.larguras):
            campos, local, idx, _ = geo.por_largura[k]
            X = B[:, idx]
            Wf = self.W[f'Rw{w}'][local]
            Z = np.einsum('nfb,fbd->nfd', X, Wf) + self.W['Rp'][campos][None]
            E[:, campos, :] = np.tanh(Z)
            cache.append(X)
        return (E, cache)

    def _somar_por_grupo(self, E):
        geo = self.geo
        S = np.zeros((E.shape[0], geo.nG, E.shape[2]), self.dtype)
        Ee = (E * geo.escala_do_campo[None, :, None].astype(self.dtype))[:, geo.ordem_por_grupo, :]
        S[:, geo.grupos_ocupados, :] = np.add.reduceat(Ee, geo.comeco_do_grupo, axis=1)
        return S

    def ler(self, B):
        B = np.asarray(B, self.dtype)
        E, cx = self._campos(B)
        S = self._somar_por_grupo(E).reshape(B.shape[0], -1)
        a1 = np.tanh(S @ self.W['T1'] + self.W['t1'])
        h = np.tanh(a1 @ self.W['T2'] + self.W['t2'])
        return (S, h, (E, cx, S, a1, h))

    def _ler_volta(self, cache, dS, dh, G):
        E, cx, S, a1, h = cache
        geo = self.geo
        dz2 = dh * (1 - h ** 2)
        G['T2'] += a1.T @ dz2
        G['t2'] += dz2.sum(0)
        da1 = dz2 @ self.W['T2'].T * (1 - a1 ** 2)
        G['T1'] += S.T @ da1
        G['t1'] += da1.sum(0)
        dS = dS + da1 @ self.W['T1'].T
        dE = dS.reshape(S.shape[0], geo.nG, -1)[:, geo.grupo_do_campo, :] * geo.escala_do_campo[None, :, None].astype(self.dtype)
        for k, w in enumerate(geo.larguras):
            campos, local, idx, _ = geo.por_largura[k]
            dZ = dE[:, campos, :] * (1 - E[:, campos, :] ** 2)
            dWf = np.einsum('nfb,nfd->fbd', cx[k], dZ)
            np.add.at(G[f'Rw{w}'], local, dWf)
            G['Rp'][campos] += dZ.sum(0)

    def contexto(self, dist_feat, nfal_frac, violacoes, phi):
        N = len(dist_feat)
        v = np.zeros((N, self.dv), self.dtype)
        v[:, 0], v[:, 1], v[:, 2] = (dist_feat[:, 0], dist_feat[:, 1], nfal_frac)
        v[:, 3] = (np.asarray(nfal_frac) == 0).astype(self.dtype)
        v[:, 4:4 + self.NC] = violacoes
        v[:, 4 + self.NC:] = phi
        return v

    def _efeito(self, S_p, h_p, S_c, v_p):
        x = np.concatenate([h_p, S_c - S_p, v_p], axis=1)
        a = np.tanh(x @ self.W['C1'] + self.W['c1'])
        z = a @ self.W['C2'] + self.W['c2']
        return (x, a, z)

    def delta_do_veredito(self, h_p, h_c):
        NC = self.NC
        zp = np.clip(self._veredito(h_p)[1][:, 1:1 + NC], 0.0, 1.0)
        zc = np.clip(self._veredito(h_c)[1][:, 1:1 + NC], 0.0, 1.0)
        return zc.sum(1) - zp.sum(1)

    def efeito(self, S_p, h_p, S_c, v_p, h_c):
        _, _, z = self._efeito(S_p, h_p, S_c, v_p)
        return (z[:, 0] + self.delta_do_veredito(h_p, h_c), _sigmoide(z[:, 1:]))

    def efeito_com_vontade(self, S_p, h_p, S_c, v_p, h_c, peso_falha=0.0, peso_quebra=0.0, confianca=None):
        _, _, z = self._efeito(S_p, h_p, S_c, v_p)
        NC = self.NC
        zp = np.clip(self._veredito(h_p)[1][:, 1:1 + NC], 0.0, 1.0)
        zc = np.clip(self._veredito(h_c)[1][:, 1:1 + NC], 0.0, 1.0)
        d = zc - zp
        falha = np.asarray(v_p)[:, 4:4 + NC] > 1e-06
        w = np.where(falha, 1.0 + float(peso_falha), np.where(d > 0, 1.0 + float(peso_quebra), 1.0))
        if confianca is not None:
            w = w * np.asarray(confianca, w.dtype)[None, :]
        return (z[:, 0] + (w * d).sum(1), _sigmoide(z[:, 1:]))

    def _lugar_logits(self, h_p, v_p):
        x = np.concatenate([h_p, v_p], axis=1)
        a = np.tanh(x @ self.W['L1'] + self.W['l1'])
        return (x, a, a @ self.W['L2'] + self.W['l2'])

    def lugar_logits(self, h_p, v_p):
        return self._lugar_logits(h_p, v_p)[2]

    def _bits_logits(self, h_p, v_p, velho, loc):
        KL = self.geo.KL
        x = np.concatenate([h_p, v_p, velho, self.W['El'][loc] + self.W['Ec'][self.geo.lugar_classe[loc]]], axis=1)
        a = np.tanh(x @ self.W['B1'] + self.W['b1'])
        z = a @ self.W['B2'] + self.W['b2']
        return (x, a, z, z[:, :KL] + z[:, KL:] * (2.0 * velho - 1.0))

    def bits_logits(self, h_p, v_p, velho, loc):
        return self._bits_logits(h_p, v_p, velho, loc)[3]

    def _veredito(self, h):
        a = np.tanh(h @ self.W['V1'] + self.W['v1'])
        return (a, a @ self.W['V2'] + self.W['v2'])

    def veredito(self, h):
        _, z = self._veredito(h)
        return (z[:, 0], z[:, 1:1 + self.NC], _sigmoide(z[:, 1 + self.NC:]))

    def grad_zero(self):
        return {k: np.zeros_like(v) for k, v in self.W.items()}

    def perda_e_gradiente(self, critico=None, escritor=None, veredito=None):
        G = self.grad_zero()
        P, NC = (self.P, self.NC)
        perdas = {}
        lam = self.pesos_perda
        if critico is not None:
            Sp, hp, cp = self.ler(critico['Bp'])
            Sc, hc, cc = self.ler(critico['Bc'])
            x, a, z = self._efeito(Sp, hp, Sc, critico['vp'])
            w = np.asarray(critico['w'], self.dtype)
            sw = max(float(w.sum()), 1e-09)
            av_p, zv_p = self._veredito(hp)
            av_c, zv_c = self._veredito(hc)
            vr_p, vr_c = (zv_p[:, 1:1 + NC], zv_c[:, 1:1 + NC])
            fv = np.clip(vr_c, 0.0, 1.0).sum(1) - np.clip(vr_p, 0.0, 1.0).sum(1)
            ef = z[:, 0] + fv - critico['y']
            perdas['f'] = float((ef ** 2 * w).sum() / sw)
            bce, dz_c = _bce_logits(z[:, 1:], critico['troca'])
            perdas['c'] = float((bce.mean(1) * w).sum() / sw)
            dz = np.zeros_like(z)
            dz[:, 0] = lam['f'] * 2.0 * ef * w / sw
            dz[:, 1:] = lam['c'] * self.peso_c * dz_c * (w / sw)[:, None] / P
            G['C2'] += a.T @ dz
            G['c2'] += dz.sum(0)
            da = dz @ self.W['C2'].T * (1 - a ** 2)
            G['C1'] += x.T @ da
            G['c1'] += da.sum(0)
            dx = da @ self.W['C1'].T
            dh_p, dS_d = (dx[:, :self.h2], dx[:, self.h2:self.h2 + self.geo.nG * self.cfg['d_f']])
            dfv = dz[:, 0]
            dzv_c, dzv_p = (np.zeros_like(zv_c), np.zeros_like(zv_p))
            dzv_c[:, 1:1 + NC] = dfv[:, None] * ((vr_c > 0.0) & (vr_c < 1.0))
            dzv_p[:, 1:1 + NC] = -dfv[:, None] * ((vr_p > 0.0) & (vr_p < 1.0))
            dh_v = []
            for a_v, dzv, h_v in ((av_p, dzv_p, hp), (av_c, dzv_c, hc)):
                G['V2'] += a_v.T @ dzv
                G['v2'] += dzv.sum(0)
                dav = dzv @ self.W['V2'].T * (1 - a_v ** 2)
                G['V1'] += h_v.T @ dav
                G['v1'] += dav.sum(0)
                dh_v.append(dav @ self.W['V1'].T)
            self._ler_volta(cp, -dS_d, dh_p + dh_v[0], G)
            self._ler_volta(cc, dS_d, dh_v[1], G)
        if escritor is not None:
            Sp, hp, cp = self.ler(escritor['Bp'])
            w = np.asarray(escritor['w'], self.dtype)
            sw = max(float(w.sum()), 1e-09)
            vp = escritor['vp']
            xl, al, zl = self._lugar_logits(hp, vp)
            zm = zl - zl.max(1, keepdims=True)
            lse = np.log(np.exp(zm).sum(1))
            loc = np.asarray(escritor['loc'])
            nll = lse - zm[np.arange(len(loc)), loc]
            perdas['loc'] = float((nll * w).sum() / sw)
            pr = np.exp(zm - lse[:, None])
            dzl = pr.copy()
            dzl[np.arange(len(loc)), loc] -= 1.0
            dzl *= (lam['loc'] * w / sw)[:, None]
            G['L2'] += al.T @ dzl
            G['l2'] += dzl.sum(0)
            dal = dzl @ self.W['L2'].T * (1 - al ** 2)
            G['L1'] += xl.T @ dal
            G['l1'] += dal.sum(0)
            dxl = dal @ self.W['L1'].T
            velho = escritor['velho']
            xb, ab, zb, lgb = self._bits_logits(hp, vp, velho, loc)
            km = escritor['kmask'].astype(self.dtype)
            novo = velho + escritor['vira'] - 2.0 * velho * escritor['vira']
            bce, dlg = _bce_logits(lgb, novo)
            nk = np.maximum(km.sum(1), 1.0)
            perdas['bits'] = float(((bce * km).sum(1) / nk * w).sum() / sw)
            dlg = dlg * km * (lam['bits'] * w / sw / nk)[:, None]
            dzb = np.concatenate([dlg, dlg * (2.0 * velho - 1.0)], axis=1)
            G['B2'] += ab.T @ dzb
            G['b2'] += dzb.sum(0)
            dab = dzb @ self.W['B2'].T * (1 - ab ** 2)
            G['B1'] += xb.T @ dab
            G['b1'] += dab.sum(0)
            dxb = dab @ self.W['B1'].T
            dxe = dxb[:, self.h2 + self.dv + self.geo.KL:]
            np.add.at(G['El'], loc, dxe)
            np.add.at(G['Ec'], self.geo.lugar_classe[loc], dxe)
            dh = dxl[:, :self.h2] + dxb[:, :self.h2]
            self._ler_volta(cp, np.zeros_like(Sp), dh, G)
        if veredito is not None:
            S, h, c = self.ler(veredito['B'])
            w = np.asarray(veredito['w'], self.dtype)
            sw = max(float(w.sum()), 1e-09)
            a, z = self._veredito(h)
            alvo = veredito['alvo']
            e = z[:, :1 + NC] - alvo[:, :1 + NC]
            bce, dzp = _bce_logits(z[:, 1 + NC:], alvo[:, 1 + NC:])
            perdas['v'] = float((((e ** 2).mean(1) + bce.mean(1)) * w).sum() / sw)
            dz = np.zeros_like(z)
            dz[:, :1 + NC] = lam['v'] * 2.0 * e / (1 + NC) * (w / sw)[:, None]
            dz[:, 1 + NC:] = lam['v'] * dzp / P * (w / sw)[:, None]
            G['V2'] += a.T @ dz
            G['v2'] += dz.sum(0)
            da = dz @ self.W['V2'].T * (1 - a ** 2)
            G['V1'] += h.T @ da
            G['v1'] += da.sum(0)
            self._ler_volta(c, np.zeros_like(S), da @ self.W['V1'].T, G)
        return (perdas, G)

    def passo(self, critico=None, escritor=None, veredito=None, lr=None):
        perdas, G = self.perda_e_gradiente(critico, escritor, veredito)
        self._adam(G, lr)
        return perdas

    def alargar(self, extra, g):
        extra = int(extra)
        self.W['T2'] = np.concatenate([self.W['T2'], g.normal(0, 0.1, (self.W['T2'].shape[0], extra)).astype(self.dtype)], axis=1)
        self.W['t2'] = np.concatenate([self.W['t2'], np.zeros(extra, self.dtype)])
        z = lambda n: np.zeros((extra, n), self.dtype)
        ini = self.W['C1'].shape[0] - self.dv - self.geo.nG * self.cfg['d_f']
        self.W['C1'] = np.concatenate([self.W['C1'][:ini], z(self.W['C1'].shape[1]), self.W['C1'][ini:]], axis=0)
        ini = self.W['L1'].shape[0] - self.dv
        self.W['L1'] = np.concatenate([self.W['L1'][:ini], z(self.W['L1'].shape[1]), self.W['L1'][ini:]], axis=0)
        ini = self.W['B1'].shape[0] - self.dv - self.geo.KL - self.cfg['d_e']
        self.W['B1'] = np.concatenate([self.W['B1'][:ini], z(self.W['B1'].shape[1]), self.W['B1'][ini:]], axis=0)
        self.W['V1'] = np.concatenate([self.W['V1'], z(self.W['V1'].shape[1])], axis=0)
        self.h2 += extra
        self.cfg['h'] = (self.cfg['h'][0], self.h2)
        self._zerar_adam()

    def copiar(self):
        r = RedeUnica(self.geo, self.NC, self.P, semente=0, lr=self.lr, l2=self.l2, peso_c=self.peso_c, pesos_perda=self.pesos_perda, dtype=self.dtype, **{**self.cfg, 'h': self.cfg['h']})
        r.W = {k: v.copy() for k, v in self.W.items()}
        r.h2 = self.h2
        r._zerar_adam()
        return r

    def n_parametros(self):
        return int(sum((v.size for v in self.W.values())))

    def estado(self):
        return {'cfg': self.cfg, 'NC': self.NC, 'P': self.P, 'lr': self.lr, 'l2': self.l2, 'peso_c': self.peso_c, 'pesos_perda': self.pesos_perda, 'W': {k: v.tolist() for k, v in self.W.items()}}

    @classmethod
    def de_estado(cls, geo, e, dtype=np.float32):
        c = e['cfg']
        r = cls(geo, e['NC'], e['P'], d_f=c['d_f'], h=tuple(c['h']), d_c=c['d_c'], d_w=c['d_w'], d_b=c['d_b'], d_e=c['d_e'], d_vh=c['d_vh'], semente=0, lr=e.get('lr', 0.003), l2=e.get('l2', 0.0), peso_c=e.get('peso_c', 0.5), pesos_perda=e.get('pesos_perda'), dtype=dtype)
        r.W = {k: np.asarray(v, dtype) for k, v in e['W'].items()}
        r.h2 = r.cfg['h'][1]
        r._zerar_adam()
        return r
