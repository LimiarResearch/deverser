# -*- coding: utf-8 -*-
import hashlib
import importlib
import json
import os
import numpy as np
PILARES_DO_SER = ('RETRO', 'W_OCULTA')
ASSINATURA_DO_SER = 'experimentos.mapa_de_assinaturas:assinatura_ativa_do_ser'
ERRO = ('erro_na_vida_de_prova',)

def vida_de_prova(bits, d=16, classes=4, n=600, semente=7, pontos=6):
    from experimentos import l_ser_interp as LI
    from experimentos import l_ser_lang as L
    g = np.random.default_rng(semente)
    W1, W2 = (g.normal(0, 1, (d, classes)), g.normal(0, 1, (d, classes)))
    X = g.normal(0, 1, (n, d)).astype(np.float32)
    Y = np.where(np.arange(n) < n // 2, np.argmax(X @ W1, 1), np.argmax(X @ W2, 1))
    S = g.normal(0, 1, (64, d)).astype(np.float32)
    a = LI.AprendizSer(d, classes, np.random.default_rng(semente), L.decodificar_bits(np.asarray(bits, np.uint8)))
    h = hashlib.sha256()
    passo = max(1, n // pontos)
    with np.errstate(all='ignore'):
        for i in range(n):
            a.aprender(X[i], int(Y[i]))
            if (i + 1) % passo == 0:
                cl, et = a.prever(S)
                for w in a.W:
                    h.update(np.asarray(w, np.float32).tobytes())
                for m in a.mask:
                    h.update(np.asarray(m).tobytes())
                h.update(np.asarray(cl, np.int64).tobytes())
                h.update(np.asarray(et, np.int8).tobytes())
    return h.hexdigest()

def assinatura_ativa_do_ser(bits):
    from experimentos import l_ser_lang as L
    b = np.asarray(bits, np.uint8)
    try:
        _, nos, _, _ = L._analisar(b)
        ref = vida_de_prova(b)
        ativas = []
        for s in L.NOMES_DAS_SECOES:
            if nos[s] is None:
                continue
            x = b.copy()
            x[L._POR_NOME[f'{s}.presente']['inicio']] = 0
            if vida_de_prova(L.canonizar_bits(x)) != ref:
                ativas.append(s)
        return tuple(ativas)
    except Exception:
        return ERRO

def _resolver(nome):
    mod, fn = nome.split(':')
    return getattr(importlib.import_module(mod), fn)

def _calcular(nome, bits):
    os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
    return tuple(_resolver(nome)(bits))

def _chave_dos_bits(bits):
    return hashlib.sha256(np.packbits(np.asarray(bits, np.uint8)).tobytes()).hexdigest()[:32]

class MapaDeAssinaturas:

    def __init__(self, assinatura=ASSINATURA_DO_SER, pilares=PILARES_DO_SER, peso_pilar=4.0, por_assinatura=4, processos=1, pasta=None):
        self.nome = assinatura
        self.fn = _resolver(assinatura)
        self.pilares = tuple(pilares)
        self.peso_pilar = float(peso_pilar)
        self.por_assinatura = max(1, int(por_assinatura))
        self.processos = int(processos)
        self.pasta = pasta
        self.cache = {}
        self.pendentes = {}
        self.elites = {}
        self.de_foto = {}
        self.calculadas = 0
        self._pool = None
        if pasta and os.path.exists(self._caminho()):
            try:
                self.cache = {k: tuple(v) for k, v in json.load(open(self._caminho(), encoding='utf-8')).items()}
            except (OSError, ValueError):
                self.cache = {}

    def _caminho(self):
        return os.path.join(self.pasta, 'assinaturas.json')

    def antecipar(self, lista_de_bits, processos=None):
        n_proc = self.processos if processos is None else int(processos)
        if n_proc <= 0:
            return
        for b in lista_de_bits:
            ch = _chave_dos_bits(b)
            if ch in self.cache or ch in self.pendentes:
                continue
            if self._pool is None:
                import multiprocessing as mp
                from concurrent.futures import ProcessPoolExecutor
                self._pool = ProcessPoolExecutor(n_proc, mp_context=mp.get_context('spawn'))
            self.pendentes[ch] = self._pool.submit(_calcular, self.nome, np.asarray(b, np.uint8).copy())

    def assinatura(self, bits):
        ch = _chave_dos_bits(bits)
        if ch in self.cache:
            return self.cache[ch]
        fut = self.pendentes.pop(ch, None)
        if fut is not None:
            try:
                sig = tuple(fut.result())
            except Exception:
                sig = ERRO
        else:
            sig = tuple(self.fn(np.asarray(bits, np.uint8)))
        self.cache[ch] = sig
        self.calculadas += 1
        return sig

    def entrar(self, ident, bits, chave):
        sig = self.assinatura(bits)
        self.de_foto[int(ident)] = sig
        if sig == ERRO:
            return sig
        lista = self.elites.setdefault(sig, [])
        e = (int(chave), int(ident))
        if len(lista) < self.por_assinatura or e < lista[-1]:
            lista.append(e)
            lista.sort()
            del lista[self.por_assinatura:]
        return sig

    def _melhor_permitida(self, sig, permitido):
        for _, i in self.elites.get(sig, ()):
            if permitido is None or permitido(i):
                return i
        return None

    def _peso(self, sig):
        return self.peso_pilar if any((p in sig for p in self.pilares)) else 1.0

    def sortear_molde(self, g, permitido=None):
        sigs = [s for s in sorted(self.elites) if self._melhor_permitida(s, permitido) is not None]
        if not sigs:
            return None
        w = np.array([self._peso(s) for s in sigs], np.float64)
        s = sigs[int(g.choice(len(sigs), p=w / w.sum()))]
        return (self._melhor_permitida(s, permitido), s)

    def doadoras(self, g, sig_do_molde, n, permitido=None):
        sig_do_molde = tuple(sig_do_molde or ())
        falta = [p for p in self.pilares if p not in sig_do_molde]
        primeiro, depois = ([], [])
        for s in sorted(self.elites):
            if s == sig_do_molde:
                continue
            i = self._melhor_permitida(s, permitido)
            if i is None:
                continue
            (primeiro if any((p in s for p in falta)) else depois).append(i)
        out = []
        for grupo in (primeiro, depois):
            if grupo:
                out += [grupo[int(j)] for j in g.permutation(len(grupo))]
        return out[:int(n)]

    def resumo(self, distancia=None):
        sigs = sorted(self.elites, key=lambda s: self.elites[s][0])
        return {'assinaturas': len(self.elites), 'com_pilar_ativo': sum((1 for s in self.elites if self._peso(s) > 1.0)), 'fotos_no_mapa': len(self.de_foto), 'calculadas': self.calculadas, 'pilares': list(self.pilares), 'elites': [{'assinatura': list(s), 'id': int(self.elites[s][0][1]), 'chave': int(self.elites[s][0][0]), **({'distancia': int(distancia(self.elites[s][0][1]))} if distancia else {})} for s in sigs[:64]]}

    def salvar(self):
        if not self.pasta:
            return
        tmp = self._caminho() + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            json.dump({k: list(v) for k, v in self.cache.items()}, f)
        os.replace(tmp, self._caminho())

    def fechar(self):
        if self._pool is not None:
            self._pool.shutdown(wait=False, cancel_futures=True)
            self._pool = None
