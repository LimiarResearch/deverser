# -*- coding: utf-8 -*-
import glob
import hashlib
import json
import os
import shutil
import time
import numpy as np
VERSAO_DO_ELO = 1
MAX_CORPOS = 32
TIPOS = ('gene', 'bits', 'presenca', 'janela', 'operador', 'biblioteca', 'unidade', 'unidades', 'motivo', 'doador')

def _sha(caminho):
    h = hashlib.sha256()
    with open(caminho, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def _json(caminho, padrao=None):
    try:
        return json.load(open(caminho, encoding='utf-8'))
    except (OSError, ValueError):
        return padrao

def _gravar(caminho, obj):
    tmp = caminho + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, caminho)

def _colunas(pasta, prefixo, colunas):
    partes = sorted((x for x in glob.glob(os.path.join(pasta, f'{prefixo}_*.npz')) if not x.endswith('.tmp.npz')))
    if not partes:
        return {c: np.zeros(0) for c in colunas}
    zs = [np.load(p) for p in partes]
    return {c: np.concatenate([z[c] for z in zs]) for c in colunas if c in zs[0].files}

def _violacoes(problema, valores):
    v = np.asarray(valores, np.float64)
    out = np.ones_like(v)
    for c in range(v.shape[1]):
        out[:, c] = np.minimum(np.asarray(problema.violacoes_de_coluna(c, v[:, c]), np.float64), 1.0)
    out[~np.isfinite(out)] = 1.0
    return out

def _efeito_das_edicoes(F, E, n_clausulas, bits_por_campo, problema):
    if len(E.get('foto', [])) == 0:
        return []
    pai, filho = (E['foto'].astype(np.int64), E['q2'].astype(np.int64))
    n = len(F['distancia'])
    ok = (pai >= 0) & (filho >= 0) & (pai < n) & (filho < n)
    ok &= (F['estado'][np.clip(pai, 0, n - 1)] == 0) & (F['estado'][np.clip(filho, 0, n - 1)] == 0)
    pai, filho, tipo, pos = (pai[ok], filho[ok], E['tipo'][ok].astype(np.int64), E['p'][ok].astype(np.int64))
    if len(pai) == 0:
        return []
    dv = _violacoes(problema, F['valores'][filho]) - _violacoes(problema, F['valores'][pai])
    campo = pos // max(1, int(bits_por_campo))
    out = []
    for t in np.unique(tipo):
        for c_ in np.unique(campo[tipo == t]):
            m = (tipo == t) & (campo == c_)
            d = dv[m]
            out.append({'tipo': TIPOS[t] if t < len(TIPOS) else int(t), 'campo': int(c_), 'edicoes': int(m.sum()), 'media_por_clausula': [round(float(x), 5) for x in d.mean(0)[:n_clausulas]], 'aproximaram': [int(x) for x in (d < -1e-09).sum(0)[:n_clausulas]], 'afastaram': [int(x) for x in (d > 1e-09).sum(0)[:n_clausulas]]})
    return out

def _corpos_bons(F, n_clausulas, problema, n_bits, k_por_clausula=2, clausulas_primeiro=()):
    ok = np.flatnonzero(F['estado'] == 0)
    if len(ok) == 0:
        return []
    d = F['distancia'][ok]
    v = _violacoes(problema, F['valores'][ok])
    chave = lambda i: (int(F['distancia'][i]),) + tuple(np.round(F['valores'][i], 6))
    escolhidos = [int(ok[np.argmin(d)])]
    vistos = {chave(escolhidos[0])}
    for c in list(clausulas_primeiro) + [c for c in range(n_clausulas) if c not in set(clausulas_primeiro)]:
        postos = 0
        for i in ok[np.lexsort((d, v[:, c]))]:
            if chave(i) in vistos:
                continue
            vistos.add(chave(i))
            escolhidos.append(int(i))
            postos += 1
            if postos >= k_por_clausula:
                break
        if len(escolhidos) >= MAX_CORPOS:
            break
    return [{'id': i, 'bits': (np.unpackbits(F['bits'][i])[:int(n_bits)] if F['bits'].dtype == np.uint8 else F['bits'][i]).tolist(), 'distancia': int(F['distancia'][i]), 'valores': [round(float(x), 6) for x in F['valores'][i]]} for i in escolhidos[:MAX_CORPOS]]

