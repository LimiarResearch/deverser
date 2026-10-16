# -*- coding: utf-8 -*-
import hashlib
import json
import os
import sys
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
VERSAO_DO_BANCO = 1
SEMENTE_DO_BANCO = 424242
VIDAS = {'seq': 4, 'ling': 2, 'age': 2}
GRADE_DOS_AGENTES = 6
CAMINHO_DO_SELO = os.path.join(RAIZ, 'experimentos', 'banco_da_prova_cega_selo.json')
DESCRICAO = {'seq': 'sequências com professor de duas camadas escondidas (16 e 16) e 16 tarefas-base (MundoDeSequenciasFundo)', 'ling': 'linguagem com alfabeto de 8 símbolos e concordância com três posições da janela (MundoDeLinguagemTres)', 'tri': 'as trilhas de composição por k, melhora com o uso, regimes e deriva, de sementes novas', 'age': 'agentes numa grade de 6 por 6 (observação de 41 dimensões)'}

def gerar_banco(semente=SEMENTE_DO_BANCO):
    from experimentos import agentes_do_ser as AG
    from experimentos import trilhas_do_ser as TR
    from experimentos import vidas_do_ser as VS
    return {'seq': VS.gerar_carga(VS.MundoDeSequenciasFundo(), semente, VIDAS['seq']), 'ling': VS.gerar_carga(VS.MundoDeLinguagemTres(), semente + 1, VIDAS['ling']), 'tri': TR.gerar_trilhas(semente + 2), 'age': AG.gerar_carga(semente + 3, VIDAS['age'], lado=GRADE_DOS_AGENTES)}

def _atualizar(h, o):
    if isinstance(o, np.ndarray):
        h.update(b'A' + str(o.dtype).encode() + str(o.shape).encode())
        a = np.ascontiguousarray(o)
        if a.dtype.kind == 'f':
            a = np.round(a.astype(np.float64), 5) + 0.0
        h.update(a.tobytes())
    elif isinstance(o, dict):
        h.update(b'D')
        for k in sorted(o, key=lambda x: str(x)):
            h.update(str(k).encode())
            _atualizar(h, o[k])
    elif isinstance(o, (list, tuple)):
        h.update(b'L' + str(len(o)).encode())
        for x in o:
            _atualizar(h, x)
    elif isinstance(o, np.integer):
        h.update(repr(o.item()).encode())
    elif isinstance(o, (float, np.floating)):
        h.update(repr(round(float(o), 5) + 0.0).encode())
    elif callable(o):
        h.update(b'F')
    else:
        h.update(repr(o).encode())

def hash_da_vida(f):
    h = hashlib.sha256()
    ler = f['abrir']()
    while True:
        ev = ler()
        if ev is None:
            break
        _atualizar(h, list(ev))
    av = f['_avaliacao'].abrir()
    _atualizar(h, {k: v for k, v in av.items() if k != 'registro'})
    return h.hexdigest()

def hashes_do_banco(banco):
    from experimentos import desafio_v_ser as V2
    out = {n: [hash_da_vida(f) for f in banco[n]['fluxos']] for n in V2.FAMILIAS}
    V2._zerar(banco)
    return out

def caminhos_dos_oraculos(semente=SEMENTE_DO_BANCO):
    pasta = os.path.join(RAIZ, 'experimentos')
    return {'seq': os.path.join(pasta, f'oraculo_banco_seq_s{semente}.npz'), 'ling': os.path.join(pasta, f'oraculo_banco_ling_s{semente}.npz'), 'der': os.path.join(pasta, f'oraculo_banco_der_s{semente}.npz')}

