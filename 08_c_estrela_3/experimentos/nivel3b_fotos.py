# -*- coding: utf-8 -*-
import glob
import hashlib
import json
import os
import shutil
import zipfile
import numpy as np
ORIGENS = ('partida', 'arquivo', 'lateral', 'colhida', 'estado_melhor', 'semente_mao', 'semente_cruzada', 'escrita_aprendida', 'escrita_cega', 'escrita_fria', 'edicao', 'retirada')
CLASSES = ('cumpre D', 'a 1 falha de D', '2 a 3 falhas', '4 a 8 falhas', '9 a 32 falhas', 'mais de 32 falhas', 'sem classe')
LIMITES_DE_CLASSE = (0, 1, 3, 8, 32)
MASCARA64 = (1 << 64) - 1
ESPACO_MINIMO = 300 * 1024 * 1024

def canonica(n, prefixo, rede):
    ultimo = [0] * n
    for i, j in prefixo:
        ultimo[i] = ultimo[j] = max(ultimo[i], ultimo[j]) + 1
    camadas = {}
    for i, j in rede:
        i, j = (int(i), int(j)) if i < j else (int(j), int(i))
        t = max(ultimo[i], ultimo[j]) + 1
        ultimo[i] = ultimo[j] = t
        camadas.setdefault(t, []).append((i, j))
    out = []
    for t in sorted(camadas):
        out.extend(sorted(camadas[t]))
    return out

def distancia_a_D(total, falhas, retirada_minima, recorde):
    if recorde is None:
        return None
    if total < recorde:
        return int(falhas)
    if total == recorde and falhas == 0 and (retirada_minima is not None) and (retirada_minima >= 0):
        return int(retirada_minima)
    return None

def classe_da_distancia(d):
    if d is None or d < 0:
        return len(CLASSES) - 1
    for k, lim in enumerate(LIMITES_DE_CLASSE):
        if d <= lim:
            return k
    return len(CLASSES) - 2

def _chave(arr, total):
    return int.from_bytes(hashlib.blake2b(arr.tobytes() + int(total).to_bytes(4, 'little'), digest_size=8).digest(), 'little')

def _dividir(v):
    v = int(v)
    return (v & MASCARA64, v >> 64 & MASCARA64)

def _juntar(lo, hi):
    return int(lo) | int(hi) << 64

def _crescer(a, cap, pad=0):
    b = np.full((cap,) + a.shape[1:], pad, a.dtype)
    b[:len(a)] = a
    return b

def _espaco_livre(pasta):
    try:
        return shutil.disk_usage(pasta).free
    except OSError:
        return ESPACO_MINIMO * 100

