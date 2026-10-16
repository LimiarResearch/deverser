# -*- coding: utf-8 -*-
import json
import math
import os
import numpy as np
from experimentos import conjunto_de_redes as CR
from experimentos import escritor_de_fotos as EF
from experimentos import nivel3b_escritor as E
from experimentos import nivel3b_meta as M
from experimentos import rede_de_fotos as RF
ARQ_PESOS_SEMANTICOS = EF.PESOS_SEMANTICOS if hasattr(EF, 'PESOS_SEMANTICOS') else (0.0, 0.25, 0.5, 1.0)

def _softmax(z):
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()

def _bits_para_int(b):
    v = 0
    for x in b:
        v = v << 1 | int(x)
    return v

def _int_para_bits(v, k):
    return np.array([int(v) >> k - 1 - t & 1 for t in range(k)], np.uint8)

def config_de_escrita_inicial(pool, k_cega):
    return {'pool': int(pool), 'k_cega': int(k_cega), 'temperatura': 1.0, 'epsilon': 0.1, 'fracao_da_rede': 0.5}

class Pai:

    def __init__(self, ap, bits, ver, passo=0):
        cod, mapa = (ap.cod, ap.mapa)
        self.bits = np.asarray(bits, np.uint8)
        self.ver = ver
        self.comp = int(ver['comportamento'])
        self.dist = int(ver['distancia'])
        self.nfal = int(ver['nfal'])
        self.passo = int(passo)
        self.ativos = np.asarray(cod.ativos(self.bits), bool)
        self.pos_ativas = np.flatnonzero(self.ativos)
        if len(self.pos_ativas) == 0:
            self.pos_ativas = np.arange(cod.n_bits)
        self.campos_ativos = np.unique(mapa.campo_de[self.pos_ativas])
        ju = mapa.unidade_de[self.pos_ativas]
        self.unidades_ativas = np.unique(ju[ju >= 0])
        self.chave = cod.chave(self.bits)
        self.vivo = ap.geo.lugares_vivos(self.ativos)
        if not self.vivo.any():
            self.vivo[:] = True
        self.phi = np.array([self.comp >> j & 1 for j in range(ap.problema.n_definidos)], np.float64)
        self.v = ap.contexto_do_veredito(ver)

class MemoriaDeEdicoes:
    COLUNAS = (('pai', np.int64, -1), ('filho', np.int64, -1), ('y', np.float32, 0), ('loc', np.int32, -1), ('vira', np.int64, 0), ('k', np.int16, 0), ('tipo', np.int8, 0), ('cego', np.int8, 0), ('rodada', np.int32, 0))

    def __init__(self, teto=150000, semente=0):
        self.teto = int(teto)
        self.g = np.random.default_rng(semente + 717)
        self._cap = 4096
        for nome, dt, pad in self.COLUNAS:
            setattr(self, '_' + nome, np.full(self._cap, pad, dt))
        self.N = 0
        self.vistas = 0

    def __len__(self):
        return self.N

    def proprios(self):
        return self.N

    @property
    def y(self):
        return self._y[:self.N]

    def coluna(self, nome):
        return getattr(self, '_' + nome)[:self.N]

    def adicionar(self, pai, filho, y, loc, vira, k, tipo, cego, rodada):
        self.vistas += 1
        if self.N < self.teto:
            if self.N >= self._cap:
                self._cap = min(self._cap * 2, self.teto)
                for nome, dt, pad in self.COLUNAS:
                    a = getattr(self, '_' + nome)
                    setattr(self, '_' + nome, np.concatenate([a, np.full(self._cap - len(a), pad, dt)]))
            i = self.N
            self.N += 1
        else:
            nao = np.flatnonzero(self._y[:self.N] >= 0)
            if len(nao) == 0 or (y < 0 and self.g.random() < 0.0):
                return
            if y >= 0 and self.g.random() > self.teto / float(self.vistas):
                return
            i = int(nao[self.g.integers(len(nao))])
        self._pai[i], self._filho[i], self._y[i], self._loc[i], self._vira[i], self._k[i], self._tipo[i], self._cego[i], self._rodada[i] = (pai, filho, y, loc, vira, k, tipo, cego, rodada)

    def amostrar_critico(self, n, g, proibidos=None):
        if self.N == 0:
            return (np.zeros(0, int), np.zeros(0))
        q = np.where(self._y[:self.N] < 0, 2.0, 1.0)
        if proibidos is not None:
            q = q * ~proibidos[self._filho[:self.N]]
        if q.sum() <= 0:
            return (np.zeros(0, int), np.zeros(0))
        idx = g.choice(self.N, size=n, p=q / q.sum())
        w = 1.0 / q[idx]
        return (idx, w / w.mean())

    def amostrar_escritor(self, n, g, proibidos=None):
        y = self._y[:self.N]
        q = np.where((y < 0) & (self._loc[:self.N] >= 0), np.minimum(-y, 3.0), 0.0)
        if proibidos is not None:
            q = q * ~proibidos[self._filho[:self.N]]
        if q.sum() <= 0:
            return np.zeros(0, int)
        return g.choice(self.N, size=n, p=q / q.sum())

    def n_que_melhoraram(self):
        return int((self._y[:self.N] < 0).sum())

    def salvar(self, caminho):
        tmp = caminho + '.tmp.npz'
        np.savez_compressed(tmp, **{nome: getattr(self, '_' + nome)[:self.N] for nome, _, _ in self.COLUNAS}, vistas=np.asarray([self.vistas]))
        os.replace(tmp, caminho)

    @classmethod
    def carregar(cls, caminho, teto=150000, semente=0):
        m = cls(teto, semente)
        if caminho and os.path.exists(caminho):
            z = np.load(caminho)
            n = min(len(z['y']), m.teto)
            m._cap = max(4096, n)
            for nome, dt, pad in cls.COLUNAS:
                a = np.full(m._cap, pad, dt)
                a[:n] = z[nome][:n]
                setattr(m, '_' + nome, a)
            m.N = n
            m.vistas = max(n, int(z['vistas'][0]))
        return m

class MemoriaDeAutoimitacao:

    def __init__(self, teto=20000):
        self.teto = int(teto)
        self.pai = np.zeros(0, np.int64)
        self.loc = np.zeros(0, np.int32)
        self.vira = np.zeros(0, np.int64)
        self.k = np.zeros(0, np.int16)
        self.w = np.zeros(0, np.float32)

    def __len__(self):
        return len(self.pai)

    def adicionar(self, pai, loc, vira, k, w):
        self.pai, self.loc, self.vira, self.k, self.w = (np.concatenate([a, [v]]).astype(a.dtype)[-self.teto:] for a, v in ((self.pai, pai), (self.loc, loc), (self.vira, vira), (self.k, k), (self.w, w)))

    def salvar(self, caminho):
        tmp = caminho + '.tmp.npz'
        np.savez_compressed(tmp, pai=self.pai, loc=self.loc, vira=self.vira, k=self.k, w=self.w)
        os.replace(tmp, caminho)

    @classmethod
    def carregar(cls, caminho, teto=20000):
        m = cls(teto)
        if caminho and os.path.exists(caminho):
            z = np.load(caminho)
            m.pai, m.loc, m.vira, m.k, m.w = (z['pai'], z['loc'], z['vira'], z['k'], z['w'])
        return m

class Piscina:
    __slots__ = ('pai', 'filhos', 'y', 'seq')

    def __init__(self, pai, filhos, y, seq):
        self.pai, self.filhos, self.y, self.seq = (int(pai), np.asarray(filhos, np.int64), np.asarray(y, np.float32), int(seq))