def oraculos_do_banco(banco, semente=SEMENTE_DO_BANCO):
    from experimentos import desafio_oraculo as OR
    from experimentos import oraculo_do_ser as OS
    c = caminhos_dos_oraculos(semente)
    out = {'seq': OR.oraculo_das_vidas(banco['seq'], c['seq']), 'ling': OR.oraculo_das_vidas(banco['ling'], c['ling'], **OS.CONFIG_LING)}
    if not os.path.exists(c['der']):
        der = [f for f in banco['tri']['fluxos'] if f['tipo'] == 'der'][0]
        OS.guardar_der(c['der'], OS.oraculo_der_da_vida(der, 0))
    out['der'] = OS.carregar_der(c['der'])
    return out

def _hash_do_arquivo(caminho):
    return hashlib.sha256(open(caminho, 'rb').read()).hexdigest()

def selo_do_banco(banco=None, semente=SEMENTE_DO_BANCO, com_oraculos=True):
    banco = gerar_banco(semente) if banco is None else banco
    s = {'versao': VERSAO_DO_BANCO, 'semente': int(semente), 'variantes': DESCRICAO, 'vidas_por_familia': {**VIDAS, 'tri': len(banco['tri']['fluxos'])}, 'grade_dos_agentes': GRADE_DOS_AGENTES, 'd_entrada': {n: int(banco[n]['d_entrada']) for n in banco}, 'hash_das_vidas': hashes_do_banco(banco), 'declaracao': 'escrito por nós, sem independência; a busca nunca o vê'}
    if com_oraculos:
        oraculos_do_banco(banco, semente)
        s['hash_dos_oraculos'] = {k: _hash_do_arquivo(v) for k, v in caminhos_dos_oraculos(semente).items()}
    s['hash_do_selo'] = hashlib.sha256(json.dumps({k: v for k, v in s.items() if k != 'hash_do_selo'}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return s

def selar(caminho=CAMINHO_DO_SELO, semente=SEMENTE_DO_BANCO):
    s = selo_do_banco(None, semente, com_oraculos=True)
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    json.dump(s, open(caminho, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return s

def ler_selo(caminho=CAMINHO_DO_SELO):
    return json.load(open(caminho, encoding='utf-8')) if os.path.exists(caminho) else None

def conferir_selo(caminho=CAMINHO_DO_SELO):
    gravado = ler_selo(caminho)
    if gravado is None:
        return (False, 'o banco retido da prova cega não está selado (falta o arquivo do selo)')
    agora = selo_do_banco(None, gravado['semente'], com_oraculos=os.path.exists(caminhos_dos_oraculos(gravado['semente'])['seq']))
    for k in ('versao', 'semente', 'vidas_por_familia', 'd_entrada', 'hash_das_vidas'):
        if agora[k] != gravado[k]:
            return (False, f'o banco mudou desde o selo: {k}')
    if 'hash_dos_oraculos' in gravado and agora.get('hash_dos_oraculos') != gravado['hash_dos_oraculos']:
        return (False, 'os oráculos do banco mudaram desde o selo')
    if 'hash_dos_oraculos' in gravado and 'hash_dos_oraculos' not in agora:
        return (False, 'faltam os arquivos de oráculo do banco')
    return (True, 'ok')

def avaliador_da_prova_cega(tempo_max=None, backend='cpp', semente=SEMENTE_DO_BANCO, conferir=True, caminho_do_selo=CAMINHO_DO_SELO):
    from experimentos import desafio_v_ser as V2
    if conferir:
        ok, msg = conferir_selo(caminho_do_selo)
        if not ok:
            raise RuntimeError(f'a prova cega não roda sem o selo conferido: {msg}')
    banco = gerar_banco(semente)
    orac = oraculos_do_banco(banco, semente)
    return V2.AvaliadorReal(semente, V2.TEMPO_MAX_PADRAO if tempo_max is None else tempo_max, backend=backend, familias=banco, orac=orac)
if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('comando', choices=['selar', 'conferir'])
    a = ap.parse_args()
    if a.comando == 'selar':
        s = selar()
        print(json.dumps({'hash_do_selo': s['hash_do_selo'], 'vidas': s['vidas_por_familia']}, ensure_ascii=False))
    else:
        print(conferir_selo())
