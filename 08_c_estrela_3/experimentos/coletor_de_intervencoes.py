# -*- coding: utf-8 -*-
import base64
import json
import os
import time
import numpy as np
from experimentos import compositor_de_corpus as CC
from experimentos import l_ser_lang as L
FINALIDADE = 'coletor de intervenções (sombra)'
VARIANTES = ('P', 'A', 'B', 'AB', 'ABR')
TOPO = 64
REUSO = 1 / 3
USADOS_MAX = 512
TENTATIVAS = 40

def _empacotar(bits):
    return base64.b64encode(np.packbits(np.asarray(bits, np.uint8)).tobytes()).decode('ascii')

def desempacotar(texto, n_bits=None):
    b = np.unpackbits(np.frombuffer(base64.b64decode(texto), np.uint8))
    return b[:n_bits or L.CODIFICACAO.n_bits]

def _secoes_vivas(p):
    return [s for s, nos in p.secoes.items() if nos is not None]

def _fragmentos(p, secao):
    tipo = L.TIPO_DA_SECAO[secao]
    _root, sub = CC.extrair(p.secoes[secao], tipo)
    return list(dict.fromkeys(sub.values()))

def _disjuntos(a, b):
    n = min(len(a), len(b))
    return tuple(a[:n]) != tuple(b[:n])

def _reparo_cego(e, caminho, g):
    no = CC.no_em(e, caminho)
    if isinstance(no, str):
        return None
    op_antiga = L.OP_DE[no.op]
    cands = [L.NOME_DA_OP[o] for o in range(len(L.NOME_DA_OP)) if o != op_antiga and L.ARIDADE[o] == L.ARIDADE[op_antiga] and (L.USA_C[o] == L.USA_C[op_antiga])]
    if not cands:
        return None
    nova = cands[int(g.integers(len(cands)))]
    return (CC.enxertar(e, caminho, CC.Expr(nova, no.args, no.q)), no.op, nova)