class BancoDePiscinas:

    def __init__(self, teto=400, semente=0):
        self.teto = int(teto)
        self.g = np.random.default_rng(semente + 555)
        self.itens = []
        self.vistas = 0

    def __len__(self):
        return len(self.itens)

    def adicionar(self, it):
        self.vistas += 1
        if len(self.itens) < self.teto:
            self.itens.append(it)
        else:
            j = int(self.g.integers(self.vistas))
            if j < self.teto:
                self.itens[j] = it

    def salvar(self, caminho):
        tmp = caminho + '.tmp.npz'
        it = self.itens
        np.savez_compressed(tmp, pai=np.array([x.pai for x in it], np.int64), off=np.cumsum([0] + [len(x.filhos) for x in it]).astype(np.int64), filhos=np.concatenate([x.filhos for x in it]) if it else np.zeros(0, np.int64), y=np.concatenate([x.y for x in it]) if it else np.zeros(0, np.float32), seq=np.array([x.seq for x in it], np.int64), vistas=np.asarray([self.vistas]))
        os.replace(tmp, caminho)

    @classmethod
    def carregar(cls, caminho, teto=400, semente=0):
        b = cls(teto, semente)
        if caminho and os.path.exists(caminho):
            z = np.load(caminho)
            off = z['off']
            b.itens = [Piscina(z['pai'][i], z['filhos'][off[i]:off[i + 1]], z['y'][off[i]:off[i + 1]], z['seq'][i]) for i in range(len(z['pai']))][:teto]
            b.vistas = max(len(b.itens), int(z['vistas'][0]))
        return b

