# -*- coding: utf-8 -*-
import bisect
import numpy as np

class Colheita:

    def __init__(self, problema, K=16, sem_clones=False):
        self.problema = problema
        self.NC, self.K = (problema.n_clausulas, int(K))
        self.sem_clones = bool(sem_clones)
        self.salao = [[] for _ in range(self.NC)]
        self.entradas = 0

    def entrar(self, ident, ver):
        if ver['estado'] != 'ok':
            return 0
        viol = np.minimum(np.asarray(ver['violacoes'], np.float64), 1.0)
        dist = int(ver['distancia'])
        n = 0
        for c in range(self.NC):
            h = self.salao[c]
            e = (float(viol[c]), dist, int(ident))
            if self.sem_clones and any((x[0] == e[0] and x[1] == e[1] for x in h)):
                continue
            if len(h) < self.K or e < h[-1]:
                bisect.insort(h, e)
                del h[self.K:]
                n += 1
        self.entradas += n
        return n

    def refazer(self, arquivo, excluir=None):
        self.salao = [[] for _ in range(self.NC)]
        n = len(arquivo)
        if n == 0:
            return
        ok = np.flatnonzero(arquivo.estado[:n] == 0)
        if excluir is not None and len(excluir):
            fora = np.zeros(n, bool)
            fora[:min(len(excluir), n)] = np.asarray(excluir, bool)[:n]
            ok = ok[~fora[ok]]
        if len(ok) == 0:
            return
        val = arquivo.valores[ok].astype(np.float64)
        dist = arquivo.distancia[ok].astype(np.int64)
        for c in range(self.NC):
            viol = np.minimum(np.asarray(self.problema.violacoes_de_coluna(c, val[:, c]), np.float64), 1.0)
            ordem = np.lexsort((ok, dist, viol))
            if self.sem_clones:
                vistos, fica = (set(), [])
                for i in ordem:
                    ch = (float(viol[i]), int(dist[i]))
                    if ch not in vistos:
                        vistos.add(ch)
                        fica.append(i)
                        if len(fica) == self.K:
                            break
                ordem = np.asarray(fica, np.int64)
            ordem = ordem[:self.K]
            self.salao[c] = [(float(viol[i]), int(dist[i]), int(ok[i])) for i in ordem]

    def resumo(self):
        ids = {e[2] for h in self.salao for e in h}
        return {'fotos_colhidas': len(ids), 'por_clausula': {self.problema.clausulas[c][0]: {'menor_violacao': round(h[0][0], 4) if h else None, 'cumprem_no_salao': int(sum((1 for e in h if e[0] <= 1e-09))), 'no_salao': len(h)} for c, h in enumerate(self.salao)}}

    def doadores_para(self, arquivo, id_do_molde, n_max=12, n_candidatos=None):
        v_m = self._violacoes(arquivo, [id_do_molde])[0]
        falha = np.flatnonzero(v_m > 1e-09)
        if len(falha) == 0:
            return (np.zeros(0, np.int64), np.zeros(0))
        cand = sorted({e[2] for c in falha for e in self.salao[c]} - {int(id_do_molde)})
        if not cand:
            return (np.zeros(0, np.int64), np.zeros(0))
        cand = np.array(cand, np.int64)
        V = self._violacoes(arquivo, cand)
        ganho = np.maximum(v_m[None, :] - V, 0.0)[:, falha].sum(1)
        mold = arquivo.bits[int(id_do_molde)]
        dif = np.unpackbits(np.bitwise_xor(arquivo.bits[cand], mold[None, :]), axis=1).sum(1).astype(np.int64)
        ordem = np.lexsort((dif, -ganho))
        ordem = ordem[(dif[ordem] > 0) & (ganho[ordem] > 0)][:int(n_max)]
        return (cand[ordem], ganho[ordem])

    def _violacoes(self, arquivo, ids):
        ids = np.asarray(ids, np.int64)
        val = arquivo.valores[ids].astype(np.float64)
        ok = arquivo.estado[ids] == 0
        out = np.ones((len(ids), self.NC))
        for c in range(self.NC):
            if ok.any():
                out[ok, c] = np.minimum(np.asarray(self.problema.violacoes_de_coluna(c, val[ok, c]), np.float64), 1.0)
        return out