class Coletor:

    def __init__(self, corrida, fracao, vidas=3):
        self.c = corrida
        self.fracao = float(fracao)
        self.vidas = int(vidas)
        self.g = np.random.default_rng(int(corrida.cfg.semente) * 104729 + 17)
        self.caminho = os.path.join(corrida.saida, 'intervencoes.jsonl')
        self.usados = []

    def devido(self):
        ct = self.c.contadores
        gasto = int(ct.get('avaliacoes_do_coletor', 0))
        busca = int(ct['avaliacoes_de_V']) - gasto
        return self.fracao > 0 and gasto < self.fracao / (1.0 - self.fracao) * busca

    def _doador(self, livres, excluir):
        if self.g.random() < 0.5:
            d = self.c.fotos.distancias()
            ok = [int(k) for k in livres if int(k) not in excluir and d[int(k)] >= 0]
            ok.sort(key=lambda k: d[k])
            pool, esquema = (ok[:TOPO], 'topo')
        else:
            pool, esquema = ([int(k) for k in livres if int(k) not in excluir], 'acaso')
        if not pool:
            return (None, esquema, 0)
        return (int(pool[int(self.g.integers(len(pool)))]), esquema, len(pool))

    def montar(self, pai_id):
        f = self.c.fotos
        pai_bits = np.asarray(f.foto(int(pai_id)), np.uint8)
        pai = L.decodificar_bits(pai_bits)
        livres = [int(k) for k in self.c._livres()]
        descartes = {'mais_de_8_nos_ou_tipo': 0, 'nao_muda': 0, 'sem_fragmento': 0}
        for _ in range(TENTATIVAS):
            reusaveis = [u for u in self.usados if pai.secoes.get(u[0]) is not None and u[2] != int(pai_id)]
            reuso = None
            if reusaveis and self.g.random() < REUSO:
                reuso = reusaveis[int(self.g.integers(len(reusaveis)))]
                sa, fa_reuso, da, esq_a, n_a = (reuso[0], reuso[1], int(reuso[2]), 'reuso', len(reusaveis))
            else:
                da, esq_a, n_a = self._doador(livres, {int(pai_id)})
            db, esq_b, n_b = self._doador(livres, {int(pai_id), da})
            if da is None or db is None:
                return (None, 'sem doadores')
            pa, pb = (L.decodificar_bits(f.foto(da)), L.decodificar_bits(f.foto(db)))
            if reuso is None:
                secoes_a = [s for s in _secoes_vivas(pai) if pa.secoes.get(s) is not None]
                if not secoes_a:
                    descartes['sem_fragmento'] += 1
                    continue
                sa = secoes_a[int(self.g.integers(len(secoes_a)))]
            secoes_b = [s for s in _secoes_vivas(pai) if pb.secoes.get(s) is not None]
            if not secoes_b:
                descartes['sem_fragmento'] += 1
                continue
            sb = secoes_b[int(self.g.integers(len(secoes_b)))]
            fr_b = _fragmentos(pb, sb)
            if reuso is None:
                fr_a = _fragmentos(pa, sa)
                fa = fr_a[int(self.g.integers(len(fr_a)))]
            else:
                fa = fa_reuso
            fb = fr_b[int(self.g.integers(len(fr_b)))]
            raiz = {s: CC.extrair(pai.secoes[s], L.TIPO_DA_SECAO[s])[0] for s in {sa, sb}}
            cam_a = list(CC.caminhos(raiz[sa]))
            ca = cam_a[int(self.g.integers(len(cam_a)))]
            if sb == sa:
                cam_b = [c for c in CC.caminhos(raiz[sb]) if _disjuntos(c, ca)]
                if not cam_b:
                    descartes['sem_fragmento'] += 1
                    continue
            else:
                cam_b = list(CC.caminhos(raiz[sb]))
            cb = cam_b[int(self.g.integers(len(cam_b)))]
            try:
                e_a = CC.enxertar(raiz[sa], ca, fa)
                e_b = CC.enxertar(raiz[sb], cb, fb)
                bits_a = CC.reencadernar(pai_bits, sa, e_a)
                bits_b = CC.reencadernar(pai_bits, sb, e_b)
                if sb == sa:
                    e_ab = CC.enxertar(e_a, cb, fb)
                    bits_ab = CC.reencadernar(pai_bits, sa, e_ab)
                else:
                    e_ab = e_a
                    bits_ab = CC.reencadernar(bits_a, sb, e_b)
            except ValueError:
                descartes['mais_de_8_nos_ou_tipo'] += 1
                continue
            if np.array_equal(bits_a, pai_bits) or np.array_equal(bits_b, pai_bits) or np.array_equal(bits_ab, bits_a) or np.array_equal(bits_ab, bits_b):
                descartes['nao_muda'] += 1
                continue
            alvo = (sa, tuple(ca[:-1]), e_ab) if ca else (sb, tuple(cb[:-1]), e_ab if sb == sa else e_b) if cb else None
            reparo, bits_r = (None, None)
            if alvo is not None:
                alvo_s, alvo_c, e_base = alvo
                for _t in range(6):
                    r = _reparo_cego(e_base, alvo_c, self.g)
                    if r is None:
                        break
                    try:
                        bits_r = CC.reencadernar(bits_ab, alvo_s, r[0])
                    except ValueError:
                        continue
                    if not np.array_equal(bits_r, bits_ab):
                        reparo = {'secao': alvo_s, 'caminho': list(alvo_c), 'op_antes': r[1], 'op_depois': r[2]}
                        break
                    bits_r = None
            desc = {'pai': int(pai_id), 'doadores': [da, db], 'esquema_dos_doadores': [esq_a, esq_b], 'tamanho_do_sorteio': [n_a, n_b], 'A': {'secao': sa, 'caminho': list(ca), 'nos': CC.numero_nos(fa), 'expressao': str(fa)[:400]}, 'B': {'secao': sb, 'caminho': list(cb), 'nos': CC.numero_nos(fb), 'expressao': str(fb)[:400]}, 'reparo': reparo, 'descartes': descartes, 'reuso_de_A': None if reuso is None else {'grupo_de_origem': int(reuso[3])}}
            self._frags_do_grupo = [(sa, fa, da), (sb, fb, db)]
            variantes = {'P': pai_bits, 'A': bits_a, 'B': bits_b, 'AB': bits_ab}
            if bits_r is not None:
                variantes['ABR'] = bits_r
            return (variantes, desc)
        return (None, f'nenhuma montagem em {TENTATIVAS} tentativas: {descartes}')

    def coletar(self, pai_id):
        variantes, desc = self.montar(pai_id)
        n = int(self.c.contadores.get('grupos_do_coletor', 0))
        if variantes is None:
            self.c.contadores['grupos_do_coletor_sem_montagem'] = int(self.c.contadores.get('grupos_do_coletor_sem_montagem', 0)) + 1
            self.c._traco({'tipo': 'coletor', 'grupo': n, 'montado': False, 'motivo': desc})
            return None
        from experimentos import c3_sonda_do_ser as S
        from experimentos import c3_v_da_busca as VB
        av = self.c.avaliador
        sal_do_grupo = int(self.g.integers(1 << 30))
        piscina = tuple(av.piscina)
        vidas = [(int(piscina[i]), int(sp)) for i, sp in VB.escolhas(S.assinatura(variantes['P']), sal_do_grupo, self.vidas, piscina)]
        nomes = [v for v in VARIANTES if v in variantes]
        t0 = time.time()
        res = self.c._pedir_a_V_nas_vidas([variantes[v] for v in nomes], vidas, FINALIDADE)
        medidas = {}
        for v, por_vida in zip(nomes, res):
            medidas[v] = []
            for (s, sp), r in zip(vidas, por_vida):
                ver = self.c.problema.julgar(r)
                medidas[v].append({'semente': int(s), 'semente_pert': int(sp), 'estado': ver['estado'], 'distancia': int(ver['distancia']), 'nfal': int(ver['nfal']), 'valores': [None if not np.isfinite(x) else round(float(x), 6) for x in ver['valores']]})
        d = {v: np.asarray([m['distancia'] for m in medidas[v]], float) for v in nomes}
        inter = d['AB'] - d['A'] - d['B'] + d['P']
        resumo = {'ganho_A': float(np.mean(d['P'] - d['A'])), 'ganho_B': float(np.mean(d['P'] - d['B'])), 'ganho_AB': float(np.mean(d['P'] - d['AB'])), 'interacao': float(np.mean(inter)), 'interacao_ep': float(np.std(inter, ddof=1) / np.sqrt(len(inter))) if len(inter) > 1 else None}
        if 'ABR' in d:
            resumo['ganho_do_reparo'] = float(np.mean(d['AB'] - d['ABR']))
        reg = dict(desc, grupo=n, rodada=int(self.c.rodada_n), geracao=int(self.c.geracao), sal_do_grupo=sal_do_grupo, vidas=[[int(s), int(sp)] for s, sp in vidas], medidas=medidas, resumo=resumo, bits={v: _empacotar(variantes[v]) for v in nomes}, segundos=round(time.time() - t0, 1), t=round(self.c.segundos(), 1))
        with open(self.caminho, 'a', encoding='utf-8', newline='\n') as fh:
            fh.write(json.dumps(reg, ensure_ascii=False) + '\n')
        self.c.contadores['grupos_do_coletor'] = n + 1
        for sec, e, doador in self._frags_do_grupo:
            self.usados.append((sec, e, int(doador), n))
        self.usados = self.usados[-USADOS_MAX:]
        self.c._traco({'tipo': 'coletor', 'grupo': n, 'montado': True, 'pai': int(pai_id), 'doadores': desc['doadores'], 'secoes': [desc['A']['secao'], desc['B']['secao']], 'variantes': nomes, 'd': {v: [int(x) for x in d[v]] for v in nomes}, 'resumo': {k: None if x is None else round(x, 1) for k, x in resumo.items()}})
        return reg