class AprendizDeFotos:

    def __init__(self, problema, fotos, semente=0, pool=256, k_modelo=8, k_cega=2, min_memoria=800, teto_memoria=150000, piscina_m=16, peso_semantico=0.5, mistura=None, membros=5, reducao=1.0, lr=0.003, l2=0.0, vontade_falha=0.0, vontade_quebra=0.0, confianca_por_clausula=False):
        self.problema, self.fotos = (problema, fotos)
        self.vontade_falha, self.vontade_quebra, self.confianca_por_clausula = (float(vontade_falha), float(vontade_quebra), bool(confianca_por_clausula))
        self.rotulo_por_d = None
        self._pesos_d = None
        self.erro_por_clausula, self._n_no_ultimo_treino = (None, 0)
        self.cod = problema.codificacao
        self.mapa = EF.Mapa(self.cod)
        self.geo = RF.Geometria(self.cod, self.mapa)
        self.sondas = problema.predicados
        self.NC, self.P = (problema.n_clausulas, problema.n_definidos)
        self.mistura = dict(mistura or EF.MISTURA_CEGA)
        self.min_memoria, self.piscina_m = (int(min_memoria), int(piscina_m))
        self.peso_semantico = float(peso_semantico)
        self.reducao = float(reducao)
        self.g = np.random.default_rng(semente + 4242)
        self.semente = int(semente)
        self.rede = CR.ConjuntoDeRedes.novo(self.geo, self.NC, self.P, membros, semente, reducao=reducao, lr=lr, l2=l2)
        self.mem = MemoriaDeEdicoes(teto=teto_memoria, semente=semente)
        self.auto = MemoriaDeAutoimitacao()
        self.piscinas = BancoDePiscinas(teto=400, semente=semente)
        self._no_banco = np.zeros(4096, bool)
        self._intocadas = np.zeros(4096, bool)
        self.biblioteca = E.Biblioteca(0)
        self.motivos = EF.Motivos(self.mapa)
        self.treinos = 0
        self.seq = 0
        self.H = []
        self.H_politica = []
        self.meta = M.MetaModelo()
        self.total_avaliado = int(k_modelo) + int(k_cega)
        self.config_de_escrita = config_de_escrita_inicial(pool, k_cega)
        self.vel = {b: [0, 0, 0] for b in EF.BRACOS[:4]}
        self._vel_anterior = {b: [0, 0, 0] for b in EF.BRACOS[:4]}
        self.contadores = {'escritas': 0, 'edicoes_avaliadas': 0, 'piscinas_rotuladas': 0, 'rodadas_de_selecao': 0, 'trocas_adotadas': 0, 'trocas_recusadas': 0, 'politicas_adotadas': 0, 'politicas_recusadas': 0, 'edicoes_que_mudaram_o_comportamento': 0, 'propostas_do_modelo': 0, 'propostas_as_cegas': 0, 'propostas_do_operador': 0, 'melhoras_do_modelo': 0, 'melhoras_as_cegas': 0, 'melhoras_do_operador': 0, 'rodadas': 0, 'propostas_da_biblioteca': 0, 'melhoras_da_biblioteca': 0, 'propostas_do_motivo': 0, 'melhoras_do_motivo': 0, 'propostas_do_filtro': 0, 'melhoras_do_filtro': 0, 'autoimitacoes': 0, 'sementes_que_ordenam': 0}

    @property
    def n_duras(self):
        return len(self.sondas.duras) if self.sondas is not None else 0

    def _mascara_das_duras(self):
        return self.sondas.mascara_das_duras() if self.sondas is not None else 0

    def _mascara_total(self):
        return (1 << len(self.sondas)) - 1 if self.sondas is not None else 0

    def bits_das_fotos(self, ids):
        ids = np.asarray(ids, np.int64)
        return np.unpackbits(self.fotos.bits[ids], axis=1)[:, :self.cod.n_bits].astype(np.float32)

    def _colunas(self, ids):
        f, NC = (self.fotos, self.NC)
        ids = np.asarray(ids, np.int64)
        d = f.distancia[ids].astype(np.float64)
        ok = f.estado[ids] == 0
        nf = np.where(ok, f.nfal[ids].astype(np.float64) / NC, 1.0)
        viol = np.ones((len(ids), NC))
        if ok.any():
            val = f.valores[ids].astype(np.float64)
            for i in range(NC):
                viol[ok, i] = np.minimum(np.asarray(self.problema.violacoes_de_coluna(i, val[ok, i]), np.float64), 1.0)
        d = np.where(ok, d, 1000.0 * NC)
        dist_feat = np.stack([np.log1p(d / 10.0) / 6.0, np.minimum(d / (1000.0 * NC), 4.0)], axis=1)
        phi = E.bits_dos_comportamentos(f.comp_lo[ids], f.comp_hi[ids], self.P).astype(np.float64)
        return (dist_feat, nf, viol, phi)

    def contexto_das_fotos(self, ids, dtype=np.float32):
        d, nf, viol, phi = self._colunas(ids)
        return self.rede.membros[0].contexto(d, nf, viol, phi).astype(dtype)

    def contexto_do_veredito(self, ver):
        NC = self.NC
        ok = ver['estado'] == 'ok'
        d = float(ver['distancia']) if ok else 1000.0 * NC
        viol = np.minimum(np.asarray(ver['violacoes'], np.float64), 1.0) if ok else np.ones(NC)
        phi = np.array([int(ver['comportamento']) >> j & 1 for j in range(self.P)], np.float64)
        dist_feat = np.array([[math.log1p(d / 10.0) / 6.0, min(d / (1000.0 * NC), 4.0)]])
        return self.rede.membros[0].contexto(dist_feat, np.array([ver['nfal'] / NC if ok else 1.0]), viol[None], phi[None])

    def definir_rotulo_por_d(self, indices, W=10.0, LAMBDA=2.0):
        w = np.ones(self.NC)
        for i in indices:
            w[int(i)] = float(W)
        self._pesos_d = w
        self.rotulo_por_d = {'indices': [int(i) for i in indices], 'W': float(W), 'LAMBDA': float(LAMBDA)}

    def _y_de_treino(self, pai_ver, ver):
        if self.rotulo_por_d is None:
            return EF.alvo(int(pai_ver['distancia']), ver['distancia']) if ver['estado'] == 'ok' else EF.CLIP_DO_ALVO
        vp = np.minimum(np.nan_to_num(np.asarray(pai_ver['violacoes'], np.float64), nan=1.0), 1.0)
        vc = np.minimum(np.nan_to_num(np.asarray(ver['violacoes'], np.float64), nan=1.0), 1.0) if ver['estado'] == 'ok' else np.ones(self.NC)
        falha = vp > 1e-09
        return float((np.where(falha, vc - vp, 0.0) * self._pesos_d).sum() + self.rotulo_por_d['LAMBDA'] * (np.where(~falha, vc, 0.0) * self._pesos_d).sum())

    def reetiquetar(self):
        if self.rotulo_por_d is None:
            return 0
        n = 0
        cache = {}

        def ver(k):
            k = int(k)
            if k not in cache:
                cache[k] = self.fotos.veredito(k)
            return cache[k]
        N = len(self.fotos)
        pais, filhos = (self.mem.coluna('pai'), self.mem.coluna('filho'))
        for j in range(len(self.mem)):
            p, f = (int(pais[j]), int(filhos[j]))
            if 0 <= p < N and 0 <= f < N:
                self.mem._y[j] = self._y_de_treino(ver(p), ver(f))
                n += 1
        for it in self.piscinas.itens:
            if 0 <= it.pai < N:
                it.y = np.asarray([self._y_de_treino(ver(it.pai), ver(f)) if 0 <= f < N else float(self._y_de_treino(ver(it.pai), {'estado': 'erro'})) for f in it.filhos], np.float32)
                n += len(it.filhos)
        return n

    def pai(self, bits, ver, passo=0):
        return Pai(self, bits, ver, passo)

    def pronto(self):
        return self.treinos > 0 and self.mem.proprios() >= self.min_memoria or bool(getattr(self, 'pronto_pelo_eixo', False))

    def _crescer_banco(self, n):
        if n > len(self._no_banco):
            self._no_banco = np.concatenate([self._no_banco, np.zeros(max(n, 2 * len(self._no_banco)) - len(self._no_banco), bool)])
        if n > len(self._intocadas):
            self._intocadas = np.concatenate([self._intocadas, np.zeros(max(n, 2 * len(self._intocadas)) - len(self._intocadas), bool)])

    def marcar_intocada(self, ident):
        self._crescer_banco(int(ident) + 1)
        self._intocadas[int(ident)] = True

    def _proibidos(self):
        self._crescer_banco(len(self.fotos) + 1)
        return self._no_banco | self._intocadas

    def _nota(self, f, q, phi_pai_duras, peso=None):
        peso = self.peso_semantico if peso is None else peso
        nd = self.n_duras
        if nd <= 0 or not peso:
            return f
        a = phi_pai_duras
        esperadas = (a + (1.0 - 2.0 * a) * q[:, :nd]).sum(1)
        return f + peso * (esperadas - a.sum(1)) / nd

    def _fq_de_bits(self, pai, Bc, conjunto=None, tamanho_lote=512):
        conj = conjunto or self.rede
        n = len(Bc)
        fs, qs = ([], [])
        for m in conj.membros:
            Sp, hp, _ = m.ler(pai.bits[None, :].astype(m.dtype))
            vp = np.asarray(pai.v, m.dtype)
            f = np.empty(n)
            q = np.empty((n, self.P))
            vontade = self._vontade_ligada()
            conf = self._confianca() if vontade else None
            for a in range(0, n, tamanho_lote):
                Sc, hc, _ = m.ler(Bc[a:a + tamanho_lote])
                k = len(Sc)
                args = (np.broadcast_to(Sp, (k,) + Sp.shape[1:]), np.broadcast_to(hp, (k,) + hp.shape[1:]), Sc, np.broadcast_to(vp, (k,) + vp.shape[1:]), hc)
                ff, qq = m.efeito_com_vontade(*args, self.vontade_falha, self.vontade_quebra, conf) if vontade else m.efeito(*args)
                f[a:a + k], q[a:a + k] = (ff, qq)
            fs.append(f)
            qs.append(q)
        return (np.stack(fs), np.stack(qs))

    def _vontade_ligada(self):
        return bool(self.vontade_falha or self.vontade_quebra or self.confianca_por_clausula)

    def _confianca(self):
        if not self.confianca_por_clausula or self.erro_por_clausula is None:
            return None
        return (1.0 / (1.0 + self.erro_por_clausula / 0.05)).astype(np.float32)

    def _medir_o_proprio_erro(self, ok):
        novas = ok[ok >= self._n_no_ultimo_treino]
        self._n_no_ultimo_treino = len(self.fotos)
        if len(novas) < 16:
            return
        ids = novas[-512:]
        B = self.bits_das_fotos(ids)
        alvo = self._alvo_de_veredito(ids)[:, 1:1 + self.NC]
        pv = np.mean([m.veredito(m.ler(B.astype(m.dtype))[1])[1] for m in self.rede.membros], 0)
        e = np.abs(pv - alvo).mean(0)
        self.erro_por_clausula = e if self.erro_por_clausula is None else 0.7 * self.erro_por_clausula + 0.3 * e

    def notas_dos_filhos(self, pai, Bc, conjunto=None, peso=None):
        f, q = self._fq_de_bits(pai, Bc, conjunto)
        a = pai.phi[None, :self.n_duras]
        N = np.stack([self._nota(f[m], q[m], np.broadcast_to(a, (f.shape[1], a.shape[1])), peso) for m in range(len(f))])
        return (N.mean(0), N.std(0), N)

    def _fq_das_piscinas(self, itens, conjunto=None, tamanho_lote=512):
        conj = conjunto or self.rede
        pais = np.array([it.pai for it in itens], np.int64)
        tam = np.array([len(it.filhos) for it in itens])
        off = np.concatenate([[0], np.cumsum(tam)])
        filhos = np.concatenate([it.filhos for it in itens]) if itens else np.zeros(0, np.int64)
        dono = np.repeat(np.arange(len(itens)), tam)
        up, inv = np.unique(pais, return_inverse=True)
        Bp = self.bits_das_fotos(up)
        Vp = self.contexto_das_fotos(up)
        phi_p = self._colunas(up)[3][:, :self.n_duras]
        fs, qs = ([], [])
        for m in conj.membros:
            Sp, hp, _ = m.ler(Bp.astype(m.dtype))
            f = np.empty(len(filhos))
            q = np.empty((len(filhos), self.P))
            for a in range(0, len(filhos), tamanho_lote):
                ids = filhos[a:a + tamanho_lote]
                pi = inv[dono[a:a + tamanho_lote]]
                Sc, hc, _ = m.ler(self.bits_das_fotos(ids).astype(m.dtype))
                ff, qq = m.efeito(Sp[pi], hp[pi], Sc, Vp[pi].astype(m.dtype), hc)
                f[a:a + len(ids)], q[a:a + len(ids)] = (ff, qq)
            fs.append(f)
            qs.append(q)
        return (np.stack(fs), np.stack(qs), phi_p[inv[dono]] if len(filhos) else np.zeros((0, self.n_duras)), off)

    def _notas_compostas(self, f, q, a_duras, peso=None):
        return np.stack([self._nota(f[m], q[m], a_duras, peso) for m in range(len(f))])

    @staticmethod
    def _top1(nota_media, itens, off):
        return np.array([float(it.y[int(np.argmin(nota_media[off[i]:off[i + 1]]))]) for i, it in enumerate(itens)])

    def escrever(self, pai, n, g=None, ja=None, temperatura=None, epsilon=None, conjunto=None):
        g = g or self.g
        cfg = self.config_de_escrita
        T = float(cfg['temperatura'] if temperatura is None else temperatura)
        eps = float(cfg['epsilon'] if epsilon is None else epsilon)
        conj = conjunto or self.rede
        geo, cod = (self.geo, self.cod)
        ja = set() if ja is None else ja
        lg, leit = (0.0, [])
        for m in conj.membros:
            S, h, _ = m.ler(pai.bits[None, :].astype(m.dtype))
            v = np.asarray(pai.v, m.dtype)
            leit.append((m, h, v))
            lg = lg + m.lugar_logits(h, v)[0]
        lg = lg / len(conj.membros)
        lg = np.where(pai.vivo, lg, RF.MENOS_INF)
        pr = _softmax(lg / max(T, 0.001))
        viv = pai.vivo.astype(np.float64)
        pr = (1.0 - eps) * pr + eps * viv / viv.sum()
        out = []
        for _ in range(3):
            if len(out) >= n:
                break
            k_pedir = int(n * 1.5) + 4
            locs = g.choice(geo.nL, size=k_pedir, p=pr / pr.sum())
            ks = geo.lugar_k[locs]
            ps = geo.lugar_p[locs]
            velho = np.zeros((len(locs), geo.KL), np.float32)
            for i in range(len(locs)):
                velho[i, :int(ks[i])] = pai.bits[int(ps[i]):int(ps[i]) + int(ks[i])]
            zb = 0.0
            for m, h, v in leit:
                zb = zb + m.bits_logits(np.repeat(h, len(locs), 0), np.repeat(v, len(locs), 0), velho.astype(m.dtype), locs)
            zb = zb / len(conj.membros)
            pb = RF._sigmoide(zb / max(T, 0.001))
            kmask = np.arange(geo.KL)[None, :] < ks[:, None]
            era = velho > 0.5
            vira = ((g.random(pb.shape) < pb) != era) & kmask
            nenhum = ~vira.any(1)
            for i in np.flatnonzero(nenhum):
                muda = np.where(era[i], 1.0 - pb[i], pb[i])
                vira[i, int(np.argmax(np.where(kmask[i], muda, -1.0)))] = True
            for i in range(len(locs)):
                if len(out) >= n:
                    break
                k, p = (int(ks[i]), int(ps[i]))
                novo = pai.bits[p:p + k].copy() ^ vira[i, :k].astype(np.uint8)
                seq = _bits_para_int(novo)
                filho = cod.aplicar(pai.bits, p, k, seq)
                if filho is None:
                    continue
                ch = cod.chave(filho)
                if ch == pai.chave or ch in ja:
                    continue
                ja.add(ch)
                tipo = {'gene': 'bits' if int(vira[i, :k].sum()) <= 3 and k > 3 else 'gene', 'unidade': 'unidade', 'unidades': 'unidades'}[geo.lugar_tipo[int(locs[i])]]
                out.append(EF.Candidato(tipo, p, k, seq, filho, 'modelo'))
        return out

    def propor(self, pai, braco, K, g=None, cfg=None, n=None):
        g = g or self.g
        if braco == 'operador':
            return ('operador', EF.amostrar_operador(pai, self.mapa, K, g))
        if braco == 'aprendida' and self.pronto():
            c = cfg or self.config_de_escrita
            total = int(n) if n is not None else self.total_avaliado
            k_cega = max(0, min(int(round(int(c['k_cega']) * total / float(self.total_avaliado))), total - 1))
            pool = int(c['pool'])
            n_rede = int(round(pool * float(c.get('fracao_da_rede', 0.5))))
            escritas = self.escrever(pai, n_rede, g, temperatura=c['temperatura'], epsilon=c['epsilon'])
            n_da_rede = len(escritas)
            ja = {pai.chave} | {self.cod.chave(c_.bits) for c_ in escritas}
            escritas += EF.amostrar_cego(pai, self.mapa, pool - len(escritas), g, ja, self.mistura)
            out = []
            if escritas:
                nota, _, _ = self.notas_dos_filhos(pai, np.stack([c_.bits for c_ in escritas]).astype(np.float32))
                ordem = np.argsort(nota, kind='stable')
                escolhidas = ordem[:total - k_cega]
                self.ultima_escolha = {'pool': len(escritas), 'da_rede': n_da_rede, 'corte': float(nota[escolhidas[-1]]) if len(escolhidas) else None, 'nota_quantis': [round(float(np.quantile(nota, q)), 5) for q in (0.0, 0.1, 0.5, 0.9, 1.0)], 'notas': {self.cod.chave(escritas[int(i)].bits): round(float(nota[int(i)]), 5) for i in escolhidas}}
                for i in escolhidas:
                    c_ = escritas[int(i)]
                    if c_.origem == 'cega':
                        c_.origem = 'filtro'
                    out.append(c_)
            ja = {pai.chave} | {self.cod.chave(c_.bits) for c_ in out}
            out += EF.amostrar_cego(pai, self.mapa, total - len(out), g, ja, self.mistura)
            return ('aprendida', out)
        return ('cega' if braco == 'cega' else 'fria', EF.amostrar_cego(pai, self.mapa, K, g, mistura=self.mistura))

    def propor_piscina(self, pai, M_=None, g=None):
        return EF.amostrar_cego(pai, self.mapa, M_ or self.piscina_m, g or self.g, mistura=self.mistura)

    def _registrar_padrao_g(self, pai, c, y, ver_filho):
        if c.tipo in ('operador', 'janela', 'unidade', 'unidades', 'doador') or c.k == 0:
            return
        mapa = self.mapa
        i = int(mapa.campo_de[c.p])
        nb, p0 = (int(mapa.bits_do_campo[i]), int(mapa.inicio[i]))
        if c.p + c.k > p0 + nb:
            return
        papel = int(mapa.papel[i])
        if c.p == p0 and c.k == nb:
            chave = (c.k, 0, papel, c.seq)
        elif c.tipo == 'bits' or c.k <= 3:
            chave = (c.k, c.p - p0 + 1, EF.REL + papel, EF._janela(pai.bits, c.p, c.k) ^ c.seq)
        else:
            return
        fix = pai.comp & ~int(ver_filho['comportamento']) & self._mascara_das_duras()
        quebra = ~pai.comp & int(ver_filho['comportamento']) & self._mascara_total()
        self.biblioteca.registrar(chave[0], chave[1], chave[2], chave[3], y, fix, quebra)

    def _linha_da_edicao(self, pai, c, filho_bits):
        if c.k <= 0:
            return (-1, 0, 0)
        loc = self.geo.lugar_da_edicao(c.p, c.k)
        if loc < 0:
            return (-1, 0, 0)
        p0, k0 = (int(self.geo.lugar_p[loc]), int(self.geo.lugar_k[loc]))
        dif = (pai.bits[p0:p0 + k0] != np.asarray(filho_bits, np.uint8)[p0:p0 + k0]).astype(np.uint8)
        if not dif.any():
            return (-1, 0, 0)
        return (loc, _bits_para_int(dif), k0)

    def registrar(self, pai, pai_foto, c, ver_filho, braco, gen=0, passo=0, filho_id=None):
        ok = ver_filho['estado'] == 'ok'
        y = EF.alvo(pai.dist, ver_filho['distancia']) if ok else EF.CLIP_DO_ALVO
        y_mem = y if self.rotulo_por_d is None else self._y_de_treino(pai.ver, ver_filho)
        mudou = int(ver_filho['comportamento']) != pai.comp
        if filho_id is not None and filho_id >= 0 and (pai_foto >= 0):
            loc, vira, k0 = self._linha_da_edicao(pai, c, c.bits)
            self.mem.adicionar(pai_foto, filho_id, y_mem, loc, vira, k0, EF.TIPOS.index(c.tipo), int(c.origem in EF.ORIGENS_SEM_MODELO), gen)
        self._registrar_padrao_g(pai, c, y, ver_filho)
        self.contadores['edicoes_avaliadas'] += 1
        self.contadores['edicoes_que_mudaram_o_comportamento'] += int(mudou)
        return y

    def registrar_rodada(self, braco, propostas, ys):
        if braco not in self.vel:
            return
        melhorou = bool(len(ys) and min(ys) < 0)
        self.vel[braco][0] += 1
        self.vel[braco][1] += int(melhorou)
        self.vel[braco][2] += len(ys)
        self.contadores['rodadas'] += 1
        for c, y in zip(propostas, ys):
            nome = {'modelo': 'do_modelo', 'filtro': 'do_filtro', 'biblioteca': 'da_biblioteca', 'cega': 'as_cegas', 'operador': 'do_operador'}.get(c.origem, 'as_cegas')
            self.contadores['propostas_' + nome] = self.contadores.get('propostas_' + nome, 0) + 1
            if y < 0:
                self.contadores['melhoras_' + nome] = self.contadores.get('melhoras_' + nome, 0) + 1

    def registrar_piscina(self, pai, pai_foto, cands, vers, rodada=0, destino='piscina', ids=None):
        if len(cands) < 6 or ids is None or pai_foto < 0:
            return
        ys = np.array([EF.alvo(pai.dist, v['distancia']) if v['estado'] == 'ok' else EF.CLIP_DO_ALVO for v in vers], np.float32)
        for c, v, y in zip(cands, vers, ys):
            self._registrar_padrao_g(pai, c, float(y), v)
        if self.rotulo_por_d is not None:
            ys = np.array([self._y_de_treino(pai.ver, v) for v in vers], np.float32)
        self.seq += 1
        if destino == 'piscina':
            self.piscinas.adicionar(Piscina(pai_foto, ids, ys, self.seq))
            self._crescer_banco(len(self.fotos) + 1)
            for k in ids:
                if k >= 0:
                    self._no_banco[int(k)] = True
        else:
            for c, v, y, k in zip(cands, vers, ys, ids):
                if k >= 0:
                    loc, vira, k0 = self._linha_da_edicao(pai, c, c.bits)
                    self.mem.adicionar(pai_foto, int(k), float(y), loc, vira, k0, EF.TIPOS.index(c.tipo), 1, rodada)
        self.contadores['piscinas_rotuladas'] += 1
        self.contadores['edicoes_avaliadas'] += len(cands)

    def atualizar_motivos(self, arquivo, g=None):
        self._crescer_banco(len(arquivo) + 1)
        return self.motivos.atualizar(arquivo, g if g is not None else self.g, excluir=self._intocadas[:len(arquivo)])

    def _contexto_e_phi(self, ids):
        d, nf, viol, phi = self._colunas(ids)
        return (self.rede.membros[0].contexto(d, nf, viol, phi).astype(np.float32), phi)

    def _lote_critico(self, n, g):
        idx, w = self.mem.amostrar_critico(n, g, self._proibidos())
        if len(idx) == 0:
            return None
        pai, filho = (self.mem.coluna('pai')[idx], self.mem.coluna('filho')[idx])
        vp, phi_p = self._contexto_e_phi(pai)
        phi_c = self._colunas(filho)[3]
        return dict(Bp=self.bits_das_fotos(pai), Bc=self.bits_das_fotos(filho), vp=vp, y=self.mem.y[idx].astype(np.float32), troca=np.abs(phi_c - phi_p).astype(np.float32), w=w.astype(np.float32))

    def _linhas_de_escrita(self, Bp, loc, vira, k):
        KL = self.geo.KL
        n = len(loc)
        velho = np.zeros((n, KL), np.float32)
        viraM = np.zeros((n, KL), np.float32)
        kmask = np.zeros((n, KL), np.float32)
        for i in range(n):
            ki, pi = (int(k[i]), int(self.geo.lugar_p[int(loc[i])]))
            velho[i, :ki] = Bp[i, pi:pi + ki]
            kmask[i, :ki] = 1.0
            viraM[i, :ki] = [int(vira[i]) >> ki - 1 - t & 1 for t in range(ki)]
        return (velho, viraM, kmask)

    def _lote_escritor(self, n, g):
        n_auto = n // 3 if len(self.auto) >= 16 else 0
        idx = self.mem.amostrar_escritor(n - n_auto, g, self._proibidos())
        pai = self.mem.coluna('pai')[idx] if len(idx) else np.zeros(0, np.int64)
        loc = self.mem.coluna('loc')[idx] if len(idx) else np.zeros(0, np.int32)
        vira = self.mem.coluna('vira')[idx] if len(idx) else np.zeros(0, np.int64)
        k = self.mem.coluna('k')[idx] if len(idx) else np.zeros(0, np.int16)
        w = np.ones(len(idx), np.float32)
        if n_auto:
            j = g.choice(len(self.auto), n_auto, p=self.auto.w / self.auto.w.sum())
            pai, loc, vira, k = (np.concatenate([pai, self.auto.pai[j]]), np.concatenate([loc, self.auto.loc[j]]), np.concatenate([vira, self.auto.vira[j]]), np.concatenate([k, self.auto.k[j]]))
            w = np.concatenate([w, np.full(n_auto, 0.5, np.float32)])
        if len(pai) == 0:
            return None
        Bp = self.bits_das_fotos(pai)
        velho, viraM, kmask = self._linhas_de_escrita(Bp, loc, vira, k)
        return dict(Bp=Bp, vp=self._contexto_e_phi(pai)[0], loc=loc.astype(np.int64), velho=velho, vira=viraM, kmask=kmask, w=w)

    def _alvo_de_veredito(self, ids):
        d, nf, viol, phi = self._colunas(ids)
        return np.concatenate([d[:, :1], viol, phi], axis=1).astype(np.float32)

    def _lote_veredito(self, n, g, ok, boas):
        ids = np.concatenate([g.choice(ok, n // 2), g.choice(boas, n - n // 2)])
        return dict(B=self.bits_das_fotos(ids), alvo=self._alvo_de_veredito(ids), w=np.ones(len(ids), np.float32))

    def _universo_do_veredito(self):
        N = len(self.fotos)
        d = self.fotos.distancias()
        livres = ~self._proibidos()[:N]
        ok = np.flatnonzero((d >= 0) & livres)
        if len(ok) < 16:
            return (None, None)
        return (ok, ok[np.argsort(d[ok], kind='stable')[:max(16, len(ok) // 4)]])

    def treinar(self, passos=25, lote=128):
        if len(self.fotos) < 32:
            return
        ok, boas = self._universo_do_veredito()
        if ok is None:
            return
        if self.confianca_por_clausula:
            self._medir_o_proprio_erro(ok)
        tem = self.mem.proprios() >= 64
        escreve = tem and (self.mem.n_que_melhoraram() >= 16 or len(self.auto) >= 16)
        for m in self.rede.membros:
            for _ in range(passos):
                m.passo(self._lote_critico(lote, self.g) if tem else None, self._lote_escritor(lote, self.g) if escreve else None, self._lote_veredito(lote, self.g, ok, boas))
        if tem:
            self.treinos += 1

    def colher_autoimitacao(self, n_pais=24, n_cand=64, top=2, margem=0.05, g=None):
        g = g or self.g
        c = self.curva()
        if c is None or c.get('erro_padrao_dev') is None or (not c['ganho_dev'] + 2 * c['erro_padrao_dev'] < 0):
            return 0
        ok, boas = self._universo_do_veredito()
        if ok is None:
            return 0
        ids = np.concatenate([g.choice(boas, n_pais // 2), g.choice(ok, n_pais - n_pais // 2)])
        guardou = 0
        for k_ in ids:
            pai = self.pai(self.fotos.foto(int(k_)), self.fotos.veredito(int(k_)))
            cs = self.escrever(pai, n_cand // 2, g)
            cs += EF.amostrar_cego(pai, self.mapa, n_cand - len(cs), g, {pai.chave} | {self.cod.chave(x.bits) for x in cs}, self.mistura)
            if len(cs) < 8:
                continue
            f, q = self._fq_de_bits(pai, np.stack([x.bits for x in cs]).astype(np.float32))
            fm = f.mean(0)
            a = pai.phi[None, :self.n_duras]
            nota = self._notas_compostas(f, q, np.broadcast_to(a, (f.shape[1], a.shape[1]))).mean(0)
            for i in np.argsort(nota, kind='stable')[:top]:
                if fm[i] < -margem:
                    loc, vira, k0 = self._linha_da_edicao(pai, cs[int(i)], cs[int(i)].bits)
                    if loc >= 0:
                        self.auto.adicionar(int(k_), loc, vira, k0, float(min(-fm[i], 2.0)))
                        guardou += 1
        self.contadores['autoimitacoes'] += guardou
        return guardou

    def _erro_do_veredito(self, ids):
        B = self.bits_das_fotos(ids)
        alvo = self._alvo_de_veredito(ids)
        z_d, z_v, p_f = ([], [], [])
        for m in self.rede.membros:
            _, h, _ = m.ler(B.astype(m.dtype))
            dd, vv, pp = m.veredito(h)
            z_d.append(dd)
            z_v.append(vv)
            p_f.append(pp)
        pd_, pv, pf = (np.mean(z_d, 0), np.mean(z_v, 0), np.clip(np.mean(p_f, 0), 1e-06, 1 - 1e-06))
        perda = float(((pd_ - alvo[:, 0]) ** 2 + ((pv - alvo[:, 1:1 + self.NC]) ** 2).mean(1)).mean() / 2 - np.mean(alvo[:, 1 + self.NC:] * np.log(pf) + (1 - alvo[:, 1 + self.NC:]) * np.log(1 - pf)))
        corr = float(np.corrcoef(pd_, alvo[:, 0])[0, 1]) if np.std(pd_) > 0 and np.std(alvo[:, 0]) > 0 else 0.0
        return (perda, corr, float(np.abs(pv - alvo[:, 1:1 + self.NC]).mean()))

    def treinar_a_intencao(self, passos=100, lote=128, blocos=10, paciencia=2):
        ok, _ = self._universo_do_veredito()
        if ok is None or passos <= 0:
            return {'pulou': 'poucas fotos medidas ou nenhum passo'}
        g = self.g
        perm = g.permutation(ok)
        n_teste = max(8, len(ok) // 7)
        teste, treino = (perm[:n_teste], perm[n_teste:])
        d = self.fotos.distancias()
        boas = treino[np.argsort(d[treino], kind='stable')[:max(16, len(treino) // 4)]]
        perdas, melhor, sem_melhora, blocos_feitos = ([], np.inf, 0, 0)
        for _ in range(max(int(blocos), 1)):
            for m in self.rede.membros:
                for _ in range(passos):
                    m.passo(None, None, self._lote_veredito(lote, g, treino, boas))
            blocos_feitos += 1
            perda = self._erro_do_veredito(teste)[0]
            perdas.append(round(perda, 5))
            if perda < 0.99 * melhor:
                melhor, sem_melhora = (perda, 0)
            else:
                sem_melhora += 1
                if sem_melhora >= int(paciencia):
                    break
        _, corr, erro_viol = self._erro_do_veredito(teste)
        return {'passos': int(passos * blocos_feitos), 'blocos': blocos_feitos, 'parou_por': 'o erro de fora deixou de cair' if blocos_feitos < max(int(blocos), 1) else 'o teto de blocos', 'membros': len(self.rede), 'fotos_de_treino': int(len(treino)), 'fotos_fora_do_treino': int(len(teste)), 'perda_de_fora_por_bloco': perdas, 'correlacao_do_veredito_previsto_com_o_de_V': round(corr, 4), 'erro_medio_da_violacao_por_clausula': round(erro_viol, 4)}

    def particoes(self, externas=None):
        ordem = sorted(self.piscinas.itens, key=lambda it: it.seq)
        n = len(ordem)
        return (ordem[n // 2:], ordem[:int(n * 0.3)] + list(externas or []))

    def _amostra_do_professor(self, conj, Bp, vp, g):
        geo = self.geo
        n = len(Bp)
        lg, leit = (0.0, [])
        for m in conj.membros:
            _, h, _ = m.ler(Bp.astype(m.dtype))
            leit.append((m, h))
            lg = lg + m.lugar_logits(h, vp.astype(m.dtype))
        lg = lg / len(conj.membros)
        pr = np.exp(lg - lg.max(1, keepdims=True))
        pr /= pr.sum(1, keepdims=True)
        loc = np.array([g.choice(geo.nL, p=pr[i]) for i in range(n)])
        k = geo.lugar_k[loc]
        velho, _, kmask = self._linhas_de_escrita(Bp, loc, np.zeros(n, np.int64), k)
        zb = 0.0
        for m, h in leit:
            zb = zb + m.bits_logits(h, vp.astype(m.dtype), velho.astype(m.dtype), loc)
        pb = RF._sigmoide(zb / len(conj.membros))
        vira = (((g.random(pb.shape) < pb) != (velho > 0.5)) * kmask).astype(np.float32)
        return dict(Bp=Bp, vp=vp, loc=loc.astype(np.int64), velho=velho, vira=vira, kmask=kmask, w=np.ones(n, np.float32))

    def _destilar(self, cand, conj, g, passos, lote):
        ok, boas = self._universo_do_veredito()
        for _ in range(passos):
            crit = self._lote_critico(lote, g)
            if crit is None or ok is None:
                break
            fs, qs = ([], [])
            for m in conj.membros:
                Sp, hp, _ = m.ler(crit['Bp'])
                Sc, hc, _ = m.ler(crit['Bc'])
                f, q = m.efeito(Sp, hp, Sc, crit['vp'], hc)
                fs.append(f)
                qs.append(q)
            crit['y'], crit['troca'], crit['w'] = (np.mean(fs, 0).astype(np.float32), np.mean(qs, 0).astype(np.float32), np.ones(len(fs[0]), np.float32))
            ids = np.concatenate([g.choice(ok, lote // 2), g.choice(boas, lote - lote // 2)])
            B = self.bits_das_fotos(ids)
            ds, vs, ps = ([], [], [])
            for m in conj.membros:
                _, h, _ = m.ler(B)
                d, v, p = m.veredito(h)
                ds.append(d)
                vs.append(v)
                ps.append(p)
            ver = dict(B=B, alvo=np.concatenate([np.mean(ds, 0)[:, None], np.mean(vs, 0), np.mean(ps, 0)], axis=1).astype(np.float32), w=np.ones(len(ids), np.float32))
            cand.passo(crit, self._amostra_do_professor(conj, crit['Bp'], crit['vp'], g), ver)

    def _construir_candidata(self, params, g, passos_destila, passos_treino, lote):
        op, conj, r = (params['op'], self.rede, self.reducao)
        if op == 'nova':
            esc = params['esc']
            h1 = max(4, int(round(esc[0] * r)))
            h2 = max(4, int(round((esc[1] if len(esc) > 1 else esc[0] // 2) * r)))
            d_f = max(2, int(round((8 if esc[0] <= 32 else 12 if esc[0] <= 64 else 16) * r)))
            cand = RF.RedeUnica(self.geo, self.NC, self.P, d_f=d_f, h=(h1, h2), d_c=max(4, int(96 * r)), d_w=max(4, int(96 * r)), d_b=max(4, int(64 * r)), d_e=max(2, int(16 * r)), d_vh=max(4, int(96 * r)), semente=int(g.integers(1 << 30)), lr=params['lr'], l2=params['l2'])
            self._destilar(cand, conj, g, passos_destila, lote)
            membro = None
        else:
            membro = int(params.get('membro', int(g.integers(len(conj)))) % len(conj))
            cand = conj.membros[membro].copiar()
            cand.lr, cand.l2 = (params['lr'], params.get('l2', 0.0))
            if op in ('alargar', 'degrau'):
                cand.alargar(params.get('extra', 8) or 8, g)
        ok, boas = self._universo_do_veredito()
        for _ in range(passos_treino):
            if ok is None:
                break
            cand.passo(self._lote_critico(lote, g), self._lote_escritor(lote, g) if self.mem.n_que_melhoraram() >= 16 else None, self._lote_veredito(lote, g, ok, boas))
        return (cand, membro)

    def rodada_de_selecao(self, externas=None, H_externa=None, minimo_dev=30, minimo_ret=15, max_degraus=6, passos_destila=60, passos_treino=60, lote=96):
        dev, ret = self.particoes(externas)
        reg = {'evento': 'candidata_escritor', 'K_dev': len(dev), 'K_ret': len(ret), 'membros': len(self.rede)}
        if len(dev) < minimo_dev or self.mem.proprios() < 300:
            return dict(reg, pulou='poucas piscinas ou pouca memória')
        conj, g = (self.rede, self.g)
        Mn = len(conj)
        f_d, q_d, a_d, off_d = self._fq_das_piscinas(dev)
        f_r, q_r, a_r, off_r = self._fq_das_piscinas(ret) if ret else (None, None, None, None)
        at_d = self._notas_compostas(f_d, q_d, a_d)
        at_r = self._notas_compostas(f_r, q_r, a_r) if ret else None
        politica = g.random() < 0.2
        if politica:
            opcoes = [w for w in ARQ_PESOS_SEMANTICOS if w != self.peso_semantico]
            w_novo = float(opcoes[int(g.integers(len(opcoes)))])
            params, cego, nota, membro, arquitetura = ({'op': 'politica', 'peso_semantico': w_novo}, False, 0.0, None, list(conj.membros[0].cfg['h']))
            novo_d = self._notas_compostas(f_d, q_d, a_d, w_novo).mean(0)
            novo_r = self._notas_compostas(f_r, q_r, a_r, w_novo).mean(0) if ret else None
        else:
            H = list(self.H) + list(H_externa or [])
            params, cego, nota = self.meta.propor(H, g, Mn)
            cand, membro = self._construir_candidata(params, g, passos_destila, passos_treino, lote)
            if membro is None:
                piores = [float(self._top1(at_d[m], dev, off_d).mean()) for m in range(Mn)]
                membro = int(np.argmax(piores))
            solo = CR.ConjuntoDeRedes([cand])
            fc, qc, _, _ = self._fq_das_piscinas(dev, solo)
            n_d = self._notas_compostas(fc, qc, a_d)[0]
            novo_d = (at_d.sum(0) - at_d[membro] + n_d) / Mn
            if ret:
                fc, qc, _, _ = self._fq_das_piscinas(ret, solo)
                novo_r = (at_r.sum(0) - at_r[membro] + self._notas_compostas(fc, qc, a_r)[0]) / Mn
            else:
                novo_r = None
            arquitetura = list(cand.cfg['h'])
        d_dev = self._top1(novo_d, dev, off_d) - self._top1(at_d.mean(0), dev, off_d)
        d_ret = self._top1(novo_r, ret, off_r) - self._top1(at_r.mean(0), ret, off_r) if ret else np.zeros(0)
        ok_dev, ok_ret = (M.passa_a_porta(d_dev, minimo_dev), M.passa_a_retencao(d_ret, minimo_ret))
        adotou = bool(ok_dev and ok_ret)
        g_antes, cap_antes = self._ganho_de_decisao(at_d.mean(0), dev, off_d)
        g_depois, cap_depois = self._ganho_de_decisao(novo_d, dev, off_d)
        if adotou:
            if politica:
                self.peso_semantico = float(params['peso_semantico'])
            else:
                self.rede = conj.com_membro(membro, cand)
        rd, rr = (M.resumo(d_dev), M.resumo(d_ret))

        def r6(x):
            return round(x, 6) if math.isfinite(x) else None
        reg.update(tipo='politica' if politica else 'rede', params=params, cego=bool(cego), nota_do_meta_modelo=round(nota, 5), membro_substituido=membro, arquitetura=arquitetura, d_dev=r6(rd['media']), se_dev=r6(rd['erro_padrao']), d_ret=r6(rr['media']), se_ret=r6(rr['erro_padrao']), passa_a_porta=bool(ok_dev), passa_a_retencao=bool(ok_ret), adotou=adotou, ganho_no_top1={'antes': r6(g_antes['media']), 'depois': r6(g_depois['media']), 'captura_antes': round(cap_antes, 4), 'captura_depois': round(cap_depois, 4)})
        (self.H_politica if politica else self.H).append({'params': params, 'd_dev': reg['d_dev'] if reg['d_dev'] is not None else 0.0})
        self.contadores['rodadas_de_selecao'] += 1
        self.contadores[('politicas' if politica else 'trocas') + ('_adotadas' if adotou else '_recusadas')] += 1
        return reg

    def _ganho_de_decisao(self, nota_media, itens, off):
        esc = self._top1(nota_media, itens, off)
        med = np.array([float(it.y.mean()) for it in itens])
        melhor = np.array([float(it.y.min()) for it in itens])
        cap = (med - esc).sum() / max((med - melhor).sum(), 1e-09)
        return (M.resumo(esc - med), float(cap))

    def _piscinas_notas(self, itens):
        f, q, a, off = self._fq_das_piscinas(itens)
        return (self._notas_compostas(f, q, a).mean(0), off)

    def curva(self, externas=None):
        dev, ret = self.particoes(externas)
        if len(dev) < 10:
            return None
        nota, off = self._piscinas_notas(dev)
        r_dev, cap_dev = self._ganho_de_decisao(nota, dev, off)
        out = {'piscinas_dev': r_dev['K'], 'ganho_dev': round(r_dev['media'], 5), 'erro_padrao_dev': round(r_dev['erro_padrao'], 5) if math.isfinite(r_dev['erro_padrao']) else None, 'captura_dev': round(cap_dev, 4)}
        if len(ret) >= 10:
            nota, off = self._piscinas_notas(ret)
            r_ret, cap_ret = self._ganho_de_decisao(nota, ret, off)
            out.update(piscinas_ret=r_ret['K'], ganho_ret=round(r_ret['media'], 5), captura_ret=round(cap_ret, 4))
        return out

    def desacordo_do_molde(self, pai, n=48, g=None):
        cs = self.escrever(pai, n, g or self.g)
        if len(cs) < 6:
            return None
        nota, sd, _ = self.notas_dos_filhos(pai, np.stack([c.bits for c in cs]).astype(np.float32))
        ix = np.argsort(nota, kind='stable')[:max(1, min(CR.K_DO_DESACORDO, len(nota)))]
        return float(sd[ix].mean())

    def teste_da_alocacao(self, max_piscinas=200, minimo=20):
        itens = self.piscinas.itens[-max_piscinas:]
        if len(itens) < minimo or len(self.rede) < 2:
            return {'pulou': 'poucas piscinas ou um membro só', 'piscinas': len(itens), 'membros': len(self.rede)}
        f, q, a, off = self._fq_das_piscinas(itens)
        N = self._notas_compostas(f, q, a)
        des, teto = ([], [])
        for i, it in enumerate(itens):
            s = N[:, off[i]:off[i + 1]]
            ix = np.argsort(s.mean(0), kind='stable')[:max(1, min(CR.K_DO_DESACORDO, s.shape[1]))]
            des.append(float(s.std(0)[ix].mean()))
            teto.append(-float(it.y.min()))
        out = CR.teste_da_alocacao(des, teto, minimo)
        out['membros'] = len(self.rede)
        return out

    def _significado_dados(self, itens):
        f, q, a, off = self._fq_das_piscinas(itens)
        filhos = np.concatenate([it.filhos for it in itens])
        pais = np.concatenate([np.full(len(it.filhos), it.pai) for it in itens])
        phi_f, phi_p = (self._colunas(filhos)[3], self._colunas(pais)[3])
        qm = q.mean(0)
        return (qm, phi_p, phi_f)

    def significado(self, itens=None, max_piscinas=120):
        itens = itens if itens is not None else self.piscinas.itens[-max_piscinas:]
        if len(itens) < 5:
            return None
        qm, pai, filho = self._significado_dados(itens)
        p = pai + (1.0 - 2.0 * pai) * qm
        eps = 1e-06
        bce = float(-(filho * np.log(p + eps) + (1 - filho) * np.log(1 - p + eps)).mean())
        pc = np.clip(pai, 0.02, 0.98)
        bce_copia = float(-(filho * np.log(pc) + (1 - filho) * np.log(1 - pc)).mean())
        troca = (filho != pai).astype(np.float64)
        taxa = np.clip(troca.mean(0), 0.0001, 1 - 0.0001)
        bce_acaso = float(-(taxa * np.log(taxa) + (1 - taxa) * np.log(1 - taxa)).mean())
        mudou = (filho != pai).reshape(-1)
        escore = np.abs(p - pai).reshape(-1)
        auc = None
        if mudou.any() and (~mudou).any():
            ordem = np.argsort(escore, kind='mergesort')
            rk = np.empty(len(escore))
            rk[ordem] = np.arange(1, len(escore) + 1)
            n1 = int(mudou.sum())
            auc = float((rk[mudou].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(escore) - n1)))
        return {'pares_edicao_sonda': int(len(mudou)), 'mudancas_de_estado': int(mudou.sum()), 'entropia_cruzada_do_modelo': round(bce, 5), 'entropia_cruzada_de_copiar_o_pai': round(bce_copia, 5), 'entropia_cruzada_do_acaso_calibrado': round(bce_acaso, 5), 'auc_de_prever_quais_sondas_mudam': round(auc, 4) if auc is not None else None}

    def significado_por_predicado(self, itens=None, max_piscinas=120):
        itens = itens if itens is not None else self.piscinas.itens[-max_piscinas:]
        if len(itens) < 5:
            return None
        q, pai, filho = self._significado_dados(itens)
        troca = filho != pai
        out = {}
        for j in range(self.P):
            t = troca[:, j]
            if 5 <= t.sum() < len(t) - 5:
                ordem = np.argsort(q[:, j], kind='mergesort')
                rk = np.empty(len(q))
                rk[ordem] = np.arange(1, len(q) + 1)
                n1 = int(t.sum())
                out[self.problema.nomes_dos_predicados[j]] = {'mudancas': n1, 'auc': round(float((rk[t].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(q) - n1))), 3)}
        return out

    def nome_do_lugar(self, i):
        geo, cod = (self.geo, self.cod)
        i = int(i)
        if geo.lugar_tipo[i] == 'gene':
            return cod.campos[i]['nome']
        return f'{geo.lugar_tipo[i]}@{int(geo.lugar_p[i])} ({cod.nomes_dos_grupos[int(self.mapa.grupo_de[int(geo.lugar_p[i])])]})'

    def o_que_a_rede_escreve(self, arquivo, quantos=15, pais=20):
        ids = arquivo.melhores(pais)
        if not ids:
            return []
        B = self.bits_das_fotos(ids)
        V = self.contexto_das_fotos(ids)
        lg = 0.0
        hs = []
        for m in self.rede.membros:
            _, h, _ = m.ler(B.astype(m.dtype))
            hs.append(h)
            lg = lg + m.lugar_logits(h, V.astype(m.dtype))
        lg = lg / len(self.rede.membros)
        pr = np.exp(lg - lg.max(1, keepdims=True))
        pr /= pr.sum(1, keepdims=True)
        media = pr.mean(0)
        out = []
        for i in np.argsort(-media)[:quantos]:
            k, p0 = (int(self.geo.lugar_k[i]), int(self.geo.lugar_p[i]))
            velho = np.zeros((len(ids), self.geo.KL), np.float32)
            velho[:, :k] = B[:, p0:p0 + k]
            zb = 0.0
            for m, h in zip(self.rede.membros, hs):
                zb = zb + m.bits_logits(h, V.astype(m.dtype), velho.astype(m.dtype), np.full(len(ids), int(i)))
            pn = RF._sigmoide(zb / len(self.rede.membros))[:, :k]
            pv = np.where(velho[:, :k] > 0.5, 1.0 - pn, pn).mean(0)
            out.append({'lugar': self.nome_do_lugar(i), 'probabilidade_de_escolher': round(float(media[i]), 4), 'probabilidade_media_de_virar_cada_bit': [round(float(x), 3) for x in pv], 'conteudo_que_a_rede_escreve_no_lugar (prob. de cada bit ser 1)': [round(float(x), 3) for x in pn.mean(0)]})
        return out

    def velocidade(self):
        out = {}
        for b in self.vel:
            atual, antes = (self.vel[b], self._vel_anterior[b])
            d = [a - c for a, c in zip(atual, antes)]
            out[b] = {'passos': d[0], 'melhoraram': d[1], 'avaliacoes': d[2], 'melhoras_por_mil_avaliacoes': round(1000.0 * d[1] / d[2], 4) if d[2] else None}
            self._vel_anterior[b] = list(atual)
        return out

    def _padrao_legivel(self, chave, entrada):
        k, o, banda, seq = chave
        t, mel, soma, fix, qb = entrada
        relativo = banda >= EF.REL
        papel = banda - EF.REL if relativo else banda
        nomes = self.problema.nomes_dos_predicados
        return {'papel': self.mapa.nomes_dos_papeis[papel] if 0 <= papel < len(self.mapa.nomes_dos_papeis) else str(papel), 'tipo': 'mascara_xor' if relativo else 'valor_do_campo', 'k': int(k), 'deslocamento_no_campo': int(o - 1) if relativo else 0, 'sequencia': format(int(seq), f'0{int(k)}b'), 'tentativas': int(t), 'melhoras': int(mel), 'taxa': round(mel / t, 4), 'delta_medio': round(soma / t, 4), 'sondas_que_mais_conserta': [nomes[int(p)] for p in np.argsort(-fix)[:3] if fix[p] > 0 and int(p) < len(nomes)]}

    def padroes(self, arquivo=None, quantos=20, minimo=8):
        y = self.mem.y
        linhas = [(k, e) for k, e in self.biblioteca.d.items() if e[0] >= minimo and e[1] > 0]
        linhas.sort(key=lambda ke: (-(ke[1][1] / ke[1][0]), -ke[1][0]))
        out = {'exemplos_proprios': int(len(y)), 'edicoes_que_melhoraram': int((y < 0).sum()), 'padroes_na_biblioteca': self.biblioteca.tamanho(), 'membros_do_conjunto': len(self.rede), 'parametros_da_rede': int(self.rede.n_parametros()), 'padroes_de_bits_que_mais_melhoraram': [self._padrao_legivel(k, e) for k, e in linhas[:quantos]], 'sondas': self.sondas.descricao()}
        if arquivo is not None and len(arquivo) > 0 and self.pronto():
            out['o_que_a_rede_escreve'] = self.o_que_a_rede_escreve(arquivo, quantos)
        if self.motivos.tem:
            out['motivos_nos_bons_corpus'] = self.motivos.relatorio(self.biblioteca.d, quantos)
        sig = self.significado_por_predicado()
        if sig:
            out['significado_que_o_modelo_sabe_prever'] = sig
        c = self.curva()
        if c:
            out['ganho_de_decisao_no_top1_contra_o_sorteio'] = c
        return out

    def salvar(self, pasta, conhecimento=None, rotulo=None):
        os.makedirs(pasta, exist_ok=True)
        self.mem.salvar(os.path.join(pasta, 'aprendiz_memoria.npz'))
        self.piscinas.salvar(os.path.join(pasta, 'aprendiz_piscinas.npz'))
        self.biblioteca.salvar(os.path.join(pasta, 'aprendiz_biblioteca.npz'))
        self.auto.salvar(os.path.join(pasta, 'aprendiz_autoimitacao.npz'))
        pesos = {}
        for i, m in enumerate(self.rede.membros):
            for k, v in m.W.items():
                pesos[f'm{i}__{k}'] = v
        tmp = os.path.join(pasta, 'aprendiz_conjunto.tmp.npz')
        np.savez_compressed(tmp, **pesos)
        os.replace(tmp, os.path.join(pasta, 'aprendiz_conjunto.npz'))
        cfgs = [{'cfg': m.cfg, 'lr': m.lr, 'l2': m.l2, 'peso_c': m.peso_c, 'pesos_perda': m.pesos_perda} for m in self.rede.membros]
        with open(os.path.join(pasta, 'aprendiz_estado.json'), 'w', encoding='utf-8') as f:
            json.dump({'treinos': self.treinos, 'seq': self.seq, 'contadores': self.contadores, 'H': self.H, 'H_politica': self.H_politica, 'vel': self.vel, 'peso_semantico': self.peso_semantico, 'config_de_escrita': self.config_de_escrita, 'cfgs': cfgs, 'reducao': self.reducao}, f)

    def carregar(self, pasta, semente=0):
        m_ = os.path.join(pasta, 'aprendiz_memoria.npz')
        if not os.path.exists(m_) or not os.path.exists(os.path.join(pasta, 'aprendiz_estado.json')):
            return False
        self.mem = MemoriaDeEdicoes.carregar(m_, teto=self.mem.teto, semente=semente)
        self.piscinas = BancoDePiscinas.carregar(os.path.join(pasta, 'aprendiz_piscinas.npz'), semente=semente)
        self.biblioteca = E.Biblioteca.carregar(os.path.join(pasta, 'aprendiz_biblioteca.npz'), 0)
        self.auto = MemoriaDeAutoimitacao.carregar(os.path.join(pasta, 'aprendiz_autoimitacao.npz'))
        self._crescer_banco(len(self.fotos) + 1)
        self._no_banco[:] = False
        for it in self.piscinas.itens:
            self._no_banco[it.filhos[it.filhos < len(self._no_banco)]] = True
        e = json.load(open(os.path.join(pasta, 'aprendiz_estado.json'), encoding='utf-8'))
        self.treinos, self.seq, self.H, self.H_politica = (int(e.get('treinos', 0)), int(e.get('seq', 0)), list(e.get('H', [])), list(e.get('H_politica', [])))
        self.contadores.update(e.get('contadores', {}))
        for b, v in e.get('vel', {}).items():
            if b in self.vel:
                self.vel[b] = list(v)
                self._vel_anterior[b] = list(v)
        self.peso_semantico = float(e.get('peso_semantico', self.peso_semantico))
        self.config_de_escrita = dict(e.get('config_de_escrita', self.config_de_escrita))
        z = np.load(os.path.join(pasta, 'aprendiz_conjunto.npz'))
        membros = []
        for i, c in enumerate(e['cfgs']):
            W = {k.split('__', 1)[1]: z[k] for k in z.files if k.startswith(f'm{i}__')}
            membros.append(RF.RedeUnica.de_estado(self.geo, {'cfg': c['cfg'], 'NC': self.NC, 'P': self.P, 'lr': c['lr'], 'l2': c['l2'], 'peso_c': c['peso_c'], 'pesos_perda': c['pesos_perda'], 'W': W}))
        self.rede = CR.ConjuntoDeRedes(membros)
        return True