def gravar(pasta_da_corrida, problema, destino, rotulo, familia=None, clausulas_primeiro=()):
    p = pasta_da_corrida
    est = _json(os.path.join(p, 'estado.json'), {})
    dec = _json(os.path.join(p, 'declaracao.json'), {}) or _json(os.path.join(p, 'declaracao_parcial.json'), {})
    F = _colunas(os.path.join(p, 'fotos'), 'fotos', ('bits', 'distancia', 'estado', 'valores', 'origem', 'pai', 'gen'))
    E = _colunas(os.path.join(p, 'edicoes'), 'edicoes', ('foto', 'tipo', 'p', 'k', 'q2', 'braco', 'gen'))
    cod = problema.codificacao
    nc = int(problema.n_clausulas)
    bits_por_campo = int(getattr(cod, 'n_bits', 0) // max(1, getattr(cod, 'n_campos', 1)))
    os.makedirs(destino, exist_ok=True)
    ok = np.flatnonzero(F['estado'] == 0) if len(F['estado']) else np.zeros(0, np.int64)
    melhor = int(ok[np.argmin(F['distancia'][ok])]) if len(ok) else None
    elo = {'versao_do_elo': VERSAO_DO_ELO, 'rotulo': rotulo, 'familia': familia, 'gravado_em': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'a_intencao_e_o_juiz': {'D': problema.nome, 'clausulas': [list(map(str, c)) for c in problema.clausulas], 'n_clausulas': nc, 'hash_de_V': problema.hash_de_v() if getattr(problema, 'hash_de_v', None) else None, 'codificacao': {'classe': type(cod).__name__, 'n_bits': int(cod.n_bits), 'n_campos': int(getattr(cod, 'n_campos', 0)), 'bits_por_campo': bits_por_campo, 'n': getattr(cod, 'n', None), 'm': getattr(cod, 'm', None)}, 'config': dec.get('config') if isinstance(dec, dict) else None, 'conta_de_V': est.get('contadores', {}).get('avaliacoes_de_V')}, 'o_resultado': {'parada': dec.get('parada') if isinstance(dec, dict) else None, 'fotos_medidas': int(len(F['distancia'])), 'melhor_distancia': int(F['distancia'][melhor]) if melhor is not None else None, 'cumpriu_D': bool(melhor is not None and int(F['distancia'][melhor]) == 0), 'curva_da_melhor': est.get('curva_da_melhor', [])[-200:] if isinstance(est.get('curva_da_melhor'), list) else None}, 'o_que_deu_certo_e_errado': {'credito_por_braco': est.get('braco'), 'efeito_das_edicoes': _efeito_das_edicoes(F, E, nc, bits_por_campo, problema)}, 'o_que_o_aprendiz_aprendeu': _json(os.path.join(p, 'padroes.json'), None), 'corpos_bons': _corpos_bons(F, nc, problema, int(cod.n_bits), clausulas_primeiro=tuple((int(c) for c in clausulas_primeiro))), 'o_que_fica_de_fora': 'o arquivo de fotos, a memória de edições, as piscinas e os logs (a corrida fica onde está)'}
    _gravar(os.path.join(destino, 'elo.json'), elo)
    ae = _json(os.path.join(p, 'aprendiz_estado.json'), None)
    if ae is not None and os.path.exists(os.path.join(p, 'aprendiz_conjunto.npz')):
        shutil.copyfile(os.path.join(p, 'aprendiz_conjunto.npz'), os.path.join(destino, 'pesos.npz'))
        _gravar(os.path.join(destino, 'aprendiz.json'), {k: ae.get(k) for k in ('cfgs', 'config_de_escrita', 'peso_semantico', 'reducao', 'treinos')})
    if os.path.exists(os.path.join(p, 'aprendiz_biblioteca.npz')):
        shutil.copyfile(os.path.join(p, 'aprendiz_biblioteca.npz'), os.path.join(destino, 'biblioteca.npz'))
    selar(destino)
    return destino

def selar(pasta):
    arquivos = sorted((f for f in os.listdir(pasta) if f != 'selo.json' and (not f.endswith('.tmp'))))
    hs = {f: _sha(os.path.join(pasta, f)) for f in arquivos}
    _gravar(os.path.join(pasta, 'selo.json'), {'arquivos': hs, 'conjunto': hashlib.sha256(json.dumps(hs, sort_keys=True).encode()).hexdigest()})

def carregar(pasta):
    selo = _json(os.path.join(pasta, 'selo.json'), None)
    if selo is None:
        raise ValueError(f'elo sem selo: {pasta}')
    for f, h in selo['arquivos'].items():
        if _sha(os.path.join(pasta, f)) != h:
            raise ValueError(f'o elo {pasta} foi mexido depois do selo: {f}')
    elo = _json(os.path.join(pasta, 'elo.json'))
    elo['_pasta'], elo['_selo'] = (pasta, selo['conjunto'])
    if os.path.exists(os.path.join(pasta, 'pesos.npz')):
        z = np.load(os.path.join(pasta, 'pesos.npz'))
        elo['_pesos'] = {k: z[k] for k in z.files}
        elo['_aprendiz'] = _json(os.path.join(pasta, 'aprendiz.json'), {})
    return elo

def transplantar(aprendiz, elo):
    if '_pesos' not in elo:
        return {'grau_C': 'o elo não tem pesos'}
    rel = {'inteiros': 0, 'em_bloco': 0, 'ficaram': 0, 'por_tensor': {}}
    for i, m in enumerate(aprendiz.rede.membros):
        for k, w in m.W.items():
            chave = f'm{i}__{k}'
            if chave not in elo['_pesos']:
                rel['ficaram'] += 1
                rel['por_tensor'].setdefault(k, 'ficou')
                continue
            v = elo['_pesos'][chave]
            if v.shape == w.shape:
                m.W[k] = v.astype(w.dtype).copy()
                rel['inteiros'] += 1
                rel['por_tensor'].setdefault(k, 'inteiro')
            elif v.ndim == w.ndim:
                sl = tuple((slice(0, min(a, b)) for a, b in zip(v.shape, w.shape)))
                novo = w.copy()
                novo[sl] = v[sl].astype(w.dtype)
                m.W[k] = novo
                rel['em_bloco'] += 1
                rel['por_tensor'].setdefault(k, f'bloco {tuple((min(a, b) for a, b in zip(v.shape, w.shape)))} de {w.shape}')
            else:
                rel['ficaram'] += 1
                rel['por_tensor'].setdefault(k, 'ficou')
        m._zerar_adam()
    return rel

def corpos_para(elo, cod):
    out = []
    c0 = elo['a_intencao_e_o_juiz']['codificacao']
    for cp in elo.get('corpos_bons', []):
        b = np.asarray(cp['bits'], np.uint8)
        if c0.get('n') is not None and hasattr(cod, 'n') and hasattr(cod, 'codificar') and (c0['classe'] == type(cod).__name__):
            from experimentos import codificacoes_existentes as CE
            velha = CE.CodificacaoDeOrdenacao(int(c0['n']), int(c0['m']))
            rede = velha.decodificar(b[:velha.n_bits])
            if rede is None:
                continue
            rede = [(i, j) for i, j in rede if max(i, j) < cod.n][:cod.m]
            while len(rede) < cod.m:
                rede.append(rede[-1] if rede else (0, 1))
            try:
                nb = cod.canonizar(cod.codificar(rede))
            except Exception:
                continue
            if nb is not None:
                out.append(np.asarray(nb, np.uint8))
        elif len(b) == int(cod.n_bits):
            out.append(b)
    return out