class Fotos:

    def __init__(self, semente=0, recorde=None):
        self.g = np.random.default_rng(semente + 909)
        self.recorde = recorde
        self._cap = 4096
        self.m = np.zeros(self._cap, np.uint16)
        self.off = np.zeros(self._cap, np.int64)
        self.total = np.zeros(self._cap, np.int32)
        self.falhas = np.zeros(self._cap, np.int32)
        self.retirada = np.full(self._cap, -1, np.int32)
        self.origem = np.zeros(self._cap, np.uint8)
        self.pai = np.full(self._cap, -1, np.int64)
        self.gen = np.zeros(self._cap, np.int32)
        self.comp_lo = np.zeros(self._cap, np.uint64)
        self.comp_hi = np.zeros(self._cap, np.uint64)
        self.sv = np.zeros(self._cap, np.uint16)
        self._buf = np.zeros(1 << 20, np.uint8)
        self._usado = 0
        self.N = 0
        self.chaves = {}
        self.vistas = 0
        self.repetidas = 0
        self.recusadas = 0
        self.cheio = False
        self.ultima_foi_nova = False
        self._salvas = 0
        self._sujas = set()
        self._pedacos = 0

    def __len__(self):
        return self.N

    def definir_recorde(self, recorde):
        self.recorde = recorde

    def _abrir_linha(self):
        if self.N >= self._cap:
            cap = self._cap * 2
            for nome, pad in (('m', 0), ('off', 0), ('total', 0), ('falhas', 0), ('retirada', -1), ('origem', 0), ('pai', -1), ('gen', 0), ('comp_lo', 0), ('comp_hi', 0), ('sv', 0)):
                setattr(self, nome, _crescer(getattr(self, nome), cap, pad))
            self._cap = cap

    def adicionar(self, rede, falhas, total, retirada_minima=None, origem='arquivo', pai=-1, gen=0, comportamento=None, versao_sondas=0):
        if self.cheio:
            self.recusadas += 1
            return -3
        m = len(rede)
        arr = np.asarray(rede, np.uint8).reshape(m, 2) if m else np.zeros((0, 2), np.uint8)
        ch = _chave(arr, total)
        self.vistas += 1
        if ch in self.chaves:
            self.repetidas += 1
            self.ultima_foi_nova = False
            ident = self.chaves[ch]
            self.atualizar(ident, retirada_minima, comportamento, versao_sondas)
            return ident
        self.ultima_foi_nova = True
        self._abrir_linha()
        k = self.N
        need = self._usado + 2 * m
        if need > len(self._buf):
            self._buf = _crescer(self._buf, max(need, 2 * len(self._buf)))
        if m:
            self._buf[self._usado:need] = arr.reshape(-1)
        self.off[k], self.m[k], self.total[k], self.falhas[k] = (self._usado, m, int(total), int(falhas))
        self._usado = need
        self.retirada[k] = -1 if retirada_minima is None else int(retirada_minima)
        self.origem[k] = ORIGENS.index(origem) if isinstance(origem, str) else int(origem)
        self.pai[k], self.gen[k] = (int(pai), int(gen))
        if comportamento is not None:
            self.comp_lo[k], self.comp_hi[k] = _dividir(comportamento)
            self.sv[k] = int(versao_sondas)
        else:
            self.comp_lo[k], self.comp_hi[k], self.sv[k] = (0, 0, 0)
        self.chaves[ch] = k
        self.N += 1
        return k

    def atualizar(self, ident, retirada_minima=None, comportamento=None, versao_sondas=0):
        k = int(ident)
        mudou = False
        if retirada_minima is not None and self.retirada[k] < 0:
            self.retirada[k] = int(retirada_minima)
            mudou = True
        if comportamento is not None and self.sv[k] != versao_sondas:
            self.comp_lo[k], self.comp_hi[k] = _dividir(comportamento)
            self.sv[k] = int(versao_sondas)
            mudou = True
        if mudou and k < self._salvas:
            self._sujas.add(k)

    def foto(self, ident):
        k = int(ident)
        o, m = (int(self.off[k]), int(self.m[k]))
        return [(int(self._buf[o + 2 * t]), int(self._buf[o + 2 * t + 1])) for t in range(m)]

    def comportamento(self, ident):
        k = int(ident)
        return (_juntar(self.comp_lo[k], self.comp_hi[k]), int(self.sv[k]))

    def distancias(self, recorde=None):
        r = self.recorde if recorde is None else recorde
        d = np.full(self.N, -1, np.int64)
        if r is None:
            return d
        tot, f, ret = (self.total[:self.N], self.falhas[:self.N], self.retirada[:self.N])
        menor = tot < r
        d[menor] = f[menor]
        igual = (tot == r) & (f == 0) & (ret >= 0)
        d[igual] = ret[igual]
        return d

    def classes(self, recorde=None):
        d = self.distancias(recorde)
        c = np.full(self.N, len(CLASSES) - 1, np.int64)
        ok = d >= 0
        c[ok] = len(CLASSES) - 2
        for k in range(len(LIMITES_DE_CLASSE) - 1, -1, -1):
            c[ok & (d <= LIMITES_DE_CLASSE[k])] = k
        return c

    def melhores(self, k, recorde=None):
        d = self.distancias(recorde)
        ok = np.flatnonzero(d >= 0)
        if len(ok) == 0:
            return []
        return [int(i) for i in ok[np.lexsort((self.g.random(len(ok)), d[ok]))][:k]]

    def com_comportamento(self, versao):
        return int((self.sv[:self.N] == int(versao)).sum())

    def resumo(self, recorde=None):
        cls = self.classes(recorde)
        d = self.distancias(recorde)
        por_classe = {CLASSES[k]: int((cls == k).sum()) for k in range(len(CLASSES))}
        og = self.origem[:self.N]
        por_origem = {ORIGENS[k]: int((og == k).sum()) for k in range(len(ORIGENS)) if (og == k).any()}
        com = d[d >= 0]
        return {'fotos': int(self.N), 'vistas': int(self.vistas), 'repetidas': int(self.repetidas), 'liberadas': 0, 'recusadas_por_falta_de_espaco': int(self.recusadas), 'cheio': bool(self.cheio), 'por_classe': por_classe, 'por_origem': por_origem, 'menor_distancia': int(com.min()) if len(com) else None, 'fotos_na_menor_distancia': int((com == com.min()).sum()) if len(com) else 0, 'bytes_de_bits': int(self._usado * 8 // 2 * 2 // 2)}

    def salvar(self, pasta):
        os.makedirs(pasta, exist_ok=True)
        if _espaco_livre(pasta) < ESPACO_MINIMO:
            self.cheio = True
            return False
        a, b = (self._salvas, self.N)
        if b == a and (not self._sujas):
            return True
        o0, o1 = (int(self.off[a]) if a < b else self._usado, self._usado)
        sujas = np.array(sorted(self._sujas), np.int64)
        nome = os.path.join(pasta, f'fotos_{self._pedacos:05d}.npz')
        tmp = nome + '.tmp.npz'
        np.savez_compressed(tmp, buf=self._buf[o0:o1], off=self.off[a:b] - o0, m=self.m[a:b], total=self.total[a:b], falhas=self.falhas[a:b], retirada=self.retirada[a:b], origem=self.origem[a:b], pai=self.pai[a:b], gen=self.gen[a:b], comp_lo=self.comp_lo[a:b], comp_hi=self.comp_hi[a:b], sv=self.sv[a:b], primeira=np.asarray([a]), upd_ids=sujas, upd_ret=self.retirada[sujas], upd_lo=self.comp_lo[sujas], upd_hi=self.comp_hi[sujas], upd_sv=self.sv[sujas], vistas=np.asarray([self.vistas]), repetidas=np.asarray([self.repetidas]), recorde=np.asarray([-1 if self.recorde is None else self.recorde]))
        os.replace(tmp, nome)
        self._pedacos += 1
        self._salvas = b
        self._sujas = set()
        return True

    @classmethod
    def carregar(cls, pasta, semente=0, recorde=None):
        f = cls(semente=semente, recorde=recorde)
        if not pasta or not os.path.isdir(pasta):
            return f
        arquivos = sorted((x for x in glob.glob(os.path.join(pasta, 'fotos_*.npz')) if not x.endswith('.tmp.npz')))
        for nome in arquivos:
            try:
                z = np.load(nome)
                a = int(z['primeira'][0])
                if a != f.N:
                    break
                nn = len(z['m'])
                while f.N + nn > f._cap:
                    f._abrir_linha_cap()
                base = f._usado
                buf = z['buf']
                need = base + len(buf)
                if need > len(f._buf):
                    f._buf = _crescer(f._buf, max(need, 2 * len(f._buf)))
                f._buf[base:need] = buf
                s = slice(f.N, f.N + nn)
                f.off[s] = z['off'] + base
                for nome_c in ('m', 'total', 'falhas', 'retirada', 'origem', 'pai', 'gen', 'comp_lo', 'comp_hi', 'sv'):
                    getattr(f, nome_c)[s] = z[nome_c]
                f._usado = need
                f.N += nn
                ids = z['upd_ids']
                if len(ids):
                    f.retirada[ids], f.comp_lo[ids], f.comp_hi[ids], f.sv[ids] = (z['upd_ret'], z['upd_lo'], z['upd_hi'], z['upd_sv'])
                f.vistas, f.repetidas = (int(z['vistas'][0]), int(z['repetidas'][0]))
                if recorde is None and int(z['recorde'][0]) >= 0:
                    f.recorde = int(z['recorde'][0])
                f._pedacos += 1
            except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
                break
        for k in range(f.N):
            arr = f._buf[int(f.off[k]):int(f.off[k]) + 2 * int(f.m[k])].reshape(-1, 2)
            f.chaves[_chave(arr, f.total[k])] = k
        f._salvas = f.N
        return f

    def _abrir_linha_cap(self):
        cap = self._cap * 2
        for nome, pad in (('m', 0), ('off', 0), ('total', 0), ('falhas', 0), ('retirada', -1), ('origem', 0), ('pai', -1), ('gen', 0), ('comp_lo', 0), ('comp_hi', 0), ('sv', 0)):
            setattr(self, nome, _crescer(getattr(self, nome), cap, pad))
        self._cap = cap

class Edicoes:
    CAMPOS = (('foto', np.int64), ('tipo', np.uint8), ('p', np.int32), ('k', np.uint8), ('seq', np.int64), ('q2', np.int32), ('passo', np.uint8), ('falhas', np.int32), ('comp_lo', np.uint64), ('comp_hi', np.uint64), ('braco', np.uint8), ('gen', np.int32))

    def __init__(self):
        self._cap = 8192
        for nome, dt in self.CAMPOS:
            setattr(self, '_' + nome, np.zeros(self._cap, dt))
        self.N = 0
        self._salvas = 0
        self._pedacos = 0
        self.total_em_disco = 0
        self.cheio = False

    def __len__(self):
        return self.N + self.total_em_disco

    def adicionar(self, foto, tipo, p, k, seq, q2, passo, falhas, comportamento, braco, gen):
        if self.cheio:
            return False
        if self.N >= self._cap:
            cap = self._cap * 2
            for nome, dt in self.CAMPOS:
                setattr(self, '_' + nome, _crescer(getattr(self, '_' + nome), cap))
            self._cap = cap
        i = self.N
        lo, hi = _dividir(comportamento or 0)
        self._foto[i], self._tipo[i], self._p[i], self._k[i], self._seq[i], self._q2[i], self._passo[i], self._falhas[i] = (foto, tipo, p, k, seq, q2, passo, falhas)
        self._comp_lo[i], self._comp_hi[i], self._braco[i], self._gen[i] = (lo, hi, braco, gen)
        self.N += 1
        return True

    def coluna(self, nome):
        return getattr(self, '_' + nome)[:self.N]

    def salvar(self, pasta):
        os.makedirs(pasta, exist_ok=True)
        if _espaco_livre(pasta) < ESPACO_MINIMO:
            self.cheio = True
            return False
        if self.N == 0:
            return True
        nome = os.path.join(pasta, f'edicoes_{self._numero_inicial(pasta):05d}.npz')
        tmp = nome + '.tmp.npz'
        np.savez_compressed(tmp, **{n_: getattr(self, '_' + n_)[:self.N] for n_, _ in self.CAMPOS})
        os.replace(tmp, nome)
        self._pedacos += 1
        self.total_em_disco += self.N
        self.N = 0
        return True

    @staticmethod
    def _numero_inicial(pasta):
        existentes = [x for x in glob.glob(os.path.join(pasta, 'edicoes_*.npz')) if not x.endswith('.tmp.npz')]
        return len(existentes)

    @staticmethod
    def contar(pasta):
        total = 0
        for nome in sorted(glob.glob(os.path.join(pasta, 'edicoes_*.npz'))):
            if nome.endswith('.tmp.npz'):
                continue
            try:
                total += len(np.load(nome)['foto'])
            except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
                continue
        return total

    @staticmethod
    def ler(pasta):
        for nome in sorted(glob.glob(os.path.join(pasta, 'edicoes_*.npz'))):
            if nome.endswith('.tmp.npz'):
                continue
            try:
                z = np.load(nome)
                yield {n_: z[n_] for n_, _ in Edicoes.CAMPOS}
            except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
                continue

    @classmethod
    def carregar(cls, pasta):
        e = cls()
        if pasta and os.path.isdir(pasta):
            e.total_em_disco = cls.contar(pasta)
            e._pedacos = 0
        return e
