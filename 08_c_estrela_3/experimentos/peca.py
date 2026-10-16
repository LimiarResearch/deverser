# -*- coding: utf-8 -*-
import numpy as np
from experimentos import escritor_de_fotos as EF

def mutar_como_a_evo(cod, bits, g):
    for _ in range(8):
        if g.random() < 0.5:
            f, tipo = (cod.mutar(bits, g), 'operador')
        else:
            at = np.flatnonzero(np.asarray(cod.ativos(bits), bool))
            if len(at) == 0:
                return (None, None)
            b = np.array(bits, np.uint8, copy=True)
            b[g.choice(at, min(len(at), 1 + int(g.integers(0, 3))), replace=False)] ^= 1
            f, tipo = (cod.canonizar(b), 'bits')
        if f is not None and (not np.array_equal(f, bits)):
            return (f, tipo)
    return (None, None)

class _PorTorneio:

    def _populacao(self, corrida):
        F = corrida.fotos
        N = len(F)
        ids = np.arange(max(0, N - self.populacao), N, dtype=np.int64)
        d = F.distancias()[ids]
        mascara = np.asarray(corrida._mascara_de_pais(), bool)
        ids = ids[(d >= 0) & ~mascara[ids]]
        return (ids, np.asarray(corrida._chave_de_nivel(ids), np.int64) if len(ids) else None)

    def _pai(self, ids, chave, g):
        amostra = g.choice(len(ids), min(self.torneio, len(ids)), replace=False)
        desempate = g.random(len(amostra))
        t = min(range(len(amostra)), key=lambda i: (int(chave[amostra[i]]), float(desempate[i])))
        return int(ids[amostra[t]])

class GeradorModulo(_PorTorneio):
    nome = 'modulo'

    def __init__(self, populacao=64, torneio=8, modo='religado'):
        self.populacao = int(populacao)
        self.torneio = int(torneio)
        self.modo = modo

    def propor(self, corrida, n, g):
        cod = corrida.cod
        from experimentos import l_ser_lang as L
        if not isinstance(cod, L.CodificacaoDoSer) or n <= 0 or len(corrida.fotos) == 0:
            return []
        from experimentos import modulo_do_ser as MS
        ids, chave = self._populacao(corrida)
        if not len(ids):
            return []
        out, ja = ([], set())
        for _ in range(8 * n):
            if len(out) >= n:
                break
            pai_id = self._pai(ids, chave, g)
            pai_bits = corrida.fotos.foto(pai_id)
            filho, _info = MS.editar_modulo(pai_bits, g, self.modo, corrida.fotos.foto(self._pai(ids, chave, g)) if self.modo == 'transplante' else None)
            if filho is None:
                continue
            ch = cod.chave(filho)
            if ch in ja:
                continue
            ja.add(ch)
            dif = np.flatnonzero(np.asarray(filho) != np.asarray(pai_bits))
            p, fim = (int(dif.min()), int(dif.max()) + 1)
            k = fim - p
            out.append((pai_id, EF.Candidato('unidades', p, k if k <= EF.KMAX else 0, EF._janela(filho, p, k) if k <= EF.KMAX else 0, filho, 'modulo')))
        return out

class GeradorEvo:
    nome = 'evo'

    def __init__(self, populacao=64, torneio=8):
        self.populacao = int(populacao)
        self.torneio = int(torneio)

    def propor(self, corrida, n, g):
        F = corrida.fotos
        N = len(F)
        if N == 0 or n <= 0:
            return []
        cod = corrida.cod
        ids = np.arange(max(0, N - self.populacao), N, dtype=np.int64)
        d = F.distancias()[ids]
        mascara = np.asarray(corrida._mascara_de_pais(), bool)
        ids = ids[(d >= 0) & ~mascara[ids]]
        if len(ids) == 0:
            return []
        chave = np.asarray(corrida._chave_de_nivel(ids), np.int64)
        out, ja = ([], set())
        for _ in range(8 * n):
            if len(out) >= n:
                break
            amostra = g.choice(len(ids), min(self.torneio, len(ids)), replace=False)
            desempate = g.random(len(amostra))
            t = min(range(len(amostra)), key=lambda i: (int(chave[amostra[i]]), float(desempate[i])))
            pai_id = int(ids[amostra[t]])
            pai_bits = F.foto(pai_id)
            filho, tipo = mutar_como_a_evo(cod, pai_bits, g)
            if filho is None:
                continue
            ch = cod.chave(filho)
            if ch in ja:
                continue
            ja.add(ch)
            dif = np.flatnonzero(np.asarray(filho) != np.asarray(pai_bits))
            p, fim = (int(dif.min()), int(dif.max()) + 1)
            k = fim - p
            out.append((pai_id, EF.Candidato(tipo, p, k if k <= EF.KMAX else 0, EF._janela(filho, p, k) if k <= EF.KMAX else 0, filho, 'evo')))
        return out
